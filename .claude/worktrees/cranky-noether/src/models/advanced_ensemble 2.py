"""
Advanced Ensemble Methods for MARTA Demand Forecasting

This module implements sophisticated ensemble techniques including
stacking, blending, and dynamic weighting for improved predictions.
"""
import os
import logging
import pickle
import json
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, ClassifierMixin
from sklearn.model_selection import KFold, StratifiedKFold, TimeSeriesSplit
from sklearn.linear_model import Ridge, LogisticRegression, ElasticNet
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import catboost as cb
import xgboost as xgb
import tensorflow as tf
from tensorflow import keras
import optuna
import mlflow
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from src.models.ml_experiment_tracker import get_experiment_tracker

logger = logging.getLogger(__name__)


class StackingEnsemble(BaseEstimator, RegressorMixin):
    """
    Advanced stacking ensemble with multiple layers and cross-validation.
    
    Features:
    - Multi-level stacking
    - Cross-validation based meta-learning
    - Automatic feature selection for meta-learner
    - Support for different CV strategies
    - Regularized meta-learners
    """
    
    def __init__(self,
                 base_models: List[Tuple[str, BaseEstimator]],
                 meta_learner: Optional[BaseEstimator] = None,
                 cv_folds: int = 5,
                 cv_strategy: str = "kfold",
                 use_features_in_secondary: bool = True,
                 random_state: int = 42):
        """
        Initialize stacking ensemble.
        
        Args:
            base_models: List of (name, model) tuples
            meta_learner: Meta-learner model (default: Ridge)
            cv_folds: Number of cross-validation folds
            cv_strategy: CV strategy ('kfold', 'stratified', 'timeseries')
            use_features_in_secondary: Whether to use original features in meta-learner
            random_state: Random state for reproducibility
        """
        self.base_models = base_models
        self.meta_learner = meta_learner or Ridge(alpha=1.0, random_state=random_state)
        self.cv_folds = cv_folds
        self.cv_strategy = cv_strategy
        self.use_features_in_secondary = use_features_in_secondary
        self.random_state = random_state
        
        self.trained_base_models_ = []
        self.meta_features_ = None
        self.feature_scaler_ = StandardScaler()
        self.is_fitted_ = False
    
    def _get_cv_splitter(self, X: np.ndarray, y: np.ndarray):
        """Get appropriate cross-validation splitter."""
        if self.cv_strategy == "stratified":
            return StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        elif self.cv_strategy == "timeseries":
            return TimeSeriesSplit(n_splits=self.cv_folds)
        else:
            return KFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'StackingEnsemble':
        """
        Fit the stacking ensemble.
        
        Args:
            X: Training features
            y: Training targets
            
        Returns:
            Self
        """
        logger.info(f"Training stacking ensemble with {len(self.base_models)} base models")
        
        # Initialize meta-features array
        meta_features = np.zeros((X.shape[0], len(self.base_models)))
        
        # Get CV splitter
        cv_splitter = self._get_cv_splitter(X, y)
        
        # Train base models with cross-validation
        self.trained_base_models_ = []
        
        for model_idx, (model_name, base_model) in enumerate(self.base_models):
            logger.info(f"Training base model: {model_name}")
            
            # Store models trained on each fold
            fold_models = []
            fold_predictions = []
            
            for fold, (train_idx, val_idx) in enumerate(cv_splitter.split(X, y)):
                X_train_fold, X_val_fold = X[train_idx], X[val_idx]
                y_train_fold, y_val_fold = y[train_idx], y[val_idx]
                
                # Clone and train model
                model_copy = self._clone_model(base_model)
                model_copy.fit(X_train_fold, y_train_fold)
                
                # Predict on validation set
                val_pred = model_copy.predict(X_val_fold)
                fold_predictions.extend(list(zip(val_idx, val_pred)))
                
                fold_models.append(model_copy)
            
            # Sort predictions by original index
            fold_predictions.sort(key=lambda x: x[0])
            meta_features[:, model_idx] = [pred for _, pred in fold_predictions]
            
            self.trained_base_models_.append((model_name, fold_models))
        
        # Prepare meta-learner features
        if self.use_features_in_secondary:
            # Scale original features
            X_scaled = self.feature_scaler_.fit_transform(X)
            meta_features_full = np.concatenate([meta_features, X_scaled], axis=1)
        else:
            meta_features_full = meta_features
        
        # Train meta-learner
        logger.info("Training meta-learner")
        self.meta_learner.fit(meta_features_full, y)
        
        self.meta_features_ = meta_features
        self.is_fitted_ = True
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions using the stacking ensemble.
        
        Args:
            X: Features for prediction
            
        Returns:
            Predictions
        """
        if not self.is_fitted_:
            raise ValueError("Ensemble must be fitted before making predictions")
        
        # Get base model predictions
        base_predictions = np.zeros((X.shape[0], len(self.trained_base_models_)))
        
        for model_idx, (model_name, fold_models) in enumerate(self.trained_base_models_):
            # Average predictions from all folds
            fold_preds = []
            for model in fold_models:
                fold_preds.append(model.predict(X))
            
            base_predictions[:, model_idx] = np.mean(fold_preds, axis=0)
        
        # Prepare meta-features
        if self.use_features_in_secondary:
            X_scaled = self.feature_scaler_.transform(X)
            meta_features = np.concatenate([base_predictions, X_scaled], axis=1)
        else:
            meta_features = base_predictions
        
        # Make final prediction
        return self.meta_learner.predict(meta_features)
    
    def _clone_model(self, model):
        """Clone a model (handle different model types)."""
        if hasattr(model, 'get_params'):
            # Sklearn-style model
            from sklearn.base import clone
            return clone(model)
        else:
            # Handle other model types
            import copy
            return copy.deepcopy(model)


class BlendingEnsemble(BaseEstimator, RegressorMixin):
    """
    Blending ensemble with optimized weights.
    
    Features:
    - Automatic weight optimization
    - Constrained optimization (weights sum to 1)
    - Multiple optimization objectives
    - Holdout-based validation
    """
    
    def __init__(self,
                 base_models: List[Tuple[str, BaseEstimator]],
                 blend_method: str = "optimal",
                 holdout_size: float = 0.2,
                 random_state: int = 42):
        """
        Initialize blending ensemble.
        
        Args:
            base_models: List of (name, model) tuples
            blend_method: Blending method ('equal', 'optimal', 'rank')
            holdout_size: Size of holdout set for weight optimization
            random_state: Random state
        """
        self.base_models = base_models
        self.blend_method = blend_method
        self.holdout_size = holdout_size
        self.random_state = random_state
        
        self.trained_models_ = []
        self.blend_weights_ = None
        self.is_fitted_ = False
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'BlendingEnsemble':
        """Fit the blending ensemble."""
        logger.info(f"Training blending ensemble with {len(self.base_models)} models")
        
        from sklearn.model_selection import train_test_split
        
        # Split data for training and weight optimization
        if self.blend_method != "equal":
            X_train, X_holdout, y_train, y_holdout = train_test_split(
                X, y, test_size=self.holdout_size, random_state=self.random_state
            )
        else:
            X_train, y_train = X, y
        
        # Train base models
        self.trained_models_ = []
        holdout_predictions = []
        
        for model_name, base_model in self.base_models:
            logger.info(f"Training model: {model_name}")
            
            # Clone and train model
            model_copy = self._clone_model(base_model)
            model_copy.fit(X_train, y_train)
            self.trained_models_.append((model_name, model_copy))
            
            # Get holdout predictions for weight optimization
            if self.blend_method != "equal":
                pred = model_copy.predict(X_holdout)
                holdout_predictions.append(pred)
        
        # Optimize blend weights
        if self.blend_method == "equal":
            self.blend_weights_ = np.ones(len(self.base_models)) / len(self.base_models)
        elif self.blend_method == "optimal":
            self.blend_weights_ = self._optimize_weights(
                np.column_stack(holdout_predictions), y_holdout
            )
        elif self.blend_method == "rank":
            self.blend_weights_ = self._rank_based_weights(
                np.column_stack(holdout_predictions), y_holdout
            )
        
        logger.info(f"Blend weights: {dict(zip([name for name, _ in self.base_models], self.blend_weights_))}")
        
        self.is_fitted_ = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using the blending ensemble."""
        if not self.is_fitted_:
            raise ValueError("Ensemble must be fitted before making predictions")
        
        predictions = []
        for model_name, model in self.trained_models_:
            pred = model.predict(X)
            predictions.append(pred)
        
        # Weighted average
        ensemble_pred = np.average(predictions, axis=0, weights=self.blend_weights_)
        return ensemble_pred
    
    def _optimize_weights(self, predictions: np.ndarray, y_true: np.ndarray) -> np.ndarray:
        """Optimize blend weights using constrained optimization."""
        from scipy.optimize import minimize
        
        def objective(weights):
            ensemble_pred = np.average(predictions, axis=0, weights=weights)
            return mean_squared_error(y_true, ensemble_pred)
        
        # Constraints: weights sum to 1 and are non-negative
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
        ]
        bounds = [(0, 1) for _ in range(len(self.base_models))]
        
        # Initial guess: equal weights
        x0 = np.ones(len(self.base_models)) / len(self.base_models)
        
        # Optimize
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        if result.success:
            return result.x
        else:
            logger.warning("Weight optimization failed, using equal weights")
            return np.ones(len(self.base_models)) / len(self.base_models)
    
    def _rank_based_weights(self, predictions: np.ndarray, y_true: np.ndarray) -> np.ndarray:
        """Calculate weights based on individual model performance."""
        scores = []
        for i in range(predictions.shape[1]):
            score = r2_score(y_true, predictions[:, i])
            scores.append(max(score, 0))  # Ensure non-negative
        
        # Normalize to get weights
        total_score = sum(scores)
        if total_score > 0:
            weights = np.array(scores) / total_score
        else:
            weights = np.ones(len(scores)) / len(scores)
        
        return weights
    
    def _clone_model(self, model):
        """Clone a model."""
        from sklearn.base import clone
        return clone(model)


class DynamicEnsemble(BaseEstimator, RegressorMixin):
    """
    Dynamic ensemble with adaptive weighting based on local performance.
    
    Features:
    - Context-aware model selection
    - Local performance estimation
    - Adaptive weight adjustment
    - Online learning capabilities
    """
    
    def __init__(self,
                 base_models: List[Tuple[str, BaseEstimator]],
                 k_neighbors: int = 10,
                 distance_metric: str = "euclidean",
                 adaptation_rate: float = 0.1):
        """
        Initialize dynamic ensemble.
        
        Args:
            base_models: List of (name, model) tuples
            k_neighbors: Number of neighbors for local performance estimation
            distance_metric: Distance metric for neighbor search
            adaptation_rate: Rate of weight adaptation
        """
        self.base_models = base_models
        self.k_neighbors = k_neighbors
        self.distance_metric = distance_metric
        self.adaptation_rate = adaptation_rate
        
        self.trained_models_ = []
        self.training_data_ = None
        self.training_predictions_ = None
        self.training_errors_ = None
        self.is_fitted_ = False
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'DynamicEnsemble':
        """Fit the dynamic ensemble."""
        logger.info(f"Training dynamic ensemble with {len(self.base_models)} models")
        
        # Train base models
        self.trained_models_ = []
        training_predictions = []
        
        for model_name, base_model in self.base_models:
            logger.info(f"Training model: {model_name}")
            
            model_copy = self._clone_model(base_model)
            model_copy.fit(X, y)
            self.trained_models_.append((model_name, model_copy))
            
            # Get training predictions
            pred = model_copy.predict(X)
            training_predictions.append(pred)
        
        # Store training data and predictions
        self.training_data_ = X.copy()
        self.training_predictions_ = np.column_stack(training_predictions)
        
        # Calculate individual model errors
        self.training_errors_ = np.abs(self.training_predictions_ - y.reshape(-1, 1))
        
        self.is_fitted_ = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using dynamic weighting."""
        if not self.is_fitted_:
            raise ValueError("Ensemble must be fitted before making predictions")
        
        from sklearn.neighbors import NearestNeighbors
        
        # Get predictions from all models
        predictions = []
        for model_name, model in self.trained_models_:
            pred = model.predict(X)
            predictions.append(pred)
        
        predictions = np.column_stack(predictions)
        
        # Find k-nearest neighbors in training data
        nn = NearestNeighbors(n_neighbors=self.k_neighbors, metric=self.distance_metric)
        nn.fit(self.training_data_)
        
        ensemble_predictions = []
        
        for i, x in enumerate(X):
            # Find neighbors
            distances, indices = nn.kneighbors([x])
            neighbor_indices = indices[0]
            neighbor_distances = distances[0]
            
            # Calculate weights based on inverse distance
            distance_weights = 1 / (neighbor_distances + 1e-8)
            distance_weights = distance_weights / np.sum(distance_weights)
            
            # Calculate local model performance
            local_errors = self.training_errors_[neighbor_indices]
            weighted_errors = np.average(local_errors, axis=0, weights=distance_weights)
            
            # Convert errors to weights (lower error = higher weight)
            model_weights = 1 / (weighted_errors + 1e-8)
            model_weights = model_weights / np.sum(model_weights)
            
            # Make weighted prediction
            ensemble_pred = np.average(predictions[i], weights=model_weights)
            ensemble_predictions.append(ensemble_pred)
        
        return np.array(ensemble_predictions)
    
    def _clone_model(self, model):
        """Clone a model."""
        from sklearn.base import clone
        return clone(model)


class AutoEnsemble:
    """
    Automated ensemble system that selects and combines the best ensemble method.
    
    Features:
    - Automatic ensemble method selection
    - Model pool management
    - Performance-based model selection
    - MLflow integration
    """
    
    def __init__(self, 
                 model_pool: Optional[List[Tuple[str, BaseEstimator]]] = None,
                 ensemble_methods: Optional[List[str]] = None,
                 selection_metric: str = "rmse",
                 cv_folds: int = 5):
        """
        Initialize automated ensemble.
        
        Args:
            model_pool: Pool of base models to choose from
            ensemble_methods: List of ensemble methods to try
            selection_metric: Metric for model selection
            cv_folds: Number of CV folds for evaluation
        """
        self.model_pool = model_pool or self._create_default_model_pool()
        self.ensemble_methods = ensemble_methods or ["stacking", "blending", "dynamic"]
        self.selection_metric = selection_metric
        self.cv_folds = cv_folds
        
        self.best_ensemble_ = None
        self.ensemble_results_ = {}
        self.experiment_tracker = get_experiment_tracker()
    
    def _create_default_model_pool(self) -> List[Tuple[str, BaseEstimator]]:
        """Create default model pool."""
        return [
            ("ridge", Ridge(alpha=1.0)),
            ("rf", RandomForestRegressor(n_estimators=100, random_state=42)),
            ("xgb", xgb.XGBRegressor(random_state=42)),
            ("lgb", lgb.LGBMRegressor(random_state=42, verbose=-1)),
            ("et", ExtraTreesRegressor(n_estimators=100, random_state=42)),
            ("svr", SVR(kernel='rbf')),
            ("mlp", MLPRegressor(hidden_layer_sizes=(100, 50), random_state=42, max_iter=500))
        ]
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'AutoEnsemble':
        """Fit automated ensemble system."""
        logger.info("Starting automated ensemble selection and training")
        
        from sklearn.model_selection import cross_val_score
        
        # Track experiment
        with self.experiment_tracker.start_run(
            run_name="auto_ensemble_selection",
            tags={"ensemble_type": "automated", "selection_metric": self.selection_metric}
        ) as run:
            
            ensemble_results = {}
            
            # Try different ensemble methods
            for method in self.ensemble_methods:
                logger.info(f"Evaluating {method} ensemble")
                
                try:
                    if method == "stacking":
                        ensemble = StackingEnsemble(
                            base_models=self.model_pool,
                            cv_folds=self.cv_folds
                        )
                    elif method == "blending":
                        ensemble = BlendingEnsemble(
                            base_models=self.model_pool,
                            blend_method="optimal"
                        )
                    elif method == "dynamic":
                        ensemble = DynamicEnsemble(
                            base_models=self.model_pool
                        )
                    else:
                        continue
                    
                    # Cross-validation evaluation
                    if self.selection_metric == "rmse":
                        scores = cross_val_score(
                            ensemble, X, y,
                            cv=self.cv_folds,
                            scoring='neg_mean_squared_error',
                            n_jobs=-1
                        )
                        score = np.sqrt(-scores.mean())
                    elif self.selection_metric == "r2":
                        scores = cross_val_score(
                            ensemble, X, y,
                            cv=self.cv_folds,
                            scoring='r2',
                            n_jobs=-1
                        )
                        score = scores.mean()
                    else:
                        scores = cross_val_score(
                            ensemble, X, y,
                            cv=self.cv_folds,
                            scoring=self.selection_metric,
                            n_jobs=-1
                        )
                        score = scores.mean()
                    
                    ensemble_results[method] = {
                        "ensemble": ensemble,
                        "score": score,
                        "scores": scores,
                        "std": scores.std()
                    }
                    
                    # Log to MLflow
                    mlflow.log_metric(f"{method}_{self.selection_metric}", score)
                    mlflow.log_metric(f"{method}_{self.selection_metric}_std", scores.std())
                    
                    logger.info(f"{method} ensemble {self.selection_metric}: {score:.4f} ± {scores.std():.4f}")
                    
                except Exception as e:
                    logger.error(f"Failed to evaluate {method} ensemble: {e}")
                    continue
            
            # Select best ensemble
            if ensemble_results:
                if self.selection_metric in ["rmse", "mae"]:
                    # Lower is better
                    best_method = min(ensemble_results.keys(), key=lambda k: ensemble_results[k]["score"])
                else:
                    # Higher is better
                    best_method = max(ensemble_results.keys(), key=lambda k: ensemble_results[k]["score"])
                
                self.best_ensemble_ = ensemble_results[best_method]["ensemble"]
                self.ensemble_results_ = ensemble_results
                
                # Train best ensemble on full data
                self.best_ensemble_.fit(X, y)
                
                # Log best results
                mlflow.log_param("best_ensemble_method", best_method)
                mlflow.log_metric("best_ensemble_score", ensemble_results[best_method]["score"])
                
                logger.info(f"Best ensemble: {best_method} ({self.selection_metric}: {ensemble_results[best_method]['score']:.4f})")
            
            else:
                raise RuntimeError("No ensemble methods were successfully evaluated")
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using the best ensemble."""
        if self.best_ensemble_ is None:
            raise ValueError("AutoEnsemble must be fitted before making predictions")
        
        return self.best_ensemble_.predict(X)
    
    def get_ensemble_comparison(self) -> pd.DataFrame:
        """Get comparison of different ensemble methods."""
        if not self.ensemble_results_:
            raise ValueError("No ensemble results available")
        
        comparison_data = []
        for method, results in self.ensemble_results_.items():
            comparison_data.append({
                "method": method,
                "score": results["score"],
                "std": results["std"],
                "cv_scores": results["scores"]
            })
        
        return pd.DataFrame(comparison_data)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Generate sample data
    np.random.seed(42)
    X = np.random.randn(1000, 10)
    y = np.sum(X[:, :3], axis=1) + np.random.randn(1000) * 0.1
    
    # Test auto ensemble
    auto_ensemble = AutoEnsemble()
    auto_ensemble.fit(X, y)
    
    predictions = auto_ensemble.predict(X[:10])
    print("Predictions:", predictions)
    
    # Show comparison
    comparison = auto_ensemble.get_ensemble_comparison()
    print("\nEnsemble Comparison:")
    print(comparison)