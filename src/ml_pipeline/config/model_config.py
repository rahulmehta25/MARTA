"""
Model Configuration Module

Centralized configuration for all ML models with dataclass-based hyperparameter
management, validation, and serialization support.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import yaml
from pathlib import Path


class ModelType(Enum):
    """Supported model types in the ML pipeline."""
    LSTM = "lstm"
    LSTM_ATTENTION = "lstm_attention"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    ENSEMBLE = "ensemble"


class TaskType(Enum):
    """ML task types."""
    REGRESSION = "regression"
    CLASSIFICATION = "classification"


@dataclass
class TrainingConfig:
    """
    Configuration for model training.

    Attributes:
        batch_size: Number of samples per gradient update.
        epochs: Maximum number of training epochs.
        learning_rate: Initial learning rate for optimizer.
        early_stopping_patience: Epochs to wait before early stopping.
        reduce_lr_patience: Epochs to wait before reducing learning rate.
        reduce_lr_factor: Factor to reduce learning rate by.
        min_lr: Minimum learning rate threshold.
        validation_split: Fraction of data for validation.
        shuffle: Whether to shuffle training data.
        random_seed: Random seed for reproducibility.
    """
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    early_stopping_patience: int = 15
    reduce_lr_patience: int = 5
    reduce_lr_factor: float = 0.5
    min_lr: float = 1e-7
    validation_split: float = 0.2
    shuffle: bool = True
    random_seed: int = 42

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)


@dataclass
class LSTMConfig:
    """
    Configuration for LSTM models with attention mechanism.

    Attributes:
        sequence_length: Number of timesteps in input sequence.
        prediction_horizon: Number of timesteps to predict ahead.
        lstm_units: List of units per LSTM layer.
        attention_units: Number of units in attention layer.
        use_attention: Whether to use attention mechanism.
        dropout_rate: Dropout rate between layers.
        recurrent_dropout: Dropout rate for recurrent connections.
        bidirectional: Whether to use bidirectional LSTM.
        num_heads: Number of attention heads (for multi-head attention).
        use_layer_norm: Whether to use layer normalization.
        dense_units: List of units for dense layers after LSTM.
        activation: Activation function for dense layers.
        output_activation: Activation for output layer.
        task_type: Regression or classification task.
        num_classes: Number of classes (for classification).
        training: Training configuration.
    """
    sequence_length: int = 24
    prediction_horizon: int = 1
    lstm_units: List[int] = field(default_factory=lambda: [128, 64, 32])
    attention_units: int = 64
    use_attention: bool = True
    dropout_rate: float = 0.2
    recurrent_dropout: float = 0.1
    bidirectional: bool = False
    num_heads: int = 4
    use_layer_norm: bool = True
    dense_units: List[int] = field(default_factory=lambda: [32, 16])
    activation: str = "relu"
    output_activation: str = "linear"
    task_type: TaskType = TaskType.REGRESSION
    num_classes: int = 4
    training: TrainingConfig = field(default_factory=TrainingConfig)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if isinstance(self.task_type, str):
            self.task_type = TaskType(self.task_type)
        if self.sequence_length < 1:
            raise ValueError("sequence_length must be >= 1")
        if self.prediction_horizon < 1:
            raise ValueError("prediction_horizon must be >= 1")
        if not self.lstm_units:
            raise ValueError("lstm_units must have at least one layer")
        if self.dropout_rate < 0 or self.dropout_rate > 1:
            raise ValueError("dropout_rate must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        d = asdict(self)
        d['task_type'] = self.task_type.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LSTMConfig":
        """Create config from dictionary."""
        if 'training' in d and isinstance(d['training'], dict):
            d['training'] = TrainingConfig(**d['training'])
        if 'task_type' in d and isinstance(d['task_type'], str):
            d['task_type'] = TaskType(d['task_type'])
        return cls(**d)


@dataclass
class XGBoostConfig:
    """
    Configuration for XGBoost models with Optuna tuning support.

    Attributes:
        objective: Learning objective function.
        n_estimators: Number of boosting rounds.
        max_depth: Maximum tree depth.
        learning_rate: Boosting learning rate (eta).
        subsample: Subsample ratio of training instances.
        colsample_bytree: Subsample ratio of columns.
        colsample_bylevel: Subsample ratio of columns per level.
        min_child_weight: Minimum sum of instance weight in child.
        reg_alpha: L1 regularization term.
        reg_lambda: L2 regularization term.
        gamma: Minimum loss reduction for split.
        scale_pos_weight: Balance of positive and negative weights.
        early_stopping_rounds: Rounds for early stopping.
        eval_metric: Evaluation metric(s) for validation.
        n_jobs: Number of parallel threads.
        random_state: Random seed for reproducibility.
        use_optuna: Whether to use Optuna for hyperparameter tuning.
        optuna_n_trials: Number of Optuna optimization trials.
        optuna_timeout: Timeout for Optuna optimization in seconds.
        cv_folds: Number of cross-validation folds.
        task_type: Regression or classification task.
        num_classes: Number of classes (for classification).
    """
    objective: str = "reg:squarederror"
    n_estimators: int = 1000
    max_depth: int = 6
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    colsample_bylevel: float = 0.8
    min_child_weight: int = 1
    reg_alpha: float = 0.0
    reg_lambda: float = 1.0
    gamma: float = 0.0
    scale_pos_weight: float = 1.0
    early_stopping_rounds: int = 50
    eval_metric: List[str] = field(default_factory=lambda: ["rmse", "mae"])
    n_jobs: int = -1
    random_state: int = 42
    use_optuna: bool = True
    optuna_n_trials: int = 100
    optuna_timeout: int = 3600
    cv_folds: int = 5
    task_type: TaskType = TaskType.REGRESSION
    num_classes: int = 4

    # Search space for Optuna
    optuna_search_space: Dict[str, Any] = field(default_factory=lambda: {
        "max_depth": {"type": "int", "low": 3, "high": 12},
        "learning_rate": {"type": "float", "low": 0.01, "high": 0.3, "log": True},
        "n_estimators": {"type": "int", "low": 100, "high": 2000},
        "subsample": {"type": "float", "low": 0.5, "high": 1.0},
        "colsample_bytree": {"type": "float", "low": 0.5, "high": 1.0},
        "min_child_weight": {"type": "int", "low": 1, "high": 10},
        "reg_alpha": {"type": "float", "low": 1e-8, "high": 10.0, "log": True},
        "reg_lambda": {"type": "float", "low": 1e-8, "high": 10.0, "log": True},
        "gamma": {"type": "float", "low": 0.0, "high": 5.0},
    })

    def __post_init__(self):
        """Validate configuration after initialization."""
        if isinstance(self.task_type, str):
            self.task_type = TaskType(self.task_type)
        if self.task_type == TaskType.CLASSIFICATION:
            self.objective = "multi:softprob"
            self.eval_metric = ["mlogloss", "merror"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        d = asdict(self)
        d['task_type'] = self.task_type.value
        return d

    def get_xgb_params(self) -> Dict[str, Any]:
        """Get parameters for XGBoost model initialization."""
        return {
            "objective": self.objective,
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "colsample_bylevel": self.colsample_bylevel,
            "min_child_weight": self.min_child_weight,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "gamma": self.gamma,
            "scale_pos_weight": self.scale_pos_weight,
            "n_jobs": self.n_jobs,
            "random_state": self.random_state,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "XGBoostConfig":
        """Create config from dictionary."""
        if 'task_type' in d and isinstance(d['task_type'], str):
            d['task_type'] = TaskType(d['task_type'])
        return cls(**d)


@dataclass
class ModelConfig:
    """
    Unified model configuration container.

    Attributes:
        name: Model name identifier.
        version: Model version string.
        model_type: Type of model (LSTM, XGBoost, etc.).
        description: Human-readable model description.
        lstm_config: Configuration for LSTM models.
        xgboost_config: Configuration for XGBoost models.
        feature_names: List of input feature names.
        target_name: Name of target variable.
        metadata: Additional metadata dictionary.
    """
    name: str
    version: str = "1.0.0"
    model_type: ModelType = ModelType.LSTM_ATTENTION
    description: str = ""
    lstm_config: Optional[LSTMConfig] = None
    xgboost_config: Optional[XGBoostConfig] = None
    feature_names: List[str] = field(default_factory=list)
    target_name: str = "target"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize appropriate config based on model type."""
        if isinstance(self.model_type, str):
            self.model_type = ModelType(self.model_type)

        if self.model_type in [ModelType.LSTM, ModelType.LSTM_ATTENTION]:
            if self.lstm_config is None:
                self.lstm_config = LSTMConfig()
        elif self.model_type == ModelType.XGBOOST:
            if self.xgboost_config is None:
                self.xgboost_config = XGBoostConfig()

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        d = {
            "name": self.name,
            "version": self.version,
            "model_type": self.model_type.value,
            "description": self.description,
            "feature_names": self.feature_names,
            "target_name": self.target_name,
            "metadata": self.metadata,
        }
        if self.lstm_config:
            d["lstm_config"] = self.lstm_config.to_dict()
        if self.xgboost_config:
            d["xgboost_config"] = self.xgboost_config.to_dict()
        return d

    def save(self, path: str) -> None:
        """Save configuration to YAML file."""
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

    @classmethod
    def load(cls, path: str) -> "ModelConfig":
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            d = yaml.safe_load(f)

        if 'lstm_config' in d and d['lstm_config']:
            d['lstm_config'] = LSTMConfig.from_dict(d['lstm_config'])
        if 'xgboost_config' in d and d['xgboost_config']:
            d['xgboost_config'] = XGBoostConfig.from_dict(d['xgboost_config'])
        if 'model_type' in d:
            d['model_type'] = ModelType(d['model_type'])

        return cls(**d)


def get_default_lstm_config(task: str = "regression") -> LSTMConfig:
    """
    Get default LSTM configuration for a specific task.

    Args:
        task: Either 'regression' or 'classification'.

    Returns:
        LSTMConfig with sensible defaults.
    """
    task_type = TaskType.REGRESSION if task == "regression" else TaskType.CLASSIFICATION
    config = LSTMConfig(
        sequence_length=24,
        prediction_horizon=1,
        lstm_units=[128, 64, 32],
        attention_units=64,
        use_attention=True,
        dropout_rate=0.2,
        bidirectional=False,
        num_heads=4,
        use_layer_norm=True,
        task_type=task_type,
        training=TrainingConfig(
            batch_size=32,
            epochs=100,
            learning_rate=0.001,
            early_stopping_patience=15,
        )
    )

    if task_type == TaskType.CLASSIFICATION:
        config.output_activation = "softmax"

    return config


def get_default_xgboost_config(task: str = "regression") -> XGBoostConfig:
    """
    Get default XGBoost configuration for a specific task.

    Args:
        task: Either 'regression' or 'classification'.

    Returns:
        XGBoostConfig with sensible defaults.
    """
    task_type = TaskType.REGRESSION if task == "regression" else TaskType.CLASSIFICATION
    return XGBoostConfig(
        n_estimators=1000,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_optuna=True,
        optuna_n_trials=100,
        cv_folds=5,
        task_type=task_type,
    )
