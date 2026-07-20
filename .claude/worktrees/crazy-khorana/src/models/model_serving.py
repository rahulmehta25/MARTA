"""
Model Serving Pipeline for MARTA Demand Forecasting

This module implements production-ready model serving with batch and real-time
inference capabilities, load balancing, caching, and monitoring.
"""
import os
import logging
import json
import asyncio
import pickle
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import numpy as np
import pandas as pd
import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from sklearn.preprocessing import StandardScaler
import joblib
import mlflow
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge
import time
import hashlib
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from src.models.ml_experiment_tracker import get_experiment_tracker

logger = logging.getLogger(__name__)

# Prometheus metrics
PREDICTION_COUNTER = Counter('model_predictions_total', 'Total predictions made', ['model_name', 'status'])
PREDICTION_LATENCY = Histogram('model_prediction_duration_seconds', 'Prediction latency', ['model_name'])
ACTIVE_MODELS = Gauge('active_models_count', 'Number of active models')
CACHE_HITS = Counter('cache_hits_total', 'Cache hits', ['cache_type'])
CACHE_MISSES = Counter('cache_misses_total', 'Cache misses', ['cache_type'])


class PredictionRequest(BaseModel):
    """Request model for predictions."""
    features: Dict[str, float] = Field(..., description="Feature values for prediction")
    model_name: Optional[str] = Field(None, description="Specific model to use")
    return_confidence: bool = Field(False, description="Whether to return confidence scores")
    return_explanation: bool = Field(False, description="Whether to return explanations")


class PredictionResponse(BaseModel):
    """Response model for predictions."""
    prediction: float = Field(..., description="Predicted value")
    model_name: str = Field(..., description="Model used for prediction")
    confidence: Optional[float] = Field(None, description="Confidence score")
    explanation: Optional[Dict[str, Any]] = Field(None, description="Prediction explanation")
    prediction_time: str = Field(..., description="Timestamp of prediction")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class BatchPredictionRequest(BaseModel):
    """Request model for batch predictions."""
    features: List[Dict[str, float]] = Field(..., description="List of feature dictionaries")
    model_name: Optional[str] = Field(None, description="Specific model to use")
    return_confidence: bool = Field(False, description="Whether to return confidence scores")
    batch_id: Optional[str] = Field(None, description="Batch identifier")


class BatchPredictionResponse(BaseModel):
    """Response model for batch predictions."""
    predictions: List[float] = Field(..., description="List of predictions")
    model_name: str = Field(..., description="Model used for predictions")
    confidences: Optional[List[float]] = Field(None, description="Confidence scores")
    batch_id: Optional[str] = Field(None, description="Batch identifier")
    total_samples: int = Field(..., description="Number of samples processed")
    processing_time_ms: float = Field(..., description="Total processing time in milliseconds")


class ModelWrapper:
    """
    Wrapper for ML models with caching, monitoring, and error handling.
    
    Features:
    - Model loading and management
    - Prediction caching
    - Performance monitoring
    - Error handling and fallbacks
    - Feature validation
    """
    
    def __init__(self, 
                 model_name: str,
                 model_path: str,
                 model_type: str = "sklearn",
                 feature_names: List[str] = None,
                 scaler_path: Optional[str] = None):
        """
        Initialize model wrapper.
        
        Args:
            model_name: Name of the model
            model_path: Path to the model file
            model_type: Type of model ('sklearn', 'tensorflow', 'mlflow')
            feature_names: Expected feature names
            scaler_path: Path to feature scaler
        """
        self.model_name = model_name
        self.model_path = model_path
        self.model_type = model_type
        self.feature_names = feature_names or []
        self.scaler_path = scaler_path
        
        self.model = None
        self.scaler = None
        self.is_loaded = False
        self.load_time = None
        self.prediction_count = 0
        self.error_count = 0
        
        # Performance tracking
        self.prediction_times = []
        self.max_history = 1000
        
        logger.info(f"Initialized model wrapper: {model_name}")
    
    def load_model(self) -> None:
        """Load the model and scaler."""
        try:
            start_time = time.time()
            
            if self.model_type == "sklearn":
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
            elif self.model_type == "joblib":
                self.model = joblib.load(self.model_path)
            elif self.model_type == "tensorflow":
                import tensorflow as tf
                self.model = tf.keras.models.load_model(self.model_path)
            elif self.model_type == "mlflow":
                self.model = mlflow.pyfunc.load_model(self.model_path)
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
            
            # Load scaler if provided
            if self.scaler_path and os.path.exists(self.scaler_path):
                if self.scaler_path.endswith('.pkl'):
                    with open(self.scaler_path, 'rb') as f:
                        self.scaler = pickle.load(f)
                else:
                    self.scaler = joblib.load(self.scaler_path)
            
            self.load_time = time.time() - start_time
            self.is_loaded = True
            
            logger.info(f"Model {self.model_name} loaded successfully in {self.load_time:.3f} seconds")
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def predict(self, 
                features: Dict[str, float],
                return_confidence: bool = False) -> Tuple[float, Optional[float]]:
        """
        Make a prediction.
        
        Args:
            features: Feature dictionary
            return_confidence: Whether to return confidence score
            
        Returns:
            (prediction, confidence)
        """
        if not self.is_loaded:
            raise RuntimeError(f"Model {self.model_name} not loaded")
        
        start_time = time.time()
        
        try:
            # Validate and prepare features
            X = self._prepare_features(features)
            
            # Scale features if scaler available
            if self.scaler is not None:
                X = self.scaler.transform(X.reshape(1, -1))[0]
            else:
                X = X.reshape(1, -1)
            
            # Make prediction
            if self.model_type == "tensorflow":
                prediction = float(self.model.predict(X, verbose=0)[0, 0])
            else:
                prediction = float(self.model.predict(X)[0])
            
            # Calculate confidence (placeholder implementation)
            confidence = None
            if return_confidence:
                confidence = self._calculate_confidence(X, prediction)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.prediction_times.append(processing_time)
            if len(self.prediction_times) > self.max_history:
                self.prediction_times = self.prediction_times[-self.max_history:]
            
            self.prediction_count += 1
            
            # Prometheus metrics
            PREDICTION_COUNTER.labels(model_name=self.model_name, status='success').inc()
            PREDICTION_LATENCY.labels(model_name=self.model_name).observe(processing_time)
            
            return prediction, confidence
            
        except Exception as e:
            self.error_count += 1
            PREDICTION_COUNTER.labels(model_name=self.model_name, status='error').inc()
            logger.error(f"Prediction error in {self.model_name}: {e}")
            raise
    
    def batch_predict(self, 
                     features_list: List[Dict[str, float]],
                     return_confidence: bool = False) -> Tuple[List[float], Optional[List[float]]]:
        """
        Make batch predictions.
        
        Args:
            features_list: List of feature dictionaries
            return_confidence: Whether to return confidence scores
            
        Returns:
            (predictions, confidences)
        """
        if not self.is_loaded:
            raise RuntimeError(f"Model {self.model_name} not loaded")
        
        start_time = time.time()
        
        try:
            # Prepare batch features
            X_batch = np.array([self._prepare_features(features) for features in features_list])
            
            # Scale features if scaler available
            if self.scaler is not None:
                X_batch = self.scaler.transform(X_batch)
            
            # Make batch predictions
            if self.model_type == "tensorflow":
                predictions = self.model.predict(X_batch, verbose=0).flatten().tolist()
            else:
                predictions = self.model.predict(X_batch).tolist()
            
            # Calculate confidences
            confidences = None
            if return_confidence:
                confidences = [self._calculate_confidence(X_batch[i:i+1], pred) for i, pred in enumerate(predictions)]
            
            # Update metrics
            processing_time = time.time() - start_time
            self.prediction_count += len(predictions)
            
            PREDICTION_COUNTER.labels(model_name=self.model_name, status='success').inc(len(predictions))
            PREDICTION_LATENCY.labels(model_name=self.model_name).observe(processing_time / len(predictions))
            
            return predictions, confidences
            
        except Exception as e:
            self.error_count += len(features_list)
            PREDICTION_COUNTER.labels(model_name=self.model_name, status='error').inc(len(features_list))
            logger.error(f"Batch prediction error in {self.model_name}: {e}")
            raise
    
    def _prepare_features(self, features: Dict[str, float]) -> np.ndarray:
        """Prepare features for prediction."""
        if self.feature_names:
            # Ensure all required features are present
            missing_features = set(self.feature_names) - set(features.keys())
            if missing_features:
                raise ValueError(f"Missing features: {missing_features}")
            
            # Order features correctly
            feature_vector = np.array([features[name] for name in self.feature_names])
        else:
            # Use features in provided order
            feature_vector = np.array(list(features.values()))
        
        return feature_vector
    
    def _calculate_confidence(self, X: np.ndarray, prediction: float) -> float:
        """Calculate prediction confidence (placeholder implementation)."""
        # This is a simplified confidence calculation
        # In production, you might use prediction intervals, ensemble variance, etc.
        
        if hasattr(self.model, 'predict_proba'):
            # For classifiers with probability output
            probas = self.model.predict_proba(X)
            confidence = float(np.max(probas))
        elif hasattr(self.model, 'decision_function'):
            # For models with decision function
            decision = self.model.decision_function(X)
            confidence = 1.0 / (1.0 + np.exp(-np.abs(decision[0])))  # Sigmoid transformation
        else:
            # Default confidence based on prediction magnitude
            confidence = min(0.9, 0.5 + 0.4 * np.exp(-abs(prediction) / 10))
        
        return float(confidence)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get model statistics."""
        avg_prediction_time = np.mean(self.prediction_times) if self.prediction_times else 0
        
        return {
            "model_name": self.model_name,
            "model_type": self.model_type,
            "is_loaded": self.is_loaded,
            "load_time": self.load_time,
            "prediction_count": self.prediction_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.prediction_count, 1),
            "avg_prediction_time": avg_prediction_time,
            "feature_count": len(self.feature_names)
        }


class PredictionCache:
    """
    Redis-based prediction caching system.
    
    Features:
    - TTL-based expiration
    - Feature-based cache keys
    - Cache hit/miss tracking
    - Batch caching support
    """
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 default_ttl: int = 300):
        """
        Initialize prediction cache.
        
        Args:
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
            default_ttl: Default TTL in seconds
        """
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.default_ttl = default_ttl
        self.enabled = True
        
        try:
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except redis.ConnectionError:
            logger.warning("Redis connection failed, caching disabled")
            self.enabled = False
    
    def _generate_key(self, model_name: str, features: Dict[str, float]) -> str:
        """Generate cache key from model name and features."""
        # Create a deterministic hash of features
        feature_str = json.dumps(features, sort_keys=True)
        feature_hash = hashlib.md5(feature_str.encode()).hexdigest()
        return f"prediction:{model_name}:{feature_hash}"
    
    def get(self, model_name: str, features: Dict[str, float]) -> Optional[float]:
        """Get cached prediction."""
        if not self.enabled:
            return None
        
        try:
            key = self._generate_key(model_name, features)
            cached_result = self.redis_client.get(key)
            
            if cached_result is not None:
                CACHE_HITS.labels(cache_type='prediction').inc()
                return float(cached_result.decode())
            else:
                CACHE_MISSES.labels(cache_type='prediction').inc()
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, 
            model_name: str, 
            features: Dict[str, float], 
            prediction: float,
            ttl: Optional[int] = None) -> None:
        """Set cached prediction."""
        if not self.enabled:
            return
        
        try:
            key = self._generate_key(model_name, features)
            ttl = ttl or self.default_ttl
            self.redis_client.setex(key, ttl, str(prediction))
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def clear(self, pattern: str = "prediction:*") -> int:
        """Clear cache entries matching pattern."""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0


class ModelRegistry:
    """
    Model registry for managing multiple models.
    
    Features:
    - Model loading and unloading
    - Model selection strategies
    - Health checking
    - A/B testing support
    """
    
    def __init__(self, cache: Optional[PredictionCache] = None):
        """Initialize model registry."""
        self.models: Dict[str, ModelWrapper] = {}
        self.default_model = None
        self.cache = cache
        self.model_configs = {}
        
        # Threading for concurrent predictions
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("Model registry initialized")
    
    def register_model(self, 
                      model_name: str,
                      model_path: str,
                      model_type: str = "sklearn",
                      feature_names: List[str] = None,
                      scaler_path: Optional[str] = None,
                      is_default: bool = False) -> None:
        """
        Register a new model.
        
        Args:
            model_name: Name of the model
            model_path: Path to the model file
            model_type: Type of model
            feature_names: Expected feature names
            scaler_path: Path to feature scaler
            is_default: Whether this is the default model
        """
        try:
            model_wrapper = ModelWrapper(
                model_name=model_name,
                model_path=model_path,
                model_type=model_type,
                feature_names=feature_names,
                scaler_path=scaler_path
            )
            
            model_wrapper.load_model()
            self.models[model_name] = model_wrapper
            
            # Store configuration
            self.model_configs[model_name] = {
                "model_path": model_path,
                "model_type": model_type,
                "feature_names": feature_names,
                "scaler_path": scaler_path,
                "registered_at": datetime.now().isoformat()
            }
            
            if is_default or self.default_model is None:
                self.default_model = model_name
            
            # Update Prometheus metric
            ACTIVE_MODELS.set(len(self.models))
            
            logger.info(f"Registered model: {model_name} (default: {is_default})")
            
        except Exception as e:
            logger.error(f"Failed to register model {model_name}: {e}")
            raise
    
    def unregister_model(self, model_name: str) -> None:
        """Unregister a model."""
        if model_name in self.models:
            del self.models[model_name]
            del self.model_configs[model_name]
            
            if self.default_model == model_name:
                self.default_model = next(iter(self.models), None)
            
            ACTIVE_MODELS.set(len(self.models))
            logger.info(f"Unregistered model: {model_name}")
    
    async def predict(self, 
                     features: Dict[str, float],
                     model_name: Optional[str] = None,
                     return_confidence: bool = False) -> Tuple[float, Optional[float], str]:
        """
        Make a prediction using specified or default model.
        
        Args:
            features: Feature dictionary
            model_name: Specific model to use
            return_confidence: Whether to return confidence
            
        Returns:
            (prediction, confidence, model_used)
        """
        # Determine which model to use
        target_model = model_name or self.default_model
        if not target_model:
            raise ValueError("No models available")
        
        if target_model not in self.models:
            raise ValueError(f"Model {target_model} not found")
        
        # Check cache first
        if self.cache:
            cached_prediction = self.cache.get(target_model, features)
            if cached_prediction is not None:
                return cached_prediction, None, target_model
        
        # Make prediction
        loop = asyncio.get_event_loop()
        prediction, confidence = await loop.run_in_executor(
            self.executor,
            self.models[target_model].predict,
            features,
            return_confidence
        )
        
        # Cache result
        if self.cache:
            self.cache.set(target_model, features, prediction)
        
        return prediction, confidence, target_model
    
    async def batch_predict(self,
                           features_list: List[Dict[str, float]],
                           model_name: Optional[str] = None,
                           return_confidence: bool = False) -> Tuple[List[float], Optional[List[float]], str]:
        """
        Make batch predictions.
        
        Args:
            features_list: List of feature dictionaries
            model_name: Specific model to use
            return_confidence: Whether to return confidences
            
        Returns:
            (predictions, confidences, model_used)
        """
        target_model = model_name or self.default_model
        if not target_model:
            raise ValueError("No models available")
        
        if target_model not in self.models:
            raise ValueError(f"Model {target_model} not found")
        
        # Make batch predictions
        loop = asyncio.get_event_loop()
        predictions, confidences = await loop.run_in_executor(
            self.executor,
            self.models[target_model].batch_predict,
            features_list,
            return_confidence
        )
        
        return predictions, confidences, target_model
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics for all models."""
        return {
            model_name: model.get_stats() 
            for model_name, model in self.models.items()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all models."""
        health_status = {
            "total_models": len(self.models),
            "default_model": self.default_model,
            "models": {}
        }
        
        for model_name, model in self.models.items():
            try:
                # Simple prediction test
                test_features = {name: 0.0 for name in model.feature_names} if model.feature_names else {"test": 0.0}
                start_time = time.time()
                _, _ = model.predict(test_features)
                response_time = time.time() - start_time
                
                health_status["models"][model_name] = {
                    "status": "healthy",
                    "response_time": response_time,
                    "prediction_count": model.prediction_count,
                    "error_count": model.error_count
                }
            except Exception as e:
                health_status["models"][model_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return health_status


# Initialize global components
model_registry = ModelRegistry()
prediction_cache = PredictionCache()
model_registry.cache = prediction_cache

# FastAPI application
app = FastAPI(
    title="MARTA Demand Forecasting API",
    description="Production ML serving API for MARTA demand predictions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_startup
async def startup_event():
    """Initialize models on startup."""
    try:
        # Register models from MLflow or local files
        await initialize_models()
        logger.info("Model serving API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")


async def initialize_models():
    """Initialize models from configuration or MLflow."""
    try:
        # Example model registration
        models_dir = settings.MODELS_DIR
        
        # Register LSTM model if available
        lstm_path = os.path.join(models_dir, "lstm_model.h5")
        lstm_scaler_path = os.path.join(models_dir, "lstm_scaler.pkl")
        
        if os.path.exists(lstm_path):
            feature_names = ["delay_minutes", "hour_of_day", "is_weekend", "is_holiday"]
            model_registry.register_model(
                model_name="lstm",
                model_path=lstm_path,
                model_type="tensorflow",
                feature_names=feature_names,
                scaler_path=lstm_scaler_path if os.path.exists(lstm_scaler_path) else None,
                is_default=True
            )
        
        # Register XGBoost model if available
        xgb_path = os.path.join(models_dir, "xgboost_model.pkl")
        if os.path.exists(xgb_path):
            feature_names = ["delay_minutes", "hour_of_day", "is_weekend", "is_holiday"]
            model_registry.register_model(
                model_name="xgboost",
                model_path=xgb_path,
                model_type="sklearn",
                feature_names=feature_names,
                is_default=not model_registry.default_model  # Default if no other model
            )
        
        logger.info(f"Initialized {len(model_registry.models)} models")
        
    except Exception as e:
        logger.error(f"Model initialization failed: {e}")
        raise


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest) -> PredictionResponse:
    """Make a single prediction."""
    start_time = time.time()
    
    try:
        prediction, confidence, model_used = await model_registry.predict(
            features=request.features,
            model_name=request.model_name,
            return_confidence=request.return_confidence
        )
        
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return PredictionResponse(
            prediction=prediction,
            model_name=model_used,
            confidence=confidence,
            prediction_time=datetime.now().isoformat(),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch_predict", response_model=BatchPredictionResponse)
async def batch_predict(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """Make batch predictions."""
    start_time = time.time()
    
    try:
        predictions, confidences, model_used = await model_registry.batch_predict(
            features_list=request.features,
            model_name=request.model_name,
            return_confidence=request.return_confidence
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return BatchPredictionResponse(
            predictions=predictions,
            model_name=model_used,
            confidences=confidences,
            batch_id=request.batch_id,
            total_samples=len(predictions),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return model_registry.health_check()


@app.get("/models")
async def list_models():
    """List available models."""
    return {
        "models": list(model_registry.models.keys()),
        "default_model": model_registry.default_model,
        "total_models": len(model_registry.models)
    }


@app.get("/stats")
async def get_stats():
    """Get model statistics."""
    return model_registry.get_model_stats()


@app.get("/metrics")
async def get_metrics():
    """Get Prometheus metrics."""
    return prometheus_client.generate_latest().decode()


@app.post("/cache/clear")
async def clear_cache():
    """Clear prediction cache."""
    if prediction_cache.enabled:
        cleared = prediction_cache.clear()
        return {"cleared_entries": cleared}
    else:
        return {"message": "Cache not enabled"}


def create_batch_inference_job(input_file: str, 
                              output_file: str,
                              model_name: Optional[str] = None,
                              batch_size: int = 1000) -> None:
    """
    Create and execute batch inference job.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file
        model_name: Model to use for predictions
        batch_size: Batch size for processing
    """
    logger.info(f"Starting batch inference job: {input_file} -> {output_file}")
    
    try:
        # Read input data
        df = pd.read_csv(input_file)
        logger.info(f"Loaded {len(df)} samples for batch inference")
        
        # Process in batches
        predictions = []
        total_batches = len(df) // batch_size + (1 if len(df) % batch_size else 0)
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            
            # Convert to feature dictionaries
            features_list = []
            for _, row in batch_df.iterrows():
                features = {col: float(row[col]) for col in batch_df.columns if col in model_registry.models[model_name or model_registry.default_model].feature_names}
                features_list.append(features)
            
            # Make batch prediction
            batch_predictions, _, _ = asyncio.run(
                model_registry.batch_predict(features_list, model_name)
            )
            
            predictions.extend(batch_predictions)
            
            logger.info(f"Processed batch {i//batch_size + 1}/{total_batches}")
        
        # Save results
        results_df = df.copy()
        results_df['prediction'] = predictions
        results_df['prediction_timestamp'] = datetime.now().isoformat()
        results_df.to_csv(output_file, index=False)
        
        logger.info(f"Batch inference completed: {len(predictions)} predictions saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Batch inference failed: {e}")
        raise


def start_model_server(host: str = "0.0.0.0", 
                      port: int = 8000,
                      workers: int = 1):
    """
    Start the model serving server.
    
    Args:
        host: Host address
        port: Port number
        workers: Number of worker processes
    """
    logger.info(f"Starting model server on {host}:{port} with {workers} workers")
    
    uvicorn.run(
        "src.models.model_serving:app",
        host=host,
        port=port,
        workers=workers,
        loop="asyncio",
        log_level="info"
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MARTA ML Model Serving")
    parser.add_argument("--mode", choices=["server", "batch"], default="server", help="Execution mode")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    parser.add_argument("--input-file", help="Input file for batch processing")
    parser.add_argument("--output-file", help="Output file for batch processing")
    parser.add_argument("--model-name", help="Model name for batch processing")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if args.mode == "server":
        start_model_server(args.host, args.port, args.workers)
    elif args.mode == "batch":
        if not args.input_file or not args.output_file:
            parser.error("Batch mode requires --input-file and --output-file")
        
        # Initialize models first
        asyncio.run(initialize_models())
        
        create_batch_inference_job(
            args.input_file,
            args.output_file,
            args.model_name,
            args.batch_size
        )