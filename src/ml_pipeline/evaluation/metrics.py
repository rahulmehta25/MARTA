"""
Model Evaluation Framework

Comprehensive evaluation metrics, comparison, and reporting for ML models.
Supports regression, classification, and time series specific metrics.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from pathlib import Path
import json
import numpy as np
import pandas as pd
import logging

from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, roc_auc_score,
    precision_recall_curve, roc_curve
)

logger = logging.getLogger(__name__)


@dataclass
class RegressionMetrics:
    """
    Regression evaluation metrics.

    Attributes:
        mae: Mean Absolute Error.
        mse: Mean Squared Error.
        rmse: Root Mean Squared Error.
        r2: R-squared score.
        mape: Mean Absolute Percentage Error.
        medae: Median Absolute Error.
        max_error: Maximum absolute error.
        explained_variance: Explained variance score.
    """
    mae: float
    mse: float
    rmse: float
    r2: float
    mape: float
    medae: float = 0.0
    max_error: float = 0.0
    explained_variance: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "mae": self.mae,
            "mse": self.mse,
            "rmse": self.rmse,
            "r2": self.r2,
            "mape": self.mape,
            "medae": self.medae,
            "max_error": self.max_error,
            "explained_variance": self.explained_variance,
        }

    def summary(self) -> str:
        """Get summary string."""
        return (
            f"RMSE: {self.rmse:.4f}, MAE: {self.mae:.4f}, "
            f"R2: {self.r2:.4f}, MAPE: {self.mape:.2f}%"
        )


@dataclass
class ClassificationMetrics:
    """
    Classification evaluation metrics.

    Attributes:
        accuracy: Overall accuracy.
        precision_macro: Macro-averaged precision.
        recall_macro: Macro-averaged recall.
        f1_macro: Macro-averaged F1 score.
        f1_weighted: Weighted F1 score.
        roc_auc: ROC AUC score.
        confusion_matrix: Confusion matrix.
        classification_report: Per-class metrics.
    """
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    f1_weighted: float
    roc_auc: Optional[float] = None
    confusion_matrix: Optional[np.ndarray] = None
    classification_report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = {
            "accuracy": self.accuracy,
            "precision_macro": self.precision_macro,
            "recall_macro": self.recall_macro,
            "f1_macro": self.f1_macro,
            "f1_weighted": self.f1_weighted,
        }
        if self.roc_auc is not None:
            d["roc_auc"] = self.roc_auc
        if self.confusion_matrix is not None:
            d["confusion_matrix"] = self.confusion_matrix.tolist()
        if self.classification_report is not None:
            d["classification_report"] = self.classification_report
        return d

    def summary(self) -> str:
        """Get summary string."""
        return (
            f"Accuracy: {self.accuracy:.4f}, F1 (macro): {self.f1_macro:.4f}, "
            f"Precision: {self.precision_macro:.4f}, Recall: {self.recall_macro:.4f}"
        )


@dataclass
class TimeSeriesMetrics:
    """
    Time series specific evaluation metrics.

    Attributes:
        directional_accuracy: Correct direction prediction rate.
        forecast_bias: Systematic over/under prediction.
        mase: Mean Absolute Scaled Error.
        smape: Symmetric Mean Absolute Percentage Error.
        coverage: Prediction interval coverage (if applicable).
    """
    directional_accuracy: float = 0.0
    forecast_bias: float = 0.0
    mase: float = 0.0
    smape: float = 0.0
    coverage: Optional[float] = None

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        d = {
            "directional_accuracy": self.directional_accuracy,
            "forecast_bias": self.forecast_bias,
            "mase": self.mase,
            "smape": self.smape,
        }
        if self.coverage is not None:
            d["coverage"] = self.coverage
        return d


@dataclass
class EvaluationResult:
    """
    Complete evaluation result.

    Attributes:
        model_name: Name of evaluated model.
        model_version: Model version.
        task_type: Task type (regression/classification).
        regression_metrics: Regression metrics (if applicable).
        classification_metrics: Classification metrics (if applicable).
        time_series_metrics: Time series metrics (if applicable).
        dataset_info: Information about evaluation dataset.
        evaluated_at: Evaluation timestamp.
        evaluation_time_seconds: Time taken for evaluation.
    """
    model_name: str
    model_version: str = ""
    task_type: str = "regression"
    regression_metrics: Optional[RegressionMetrics] = None
    classification_metrics: Optional[ClassificationMetrics] = None
    time_series_metrics: Optional[TimeSeriesMetrics] = None
    dataset_info: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.now)
    evaluation_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "task_type": self.task_type,
            "dataset_info": self.dataset_info,
            "evaluated_at": self.evaluated_at.isoformat(),
            "evaluation_time_seconds": self.evaluation_time_seconds,
        }
        if self.regression_metrics:
            d["regression_metrics"] = self.regression_metrics.to_dict()
        if self.classification_metrics:
            d["classification_metrics"] = self.classification_metrics.to_dict()
        if self.time_series_metrics:
            d["time_series_metrics"] = self.time_series_metrics.to_dict()
        return d

    def save(self, path: str) -> None:
        """Save evaluation result to JSON."""
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @property
    def primary_metric(self) -> float:
        """Get primary metric value."""
        if self.regression_metrics:
            return self.regression_metrics.rmse
        if self.classification_metrics:
            return self.classification_metrics.f1_macro
        return 0.0


@dataclass
class ModelComparison:
    """
    Comparison results across multiple models.

    Attributes:
        models: List of model names.
        metrics: Metric names being compared.
        results: Comparison data.
        best_model: Best performing model.
        comparison_timestamp: When comparison was made.
    """
    models: List[str]
    metrics: List[str]
    results: pd.DataFrame = field(default_factory=pd.DataFrame)
    best_model: str = ""
    comparison_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "models": self.models,
            "metrics": self.metrics,
            "results": self.results.to_dict('records'),
            "best_model": self.best_model,
            "comparison_timestamp": self.comparison_timestamp.isoformat(),
        }


class ModelEvaluator:
    """
    Comprehensive model evaluation framework.

    Features:
    - Regression and classification metrics
    - Time series specific evaluation
    - Model comparison
    - Evaluation reports
    - Metric visualization support

    Example:
        >>> evaluator = ModelEvaluator()
        >>> result = evaluator.evaluate_regression(y_true, y_pred, model_name="lstm_v1")
        >>> print(result.regression_metrics.summary())
    """

    def __init__(self, output_dir: str = "./evaluation_results"):
        """
        Initialize model evaluator.

        Args:
            output_dir: Directory for saving evaluation results.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.evaluation_history: List[EvaluationResult] = []

        logger.info(f"ModelEvaluator initialized, output: {self.output_dir}")

    def evaluate_regression(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str,
        model_version: str = "",
        dataset_info: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate regression model.

        Args:
            y_true: True target values.
            y_pred: Predicted values.
            model_name: Model name.
            model_version: Model version.
            dataset_info: Information about evaluation dataset.

        Returns:
            EvaluationResult with regression metrics.
        """
        start_time = datetime.now()

        # Flatten arrays
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        # Compute metrics
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_true, y_pred)

        # MAPE (avoid division by zero)
        mask = y_true != 0
        if mask.any():
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        else:
            mape = 0.0

        # Additional metrics
        medae = np.median(np.abs(y_true - y_pred))
        max_error = np.max(np.abs(y_true - y_pred))

        # Explained variance
        explained_var = 1 - np.var(y_true - y_pred) / np.var(y_true) if np.var(y_true) > 0 else 0

        regression_metrics = RegressionMetrics(
            mae=mae,
            mse=mse,
            rmse=rmse,
            r2=r2,
            mape=mape,
            medae=medae,
            max_error=max_error,
            explained_variance=explained_var,
        )

        # Time series metrics
        ts_metrics = self._compute_time_series_metrics(y_true, y_pred)

        eval_time = (datetime.now() - start_time).total_seconds()

        result = EvaluationResult(
            model_name=model_name,
            model_version=model_version,
            task_type="regression",
            regression_metrics=regression_metrics,
            time_series_metrics=ts_metrics,
            dataset_info=dataset_info or {"n_samples": len(y_true)},
            evaluation_time_seconds=eval_time,
        )

        self.evaluation_history.append(result)
        logger.info(f"Evaluated {model_name}: {regression_metrics.summary()}")

        return result

    def evaluate_classification(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str,
        model_version: str = "",
        class_names: Optional[List[str]] = None,
        y_prob: Optional[np.ndarray] = None,
        dataset_info: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        """
        Evaluate classification model.

        Args:
            y_true: True labels.
            y_pred: Predicted labels.
            model_name: Model name.
            model_version: Model version.
            class_names: Names of classes.
            y_prob: Prediction probabilities (for ROC AUC).
            dataset_info: Information about evaluation dataset.

        Returns:
            EvaluationResult with classification metrics.
        """
        start_time = datetime.now()

        # Flatten arrays
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        # Compute metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision_macro = precision_score(y_true, y_pred, average='macro', zero_division=0)
        recall_macro = recall_score(y_true, y_pred, average='macro', zero_division=0)
        f1_macro = f1_score(y_true, y_pred, average='macro', zero_division=0)
        f1_weighted = f1_score(y_true, y_pred, average='weighted', zero_division=0)

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)

        # Classification report
        target_names = class_names or [str(i) for i in np.unique(y_true)]
        report = classification_report(y_true, y_pred, target_names=target_names, output_dict=True, zero_division=0)

        # ROC AUC (multiclass)
        roc_auc = None
        if y_prob is not None:
            try:
                roc_auc = roc_auc_score(y_true, y_prob, multi_class='ovr', average='macro')
            except Exception as e:
                logger.warning(f"Could not compute ROC AUC: {e}")

        classification_metrics = ClassificationMetrics(
            accuracy=accuracy,
            precision_macro=precision_macro,
            recall_macro=recall_macro,
            f1_macro=f1_macro,
            f1_weighted=f1_weighted,
            roc_auc=roc_auc,
            confusion_matrix=cm,
            classification_report=report,
        )

        eval_time = (datetime.now() - start_time).total_seconds()

        result = EvaluationResult(
            model_name=model_name,
            model_version=model_version,
            task_type="classification",
            classification_metrics=classification_metrics,
            dataset_info=dataset_info or {"n_samples": len(y_true)},
            evaluation_time_seconds=eval_time,
        )

        self.evaluation_history.append(result)
        logger.info(f"Evaluated {model_name}: {classification_metrics.summary()}")

        return result

    def _compute_time_series_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> TimeSeriesMetrics:
        """Compute time series specific metrics."""

        # Directional accuracy (correct trend prediction)
        if len(y_true) > 1:
            true_direction = np.sign(np.diff(y_true))
            pred_direction = np.sign(np.diff(y_pred))
            directional_accuracy = np.mean(true_direction == pred_direction)
        else:
            directional_accuracy = 0.0

        # Forecast bias (mean error)
        forecast_bias = np.mean(y_pred - y_true)

        # SMAPE (Symmetric MAPE)
        denominator = np.abs(y_true) + np.abs(y_pred)
        mask = denominator > 0
        if mask.any():
            smape = np.mean(2 * np.abs(y_true[mask] - y_pred[mask]) / denominator[mask]) * 100
        else:
            smape = 0.0

        # MASE (Mean Absolute Scaled Error) - using naive forecast
        if len(y_true) > 1:
            naive_error = np.mean(np.abs(np.diff(y_true)))
            if naive_error > 0:
                mase = np.mean(np.abs(y_true - y_pred)) / naive_error
            else:
                mase = 0.0
        else:
            mase = 0.0

        return TimeSeriesMetrics(
            directional_accuracy=directional_accuracy,
            forecast_bias=forecast_bias,
            mase=mase,
            smape=smape,
        )

    def compare_models(
        self,
        results: List[EvaluationResult],
        metrics: Optional[List[str]] = None,
        primary_metric: str = "rmse",
        ascending: bool = True,
    ) -> ModelComparison:
        """
        Compare multiple model evaluations.

        Args:
            results: List of evaluation results.
            metrics: Metrics to compare.
            primary_metric: Metric for ranking.
            ascending: Sort order for primary metric.

        Returns:
            ModelComparison with comparison data.
        """
        if not results:
            return ModelComparison(models=[], metrics=[], results=pd.DataFrame())

        # Determine task type from first result
        task_type = results[0].task_type

        if metrics is None:
            if task_type == "regression":
                metrics = ["rmse", "mae", "r2", "mape"]
            else:
                metrics = ["accuracy", "f1_macro", "precision_macro", "recall_macro"]

        # Build comparison dataframe
        comparison_data = []
        for result in results:
            row = {
                "model_name": result.model_name,
                "model_version": result.model_version,
            }

            if result.regression_metrics:
                row.update(result.regression_metrics.to_dict())
            if result.classification_metrics:
                row.update(result.classification_metrics.to_dict())
            if result.time_series_metrics:
                row.update(result.time_series_metrics.to_dict())

            comparison_data.append(row)

        df = pd.DataFrame(comparison_data)

        # Sort by primary metric
        if primary_metric in df.columns:
            df = df.sort_values(primary_metric, ascending=ascending)

        # Determine best model
        best_model = df.iloc[0]["model_name"] if len(df) > 0 else ""

        comparison = ModelComparison(
            models=[r.model_name for r in results],
            metrics=metrics,
            results=df,
            best_model=best_model,
        )

        logger.info(f"Compared {len(results)} models, best: {best_model}")
        return comparison

    def generate_report(
        self,
        result: EvaluationResult,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate evaluation report.

        Args:
            result: Evaluation result.
            output_path: Path to save report.

        Returns:
            Report dictionary.
        """
        report = {
            "model": {
                "name": result.model_name,
                "version": result.model_version,
                "task_type": result.task_type,
            },
            "dataset": result.dataset_info,
            "metrics": {},
            "evaluation_info": {
                "evaluated_at": result.evaluated_at.isoformat(),
                "evaluation_time_seconds": result.evaluation_time_seconds,
            },
        }

        if result.regression_metrics:
            report["metrics"]["regression"] = result.regression_metrics.to_dict()
            report["summary"] = result.regression_metrics.summary()

        if result.classification_metrics:
            report["metrics"]["classification"] = result.classification_metrics.to_dict()
            report["summary"] = result.classification_metrics.summary()

        if result.time_series_metrics:
            report["metrics"]["time_series"] = result.time_series_metrics.to_dict()

        # Save report
        if output_path:
            report_path = Path(output_path)
        else:
            report_path = self.output_dir / f"{result.model_name}_{result.model_version}_report.json"

        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Report saved to {report_path}")
        return report

    def get_evaluation_history(
        self,
        model_name: Optional[str] = None,
    ) -> List[EvaluationResult]:
        """
        Get evaluation history.

        Args:
            model_name: Filter by model name.

        Returns:
            List of evaluation results.
        """
        if model_name:
            return [r for r in self.evaluation_history if r.model_name == model_name]
        return self.evaluation_history

    def compute_baseline_metrics(
        self,
        y_true: np.ndarray,
        task_type: str = "regression",
    ) -> Dict[str, float]:
        """
        Compute baseline metrics for comparison.

        Args:
            y_true: True values.
            task_type: Task type.

        Returns:
            Baseline metrics dictionary.
        """
        y_true = np.asarray(y_true).flatten()

        if task_type == "regression":
            # Mean baseline
            mean_pred = np.full_like(y_true, np.mean(y_true))
            mean_rmse = np.sqrt(mean_squared_error(y_true, mean_pred))

            # Naive baseline (persistence)
            naive_pred = np.roll(y_true, 1)
            naive_pred[0] = y_true[0]
            naive_rmse = np.sqrt(mean_squared_error(y_true, naive_pred))

            return {
                "mean_baseline_rmse": mean_rmse,
                "naive_baseline_rmse": naive_rmse,
            }
        else:
            # Majority class baseline
            from collections import Counter
            majority_class = Counter(y_true).most_common(1)[0][0]
            majority_pred = np.full_like(y_true, majority_class)
            majority_accuracy = accuracy_score(y_true, majority_pred)

            return {
                "majority_baseline_accuracy": majority_accuracy,
            }
