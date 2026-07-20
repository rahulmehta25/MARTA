"""
MLflow Experiment Tracking for MARTA Demand Forecasting

This module provides comprehensive experiment tracking, model versioning,
and model registry functionality using MLflow.
"""
import os
import logging
import hashlib
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import mlflow
import mlflow.tensorflow
import mlflow.xgboost
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from mlflow.entities import Run, Experiment
import tempfile
import shutil
from contextlib import contextmanager
import pickle

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)


class MLExperimentTracker:
    """
    MLflow-based experiment tracking system for MARTA demand forecasting.
    
    Features:
    - Experiment lifecycle management
    - Model versioning and registry
    - Hyperparameter logging
    - Metrics tracking
    - Artifact management
    - Model comparison and selection
    """
    
    def __init__(self, tracking_uri: Optional[str] = None):
        """
        Initialize the ML experiment tracker.
        
        Args:
            tracking_uri: MLflow tracking URI. If None, uses local directory.
        """
        # Set MLflow tracking URI
        if tracking_uri is None:
            tracking_uri = f"file://{os.path.abspath('mlruns')}"
        
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
        
        # Create mlruns directory if it doesn't exist
        os.makedirs("mlruns", exist_ok=True)
        
        # Set default experiment
        self.experiment_name = "marta_demand_forecasting"
        self.experiment_id = self._get_or_create_experiment(self.experiment_name)
        
        logger.info(f"MLflow tracker initialized with URI: {tracking_uri}")
        logger.info(f"Default experiment: {self.experiment_name} (ID: {self.experiment_id})")
    
    def _get_or_create_experiment(self, name: str) -> str:
        """Get or create MLflow experiment."""
        try:
            experiment = mlflow.get_experiment_by_name(name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(name)
                logger.info(f"Created new experiment: {name} (ID: {experiment_id})")
            else:
                experiment_id = experiment.experiment_id
                logger.info(f"Using existing experiment: {name} (ID: {experiment_id})")
            return experiment_id
        except Exception as e:
            logger.error(f"Error creating/getting experiment {name}: {e}")
            raise
    
    @contextmanager
    def start_run(self, 
                  run_name: Optional[str] = None,
                  experiment_name: Optional[str] = None,
                  tags: Optional[Dict[str, str]] = None):
        """
        Context manager for MLflow runs.
        
        Args:
            run_name: Name for the run
            experiment_name: Experiment name (creates if doesn't exist)
            tags: Additional tags for the run
        """
        if experiment_name and experiment_name != self.experiment_name:
            experiment_id = self._get_or_create_experiment(experiment_name)
        else:
            experiment_id = self.experiment_id
        
        # Default tags
        default_tags = {
            "project": "marta_demand_forecasting",
            "framework": "tensorflow_xgboost",
            "environment": "production",
            "created_by": "marta_ml_pipeline"
        }
        
        if tags:
            default_tags.update(tags)
        
        with mlflow.start_run(
            experiment_id=experiment_id,
            run_name=run_name,
            tags=default_tags
        ) as run:
            try:
                yield run
            except Exception as e:
                mlflow.set_tag("status", "failed")
                mlflow.log_param("error", str(e))
                logger.error(f"Run failed: {e}")
                raise
            else:
                mlflow.set_tag("status", "completed")
    
    def log_model_params(self, model_config: Dict[str, Any]) -> None:
        """Log model parameters and hyperparameters."""
        try:
            # Flatten nested dictionaries
            flat_params = self._flatten_dict(model_config)
            
            for key, value in flat_params.items():
                # MLflow params must be strings
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                mlflow.log_param(key, value)
            
            logger.info(f"Logged {len(flat_params)} parameters")
        except Exception as e:
            logger.error(f"Error logging parameters: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log model performance metrics."""
        try:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value, step=step)
                else:
                    logger.warning(f"Skipping non-numeric metric: {key}={value}")
            
            logger.info(f"Logged {len(metrics)} metrics")
        except Exception as e:
            logger.error(f"Error logging metrics: {e}")
    
    def log_model(self, 
                  model: Any, 
                  model_type: str,
                  model_name: str,
                  signature: Optional[Any] = None,
                  input_example: Optional[Any] = None,
                  conda_env: Optional[Dict] = None) -> str:
        """
        Log model to MLflow with appropriate framework.
        
        Returns:
            Model URI for the logged model
        """
        try:
            if model_type.lower() == "tensorflow" or model_type.lower() == "lstm":
                model_uri = mlflow.tensorflow.log_model(
                    model=model,
                    artifact_path=model_name,
                    signature=signature,
                    input_example=input_example,
                    conda_env=conda_env
                )
            elif model_type.lower() == "xgboost":
                model_uri = mlflow.xgboost.log_model(
                    model=model,
                    artifact_path=model_name,
                    signature=signature,
                    input_example=input_example,
                    conda_env=conda_env
                )
            elif model_type.lower() == "sklearn":
                model_uri = mlflow.sklearn.log_model(
                    model=model,
                    artifact_path=model_name,
                    signature=signature,
                    input_example=input_example,
                    conda_env=conda_env
                )
            else:
                # Generic pickle model
                with tempfile.TemporaryDirectory() as temp_dir:
                    model_path = os.path.join(temp_dir, "model.pkl")
                    with open(model_path, "wb") as f:
                        pickle.dump(model, f)
                    mlflow.log_artifact(model_path, model_name)
                    model_uri = f"runs:/{mlflow.active_run().info.run_id}/{model_name}"
            
            logger.info(f"Logged {model_type} model: {model_name}")
            return model_uri
        except Exception as e:
            logger.error(f"Error logging model {model_name}: {e}")
            raise
    
    def log_dataset_info(self, 
                        dataset: pd.DataFrame, 
                        dataset_name: str,
                        version: Optional[str] = None) -> None:
        """Log dataset information and statistics."""
        try:
            # Dataset metadata
            dataset_info = {
                "name": dataset_name,
                "shape": dataset.shape,
                "columns": list(dataset.columns),
                "dtypes": dataset.dtypes.to_dict(),
                "memory_usage_mb": dataset.memory_usage(deep=True).sum() / 1024**2,
                "created_at": datetime.now().isoformat()
            }
            
            if version:
                dataset_info["version"] = version
            
            # Log as parameters
            mlflow.log_param(f"{dataset_name}_shape", str(dataset.shape))
            mlflow.log_param(f"{dataset_name}_columns", len(dataset.columns))
            mlflow.log_param(f"{dataset_name}_memory_mb", round(dataset_info["memory_usage_mb"], 2))
            
            # Log dataset statistics
            numeric_columns = dataset.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                stats = dataset[numeric_columns].describe()
                stats_dict = stats.to_dict()
                
                # Log key statistics
                for col in numeric_columns:
                    mlflow.log_metric(f"{col}_mean", stats_dict[col]["mean"])
                    mlflow.log_metric(f"{col}_std", stats_dict[col]["std"])
                    mlflow.log_metric(f"{col}_min", stats_dict[col]["min"])
                    mlflow.log_metric(f"{col}_max", stats_dict[col]["max"])
            
            # Save dataset info as artifact
            with tempfile.TemporaryDirectory() as temp_dir:
                info_path = os.path.join(temp_dir, f"{dataset_name}_info.json")
                with open(info_path, "w") as f:
                    # Convert numpy types to native Python types for JSON serialization
                    serializable_info = self._make_serializable(dataset_info)
                    json.dump(serializable_info, f, indent=2)
                mlflow.log_artifact(info_path, "datasets")
            
            logger.info(f"Logged dataset info for {dataset_name}")
        except Exception as e:
            logger.error(f"Error logging dataset info: {e}")
    
    def log_feature_importance(self, 
                             feature_importance: Dict[str, float],
                             model_name: str) -> None:
        """Log feature importance scores."""
        try:
            # Log as metrics
            for feature, importance in feature_importance.items():
                mlflow.log_metric(f"feature_importance_{feature}", importance)
            
            # Create and log feature importance chart
            if len(feature_importance) > 0:
                import matplotlib.pyplot as plt
                
                # Sort by importance
                sorted_features = dict(sorted(feature_importance.items(), 
                                            key=lambda x: x[1], reverse=True))
                
                plt.figure(figsize=(12, 8))
                features = list(sorted_features.keys())[:20]  # Top 20 features
                importances = list(sorted_features.values())[:20]
                
                plt.barh(range(len(features)), importances)
                plt.yticks(range(len(features)), features)
                plt.xlabel("Feature Importance")
                plt.title(f"Feature Importance - {model_name}")
                plt.tight_layout()
                
                # Save and log plot
                with tempfile.TemporaryDirectory() as temp_dir:
                    plot_path = os.path.join(temp_dir, f"{model_name}_feature_importance.png")
                    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
                    mlflow.log_artifact(plot_path, "plots")
                
                plt.close()
                
                logger.info(f"Logged feature importance for {model_name}")
        except Exception as e:
            logger.error(f"Error logging feature importance: {e}")
    
    def log_training_history(self, 
                           history: Dict[str, List[float]], 
                           model_name: str) -> None:
        """Log training history (e.g., from Keras)."""
        try:
            # Log final metrics
            for metric, values in history.items():
                if len(values) > 0:
                    mlflow.log_metric(f"final_{metric}", values[-1])
                    
                    # Log all epochs
                    for epoch, value in enumerate(values):
                        mlflow.log_metric(metric, value, step=epoch)
            
            # Create training curves plot
            if history:
                import matplotlib.pyplot as plt
                
                fig, axes = plt.subplots(2, 2, figsize=(12, 10))
                fig.suptitle(f"Training History - {model_name}")
                
                # Common metric pairs
                metric_pairs = [
                    ("loss", "val_loss"),
                    ("mae", "val_mae"),
                    ("mse", "val_mse"),
                    ("accuracy", "val_accuracy")
                ]
                
                plot_idx = 0
                for train_metric, val_metric in metric_pairs:
                    if train_metric in history and val_metric in history and plot_idx < 4:
                        ax = axes[plot_idx // 2, plot_idx % 2]
                        epochs = range(1, len(history[train_metric]) + 1)
                        
                        ax.plot(epochs, history[train_metric], 'b-', label=f'Training {train_metric}')
                        ax.plot(epochs, history[val_metric], 'r-', label=f'Validation {val_metric}')
                        ax.set_xlabel('Epoch')
                        ax.set_ylabel(train_metric.capitalize())
                        ax.legend()
                        ax.grid(True)
                        
                        plot_idx += 1
                
                # Remove empty subplots
                for i in range(plot_idx, 4):
                    axes[i // 2, i % 2].remove()
                
                plt.tight_layout()
                
                # Save and log plot
                with tempfile.TemporaryDirectory() as temp_dir:
                    plot_path = os.path.join(temp_dir, f"{model_name}_training_history.png")
                    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
                    mlflow.log_artifact(plot_path, "plots")
                
                plt.close()
            
            logger.info(f"Logged training history for {model_name}")
        except Exception as e:
            logger.error(f"Error logging training history: {e}")
    
    def log_confusion_matrix(self, 
                           y_true: np.ndarray, 
                           y_pred: np.ndarray,
                           model_name: str,
                           labels: Optional[List[str]] = None) -> None:
        """Log confusion matrix for classification models."""
        try:
            from sklearn.metrics import confusion_matrix, classification_report
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Calculate confusion matrix
            cm = confusion_matrix(y_true, y_pred)
            
            # Create heatmap
            plt.figure(figsize=(8, 6))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                       xticklabels=labels, yticklabels=labels)
            plt.title(f"Confusion Matrix - {model_name}")
            plt.ylabel('True Label')
            plt.xlabel('Predicted Label')
            
            # Save and log plot
            with tempfile.TemporaryDirectory() as temp_dir:
                plot_path = os.path.join(temp_dir, f"{model_name}_confusion_matrix.png")
                plt.savefig(plot_path, dpi=150, bbox_inches='tight')
                mlflow.log_artifact(plot_path, "plots")
            
            plt.close()
            
            # Log classification report
            report = classification_report(y_true, y_pred, output_dict=True)
            for label, metrics in report.items():
                if isinstance(metrics, dict):
                    for metric, value in metrics.items():
                        mlflow.log_metric(f"{label}_{metric}", value)
            
            logger.info(f"Logged confusion matrix for {model_name}")
        except Exception as e:
            logger.error(f"Error logging confusion matrix: {e}")
    
    def register_model(self, 
                      model_uri: str, 
                      model_name: str,
                      version_description: Optional[str] = None,
                      tags: Optional[Dict[str, str]] = None) -> str:
        """
        Register model in MLflow Model Registry.
        
        Returns:
            Model version
        """
        try:
            # Create registered model if it doesn't exist
            try:
                self.client.create_registered_model(model_name)
                logger.info(f"Created registered model: {model_name}")
            except Exception:
                # Model already exists
                pass
            
            # Create model version
            model_version = self.client.create_model_version(
                name=model_name,
                source=model_uri,
                description=version_description
            )
            
            # Add tags if provided
            if tags:
                for key, value in tags.items():
                    self.client.set_model_version_tag(
                        name=model_name,
                        version=model_version.version,
                        key=key,
                        value=value
                    )
            
            logger.info(f"Registered model version {model_version.version} for {model_name}")
            return model_version.version
        except Exception as e:
            logger.error(f"Error registering model {model_name}: {e}")
            raise
    
    def promote_model(self, 
                     model_name: str, 
                     version: str, 
                     stage: str) -> None:
        """
        Promote model to a specific stage (Staging, Production, Archived).
        
        Args:
            model_name: Name of the registered model
            version: Version to promote
            stage: Target stage ('Staging', 'Production', 'Archived')
        """
        try:
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage
            )
            logger.info(f"Promoted model {model_name} v{version} to {stage}")
        except Exception as e:
            logger.error(f"Error promoting model {model_name} v{version}: {e}")
            raise
    
    def get_best_model(self, 
                      experiment_name: str, 
                      metric_name: str,
                      ascending: bool = False) -> Optional[Run]:
        """
        Get the best model from an experiment based on a metric.
        
        Args:
            experiment_name: Name of the experiment
            metric_name: Metric to optimize
            ascending: Whether to sort ascending (True for minimizing metrics)
        
        Returns:
            Best run or None if no runs found
        """
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if not experiment:
                logger.error(f"Experiment {experiment_name} not found")
                return None
            
            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=[f"metrics.{metric_name} {'ASC' if ascending else 'DESC'}"],
                max_results=1
            )
            
            if len(runs) > 0:
                run = runs.iloc[0]
                logger.info(f"Best run: {run['run_id']} with {metric_name}={run[f'metrics.{metric_name}']}")
                return run
            else:
                logger.warning(f"No runs found in experiment {experiment_name}")
                return None
        except Exception as e:
            logger.error(f"Error finding best model: {e}")
            return None
    
    def compare_models(self, 
                      run_ids: List[str], 
                      metrics: List[str]) -> pd.DataFrame:
        """
        Compare multiple models across specified metrics.
        
        Args:
            run_ids: List of MLflow run IDs to compare
            metrics: List of metric names to compare
        
        Returns:
            DataFrame with comparison results
        """
        try:
            comparison_data = []
            
            for run_id in run_ids:
                run = self.client.get_run(run_id)
                row = {
                    "run_id": run_id,
                    "run_name": run.data.tags.get("mlflow.runName", ""),
                    "start_time": run.info.start_time,
                    "status": run.info.status
                }
                
                # Add metrics
                for metric in metrics:
                    metric_value = run.data.metrics.get(metric)
                    row[metric] = metric_value
                
                comparison_data.append(row)
            
            df = pd.DataFrame(comparison_data)
            logger.info(f"Compared {len(run_ids)} models across {len(metrics)} metrics")
            return df
        except Exception as e:
            logger.error(f"Error comparing models: {e}")
            raise
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _make_serializable(self, obj: Any) -> Any:
        """Make object JSON serializable."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        else:
            return obj


# Global experiment tracker instance
_experiment_tracker = None

def get_experiment_tracker() -> MLExperimentTracker:
    """Get global experiment tracker instance (singleton pattern)."""
    global _experiment_tracker
    if _experiment_tracker is None:
        _experiment_tracker = MLExperimentTracker()
    return _experiment_tracker


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    tracker = get_experiment_tracker()
    
    # Example run
    with tracker.start_run(run_name="example_run") as run:
        # Log parameters
        tracker.log_model_params({
            "model_type": "LSTM",
            "epochs": 100,
            "batch_size": 32,
            "learning_rate": 0.001
        })
        
        # Log metrics
        tracker.log_metrics({
            "mse": 0.25,
            "mae": 0.15,
            "r2": 0.85
        })
        
        print(f"Example run completed: {run.info.run_id}")