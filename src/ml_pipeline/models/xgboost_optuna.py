"""
XGBoost with Optuna Hyperparameter Optimization

Implements XGBoost model with Optuna-based hyperparameter tuning,
cross-validation, and comprehensive feature engineering pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
import numpy as np
import pandas as pd
import logging
from pathlib import Path
import json
from datetime import datetime

import xgboost as xgb
from sklearn.model_selection import cross_val_score, KFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    accuracy_score, f1_score, classification_report
)
import joblib

try:
    import optuna
    from optuna.pruners import MedianPruner
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class OptunaStudyResults:
    """
    Results from Optuna hyperparameter optimization.

    Attributes:
        best_params: Best hyperparameters found.
        best_score: Best objective score achieved.
        n_trials: Number of trials completed.
        optimization_history: History of trial scores.
        study_name: Name of the Optuna study.
        duration_seconds: Total optimization time.
    """
    best_params: Dict[str, Any]
    best_score: float
    n_trials: int
    optimization_history: List[float] = field(default_factory=list)
    study_name: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "n_trials": self.n_trials,
            "optimization_history": self.optimization_history,
            "study_name": self.study_name,
            "duration_seconds": self.duration_seconds,
        }


class XGBoostOptuna:
    """
    XGBoost model with Optuna hyperparameter optimization.

    Features:
    - Optuna-based hyperparameter tuning with pruning
    - Cross-validation for robust evaluation
    - Feature importance analysis
    - Support for regression and classification
    - Early stopping during training
    - Comprehensive feature engineering pipeline

    Example:
        >>> from src.ml_pipeline.config import XGBoostConfig
        >>> config = XGBoostConfig(use_optuna=True, optuna_n_trials=50)
        >>> model = XGBoostOptuna(config)
        >>> model.optimize(X_train, y_train, X_val, y_val)
        >>> predictions = model.predict(X_test)
    """

    def __init__(
        self,
        config: Any,
        name: str = "xgboost_optuna"
    ):
        """
        Initialize XGBoostOptuna model.

        Args:
            config: XGBoostConfig with hyperparameters.
            name: Model name for saving/loading.
        """
        self.config = config
        self.name = name
        self.model: Optional[xgb.XGBModel] = None
        self.feature_scaler: Optional[StandardScaler] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.feature_names: List[str] = []
        self.study_results: Optional[OptunaStudyResults] = None
        self.feature_importance_: Optional[Dict[str, float]] = None

        logger.info(f"Initialized XGBoostOptuna: {name}")

    def _create_objective(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_folds: int = 5,
    ) -> Callable:
        """
        Create Optuna objective function.

        Args:
            X: Training features.
            y: Training targets.
            cv_folds: Number of cross-validation folds.

        Returns:
            Objective function for Optuna.
        """
        cfg = self.config
        search_space = cfg.optuna_search_space

        def objective(trial: optuna.Trial) -> float:
            # Sample hyperparameters
            params = {}
            for param_name, param_config in search_space.items():
                if param_config["type"] == "int":
                    params[param_name] = trial.suggest_int(
                        param_name,
                        param_config["low"],
                        param_config["high"]
                    )
                elif param_config["type"] == "float":
                    if param_config.get("log", False):
                        params[param_name] = trial.suggest_float(
                            param_name,
                            param_config["low"],
                            param_config["high"],
                            log=True
                        )
                    else:
                        params[param_name] = trial.suggest_float(
                            param_name,
                            param_config["low"],
                            param_config["high"]
                        )
                elif param_config["type"] == "categorical":
                    params[param_name] = trial.suggest_categorical(
                        param_name,
                        param_config["choices"]
                    )

            # Fixed parameters
            params.update({
                "objective": cfg.objective,
                "n_jobs": cfg.n_jobs,
                "random_state": cfg.random_state,
                "early_stopping_rounds": cfg.early_stopping_rounds,
            })

            # Create model
            if cfg.task_type.value == "classification":
                params["num_class"] = cfg.num_classes
                model = xgb.XGBClassifier(**params)
                scoring = 'accuracy'
                cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=cfg.random_state)
            else:
                model = xgb.XGBRegressor(**params)
                scoring = 'neg_mean_squared_error'
                cv = KFold(n_splits=cv_folds, shuffle=True, random_state=cfg.random_state)

            # Cross-validation with pruning
            scores = []
            for fold_idx, (train_idx, val_idx) in enumerate(cv.split(X, y)):
                X_fold_train, X_fold_val = X[train_idx], X[val_idx]
                y_fold_train, y_fold_val = y[train_idx], y[val_idx]

                model.fit(
                    X_fold_train, y_fold_train,
                    eval_set=[(X_fold_val, y_fold_val)],
                    verbose=False
                )

                if cfg.task_type.value == "classification":
                    y_pred = model.predict(X_fold_val)
                    score = accuracy_score(y_fold_val, y_pred)
                else:
                    y_pred = model.predict(X_fold_val)
                    score = -mean_squared_error(y_fold_val, y_pred)  # Negative for minimization

                scores.append(score)

                # Report for pruning
                trial.report(np.mean(scores), fold_idx)
                if trial.should_prune():
                    raise optuna.TrialPruned()

            return np.mean(scores)

        return objective

    def optimize(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
    ) -> OptunaStudyResults:
        """
        Run Optuna hyperparameter optimization.

        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features (optional).
            y_val: Validation targets (optional).
            feature_names: Names of features.

        Returns:
            OptunaStudyResults with best parameters and history.
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError("Optuna not installed. Run: pip install optuna")

        cfg = self.config
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X_train.shape[1])]

        logger.info(f"Starting Optuna optimization with {cfg.optuna_n_trials} trials")

        # Create study
        study_name = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        sampler = TPESampler(seed=cfg.random_state)
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=3)

        study = optuna.create_study(
            study_name=study_name,
            direction="maximize" if cfg.task_type.value == "classification" else "maximize",
            sampler=sampler,
            pruner=pruner,
        )

        # Optimization
        start_time = datetime.now()

        objective = self._create_objective(X_train, y_train, cfg.cv_folds)

        study.optimize(
            objective,
            n_trials=cfg.optuna_n_trials,
            timeout=cfg.optuna_timeout,
            show_progress_bar=True,
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Get results
        self.study_results = OptunaStudyResults(
            best_params=study.best_params,
            best_score=study.best_value,
            n_trials=len(study.trials),
            optimization_history=[t.value for t in study.trials if t.value is not None],
            study_name=study_name,
            duration_seconds=duration,
        )

        logger.info(f"Optimization complete. Best score: {study.best_value:.4f}")
        logger.info(f"Best params: {study.best_params}")

        # Train final model with best params
        self._train_final_model(X_train, y_train, X_val, y_val, study.best_params)

        return self.study_results

    def _train_final_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray],
        y_val: Optional[np.ndarray],
        best_params: Dict[str, Any],
    ) -> None:
        """Train final model with best hyperparameters."""
        cfg = self.config

        # Merge best params with fixed params
        params = {
            "objective": cfg.objective,
            "n_jobs": cfg.n_jobs,
            "random_state": cfg.random_state,
            "early_stopping_rounds": cfg.early_stopping_rounds,
            **best_params
        }

        if cfg.task_type.value == "classification":
            params["num_class"] = cfg.num_classes
            self.model = xgb.XGBClassifier(**params)
        else:
            self.model = xgb.XGBRegressor(**params)

        # Prepare eval set
        eval_set = [(X_train, y_train)]
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))

        # Train
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=True
        )

        # Store feature importance
        self.feature_importance_ = dict(zip(
            self.feature_names,
            self.model.feature_importances_
        ))

        logger.info(f"Final model trained with {self.model.n_estimators} estimators")

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Train model (with or without Optuna optimization).

        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features.
            y_val: Validation targets.
            feature_names: Names of features.

        Returns:
            Training info dictionary.
        """
        cfg = self.config
        self.feature_names = feature_names or [f"feature_{i}" for i in range(X_train.shape[1])]

        if cfg.use_optuna:
            self.optimize(X_train, y_train, X_val, y_val, feature_names)
            return {
                "method": "optuna",
                "best_params": self.study_results.best_params if self.study_results else {},
                "best_score": self.study_results.best_score if self.study_results else None,
            }
        else:
            # Train with default config
            params = cfg.get_xgb_params()

            if cfg.task_type.value == "classification":
                params["num_class"] = cfg.num_classes
                self.model = xgb.XGBClassifier(**params)
            else:
                self.model = xgb.XGBRegressor(**params)

            eval_set = [(X_train, y_train)]
            if X_val is not None and y_val is not None:
                eval_set.append((X_val, y_val))

            self.model.fit(
                X_train, y_train,
                eval_set=eval_set,
                verbose=True
            )

            self.feature_importance_ = dict(zip(
                self.feature_names,
                self.model.feature_importances_
            ))

            return {
                "method": "default",
                "params": params,
            }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Input features.

        Returns:
            Model predictions.
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Get prediction probabilities (classification only).

        Args:
            X: Input features.

        Returns:
            Prediction probabilities.
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        if self.config.task_type.value != "classification":
            raise ValueError("predict_proba only available for classification")

        return self.model.predict_proba(X)

    def get_feature_importance(
        self,
        importance_type: str = "weight"
    ) -> pd.DataFrame:
        """
        Get feature importance scores.

        Args:
            importance_type: Type of importance ('weight', 'gain', 'cover').

        Returns:
            DataFrame with feature importance.
        """
        if self.model is None:
            raise ValueError("Model not trained.")

        booster = self.model.get_booster()
        importance = booster.get_score(importance_type=importance_type)

        df = pd.DataFrame([
            {"feature": self.feature_names[int(k.replace('f', ''))] if k.startswith('f') else k,
             "importance": v}
            for k, v in importance.items()
        ])

        return df.sort_values("importance", ascending=False).reset_index(drop=True)

    def cross_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_folds: int = 5,
    ) -> Dict[str, Any]:
        """
        Perform cross-validation.

        Args:
            X: Features.
            y: Targets.
            cv_folds: Number of folds.

        Returns:
            Cross-validation results.
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        cfg = self.config

        if cfg.task_type.value == "classification":
            cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=cfg.random_state)
            scoring = 'accuracy'
        else:
            cv = KFold(n_splits=cv_folds, shuffle=True, random_state=cfg.random_state)
            scoring = 'neg_mean_squared_error'

        scores = cross_val_score(self.model, X, y, cv=cv, scoring=scoring)

        return {
            "scores": scores.tolist(),
            "mean": float(np.mean(scores)),
            "std": float(np.std(scores)),
            "cv_folds": cv_folds,
        }

    def evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate model performance.

        Args:
            X: Test features.
            y: Test targets.

        Returns:
            Dictionary of evaluation metrics.
        """
        y_pred = self.predict(X)

        if self.config.task_type.value == "classification":
            return {
                "accuracy": accuracy_score(y, y_pred),
                "f1_macro": f1_score(y, y_pred, average='macro'),
                "f1_weighted": f1_score(y, y_pred, average='weighted'),
            }
        else:
            return {
                "mse": mean_squared_error(y, y_pred),
                "rmse": np.sqrt(mean_squared_error(y, y_pred)),
                "mae": mean_absolute_error(y, y_pred),
                "r2": r2_score(y, y_pred),
                "mape": np.mean(np.abs((y - y_pred) / (y + 1e-8))) * 100,
            }

    def save(self, path: str) -> None:
        """
        Save model and metadata.

        Args:
            path: Directory path for saving.
        """
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = save_dir / f"{self.name}_model.json"
        self.model.save_model(model_path)

        # Save metadata
        meta = {
            "name": self.name,
            "config": self.config.to_dict(),
            "feature_names": self.feature_names,
            "feature_importance": self.feature_importance_,
            "study_results": self.study_results.to_dict() if self.study_results else None,
            "saved_at": datetime.now().isoformat(),
        }
        with open(save_dir / f"{self.name}_meta.json", 'w') as f:
            json.dump(meta, f, indent=2, default=str)

        # Save scalers
        if self.feature_scaler:
            joblib.dump(self.feature_scaler, save_dir / f"{self.name}_scaler.pkl")
        if self.label_encoder:
            joblib.dump(self.label_encoder, save_dir / f"{self.name}_encoder.pkl")

        logger.info(f"Model saved to {save_dir}")

    @classmethod
    def load(cls, path: str) -> "XGBoostOptuna":
        """
        Load model from directory.

        Args:
            path: Directory containing saved model.

        Returns:
            Loaded XGBoostOptuna instance.
        """
        from ..config.model_config import XGBoostConfig

        load_dir = Path(path)

        # Find model file
        model_files = list(load_dir.glob("*_model.json"))
        if not model_files:
            raise FileNotFoundError(f"No model file found in {load_dir}")

        model_path = model_files[0]
        name = model_path.stem.replace("_model", "")

        # Load metadata
        meta_path = load_dir / f"{name}_meta.json"
        with open(meta_path, 'r') as f:
            meta = json.load(f)

        config = XGBoostConfig.from_dict(meta['config'])

        # Create instance
        instance = cls(config=config, name=name)
        instance.feature_names = meta.get('feature_names', [])
        instance.feature_importance_ = meta.get('feature_importance')

        # Load model
        if config.task_type.value == "classification":
            instance.model = xgb.XGBClassifier()
        else:
            instance.model = xgb.XGBRegressor()
        instance.model.load_model(model_path)

        # Load scalers
        scaler_path = load_dir / f"{name}_scaler.pkl"
        encoder_path = load_dir / f"{name}_encoder.pkl"

        if scaler_path.exists():
            instance.feature_scaler = joblib.load(scaler_path)
        if encoder_path.exists():
            instance.label_encoder = joblib.load(encoder_path)

        logger.info(f"Model loaded from {load_dir}")
        return instance
