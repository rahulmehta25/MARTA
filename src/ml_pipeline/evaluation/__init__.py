"""Model evaluation framework with metrics, comparison, reports, and explainability."""

from .metrics import ModelEvaluator, EvaluationResult, ModelComparison
from .explainability import (
    XGBoostExplainer,
    LSTMExplainer,
    ModelExplainerFactory,
    FeatureImportance,
    LocalExplanation,
    AttentionWeights,
)

__all__ = [
    "ModelEvaluator",
    "EvaluationResult",
    "ModelComparison",
    "XGBoostExplainer",
    "LSTMExplainer",
    "ModelExplainerFactory",
    "FeatureImportance",
    "LocalExplanation",
    "AttentionWeights",
]
