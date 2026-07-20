"""
Online Learning System for MARTA Demand Forecasting

This module implements online learning capabilities for real-time model updates
using incremental learning algorithms and streaming data processing.
"""
import os
import logging
import json
import pickle
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from collections import deque
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.linear_model import SGDRegressor, PassiveAggressiveRegressor
from sklearn.ensemble import RandomForestRegressor
import asyncio
import asyncpg
from river import linear_model, ensemble, metrics, preprocessing, compose
from river.drift import ADWIN
import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, Dense, LSTM, Dropout
from tensorflow.keras.optimizers import Adam
import mlflow
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from src.models.ml_experiment_tracker import get_experiment_tracker

logger = logging.getLogger(__name__)


class OnlineLearningBuffer:
    """
    Circular buffer for storing recent training examples in online learning.
    
    Features:
    - Fixed size buffer with automatic eviction
    - Statistics tracking
    - Data quality validation
    - Efficient batch processing
    """
    
    def __init__(self, max_size: int = 10000, feature_names: List[str] = None):
        """
        Initialize online learning buffer.
        
        Args:
            max_size: Maximum number of samples to store
            feature_names: List of feature names
        """
        self.max_size = max_size
        self.feature_names = feature_names or []
        self.buffer_X = deque(maxlen=max_size)
        self.buffer_y = deque(maxlen=max_size)
        self.timestamps = deque(maxlen=max_size)
        
        # Statistics
        self.total_samples = 0
        self.mean_target = 0.0
        self.var_target = 0.0
        
        logger.info(f"Initialized online learning buffer with max_size={max_size}")
    
    def add_sample(self, X: np.ndarray, y: float, timestamp: Optional[datetime] = None) -> None:
        """
        Add a new sample to the buffer.
        
        Args:
            X: Feature vector
            y: Target value
            timestamp: Timestamp of the sample
        """
        # Validate input
        if len(X) != len(self.feature_names) and self.feature_names:
            raise ValueError(f"Feature dimension mismatch: {len(X)} != {len(self.feature_names)}")
        
        # Add to buffer
        self.buffer_X.append(X.copy())
        self.buffer_y.append(y)
        self.timestamps.append(timestamp or datetime.now())
        
        # Update statistics
        self.total_samples += 1
        
        # Update running mean and variance
        if len(self.buffer_y) == 1:
            self.mean_target = y
            self.var_target = 0.0
        else:
            # Online Welford's algorithm
            delta = y - self.mean_target
            self.mean_target += delta / len(self.buffer_y)
            delta2 = y - self.mean_target
            self.var_target += delta * delta2
    
    def get_batch(self, batch_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get a batch of samples from the buffer.
        
        Args:
            batch_size: Size of batch (all samples if None)
            
        Returns:
            (X_batch, y_batch)
        """
        if len(self.buffer_X) == 0:
            return np.array([]), np.array([])
        
        if batch_size is None or batch_size >= len(self.buffer_X):
            X_batch = np.array(list(self.buffer_X))
            y_batch = np.array(list(self.buffer_y))
        else:
            # Get most recent samples
            X_batch = np.array(list(self.buffer_X)[-batch_size:])
            y_batch = np.array(list(self.buffer_y)[-batch_size:])
        
        return X_batch, y_batch
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        return {
            "buffer_size": len(self.buffer_X),
            "max_size": self.max_size,
            "total_samples": self.total_samples,
            "mean_target": self.mean_target,
            "std_target": np.sqrt(self.var_target / max(len(self.buffer_y) - 1, 1)) if len(self.buffer_y) > 1 else 0.0,
            "oldest_timestamp": self.timestamps[0] if self.timestamps else None,
            "newest_timestamp": self.timestamps[-1] if self.timestamps else None
        }


class IncrementalLSTM:
    """
    Incremental LSTM model for online learning.
    
    Features:
    - Mini-batch gradient updates
    - Adaptive learning rate
    - Memory management
    - Model checkpointing
    """
    
    def __init__(self, 
                 input_dim: int,
                 sequence_length: int = 24,
                 lstm_units: int = 50,
                 learning_rate: float = 0.001,
                 checkpoint_dir: str = None):
        """
        Initialize incremental LSTM.
        
        Args:
            input_dim: Number of input features
            sequence_length: Length of input sequences
            lstm_units: Number of LSTM units
            learning_rate: Initial learning rate
            checkpoint_dir: Directory for model checkpoints
        """
        self.input_dim = input_dim
        self.sequence_length = sequence_length
        self.lstm_units = lstm_units
        self.learning_rate = learning_rate
        self.checkpoint_dir = checkpoint_dir or os.path.join(settings.MODELS_DIR, "online_lstm")
        
        # Create model
        self.model = self._build_model()
        self.scaler = StandardScaler()
        
        # Training state
        self.is_fitted = False
        self.update_count = 0
        self.sequence_buffer = deque(maxlen=sequence_length)
        
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        logger.info("Initialized incremental LSTM model")
    
    def _build_model(self) -> Model:
        """Build LSTM model architecture."""
        inputs = Input(shape=(self.sequence_length, self.input_dim))
        lstm1 = LSTM(self.lstm_units, return_sequences=True)(inputs)
        dropout1 = Dropout(0.2)(lstm1)
        lstm2 = LSTM(self.lstm_units // 2, return_sequences=False)(dropout1)
        dropout2 = Dropout(0.2)(lstm2)
        outputs = Dense(1, activation='linear')(dropout2)
        
        model = Model(inputs=inputs, outputs=outputs)
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def initial_fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """
        Initial model training on historical data.
        
        Args:
            X: Historical features
            y: Historical targets
        """
        logger.info("Performing initial LSTM training...")
        
        # Scale data
        X_scaled = self.scaler.fit_transform(X)
        
        # Create sequences
        X_seq, y_seq = self._create_sequences(X_scaled, y)
        
        if len(X_seq) > 0:
            # Train model
            self.model.fit(
                X_seq, y_seq,
                batch_size=32,
                epochs=50,
                validation_split=0.2,
                verbose=0
            )
            
            self.is_fitted = True
            self._save_checkpoint()
            logger.info("Initial LSTM training completed")
        else:
            logger.warning("Insufficient data for initial LSTM training")
    
    def update(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Online update with new data.
        
        Args:
            X: New features
            y: New targets
            
        Returns:
            Update metrics
        """
        if not self.is_fitted:
            logger.warning("Model not initially fitted. Performing initial fit...")
            self.initial_fit(X, y)
            return {"status": "initial_fit"}
        
        # Scale new data
        X_scaled = self.scaler.transform(X)
        
        # Update sequence buffer
        for i in range(len(X_scaled)):
            self.sequence_buffer.append(X_scaled[i])
            
            # If we have enough data, create sequence and update
            if len(self.sequence_buffer) == self.sequence_length:
                sequence = np.array(list(self.sequence_buffer)).reshape(1, self.sequence_length, self.input_dim)
                target = np.array([y[i]])
                
                # Make prediction before update
                pred_before = self.model.predict(sequence, verbose=0)[0, 0]
                
                # Update model
                loss = self.model.train_on_batch(sequence, target)
                
                # Make prediction after update
                pred_after = self.model.predict(sequence, verbose=0)[0, 0]
                
                self.update_count += 1
                
                # Periodic checkpoint
                if self.update_count % 100 == 0:
                    self._save_checkpoint()
                
                return {
                    "loss": float(loss) if isinstance(loss, (list, np.ndarray)) else loss,
                    "pred_before": float(pred_before),
                    "pred_after": float(pred_after),
                    "target": float(y[i]),
                    "update_count": self.update_count
                }
        
        return {"status": "insufficient_sequence_data"}
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        X_scaled = self.scaler.transform(X)
        
        predictions = []
        for i in range(len(X_scaled)):
            # Use recent sequence buffer + current sample
            if len(self.sequence_buffer) >= self.sequence_length - 1:
                sequence_data = list(self.sequence_buffer)[-(self.sequence_length-1):] + [X_scaled[i]]
            else:
                # Pad with zeros if not enough historical data
                padding = [np.zeros(self.input_dim)] * (self.sequence_length - len(self.sequence_buffer) - 1)
                sequence_data = padding + list(self.sequence_buffer) + [X_scaled[i]]
            
            sequence = np.array(sequence_data).reshape(1, self.sequence_length, self.input_dim)
            pred = self.model.predict(sequence, verbose=0)[0, 0]
            predictions.append(pred)
        
        return np.array(predictions)
    
    def _create_sequences(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training."""
        if len(X) <= self.sequence_length:
            return np.array([]), np.array([])
        
        X_seq, y_seq = [], []
        for i in range(len(X) - self.sequence_length):
            X_seq.append(X[i:i + self.sequence_length])
            y_seq.append(y[i + self.sequence_length])
        
        return np.array(X_seq), np.array(y_seq)
    
    def _save_checkpoint(self) -> None:
        """Save model checkpoint."""
        try:
            model_path = os.path.join(self.checkpoint_dir, f"model_checkpoint_{self.update_count}.h5")
            self.model.save(model_path)
            
            scaler_path = os.path.join(self.checkpoint_dir, f"scaler_checkpoint_{self.update_count}.pkl")
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
                
            logger.info(f"Saved checkpoint at update {self.update_count}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")


class RiverOnlineLearner:
    """
    Online learning using River library for incremental algorithms.
    
    Features:
    - Multiple incremental algorithms
    - Concept drift detection
    - Automatic model selection
    - Performance tracking
    """
    
    def __init__(self, 
                 model_type: str = "linear",
                 drift_detection: bool = True,
                 ensemble_size: int = 5):
        """
        Initialize River online learner.
        
        Args:
            model_type: Type of model ('linear', 'forest', 'ensemble')
            drift_detection: Whether to use drift detection
            ensemble_size: Size of ensemble models
        """
        self.model_type = model_type
        self.drift_detection = drift_detection
        self.ensemble_size = ensemble_size
        
        # Create model
        self.model = self._create_model()
        self.scaler = preprocessing.StandardScaler()
        
        # Drift detection
        if drift_detection:
            self.drift_detector = ADWIN()
            self.drift_detected = False
        
        # Performance tracking
        self.metric = metrics.MAE()
        self.performance_history = []
        
        logger.info(f"Initialized River online learner ({model_type})")
    
    def _create_model(self):
        """Create River model based on type."""
        if self.model_type == "linear":
            return compose.Pipeline(
                preprocessing.StandardScaler(),
                linear_model.LinearRegression(
                    optimizer=linear_model.optim.SGD(lr=0.01),
                    l2=0.001
                )
            )
        elif self.model_type == "pa":
            return compose.Pipeline(
                preprocessing.StandardScaler(),
                linear_model.PARegressor(C=1.0, mode=1)
            )
        elif self.model_type == "ensemble":
            models = []
            for i in range(self.ensemble_size):
                if i % 2 == 0:
                    model = linear_model.LinearRegression(optimizer=linear_model.optim.SGD(lr=0.01))
                else:
                    model = linear_model.PARegressor(C=1.0)
                models.append(model)
            
            return compose.Pipeline(
                preprocessing.StandardScaler(),
                ensemble.VotingRegressor(models)
            )
        else:
            # Default to linear
            return compose.Pipeline(
                preprocessing.StandardScaler(),
                linear_model.LinearRegression()
            )
    
    def update(self, X: Dict[str, float], y: float) -> Dict[str, Any]:
        """
        Update model with new sample.
        
        Args:
            X: Feature dictionary
            y: Target value
            
        Returns:
            Update results
        """
        # Make prediction before update
        pred_before = self.model.predict_one(X)
        
        # Update model
        self.model.learn_one(X, y)
        
        # Update metrics
        self.metric.update(y, pred_before)
        
        # Drift detection
        drift_detected = False
        if self.drift_detection:
            error = abs(y - pred_before)
            self.drift_detector.update(error)
            
            if self.drift_detector.drift_detected:
                drift_detected = True
                logger.warning("Concept drift detected!")
                self._handle_drift()
        
        # Track performance
        current_mae = self.metric.get()
        self.performance_history.append({
            "timestamp": datetime.now(),
            "mae": current_mae,
            "prediction": pred_before,
            "target": y,
            "error": abs(y - pred_before),
            "drift_detected": drift_detected
        })
        
        # Keep only recent history
        if len(self.performance_history) > 10000:
            self.performance_history = self.performance_history[-5000:]
        
        return {
            "prediction": pred_before,
            "target": y,
            "mae": current_mae,
            "drift_detected": drift_detected,
            "model_type": self.model_type
        }
    
    def predict(self, X: Dict[str, float]) -> float:
        """Make prediction for single sample."""
        return self.model.predict_one(X)
    
    def batch_predict(self, X_batch: List[Dict[str, float]]) -> List[float]:
        """Make predictions for batch of samples."""
        return [self.predict(x) for x in X_batch]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.performance_history:
            return {}
        
        recent_history = self.performance_history[-1000:]  # Last 1000 samples
        errors = [h["error"] for h in recent_history]
        
        return {
            "current_mae": self.metric.get(),
            "recent_mean_error": np.mean(errors),
            "recent_std_error": np.std(errors),
            "total_samples": len(self.performance_history),
            "drift_detections": sum(1 for h in self.performance_history if h["drift_detected"])
        }
    
    def _handle_drift(self) -> None:
        """Handle concept drift detection."""
        # Reset model or adapt learning rate
        logger.info("Handling concept drift - resetting model")
        self.model = self._create_model()
        self.metric = metrics.MAE()


class OnlineLearningOrchestrator:
    """
    Orchestrator for online learning system with multiple models and data streams.
    
    Features:
    - Multi-model online learning
    - Data stream management
    - Performance monitoring
    - Automatic model selection
    - Database integration
    """
    
    def __init__(self, 
                 feature_names: List[str],
                 models_config: Dict[str, Dict] = None):
        """
        Initialize online learning orchestrator.
        
        Args:
            feature_names: List of feature names
            models_config: Configuration for different models
        """
        self.feature_names = feature_names
        self.models_config = models_config or self._default_models_config()
        
        # Initialize models
        self.models = {}
        self.buffers = {}
        
        for model_name, config in self.models_config.items():
            self._initialize_model(model_name, config)
        
        # Performance tracking
        self.model_performance = {name: deque(maxlen=1000) for name in self.models.keys()}
        self.best_model = None
        
        # Database connection
        self.db_pool = None
        
        self.experiment_tracker = get_experiment_tracker()
        
        logger.info(f"Initialized online learning orchestrator with models: {list(self.models.keys())}")
    
    def _default_models_config(self) -> Dict[str, Dict]:
        """Default configuration for models."""
        return {
            "river_linear": {
                "type": "river",
                "model_type": "linear",
                "buffer_size": 5000
            },
            "river_ensemble": {
                "type": "river", 
                "model_type": "ensemble",
                "buffer_size": 5000
            },
            "incremental_lstm": {
                "type": "lstm",
                "sequence_length": 24,
                "buffer_size": 10000
            },
            "sgd_regressor": {
                "type": "sklearn",
                "model_class": SGDRegressor,
                "model_params": {"learning_rate": "adaptive", "alpha": 0.001},
                "buffer_size": 3000
            }
        }
    
    def _initialize_model(self, model_name: str, config: Dict) -> None:
        """Initialize a single model."""
        try:
            if config["type"] == "river":
                self.models[model_name] = RiverOnlineLearner(
                    model_type=config["model_type"],
                    drift_detection=config.get("drift_detection", True)
                )
            elif config["type"] == "lstm":
                self.models[model_name] = IncrementalLSTM(
                    input_dim=len(self.feature_names),
                    sequence_length=config.get("sequence_length", 24)
                )
            elif config["type"] == "sklearn":
                model_class = config["model_class"]
                model_params = config.get("model_params", {})
                self.models[model_name] = model_class(**model_params)
            
            # Initialize buffer
            self.buffers[model_name] = OnlineLearningBuffer(
                max_size=config.get("buffer_size", 5000),
                feature_names=self.feature_names
            )
            
            logger.info(f"Initialized model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize model {model_name}: {e}")
    
    async def initialize_db_connection(self):
        """Initialize database connection for real-time data streaming."""
        try:
            connection_string = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            self.db_pool = await asyncpg.create_pool(connection_string, min_size=2, max_size=10)
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
    
    async def process_new_data(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        Process new data with all online models.
        
        Args:
            X: New feature data
            y: New target data
            
        Returns:
            Processing results
        """
        results = {}
        
        for model_name, model in self.models.items():
            try:
                # Add to buffer
                for i in range(len(X)):
                    self.buffers[model_name].add_sample(X[i], y[i])
                
                # Update model based on type
                if isinstance(model, RiverOnlineLearner):
                    # River model - update sample by sample
                    model_results = []
                    for i in range(len(X)):
                        X_dict = {name: X[i, j] for j, name in enumerate(self.feature_names)}
                        result = model.update(X_dict, y[i])
                        model_results.append(result)
                    
                    # Average metrics
                    avg_mae = np.mean([r["mae"] for r in model_results])
                    results[model_name] = {
                        "type": "river",
                        "avg_mae": avg_mae,
                        "drift_detections": sum(1 for r in model_results if r["drift_detected"]),
                        "samples_processed": len(model_results)
                    }
                
                elif isinstance(model, IncrementalLSTM):
                    # LSTM model - batch update
                    lstm_result = model.update(X, y)
                    results[model_name] = {
                        "type": "lstm",
                        "update_result": lstm_result
                    }
                
                elif hasattr(model, 'partial_fit'):
                    # Sklearn incremental model
                    model.partial_fit(X, y)
                    
                    # Evaluate on recent data
                    X_recent, y_recent = self.buffers[model_name].get_batch(100)
                    if len(X_recent) > 0:
                        pred_recent = model.predict(X_recent)
                        mae = mean_absolute_error(y_recent, pred_recent)
                        results[model_name] = {
                            "type": "sklearn",
                            "mae": mae,
                            "samples_evaluated": len(y_recent)
                        }
                
                # Track performance
                if "mae" in results[model_name] or "avg_mae" in results[model_name]:
                    mae = results[model_name].get("mae", results[model_name].get("avg_mae", 0))
                    self.model_performance[model_name].append({
                        "timestamp": datetime.now(),
                        "mae": mae
                    })
                
            except Exception as e:
                logger.error(f"Failed to process data with model {model_name}: {e}")
                results[model_name] = {"error": str(e)}
        
        # Update best model selection
        self._update_best_model()
        
        return results
    
    async def start_real_time_learning(self, check_interval: int = 60):
        """
        Start real-time learning from database stream.
        
        Args:
            check_interval: Interval in seconds to check for new data
        """
        logger.info("Starting real-time learning...")
        
        if not self.db_pool:
            await self.initialize_db_connection()
        
        last_check = datetime.now() - timedelta(minutes=5)
        
        while True:
            try:
                # Query for new data
                async with self.db_pool.acquire() as conn:
                    query = """
                        SELECT * FROM unified_realtime_historical_data
                        WHERE timestamp > $1
                        AND delay_minutes IS NOT NULL
                        ORDER BY timestamp
                        LIMIT 1000
                    """
                    
                    rows = await conn.fetch(query, last_check)
                
                if rows:
                    # Convert to arrays
                    df = pd.DataFrame(rows)
                    
                    # Prepare features (simplified feature engineering)
                    feature_columns = [col for col in df.columns if col in self.feature_names]
                    X = df[feature_columns].values
                    y = df['delay_minutes'].values
                    
                    # Process with online models
                    results = await self.process_new_data(X, y)
                    
                    # Log results
                    with self.experiment_tracker.start_run(
                        run_name="online_learning_update",
                        tags={"learning_type": "online", "samples": len(rows)}
                    ) as run:
                        
                        for model_name, result in results.items():
                            if "error" not in result:
                                if "mae" in result:
                                    mlflow.log_metric(f"{model_name}_mae", result["mae"])
                                elif "avg_mae" in result:
                                    mlflow.log_metric(f"{model_name}_avg_mae", result["avg_mae"])
                    
                    logger.info(f"Processed {len(rows)} new samples with online learning")
                    last_check = max(pd.to_datetime(df['timestamp']))
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in real-time learning: {e}")
                await asyncio.sleep(check_interval * 2)  # Wait longer on error
    
    def get_model_predictions(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        """Get predictions from all models."""
        predictions = {}
        
        for model_name, model in self.models.items():
            try:
                if isinstance(model, RiverOnlineLearner):
                    # Convert to dict format for River models
                    X_dicts = []
                    for i in range(len(X)):
                        X_dict = {name: X[i, j] for j, name in enumerate(self.feature_names)}
                        X_dicts.append(X_dict)
                    
                    preds = model.batch_predict(X_dicts)
                    predictions[model_name] = np.array(preds)
                
                elif hasattr(model, 'predict'):
                    predictions[model_name] = model.predict(X)
                
            except Exception as e:
                logger.error(f"Failed to get predictions from {model_name}: {e}")
        
        return predictions
    
    def _update_best_model(self) -> None:
        """Update best model selection based on recent performance."""
        model_scores = {}
        
        for model_name, performance in self.model_performance.items():
            if len(performance) > 0:
                # Use recent average MAE
                recent_mae = np.mean([p["mae"] for p in list(performance)[-50:]])
                model_scores[model_name] = recent_mae
        
        if model_scores:
            self.best_model = min(model_scores.keys(), key=lambda k: model_scores[k])
            logger.info(f"Best model updated: {self.best_model} (MAE: {model_scores[self.best_model]:.4f})")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        status = {
            "models": {},
            "best_model": self.best_model,
            "total_models": len(self.models),
            "system_uptime": datetime.now().isoformat()
        }
        
        for model_name in self.models.keys():
            buffer_stats = self.buffers[model_name].get_statistics()
            
            model_status = {
                "buffer_stats": buffer_stats,
                "recent_performance": []
            }
            
            # Recent performance
            if self.model_performance[model_name]:
                recent_perf = list(self.model_performance[model_name])[-10:]
                model_status["recent_performance"] = [
                    {"timestamp": p["timestamp"].isoformat(), "mae": p["mae"]} 
                    for p in recent_perf
                ]
            
            # Model-specific stats
            if isinstance(self.models[model_name], RiverOnlineLearner):
                model_status["river_stats"] = self.models[model_name].get_performance_stats()
            
            status["models"][model_name] = model_status
        
        return status


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Initialize orchestrator
    feature_names = ["delay_minutes", "hour_of_day", "is_weekend", "is_holiday"]
    orchestrator = OnlineLearningOrchestrator(feature_names)
    
    # Simulate online learning
    async def simulate_online_learning():
        # Generate sample data
        np.random.seed(42)
        
        for batch in range(10):
            # Simulate new batch of data
            X_batch = np.random.randn(10, len(feature_names))
            y_batch = np.sum(X_batch[:, :2], axis=1) + np.random.randn(10) * 0.1
            
            # Process with online learning
            results = await orchestrator.process_new_data(X_batch, y_batch)
            print(f"Batch {batch + 1} processed:")
            for model_name, result in results.items():
                print(f"  {model_name}: {result}")
            
            # Simulate real-time delay
            await asyncio.sleep(1)
        
        # Get system status
        status = orchestrator.get_system_status()
        print("\nSystem Status:")
        print(json.dumps(status, indent=2, default=str))
    
    # Run simulation
    asyncio.run(simulate_online_learning())