"""
Model Explainability Module

SHAP-based explainability for XGBoost and attention visualization for LSTM models.
Provides both global and local explanations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class FeatureImportance:
    """
    Feature importance container.

    Attributes:
        feature_names: List of feature names.
        importance_values: Importance scores per feature.
        importance_type: Type of importance (shap, gain, permutation).
        model_name: Model name.
    """
    feature_names: List[str]
    importance_values: np.ndarray
    importance_type: str = "shap"
    model_name: str = ""

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to sorted DataFrame."""
        df = pd.DataFrame({
            "feature": self.feature_names,
            "importance": self.importance_values,
        })
        return df.sort_values("importance", ascending=False).reset_index(drop=True)

    def top_features(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top N features."""
        df = self.to_dataframe()
        return list(zip(df["feature"].head(n), df["importance"].head(n)))


@dataclass
class LocalExplanation:
    """
    Local explanation for a single prediction.

    Attributes:
        instance_id: Instance identifier.
        prediction: Model prediction.
        base_value: Expected/baseline value.
        feature_contributions: Contribution of each feature.
        feature_names: Feature names.
        feature_values: Actual feature values.
    """
    instance_id: str
    prediction: float
    base_value: float
    feature_contributions: np.ndarray
    feature_names: List[str]
    feature_values: np.ndarray

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instance_id": self.instance_id,
            "prediction": float(self.prediction),
            "base_value": float(self.base_value),
            "contributions": {
                name: {"value": float(val), "contribution": float(contrib)}
                for name, val, contrib in zip(
                    self.feature_names,
                    self.feature_values,
                    self.feature_contributions
                )
            },
        }

    def top_contributors(self, n: int = 5) -> List[Tuple[str, float, float]]:
        """Get top contributing features."""
        sorted_idx = np.argsort(np.abs(self.feature_contributions))[::-1]
        return [
            (
                self.feature_names[i],
                float(self.feature_values[i]),
                float(self.feature_contributions[i])
            )
            for i in sorted_idx[:n]
        ]


@dataclass
class AttentionWeights:
    """
    Attention weights from LSTM model.

    Attributes:
        instance_id: Instance identifier.
        weights: Attention weights per timestep.
        timesteps: Timestep labels.
        prediction: Model prediction.
    """
    instance_id: str
    weights: np.ndarray
    timesteps: List[str]
    prediction: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instance_id": self.instance_id,
            "weights": {ts: float(w) for ts, w in zip(self.timesteps, self.weights)},
            "prediction": float(self.prediction),
        }

    def top_timesteps(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get top attended timesteps."""
        sorted_idx = np.argsort(self.weights)[::-1]
        return [(self.timesteps[i], float(self.weights[i])) for i in sorted_idx[:n]]


class XGBoostExplainer:
    """
    SHAP-based explainer for XGBoost models.

    Features:
    - Global feature importance (SHAP values)
    - Local explanations for individual predictions
    - Feature interaction analysis
    - Dependence plots
    """

    def __init__(self, model: Any, feature_names: List[str]):
        """
        Initialize XGBoost explainer.

        Args:
            model: Trained XGBoost model.
            feature_names: List of feature names.
        """
        self.model = model
        self.feature_names = feature_names
        self.shap_values = None
        self.base_value = None

        try:
            import shap
            self.shap_explainer = shap.TreeExplainer(model)
            logger.info("SHAP TreeExplainer initialized for XGBoost")
        except ImportError:
            logger.warning("SHAP not installed. Install with: pip install shap")
            self.shap_explainer = None

    def compute_shap_values(
        self,
        X: np.ndarray,
        max_samples: int = 1000
    ) -> np.ndarray:
        """
        Compute SHAP values for dataset.

        Args:
            X: Feature array.
            max_samples: Maximum samples to use.

        Returns:
            SHAP values array.
        """
        if self.shap_explainer is None:
            raise RuntimeError("SHAP explainer not available")

        # Sample if needed
        if len(X) > max_samples:
            indices = np.random.choice(len(X), max_samples, replace=False)
            X_sample = X[indices]
        else:
            X_sample = X

        self.shap_values = self.shap_explainer.shap_values(X_sample)
        self.base_value = self.shap_explainer.expected_value

        logger.info(f"Computed SHAP values for {len(X_sample)} samples")
        return self.shap_values

    def get_global_importance(self, X: np.ndarray = None) -> FeatureImportance:
        """
        Get global feature importance from SHAP values.

        Args:
            X: Optional feature array to compute SHAP values.

        Returns:
            FeatureImportance object.
        """
        if X is not None:
            self.compute_shap_values(X)

        if self.shap_values is None:
            raise ValueError("SHAP values not computed. Call compute_shap_values first.")

        # Mean absolute SHAP value per feature
        mean_shap = np.abs(self.shap_values).mean(axis=0)

        return FeatureImportance(
            feature_names=self.feature_names,
            importance_values=mean_shap,
            importance_type="shap",
            model_name="xgboost",
        )

    def explain_instance(
        self,
        X_instance: np.ndarray,
        instance_id: str = "sample"
    ) -> LocalExplanation:
        """
        Explain a single prediction.

        Args:
            X_instance: Single instance features.
            instance_id: Instance identifier.

        Returns:
            LocalExplanation object.
        """
        if self.shap_explainer is None:
            raise RuntimeError("SHAP explainer not available")

        # Ensure 2D
        if X_instance.ndim == 1:
            X_instance = X_instance.reshape(1, -1)

        shap_values = self.shap_explainer.shap_values(X_instance)
        prediction = self.model.predict(X_instance)[0]

        return LocalExplanation(
            instance_id=instance_id,
            prediction=float(prediction),
            base_value=float(self.shap_explainer.expected_value),
            feature_contributions=shap_values[0],
            feature_names=self.feature_names,
            feature_values=X_instance[0],
        )

    def save_explanations(
        self,
        output_dir: str,
        X: np.ndarray,
        sample_indices: Optional[List[int]] = None,
    ) -> Dict[str, str]:
        """
        Save explanation artifacts.

        Args:
            output_dir: Output directory.
            X: Feature array.
            sample_indices: Indices of samples to explain locally.

        Returns:
            Dictionary of saved file paths.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_paths = {}

        # Compute and save global importance
        if self.shap_values is None:
            self.compute_shap_values(X)

        importance = self.get_global_importance()
        importance_path = output_path / "global_importance.csv"
        importance.to_dataframe().to_csv(importance_path, index=False)
        saved_paths["global_importance"] = str(importance_path)

        # Save local explanations
        if sample_indices is None:
            sample_indices = list(range(min(5, len(X))))

        local_explanations = []
        for idx in sample_indices:
            exp = self.explain_instance(X[idx], f"sample_{idx}")
            local_explanations.append(exp.to_dict())

        local_path = output_path / "local_explanations.json"
        with open(local_path, 'w') as f:
            json.dump(local_explanations, f, indent=2)
        saved_paths["local_explanations"] = str(local_path)

        logger.info(f"Saved explanations to {output_path}")
        return saved_paths


class LSTMExplainer:
    """
    Attention-based explainer for LSTM models.

    Features:
    - Attention weight visualization
    - Temporal importance analysis
    - Feature importance from attention
    """

    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        sequence_length: int = 24
    ):
        """
        Initialize LSTM explainer.

        Args:
            model: Trained AttentionLSTM model.
            feature_names: List of feature names.
            sequence_length: Sequence length.
        """
        self.model = model
        self.feature_names = feature_names
        self.sequence_length = sequence_length

    def get_attention_weights(
        self,
        X_sequence: np.ndarray,
        instance_id: str = "sample"
    ) -> AttentionWeights:
        """
        Get attention weights for a sequence.

        Args:
            X_sequence: Input sequence (seq_len, n_features).
            instance_id: Instance identifier.

        Returns:
            AttentionWeights object.
        """
        if X_sequence.ndim == 2:
            X_sequence = X_sequence.reshape(1, *X_sequence.shape)

        # Check if model has attention
        if hasattr(self.model, 'get_attention_weights'):
            weights = self.model.get_attention_weights(X_sequence)
            weights = weights[0]  # First sample
        elif hasattr(self.model, 'attention_model') and self.model.attention_model is not None:
            _, weights = self.model.attention_model.predict(X_sequence, verbose=0)
            weights = weights[0]
        else:
            # Fallback: uniform weights
            logger.warning("Model does not have attention weights")
            weights = np.ones(self.sequence_length) / self.sequence_length

        prediction = self.model.predict(X_sequence)
        if hasattr(prediction, 'flatten'):
            prediction = prediction.flatten()[0]

        # Create timestep labels
        timesteps = [f"t-{self.sequence_length - i - 1}" for i in range(self.sequence_length)]

        return AttentionWeights(
            instance_id=instance_id,
            weights=weights,
            timesteps=timesteps,
            prediction=float(prediction),
        )

    def get_feature_attention(
        self,
        X_sequences: np.ndarray,
    ) -> FeatureImportance:
        """
        Get feature importance based on attention-weighted features.

        This computes importance by looking at which features have high
        values when attention is high.

        Args:
            X_sequences: Input sequences (n_samples, seq_len, n_features).

        Returns:
            FeatureImportance object.
        """
        if X_sequences.ndim == 2:
            X_sequences = X_sequences.reshape(1, *X_sequences.shape)

        n_samples = len(X_sequences)
        feature_importance = np.zeros(len(self.feature_names))

        for i in range(n_samples):
            attn = self.get_attention_weights(X_sequences[i], f"sample_{i}")
            weights = attn.weights.reshape(-1, 1)

            # Weighted average of feature values
            weighted_features = np.abs(X_sequences[i]) * weights
            feature_importance += weighted_features.mean(axis=0)

        feature_importance /= n_samples

        return FeatureImportance(
            feature_names=self.feature_names,
            importance_values=feature_importance,
            importance_type="attention",
            model_name="lstm",
        )

    def analyze_temporal_patterns(
        self,
        X_sequences: np.ndarray,
        n_samples: int = 100,
    ) -> Dict[str, Any]:
        """
        Analyze temporal attention patterns.

        Args:
            X_sequences: Input sequences.
            n_samples: Number of samples to analyze.

        Returns:
            Temporal pattern analysis.
        """
        if len(X_sequences) > n_samples:
            indices = np.random.choice(len(X_sequences), n_samples, replace=False)
            X_sample = X_sequences[indices]
        else:
            X_sample = X_sequences

        all_weights = []
        for i in range(len(X_sample)):
            attn = self.get_attention_weights(X_sample[i], f"sample_{i}")
            all_weights.append(attn.weights)

        all_weights = np.array(all_weights)

        # Analyze patterns
        mean_weights = all_weights.mean(axis=0)
        std_weights = all_weights.std(axis=0)

        # Find most important timesteps on average
        top_timesteps = np.argsort(mean_weights)[::-1][:5]

        return {
            "mean_attention": {f"t-{self.sequence_length - i - 1}": float(mean_weights[i])
                              for i in range(len(mean_weights))},
            "std_attention": {f"t-{self.sequence_length - i - 1}": float(std_weights[i])
                             for i in range(len(std_weights))},
            "top_timesteps": [f"t-{self.sequence_length - i - 1}" for i in top_timesteps],
            "recency_bias": float(mean_weights[-5:].mean() / mean_weights[:-5].mean())
            if len(mean_weights) > 5 else 1.0,
        }

    def save_explanations(
        self,
        output_dir: str,
        X_sequences: np.ndarray,
        sample_indices: Optional[List[int]] = None,
    ) -> Dict[str, str]:
        """
        Save LSTM explanation artifacts.

        Args:
            output_dir: Output directory.
            X_sequences: Input sequences.
            sample_indices: Indices of samples to explain.

        Returns:
            Dictionary of saved file paths.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_paths = {}

        # Feature importance
        importance = self.get_feature_attention(X_sequences[:100])
        importance_path = output_path / "feature_importance.csv"
        importance.to_dataframe().to_csv(importance_path, index=False)
        saved_paths["feature_importance"] = str(importance_path)

        # Temporal patterns
        patterns = self.analyze_temporal_patterns(X_sequences)
        patterns_path = output_path / "temporal_patterns.json"
        with open(patterns_path, 'w') as f:
            json.dump(patterns, f, indent=2)
        saved_paths["temporal_patterns"] = str(patterns_path)

        # Sample attention weights
        if sample_indices is None:
            sample_indices = list(range(min(5, len(X_sequences))))

        attention_data = []
        for idx in sample_indices:
            attn = self.get_attention_weights(X_sequences[idx], f"sample_{idx}")
            attention_data.append(attn.to_dict())

        attention_path = output_path / "sample_attention.json"
        with open(attention_path, 'w') as f:
            json.dump(attention_data, f, indent=2)
        saved_paths["sample_attention"] = str(attention_path)

        logger.info(f"Saved LSTM explanations to {output_path}")
        return saved_paths


class ModelExplainerFactory:
    """Factory for creating appropriate model explainers."""

    @staticmethod
    def create_explainer(
        model: Any,
        model_type: str,
        feature_names: List[str],
        **kwargs
    ) -> Union[XGBoostExplainer, LSTMExplainer]:
        """
        Create explainer for model type.

        Args:
            model: Trained model.
            model_type: Type of model.
            feature_names: Feature names.
            **kwargs: Additional arguments.

        Returns:
            Appropriate explainer instance.
        """
        if model_type.lower() in ["xgboost", "xgb", "tree", "ensemble"]:
            return XGBoostExplainer(model, feature_names)
        elif model_type.lower() in ["lstm", "lstm_attention", "rnn"]:
            return LSTMExplainer(model, feature_names, **kwargs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
