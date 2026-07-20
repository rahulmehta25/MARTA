"""
Optuna-based Hyperparameter Optimization for MARTA Demand Forecasting

This module provides automated hyperparameter tuning using Optuna
for LSTM and XGBoost models with MLflow integration.
"""
import os
import logging
import json
from typing import Dict, Any, Optional, List, Callable, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
import optuna
from optuna.integration.mlflow import MLflowCallback
from optuna.samplers import TPESampler, CmaEsSampler
from optuna.pruners import MedianPruner, HyperbandPruner
import mlflow
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam, RMSprop
from tensorflow.keras.callbacks import EarlyStopping
import xgboost as xgb
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from src.models.ml_experiment_tracker import get_experiment_tracker

logger = logging.getLogger(__name__)


class HyperparameterOptimizer:
    """
    Optuna-based hyperparameter optimization for ML models.
    
    Features:
    - Multi-objective optimization
    - Pruning for early stopping of unpromising trials
    - MLflow integration for tracking
    - Support for LSTM and XGBoost models
    - Cross-validation and time-series aware validation
    - Automated search space definition
    """
    
    def __init__(self, 
                 study_name: str = "marta_hyperopt",
                 storage_url: Optional[str] = None,
                 n_trials: int = 100,
                 sampler_name: str = "tpe",
                 pruner_name: str = "median"):
        """
        Initialize hyperparameter optimizer.
        
        Args:
            study_name: Name of the Optuna study
            storage_url: Database URL for study storage (None for in-memory)
            n_trials: Number of optimization trials
            sampler_name: Sampling algorithm ('tpe', 'cmaes', 'random')
            pruner_name: Pruning algorithm ('median', 'hyperband', 'none')
        """
        self.study_name = study_name
        self.storage_url = storage_url
        self.n_trials = n_trials
        
        # Configure sampler
        if sampler_name.lower() == "tpe":
            self.sampler = TPESampler(seed=settings.RANDOM_SEED)
        elif sampler_name.lower() == "cmaes":
            self.sampler = CmaEsSampler(seed=settings.RANDOM_SEED)
        else:
            self.sampler = optuna.samplers.RandomSampler(seed=settings.RANDOM_SEED)
        
        # Configure pruner
        if pruner_name.lower() == "median":
            self.pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=10)
        elif pruner_name.lower() == "hyperband":
            self.pruner = HyperbandPruner(min_resource=1, max_resource=50, reduction_factor=3)
        else:
            self.pruner = optuna.pruners.NopPruner()
        
        # MLflow integration
        self.experiment_tracker = get_experiment_tracker()
        
        # Data placeholders
        self.X_train = None
        self.y_train = None
        self.X_val = None
        self.y_val = None
        self.model_type = None
        
        logger.info(f"Initialized hyperparameter optimizer: {study_name}")
        logger.info(f"Sampler: {sampler_name}, Pruner: {pruner_name}, Trials: {n_trials}")
    
    def set_data(self, 
                 X_train: np.ndarray, 
                 y_train: np.ndarray,
                 X_val: Optional[np.ndarray] = None,
                 y_val: Optional[np.ndarray] = None):
        """Set training and validation data."""
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        
        logger.info(f"Data set - Train: {X_train.shape}, Val: {X_val.shape if X_val is not None else 'None'}")
    
    def create_lstm_search_space(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Define search space for LSTM hyperparameters."""
        params = {
            # Architecture
            'n_layers': trial.suggest_int('n_layers', 1, 3),
            'units_l1': trial.suggest_int('units_l1', 32, 256, step=32),
            'units_l2': trial.suggest_int('units_l2', 16, 128, step=16),
            'units_l3': trial.suggest_int('units_l3', 8, 64, step=8),
            'dense_units': trial.suggest_int('dense_units', 16, 128, step=16),
            
            # Regularization
            'dropout_rate': trial.suggest_float('dropout_rate', 0.1, 0.5, step=0.1),
            'recurrent_dropout': trial.suggest_float('recurrent_dropout', 0.0, 0.3, step=0.1),
            'use_batch_norm': trial.suggest_categorical('use_batch_norm', [True, False]),
            
            # Optimization
            'learning_rate': trial.suggest_float('learning_rate', 1e-4, 1e-2, log=True),
            'optimizer': trial.suggest_categorical('optimizer', ['adam', 'rmsprop']),
            'beta_1': trial.suggest_float('beta_1', 0.8, 0.99, step=0.01),
            'beta_2': trial.suggest_float('beta_2', 0.9, 0.999, step=0.001),
            
            # Training
            'batch_size': trial.suggest_categorical('batch_size', [16, 32, 64, 128]),
            'epochs': trial.suggest_int('epochs', 50, 200, step=25),
            'early_stopping_patience': trial.suggest_int('early_stopping_patience', 10, 30, step=5),
            
            # Data preprocessing
            'sequence_length': trial.suggest_int('sequence_length', 12, 48, step=6)
        }
        
        return params
    
    def create_xgboost_search_space(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Define search space for XGBoost hyperparameters."""
        params = {
            # Tree structure
            'n_estimators': trial.suggest_int('n_estimators', 100, 2000, step=100),
            'max_depth': trial.suggest_int('max_depth', 3, 12),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0, step=0.1),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0, step=0.1),
            'colsample_bylevel': trial.suggest_float('colsample_bylevel', 0.6, 1.0, step=0.1),
            
            # Learning
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'gamma': trial.suggest_float('gamma', 0.0, 1.0, step=0.1),
            'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1.0, 10.0, log=True),
            
            # Other parameters
            'random_state': settings.RANDOM_SEED,
            'n_jobs': -1,
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse'
        }
        
        return params
    
    def build_lstm_model(self, params: Dict[str, Any], input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Build LSTM model with given hyperparameters."""
        model = Sequential()
        
        # First LSTM layer
        model.add(LSTM(
            units=params['units_l1'],
            return_sequences=params['n_layers'] > 1,
            input_shape=input_shape,
            dropout=params['dropout_rate'],
            recurrent_dropout=params['recurrent_dropout']
        ))
        
        if params['use_batch_norm']:
            model.add(BatchNormalization())
        
        # Additional LSTM layers
        if params['n_layers'] > 1:
            model.add(LSTM(
                units=params['units_l2'],
                return_sequences=params['n_layers'] > 2,
                dropout=params['dropout_rate'],
                recurrent_dropout=params['recurrent_dropout']
            ))
            
            if params['use_batch_norm']:
                model.add(BatchNormalization())
        
        if params['n_layers'] > 2:
            model.add(LSTM(
                units=params['units_l3'],
                return_sequences=False,
                dropout=params['dropout_rate'],
                recurrent_dropout=params['recurrent_dropout']
            ))
            
            if params['use_batch_norm']:
                model.add(BatchNormalization())
        
        # Dense layers
        model.add(Dense(params['dense_units'], activation='relu'))
        model.add(Dropout(params['dropout_rate']))
        model.add(Dense(1))  # Output layer
        
        # Configure optimizer
        if params['optimizer'] == 'adam':
            optimizer = Adam(
                learning_rate=params['learning_rate'],
                beta_1=params['beta_1'],
                beta_2=params['beta_2']
            )
        else:
            optimizer = RMSprop(learning_rate=params['learning_rate'])
        
        model.compile(
            optimizer=optimizer,
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def lstm_objective(self, trial: optuna.Trial) -> float:
        """Objective function for LSTM optimization."""
        try:
            # Get hyperparameters
            params = self.create_lstm_search_space(trial)
            
            # Prepare sequences
            sequence_length = params['sequence_length']
            X_sequences = self._create_sequences(self.X_train, sequence_length)
            y_sequences = self.y_train[sequence_length:]
            
            if len(X_sequences) == 0:
                raise optuna.TrialPruned("Not enough data for sequence length")
            
            # Build model
            model = self.build_lstm_model(params, (sequence_length, X_sequences.shape[2]))
            
            # Early stopping callback
            early_stopping = EarlyStopping(
                monitor='val_loss',
                patience=params['early_stopping_patience'],
                restore_best_weights=True,
                verbose=0
            )
            
            # Train model
            history = model.fit(
                X_sequences, y_sequences,
                batch_size=params['batch_size'],
                epochs=params['epochs'],
                validation_split=0.2,
                callbacks=[early_stopping],
                verbose=0
            )
            
            # Calculate validation score
            val_loss = min(history.history['val_loss'])
            
            # Report intermediate values for pruning
            for epoch, loss in enumerate(history.history['val_loss']):
                trial.report(loss, epoch)
                if trial.should_prune():
                    raise optuna.TrialPruned()
            
            return val_loss
            
        except Exception as e:
            logger.error(f"LSTM trial failed: {e}")
            raise optuna.TrialPruned()
    
    def xgboost_objective(self, trial: optuna.Trial) -> float:
        """Objective function for XGBoost optimization."""
        try:
            # Get hyperparameters
            params = self.create_xgboost_search_space(trial)
            
            # Create model
            model = xgb.XGBRegressor(**params)
            
            # Use time series cross-validation
            tscv = TimeSeriesSplit(n_splits=3)
            
            # Calculate cross-validation score
            cv_scores = cross_val_score(
                model, self.X_train, self.y_train,
                cv=tscv,
                scoring='neg_mean_squared_error',
                n_jobs=1  # Avoid nested parallelism
            )
            
            # Return negative MSE (Optuna minimizes)
            score = -cv_scores.mean()
            
            # Report for pruning
            trial.report(score, 0)
            
            return score
            
        except Exception as e:
            logger.error(f"XGBoost trial failed: {e}")
            raise optuna.TrialPruned()
    
    def optimize_lstm(self, 
                     direction: str = "minimize",
                     timeout: Optional[int] = None) -> optuna.Study:
        """
        Optimize LSTM hyperparameters.
        
        Args:
            direction: Optimization direction ('minimize' or 'maximize')
            timeout: Time limit in seconds
            
        Returns:
            Completed Optuna study
        """
        logger.info("Starting LSTM hyperparameter optimization...")
        
        # Create study
        study = optuna.create_study(
            study_name=f"{self.study_name}_lstm",
            storage=self.storage_url,
            sampler=self.sampler,
            pruner=self.pruner,
            direction=direction,
            load_if_exists=True
        )
        
        # MLflow callback
        mlflc = MLflowCallback(
            tracking_uri=mlflow.get_tracking_uri(),
            create_experiment=True
        )
        
        # Optimize
        study.optimize(
            self.lstm_objective,
            n_trials=self.n_trials,
            timeout=timeout,
            callbacks=[mlflc],
            catch=(Exception,)
        )
        
        logger.info("LSTM optimization completed")
        logger.info(f"Best trial: {study.best_trial.number}")
        logger.info(f"Best value: {study.best_value:.4f}")
        logger.info(f"Best params: {study.best_params}")
        
        return study
    
    def optimize_xgboost(self, 
                        direction: str = "minimize",
                        timeout: Optional[int] = None) -> optuna.Study:
        """
        Optimize XGBoost hyperparameters.
        
        Args:
            direction: Optimization direction ('minimize' or 'maximize')
            timeout: Time limit in seconds
            
        Returns:
            Completed Optuna study
        """
        logger.info("Starting XGBoost hyperparameter optimization...")
        
        # Create study
        study = optuna.create_study(
            study_name=f"{self.study_name}_xgboost",
            storage=self.storage_url,
            sampler=self.sampler,
            pruner=self.pruner,
            direction=direction,
            load_if_exists=True
        )
        
        # MLflow callback
        mlflc = MLflowCallback(
            tracking_uri=mlflow.get_tracking_uri(),
            create_experiment=True
        )
        
        # Optimize
        study.optimize(
            self.xgboost_objective,
            n_trials=self.n_trials,
            timeout=timeout,
            callbacks=[mlflc],
            catch=(Exception,)
        )
        
        logger.info("XGBoost optimization completed")
        logger.info(f"Best trial: {study.best_trial.number}")
        logger.info(f"Best value: {study.best_value:.4f}")
        logger.info(f"Best params: {study.best_params}")
        
        return study
    
    def get_best_params(self, study: optuna.Study) -> Dict[str, Any]:
        """Get best parameters from completed study."""
        return study.best_params
    
    def visualize_optimization(self, study: optuna.Study, save_path: str) -> None:
        """Create optimization visualization plots."""
        try:
            import matplotlib.pyplot as plt
            from optuna.visualization.matplotlib import (
                plot_optimization_history,
                plot_param_importances,
                plot_slice
            )
            
            # Create subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle(f"Hyperparameter Optimization Results - {study.study_name}")
            
            # Optimization history
            plot_optimization_history(study, ax=axes[0, 0])
            axes[0, 0].set_title("Optimization History")
            
            # Parameter importances
            plot_param_importances(study, ax=axes[0, 1])
            axes[0, 1].set_title("Parameter Importances")
            
            # Slice plot for top 2 parameters
            important_params = list(study.best_params.keys())[:2]
            if len(important_params) >= 1:
                plot_slice(study, params=important_params[0], ax=axes[1, 0])
                axes[1, 0].set_title(f"Parameter Slice: {important_params[0]}")
            
            if len(important_params) >= 2:
                plot_slice(study, params=important_params[1], ax=axes[1, 1])
                axes[1, 1].set_title(f"Parameter Slice: {important_params[1]}")
            
            plt.tight_layout()
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Optimization visualization saved to {save_path}")
            
        except Exception as e:
            logger.error(f"Error creating optimization visualization: {e}")
    
    def save_study_results(self, 
                          study: optuna.Study, 
                          save_dir: str) -> None:
        """Save study results to files."""
        try:
            os.makedirs(save_dir, exist_ok=True)
            
            # Save study summary
            study_info = {
                "study_name": study.study_name,
                "direction": study.direction.name,
                "n_trials": len(study.trials),
                "best_trial": study.best_trial.number,
                "best_value": study.best_value,
                "best_params": study.best_params,
                "optimization_completed": datetime.now().isoformat()
            }
            
            with open(os.path.join(save_dir, "study_summary.json"), "w") as f:
                json.dump(study_info, f, indent=2)
            
            # Save trials dataframe
            trials_df = study.trials_dataframe()
            trials_df.to_csv(os.path.join(save_dir, "trials.csv"), index=False)
            
            # Save visualization
            viz_path = os.path.join(save_dir, "optimization_plots.png")
            self.visualize_optimization(study, viz_path)
            
            logger.info(f"Study results saved to {save_dir}")
            
        except Exception as e:
            logger.error(f"Error saving study results: {e}")
    
    def _create_sequences(self, data: np.ndarray, sequence_length: int) -> np.ndarray:
        """Create sequences for LSTM training."""
        if len(data) <= sequence_length:
            return np.array([])
        
        sequences = []
        for i in range(len(data) - sequence_length + 1):
            sequences.append(data[i:i + sequence_length])
        
        return np.array(sequences)


def multi_objective_optimization(X_train: np.ndarray, 
                               y_train: np.ndarray,
                               X_val: np.ndarray, 
                               y_val: np.ndarray,
                               n_trials: int = 50) -> Tuple[optuna.Study, optuna.Study]:
    """
    Run multi-objective optimization for both LSTM and XGBoost models.
    
    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data
        n_trials: Number of trials per model
        
    Returns:
        Tuple of (LSTM study, XGBoost study)
    """
    logger.info("Starting multi-objective optimization...")
    
    # Initialize optimizer
    optimizer = HyperparameterOptimizer(
        study_name="marta_multi_objective",
        n_trials=n_trials
    )
    
    # Set data
    optimizer.set_data(X_train, y_train, X_val, y_val)
    
    # Optimize LSTM
    lstm_study = optimizer.optimize_lstm(timeout=3600)  # 1 hour timeout
    
    # Optimize XGBoost
    xgb_study = optimizer.optimize_xgboost(timeout=1800)  # 30 min timeout
    
    # Save results
    results_dir = os.path.join(settings.MODELS_DIR, "hyperparameter_optimization")
    
    optimizer.save_study_results(lstm_study, os.path.join(results_dir, "lstm"))
    optimizer.save_study_results(xgb_study, os.path.join(results_dir, "xgboost"))
    
    logger.info("Multi-objective optimization completed")
    
    return lstm_study, xgb_study


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Generate sample data
    np.random.seed(settings.RANDOM_SEED)
    X_train = np.random.randn(1000, 10)
    y_train = np.random.randn(1000)
    X_val = np.random.randn(200, 10)
    y_val = np.random.randn(200)
    
    # Run optimization
    lstm_study, xgb_study = multi_objective_optimization(
        X_train, y_train, X_val, y_val, n_trials=10
    )
    
    print("LSTM Best Params:", lstm_study.best_params)
    print("XGBoost Best Params:", xgb_study.best_params)