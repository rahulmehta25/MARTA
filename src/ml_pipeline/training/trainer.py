"""
Training Orchestrator Module

Unified training pipeline orchestrating data preparation, model training,
evaluation, and registry integration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
import json
import numpy as np
import pandas as pd
import logging
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
import joblib

from ..config.model_config import ModelConfig, LSTMConfig, XGBoostConfig, ModelType
from ..data.temporal_split import TemporalSplitter, TimeSeriesSplit
from ..data.data_validator import DataValidator, ValidationResult
from ..feature_store.feature_store import FeatureStore
from ..registry.model_registry import ModelRegistry, ModelMetrics, ModelStage
from ..evaluation.metrics import ModelEvaluator, EvaluationResult

logger = logging.getLogger(__name__)


@dataclass
class TrainingJob:
    """
    Training job configuration.

    Attributes:
        job_id: Unique job identifier.
        model_config: Model configuration.
        data_path: Path to training data.
        feature_set: Feature set name.
        target_col: Target column name.
        train_ratio: Training data ratio.
        val_ratio: Validation data ratio.
        test_ratio: Test data ratio.
        auto_register: Auto-register to model registry.
        auto_promote: Auto-promote if metrics improve.
    """
    job_id: str
    model_config: ModelConfig
    data_path: Optional[str] = None
    feature_set: str = ""
    target_col: str = "target_dwell_time_seconds"
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    auto_register: bool = True
    auto_promote: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "model_name": self.model_config.name,
            "model_type": self.model_config.model_type.value,
            "data_path": self.data_path,
            "feature_set": self.feature_set,
            "target_col": self.target_col,
            "train_ratio": self.train_ratio,
            "auto_register": self.auto_register,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TrainingResult:
    """
    Training result container.

    Attributes:
        job_id: Job identifier.
        model_name: Model name.
        model_version: Registered version.
        status: Training status.
        metrics: Evaluation metrics.
        training_history: Training history (for neural nets).
        duration_seconds: Training duration.
        artifacts_path: Path to saved artifacts.
        error_message: Error message if failed.
    """
    job_id: str
    model_name: str
    model_version: Optional[int] = None
    status: str = "pending"
    metrics: Dict[str, float] = field(default_factory=dict)
    training_history: Dict[str, List[float]] = field(default_factory=dict)
    duration_seconds: float = 0.0
    artifacts_path: str = ""
    error_message: str = ""
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "status": self.status,
            "metrics": self.metrics,
            "duration_seconds": self.duration_seconds,
            "artifacts_path": self.artifacts_path,
            "error_message": self.error_message,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def save(self, path: str) -> None:
        """Save result to JSON."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class TrainingOrchestrator:
    """
    Unified training orchestrator for ML models.

    Coordinates:
    - Data loading and validation
    - Feature computation
    - Temporal data splitting
    - Model training (LSTM, XGBoost)
    - Evaluation
    - Model registry integration
    - Experiment tracking

    Example:
        >>> orchestrator = TrainingOrchestrator()
        >>> config = ModelConfig(name="demand_lstm", model_type=ModelType.LSTM_ATTENTION)
        >>> result = orchestrator.train(config, data, target_col="target_dwell_time_seconds")
    """

    def __init__(
        self,
        output_dir: str = "./training_output",
        registry_path: str = "./model_registry",
        feature_store_path: str = "./feature_store",
    ):
        """
        Initialize training orchestrator.

        Args:
            output_dir: Directory for training outputs.
            registry_path: Path to model registry.
            feature_store_path: Path to feature store.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.registry = ModelRegistry(registry_path)
        self.feature_store = FeatureStore(feature_store_path)
        self.evaluator = ModelEvaluator(str(self.output_dir / "evaluations"))
        self.validator = DataValidator()
        self.splitter = TemporalSplitter()

        # Scalers and encoders
        self.feature_scaler = StandardScaler()
        self.target_scaler = MinMaxScaler()
        self.label_encoder = LabelEncoder()

        logger.info(f"TrainingOrchestrator initialized, output: {self.output_dir}")

    def train(
        self,
        config: ModelConfig,
        data: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        timestamp_col: str = "timestamp",
        job_id: Optional[str] = None,
        auto_register: bool = True,
    ) -> TrainingResult:
        """
        Run complete training pipeline.

        Args:
            config: Model configuration.
            data: Training DataFrame.
            target_col: Target column name.
            feature_cols: Feature columns (None = auto-detect).
            timestamp_col: Timestamp column.
            job_id: Optional job ID.
            auto_register: Auto-register to model registry.

        Returns:
            TrainingResult with metrics and paths.
        """
        job_id = job_id or f"{config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        result = TrainingResult(
            job_id=job_id,
            model_name=config.name,
            status="running",
        )

        try:
            logger.info(f"Starting training job: {job_id}")

            # 1. Validate data
            validation = self.validator.validate_ml_features(data)
            if not validation.is_valid:
                logger.warning(f"Data validation issues: {len(validation.issues)}")

            # 2. Prepare features
            if feature_cols is None:
                exclude_cols = [target_col, timestamp_col, 'feature_id', 'created_at',
                               'target_demand_level', 'target_dwell_time_seconds']
                feature_cols = [c for c in data.select_dtypes(include=[np.number]).columns
                               if c not in exclude_cols]

            logger.info(f"Using {len(feature_cols)} features")

            # 3. Temporal split
            split = self.splitter.split(
                data,
                timestamp_col=timestamp_col,
                feature_cols=feature_cols,
                target_col=target_col,
            )

            logger.info(f"Data split: train={len(split.X_train)}, val={len(split.X_val)}, test={len(split.X_test)}")

            # 4. Scale features
            X_train = self.feature_scaler.fit_transform(split.X_train)
            X_val = self.feature_scaler.transform(split.X_val)
            X_test = self.feature_scaler.transform(split.X_test)

            y_train, y_val, y_test = split.y_train, split.y_val, split.y_test

            # Scale targets for regression
            if config.lstm_config and config.lstm_config.task_type.value == "regression":
                y_train = self.target_scaler.fit_transform(y_train.reshape(-1, 1)).flatten()
                y_val = self.target_scaler.transform(y_val.reshape(-1, 1)).flatten()
                y_test_scaled = self.target_scaler.transform(y_test.reshape(-1, 1)).flatten()
            else:
                y_test_scaled = y_test

            # 5. Train model based on type
            if config.model_type in [ModelType.LSTM, ModelType.LSTM_ATTENTION]:
                model, history = self._train_lstm(
                    config.lstm_config, X_train, y_train, X_val, y_val, feature_cols
                )
                result.training_history = history or {}
            elif config.model_type == ModelType.XGBOOST:
                model, study_results = self._train_xgboost(
                    config.xgboost_config, X_train, y_train, X_val, y_val, feature_cols
                )
            else:
                raise ValueError(f"Unsupported model type: {config.model_type}")

            # 6. Evaluate
            y_pred_scaled = model.predict(X_test)
            if hasattr(y_pred_scaled, 'flatten'):
                y_pred_scaled = y_pred_scaled.flatten()

            # Inverse transform for evaluation
            if config.lstm_config and config.lstm_config.task_type.value == "regression":
                y_pred = self.target_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
            else:
                y_pred = y_pred_scaled

            evaluation = self.evaluator.evaluate_regression(
                y_test, y_pred, config.name, config.version
            )
            result.metrics = evaluation.regression_metrics.to_dict()

            # 7. Save artifacts
            artifacts_dir = self.output_dir / "artifacts" / job_id
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            if hasattr(model, 'save'):
                model.save(str(artifacts_dir))
            else:
                joblib.dump(model, artifacts_dir / "model.pkl")

            joblib.dump(self.feature_scaler, artifacts_dir / "feature_scaler.pkl")
            joblib.dump(self.target_scaler, artifacts_dir / "target_scaler.pkl")

            # Save config and metadata
            config.save(str(artifacts_dir / "config.yaml"))
            with open(artifacts_dir / "feature_names.json", 'w') as f:
                json.dump(feature_cols, f)

            result.artifacts_path = str(artifacts_dir)

            # 8. Register to model registry
            if auto_register:
                version = self.registry.register_model(
                    model_path=str(artifacts_dir),
                    model_name=config.name,
                    config=config.to_dict(),
                    metrics=ModelMetrics(**{k: v for k, v in result.metrics.items()
                                          if k in ['mae', 'mse', 'rmse', 'r2', 'mape']}),
                    training_info={
                        "job_id": job_id,
                        "train_samples": len(X_train),
                        "val_samples": len(X_val),
                        "test_samples": len(X_test),
                        "feature_count": len(feature_cols),
                    },
                    description=f"Trained by job {job_id}",
                )
                result.model_version = version.version

            result.status = "completed"
            result.completed_at = datetime.now()
            result.duration_seconds = (result.completed_at - start_time).total_seconds()

            logger.info(
                f"Training completed: {config.name} v{result.model_version} "
                f"RMSE={result.metrics.get('rmse', 0):.4f}"
            )

        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            logger.error(f"Training failed: {e}")
            raise

        # Save result
        result.save(str(self.output_dir / f"{job_id}_result.json"))

        return result

    def _train_lstm(
        self,
        config: LSTMConfig,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: List[str],
    ) -> tuple:
        """Train LSTM model."""
        from ..models.attention_lstm import AttentionLSTM

        # Create sequences
        X_train_seq, y_train_seq = self.splitter.create_sequences(
            X_train, y_train, config.sequence_length, config.prediction_horizon
        )
        X_val_seq, y_val_seq = self.splitter.create_sequences(
            X_val, y_val, config.sequence_length, config.prediction_horizon
        )

        logger.info(f"LSTM sequences: train={len(X_train_seq)}, val={len(X_val_seq)}")

        # Build and train model
        model = AttentionLSTM(config, name="demand_lstm")
        model.build_model(input_shape=(config.sequence_length, len(feature_names)))
        model.feature_scaler = self.feature_scaler
        model.target_scaler = self.target_scaler

        history = model.fit(X_train_seq, y_train_seq, X_val_seq, y_val_seq)

        return model, history

    def _train_xgboost(
        self,
        config: XGBoostConfig,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: List[str],
    ) -> tuple:
        """Train XGBoost model."""
        from ..models.xgboost_optuna import XGBoostOptuna

        model = XGBoostOptuna(config, name="demand_xgboost")
        model.feature_scaler = self.feature_scaler

        training_info = model.fit(
            X_train, y_train, X_val, y_val, feature_names=feature_names
        )

        return model, model.study_results

    def run_comparison(
        self,
        configs: List[ModelConfig],
        data: pd.DataFrame,
        target_col: str,
        **train_kwargs,
    ) -> Dict[str, TrainingResult]:
        """
        Train and compare multiple models.

        Args:
            configs: List of model configurations.
            data: Training data.
            target_col: Target column.
            **train_kwargs: Additional training arguments.

        Returns:
            Dictionary of model names to training results.
        """
        results = {}

        for config in configs:
            try:
                result = self.train(config, data, target_col, **train_kwargs)
                results[config.name] = result
            except Exception as e:
                logger.error(f"Failed to train {config.name}: {e}")
                results[config.name] = TrainingResult(
                    job_id=f"{config.name}_failed",
                    model_name=config.name,
                    status="failed",
                    error_message=str(e),
                )

        # Generate comparison
        successful = [r for r in results.values() if r.status == "completed"]
        if successful:
            eval_results = [
                EvaluationResult(
                    model_name=r.model_name,
                    model_version=str(r.model_version or ""),
                    task_type="regression",
                    regression_metrics=self.evaluator.evaluate_regression(
                        np.zeros(10), np.zeros(10), r.model_name  # Placeholder
                    ).regression_metrics,
                )
                for r in successful
            ]

            comparison = self.evaluator.compare_models(eval_results)
            logger.info(f"Best model: {comparison.best_model}")

        return results

    def promote_best_model(
        self,
        model_name: str,
        metric: str = "rmse",
        threshold: Optional[float] = None,
    ) -> bool:
        """
        Promote best model version to production.

        Args:
            model_name: Model name.
            metric: Metric to compare.
            threshold: Required metric threshold.

        Returns:
            True if promoted successfully.
        """
        versions = self.registry.list_versions(model_name)
        if not versions:
            logger.warning(f"No versions found for {model_name}")
            return False

        # Find best version by metric
        best_version = None
        best_value = float('inf')

        for v in versions:
            metric_value = getattr(v.metrics, metric, None)
            if metric_value is not None and metric_value < best_value:
                best_value = metric_value
                best_version = v

        if best_version is None:
            logger.warning(f"No version with metric {metric} found")
            return False

        # Check threshold
        if threshold is not None and best_value > threshold:
            logger.warning(f"Best {metric}={best_value} exceeds threshold {threshold}")
            return False

        # Promote
        self.registry.promote_model(model_name, best_version.version, ModelStage.PRODUCTION)
        logger.info(f"Promoted {model_name} v{best_version.version} to production ({metric}={best_value})")

        return True
