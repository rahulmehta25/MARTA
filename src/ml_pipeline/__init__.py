"""
MARTA ML Pipeline - Modern Machine Learning Infrastructure

This package provides a comprehensive, modular ML pipeline for transit demand
forecasting including:
- Advanced models (LSTM with attention, XGBoost with Optuna tuning)
- Feature store with versioning
- Model registry with promotion workflows
- Temporal-aware data splitting
- Comprehensive evaluation framework
- Production-ready model serving

Modules:
    config: Hyperparameter configurations and model settings
    data: Data validation, preprocessing, and temporal splitting
    models: ML model implementations (LSTM, XGBoost, ensemble)
    feature_store: Centralized feature computation and serving
    registry: Model versioning, tracking, and promotion
    training: Training orchestration and experiment tracking
    evaluation: Metrics, comparison, and evaluation reports
    inference: Real-time and batch prediction serving
"""

__version__ = "2.0.0"
__author__ = "MARTA ML Team"

from .config.model_config import ModelConfig, LSTMConfig, XGBoostConfig
from .registry.model_registry import ModelRegistry, ModelVersion
from .feature_store.feature_store import FeatureStore
from .evaluation.metrics import ModelEvaluator

__all__ = [
    "ModelConfig",
    "LSTMConfig",
    "XGBoostConfig",
    "ModelRegistry",
    "ModelVersion",
    "FeatureStore",
    "ModelEvaluator",
]
