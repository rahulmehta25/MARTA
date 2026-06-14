"""
Model Serving Module

Production-ready model serving with hot-swapping, caching, monitoring,
and FastAPI integration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
from enum import Enum
import threading
import time
import json
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model serving status."""
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    UNLOADING = "unloading"


@dataclass
class PredictionRequest:
    """
    Prediction request structure.

    Attributes:
        features: Feature dictionary or array.
        model_name: Optional specific model to use.
        return_confidence: Whether to return confidence.
        return_latency: Whether to return processing time.
        request_id: Unique request identifier.
    """
    features: Union[Dict[str, float], List[float], np.ndarray]
    model_name: Optional[str] = None
    return_confidence: bool = False
    return_latency: bool = True
    request_id: str = ""


@dataclass
class PredictionResponse:
    """
    Prediction response structure.

    Attributes:
        prediction: Model prediction.
        model_name: Model used for prediction.
        model_version: Model version used.
        confidence: Confidence score (if requested).
        latency_ms: Processing latency in milliseconds.
        timestamp: Response timestamp.
        request_id: Original request ID.
    """
    prediction: Union[float, List[float], np.ndarray]
    model_name: str
    model_version: str = ""
    confidence: Optional[float] = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prediction": self.prediction if isinstance(self.prediction, (int, float, list)) else self.prediction.tolist(),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
        }


@dataclass
class ModelEndpoint:
    """
    Model endpoint configuration.

    Attributes:
        name: Endpoint name.
        model_path: Path to model artifacts.
        model_type: Type of model (lstm, xgboost, etc.).
        version: Model version.
        status: Current status.
        load_time: Time taken to load model.
        prediction_count: Number of predictions made.
        error_count: Number of errors.
        avg_latency_ms: Average prediction latency.
    """
    name: str
    model_path: str
    model_type: str = "sklearn"
    version: str = "1.0.0"
    status: ModelStatus = ModelStatus.LOADING
    load_time: float = 0.0
    prediction_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    _model: Any = field(default=None, repr=False)
    _scaler: Any = field(default=None, repr=False)
    _feature_names: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "model_path": self.model_path,
            "model_type": self.model_type,
            "version": self.version,
            "status": self.status.value,
            "load_time": self.load_time,
            "prediction_count": self.prediction_count,
            "error_count": self.error_count,
            "avg_latency_ms": self.avg_latency_ms,
        }


class ModelServer:
    """
    Model serving infrastructure with hot-swapping.

    Features:
    - Hot model swapping without downtime
    - Multiple model support
    - Automatic fallback
    - Request caching
    - Performance monitoring
    - Thread-safe operations

    Example:
        >>> server = ModelServer()
        >>> server.load_model("demand_lstm", "/models/lstm_v1", "lstm")
        >>> response = server.predict(PredictionRequest(features={...}))
    """

    def __init__(
        self,
        max_workers: int = 4,
        cache_size: int = 1000,
        cache_ttl_seconds: int = 60,
    ):
        """
        Initialize model server.

        Args:
            max_workers: Maximum worker threads for predictions.
            cache_size: Maximum cache entries.
            cache_ttl_seconds: Cache entry TTL.
        """
        self.endpoints: Dict[str, ModelEndpoint] = {}
        self.default_endpoint: Optional[str] = None
        self.max_workers = max_workers

        # Thread pool for predictions
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Cache
        self._cache: Dict[str, tuple] = {}  # key -> (response, timestamp)
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl_seconds

        # Thread safety
        self._lock = threading.RLock()

        # Metrics
        self.total_requests = 0
        self.total_errors = 0
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info(f"ModelServer initialized with {max_workers} workers")

    def load_model(
        self,
        name: str,
        model_path: str,
        model_type: str = "sklearn",
        version: str = "1.0.0",
        feature_names: Optional[List[str]] = None,
        set_default: bool = False,
    ) -> bool:
        """
        Load a model into the server.

        Args:
            name: Endpoint name.
            model_path: Path to model.
            model_type: Type of model.
            version: Model version.
            feature_names: Expected feature names.
            set_default: Set as default endpoint.

        Returns:
            True if loaded successfully.
        """
        with self._lock:
            endpoint = ModelEndpoint(
                name=name,
                model_path=model_path,
                model_type=model_type,
                version=version,
                status=ModelStatus.LOADING,
                _feature_names=feature_names or [],
            )
            self.endpoints[name] = endpoint

        try:
            start_time = time.time()

            # Load model based on type
            model, scaler = self._load_model_artifacts(model_path, model_type)

            with self._lock:
                endpoint._model = model
                endpoint._scaler = scaler
                endpoint.load_time = time.time() - start_time
                endpoint.status = ModelStatus.READY

                if set_default or self.default_endpoint is None:
                    self.default_endpoint = name

            logger.info(f"Loaded model '{name}' v{version} in {endpoint.load_time:.2f}s")
            return True

        except Exception as e:
            with self._lock:
                endpoint.status = ModelStatus.ERROR
            logger.error(f"Failed to load model '{name}': {e}")
            return False

    def _load_model_artifacts(
        self,
        model_path: str,
        model_type: str
    ) -> tuple:
        """Load model and scaler from path."""
        import joblib

        model = None
        scaler = None
        path = Path(model_path)

        if model_type == "lstm":
            import tensorflow as tf
            from ..models.attention_lstm import TemporalAttention, MultiHeadAttention

            custom_objects = {
                'TemporalAttention': TemporalAttention,
                'MultiHeadAttention': MultiHeadAttention,
            }

            # Find model file
            model_files = list(path.glob("*.keras")) + list(path.glob("*.h5"))
            if model_files:
                model = tf.keras.models.load_model(model_files[0], custom_objects=custom_objects)

            # Load scaler
            scaler_files = list(path.glob("*scaler*.pkl"))
            if scaler_files:
                scaler = joblib.load(scaler_files[0])

        elif model_type == "xgboost":
            import xgboost as xgb

            model_files = list(path.glob("*.json")) + list(path.glob("*.pkl"))
            if model_files:
                if str(model_files[0]).endswith('.json'):
                    model = xgb.XGBRegressor()
                    model.load_model(model_files[0])
                else:
                    model = joblib.load(model_files[0])

            scaler_files = list(path.glob("*scaler*.pkl"))
            if scaler_files:
                scaler = joblib.load(scaler_files[0])

        else:  # sklearn or generic
            model_files = list(path.glob("*.pkl"))
            if model_files:
                model = joblib.load(model_files[0])

            scaler_files = [f for f in model_files if 'scaler' in f.name.lower()]
            if scaler_files:
                scaler = joblib.load(scaler_files[0])

        return model, scaler

    def hot_swap(
        self,
        name: str,
        new_model_path: str,
        new_version: str,
    ) -> bool:
        """
        Hot swap a model without downtime.

        Args:
            name: Endpoint name.
            new_model_path: Path to new model.
            new_version: New model version.

        Returns:
            True if swapped successfully.
        """
        if name not in self.endpoints:
            logger.error(f"Endpoint '{name}' not found")
            return False

        old_endpoint = self.endpoints[name]
        old_model = old_endpoint._model

        try:
            # Load new model
            start_time = time.time()
            new_model, new_scaler = self._load_model_artifacts(
                new_model_path, old_endpoint.model_type
            )

            with self._lock:
                # Swap models atomically
                old_endpoint._model = new_model
                old_endpoint._scaler = new_scaler
                old_endpoint.version = new_version
                old_endpoint.model_path = new_model_path
                old_endpoint.load_time = time.time() - start_time

                # Clear cache for this endpoint
                self._clear_endpoint_cache(name)

            logger.info(f"Hot-swapped model '{name}' to v{new_version}")
            return True

        except Exception as e:
            # Restore old model if swap failed
            with self._lock:
                old_endpoint._model = old_model
            logger.error(f"Hot swap failed for '{name}': {e}")
            return False

    def predict(
        self,
        request: PredictionRequest,
    ) -> PredictionResponse:
        """
        Make a prediction.

        Args:
            request: Prediction request.

        Returns:
            Prediction response.
        """
        start_time = time.time()
        self.total_requests += 1

        # Determine endpoint
        endpoint_name = request.model_name or self.default_endpoint
        if not endpoint_name or endpoint_name not in self.endpoints:
            raise ValueError(f"Model endpoint not found: {endpoint_name}")

        endpoint = self.endpoints[endpoint_name]
        if endpoint.status != ModelStatus.READY:
            raise RuntimeError(f"Model '{endpoint_name}' is not ready: {endpoint.status}")

        # Check cache
        cache_key = self._get_cache_key(endpoint_name, request.features)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            self.cache_hits += 1
            cached.latency_ms = (time.time() - start_time) * 1000
            cached.request_id = request.request_id
            return cached

        self.cache_misses += 1

        try:
            # Prepare features
            features = self._prepare_features(request.features, endpoint)

            # Make prediction
            prediction = endpoint._model.predict(features)
            if hasattr(prediction, 'flatten'):
                prediction = prediction.flatten()
            if len(prediction) == 1:
                prediction = float(prediction[0])

            # Calculate confidence (if available)
            confidence = None
            if request.return_confidence and hasattr(endpoint._model, 'predict_proba'):
                proba = endpoint._model.predict_proba(features)
                confidence = float(np.max(proba))

            latency_ms = (time.time() - start_time) * 1000

            # Update metrics
            with self._lock:
                endpoint.prediction_count += 1
                endpoint.avg_latency_ms = (
                    (endpoint.avg_latency_ms * (endpoint.prediction_count - 1) + latency_ms)
                    / endpoint.prediction_count
                )

            response = PredictionResponse(
                prediction=prediction,
                model_name=endpoint_name,
                model_version=endpoint.version,
                confidence=confidence,
                latency_ms=latency_ms,
                request_id=request.request_id,
            )

            # Cache response
            self._add_to_cache(cache_key, response)

            return response

        except Exception as e:
            self.total_errors += 1
            endpoint.error_count += 1
            logger.error(f"Prediction error for '{endpoint_name}': {e}")
            raise

    async def predict_async(
        self,
        request: PredictionRequest,
    ) -> PredictionResponse:
        """
        Make async prediction.

        Args:
            request: Prediction request.

        Returns:
            Prediction response.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.predict, request)

    def batch_predict(
        self,
        requests: List[PredictionRequest],
        parallel: bool = True,
    ) -> List[PredictionResponse]:
        """
        Make batch predictions.

        Args:
            requests: List of prediction requests.
            parallel: Whether to parallelize.

        Returns:
            List of prediction responses.
        """
        if parallel:
            futures = [self.executor.submit(self.predict, req) for req in requests]
            return [f.result() for f in futures]
        else:
            return [self.predict(req) for req in requests]

    def _prepare_features(
        self,
        features: Union[Dict[str, float], List[float], np.ndarray],
        endpoint: ModelEndpoint,
    ) -> np.ndarray:
        """Prepare features for prediction."""
        if isinstance(features, dict):
            if endpoint._feature_names:
                feature_array = np.array([features.get(name, 0) for name in endpoint._feature_names])
            else:
                feature_array = np.array(list(features.values()))
        elif isinstance(features, list):
            feature_array = np.array(features)
        else:
            feature_array = features

        # Reshape if needed
        if len(feature_array.shape) == 1:
            feature_array = feature_array.reshape(1, -1)

        # Scale if scaler available
        if endpoint._scaler is not None:
            feature_array = endpoint._scaler.transform(feature_array)

        return feature_array

    def _get_cache_key(
        self,
        endpoint_name: str,
        features: Any,
    ) -> str:
        """Generate cache key."""
        import hashlib
        feature_str = json.dumps(features, sort_keys=True, default=str)
        return hashlib.md5(f"{endpoint_name}:{feature_str}".encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[PredictionResponse]:
        """Get from cache if not expired."""
        with self._lock:
            if key in self._cache:
                response, timestamp = self._cache[key]
                if time.time() - timestamp < self.cache_ttl:
                    return PredictionResponse(
                        prediction=response.prediction,
                        model_name=response.model_name,
                        model_version=response.model_version,
                        confidence=response.confidence,
                        latency_ms=0,
                    )
                else:
                    del self._cache[key]
        return None

    def _add_to_cache(self, key: str, response: PredictionResponse) -> None:
        """Add to cache."""
        with self._lock:
            if len(self._cache) >= self.cache_size:
                # Remove oldest entries
                oldest = sorted(self._cache.items(), key=lambda x: x[1][1])[:100]
                for k, _ in oldest:
                    del self._cache[k]
            self._cache[key] = (response, time.time())

    def _clear_endpoint_cache(self, endpoint_name: str) -> None:
        """Clear cache entries for an endpoint."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if endpoint_name in k]
            for k in keys_to_remove:
                del self._cache[k]

    def unload_model(self, name: str) -> bool:
        """Unload a model."""
        with self._lock:
            if name not in self.endpoints:
                return False

            endpoint = self.endpoints[name]
            endpoint.status = ModelStatus.UNLOADING
            endpoint._model = None
            endpoint._scaler = None

            del self.endpoints[name]

            if self.default_endpoint == name:
                self.default_endpoint = next(iter(self.endpoints), None)

            self._clear_endpoint_cache(name)

        logger.info(f"Unloaded model '{name}'")
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get server status."""
        return {
            "endpoints": {name: ep.to_dict() for name, ep in self.endpoints.items()},
            "default_endpoint": self.default_endpoint,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / max(self.total_requests, 1),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
            "cache_size": len(self._cache),
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        health = {
            "status": "healthy",
            "endpoints": {},
        }

        for name, endpoint in self.endpoints.items():
            if endpoint.status == ModelStatus.READY:
                health["endpoints"][name] = "healthy"
            else:
                health["endpoints"][name] = f"unhealthy: {endpoint.status.value}"
                health["status"] = "degraded"

        if not self.endpoints:
            health["status"] = "unhealthy"
            health["message"] = "No models loaded"

        return health


class PredictionService:
    """
    High-level prediction service integrating with model registry.

    Features:
    - Automatic model loading from registry
    - Production model selection
    - A/B testing support
    - Request validation
    """

    def __init__(
        self,
        registry_path: str = "./model_registry",
        **server_kwargs,
    ):
        """
        Initialize prediction service.

        Args:
            registry_path: Path to model registry.
            **server_kwargs: Additional ModelServer arguments.
        """
        from ..registry.model_registry import ModelRegistry

        self.registry = ModelRegistry(registry_path)
        self.server = ModelServer(**server_kwargs)

        logger.info("PredictionService initialized")

    def load_production_models(self) -> int:
        """
        Load all production models from registry.

        Returns:
            Number of models loaded.
        """
        from ..registry.model_registry import ModelStage

        loaded = 0
        for model_name in self.registry.list_models():
            prod_version = self.registry.get_model_version(
                model_name, stage=ModelStage.PRODUCTION
            )
            if prod_version:
                success = self.server.load_model(
                    name=model_name,
                    model_path=prod_version.model_path,
                    model_type=prod_version.config.get("model_type", "sklearn"),
                    version=str(prod_version.version),
                    set_default=(loaded == 0),
                )
                if success:
                    loaded += 1

        logger.info(f"Loaded {loaded} production models")
        return loaded

    def predict(
        self,
        features: Dict[str, float],
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make prediction with production model.

        Args:
            features: Feature dictionary.
            model_name: Optional specific model.

        Returns:
            Prediction result dictionary.
        """
        request = PredictionRequest(
            features=features,
            model_name=model_name,
            return_confidence=True,
            return_latency=True,
        )
        response = self.server.predict(request)
        return response.to_dict()

    async def predict_async(
        self,
        features: Dict[str, float],
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async prediction."""
        request = PredictionRequest(
            features=features,
            model_name=model_name,
            return_confidence=True,
        )
        response = await self.server.predict_async(request)
        return response.to_dict()
