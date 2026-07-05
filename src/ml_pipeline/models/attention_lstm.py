"""
Attention-Enhanced LSTM Model

Implements LSTM with attention mechanism for improved time series forecasting.
Includes multi-head self-attention, temporal attention, and proper regularization.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import logging
import os
from pathlib import Path

import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import (
    Layer, Input, LSTM, Dense, Dropout, BatchNormalization,
    Bidirectional, LayerNormalization, Concatenate, Multiply, Add,
    Attention, MultiHeadAttention as KerasMultiHeadAttention
)
from tensorflow.keras.callbacks import (
    EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, TensorBoard
)
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l2
import joblib

logger = logging.getLogger(__name__)


class TemporalAttention(Layer):
    """
    Temporal attention layer for time series.

    Computes attention weights over the temporal dimension to highlight
    important timesteps for prediction.

    Attributes:
        units: Number of attention units.
        return_attention: Whether to return attention weights.
    """

    def __init__(
        self,
        units: int = 64,
        return_attention: bool = False,
        **kwargs
    ):
        """
        Initialize temporal attention layer.

        Args:
            units: Number of units in attention mechanism.
            return_attention: Whether to return attention weights.
        """
        super().__init__(**kwargs)
        self.units = units
        self.return_attention = return_attention

    def build(self, input_shape):
        """Build attention weights."""
        self.W = self.add_weight(
            name='attention_weight',
            shape=(input_shape[-1], self.units),
            initializer='glorot_uniform',
            trainable=True
        )
        self.b = self.add_weight(
            name='attention_bias',
            shape=(self.units,),
            initializer='zeros',
            trainable=True
        )
        self.u = self.add_weight(
            name='attention_context',
            shape=(self.units,),
            initializer='glorot_uniform',
            trainable=True
        )
        super().build(input_shape)

    def call(self, inputs):
        """
        Apply temporal attention.

        Args:
            inputs: Input tensor of shape (batch, timesteps, features).

        Returns:
            Context vector and optionally attention weights.
        """
        # Score function: tanh(W*h + b)
        score = tf.tanh(tf.tensordot(inputs, self.W, axes=1) + self.b)

        # Attention weights: softmax(score * u)
        attention_weights = tf.nn.softmax(
            tf.tensordot(score, self.u, axes=1),
            axis=1
        )

        # Weighted sum
        context = tf.reduce_sum(
            inputs * tf.expand_dims(attention_weights, -1),
            axis=1
        )

        if self.return_attention:
            return context, attention_weights
        return context

    def get_config(self):
        """Get layer configuration."""
        config = super().get_config()
        config.update({
            'units': self.units,
            'return_attention': self.return_attention,
        })
        return config


class MultiHeadAttention(Layer):
    """
    Multi-head self-attention for sequence modeling.

    Implements scaled dot-product attention with multiple heads for
    capturing different aspects of temporal dependencies.
    """

    def __init__(
        self,
        num_heads: int = 4,
        key_dim: int = 32,
        dropout: float = 0.1,
        **kwargs
    ):
        """
        Initialize multi-head attention.

        Args:
            num_heads: Number of attention heads.
            key_dim: Dimension of key/query vectors.
            dropout: Dropout rate for attention weights.
        """
        super().__init__(**kwargs)
        self.num_heads = num_heads
        self.key_dim = key_dim
        self.dropout_rate = dropout

    def build(self, input_shape):
        """Build attention layers."""
        self.mha = KerasMultiHeadAttention(
            num_heads=self.num_heads,
            key_dim=self.key_dim,
            dropout=self.dropout_rate
        )
        self.layernorm = LayerNormalization()
        self.dropout = Dropout(self.dropout_rate)
        super().build(input_shape)

    def call(self, inputs, training=None):
        """
        Apply multi-head self-attention.

        Args:
            inputs: Input tensor of shape (batch, timesteps, features).
            training: Whether in training mode.

        Returns:
            Attention output with residual connection.
        """
        attention_output = self.mha(inputs, inputs, training=training)
        attention_output = self.dropout(attention_output, training=training)
        return self.layernorm(inputs + attention_output)

    def get_config(self):
        """Get layer configuration."""
        config = super().get_config()
        config.update({
            'num_heads': self.num_heads,
            'key_dim': self.key_dim,
            'dropout': self.dropout_rate,
        })
        return config


@dataclass
class AttentionLSTMOutput:
    """
    Output container for AttentionLSTM predictions.

    Attributes:
        predictions: Model predictions.
        attention_weights: Attention weights (if available).
        confidence: Prediction confidence scores.
    """
    predictions: np.ndarray
    attention_weights: Optional[np.ndarray] = None
    confidence: Optional[np.ndarray] = None


class AttentionLSTM:
    """
    LSTM model with attention mechanism for time series forecasting.

    Features:
    - Multi-layer LSTM with optional bidirectional processing
    - Multi-head self-attention for capturing complex dependencies
    - Temporal attention for timestep importance
    - Layer normalization for training stability
    - Flexible architecture configuration
    - Training callbacks for early stopping and learning rate scheduling

    Example:
        >>> from src.ml_pipeline.config import LSTMConfig
        >>> config = LSTMConfig(lstm_units=[128, 64], use_attention=True)
        >>> model = AttentionLSTM(config)
        >>> model.build_model(input_shape=(24, 10))
        >>> history = model.fit(X_train, y_train, X_val, y_val)
    """

    def __init__(
        self,
        config: Any,
        name: str = "attention_lstm"
    ):
        """
        Initialize AttentionLSTM model.

        Args:
            config: LSTMConfig with hyperparameters.
            name: Model name for saving/loading.
        """
        self.config = config
        self.name = name
        self.model: Optional[Model] = None
        self.attention_model: Optional[Model] = None
        self.history: Optional[Dict] = None
        self.feature_scaler = None
        self.target_scaler = None

        logger.info(f"Initialized AttentionLSTM: {name}")

    def build_model(
        self,
        input_shape: Tuple[int, int],
        output_dim: int = 1
    ) -> Model:
        """
        Build the LSTM model with attention.

        Args:
            input_shape: Shape of input (sequence_length, n_features).
            output_dim: Output dimension (1 for regression, n_classes for classification).

        Returns:
            Compiled Keras Model.
        """
        sequence_length, n_features = input_shape
        cfg = self.config

        # Input layer
        inputs = Input(shape=(sequence_length, n_features), name='input')
        x = inputs

        # Multi-head self-attention (if enabled)
        if cfg.use_attention and cfg.num_heads > 0:
            x = MultiHeadAttention(
                num_heads=cfg.num_heads,
                key_dim=cfg.attention_units // cfg.num_heads,
                dropout=cfg.dropout_rate,
                name='multi_head_attention'
            )(x)

        # LSTM layers
        attention_outputs = []
        for i, units in enumerate(cfg.lstm_units[:-1]):
            return_sequences = True

            if cfg.bidirectional:
                x = Bidirectional(
                    LSTM(
                        units,
                        return_sequences=return_sequences,
                        dropout=cfg.dropout_rate,
                        recurrent_dropout=cfg.recurrent_dropout,
                        kernel_regularizer=l2(0.001)
                    ),
                    name=f'bilstm_{i}'
                )(x)
            else:
                x = LSTM(
                    units,
                    return_sequences=return_sequences,
                    dropout=cfg.dropout_rate,
                    recurrent_dropout=cfg.recurrent_dropout,
                    kernel_regularizer=l2(0.001),
                    name=f'lstm_{i}'
                )(x)

            if cfg.use_layer_norm:
                x = LayerNormalization(name=f'layernorm_{i}')(x)

            x = Dropout(cfg.dropout_rate, name=f'dropout_{i}')(x)
            attention_outputs.append(x)

        # Final LSTM layer
        if cfg.bidirectional:
            x = Bidirectional(
                LSTM(
                    cfg.lstm_units[-1],
                    return_sequences=cfg.use_attention,
                    dropout=cfg.dropout_rate,
                    recurrent_dropout=cfg.recurrent_dropout,
                ),
                name='bilstm_final'
            )(x)
        else:
            x = LSTM(
                cfg.lstm_units[-1],
                return_sequences=cfg.use_attention,
                dropout=cfg.dropout_rate,
                recurrent_dropout=cfg.recurrent_dropout,
                name='lstm_final'
            )(x)

        # Temporal attention (if enabled)
        if cfg.use_attention:
            attention_layer = TemporalAttention(
                units=cfg.attention_units,
                return_attention=True,
                name='temporal_attention'
            )
            x, attention_weights = attention_layer(x)

        if cfg.use_layer_norm:
            x = LayerNormalization(name='layernorm_final')(x)

        x = Dropout(cfg.dropout_rate, name='dropout_final')(x)

        # Dense layers
        for i, units in enumerate(cfg.dense_units):
            x = Dense(
                units,
                activation=cfg.activation,
                kernel_regularizer=l2(0.001),
                name=f'dense_{i}'
            )(x)
            x = Dropout(cfg.dropout_rate, name=f'dense_dropout_{i}')(x)

        # Output layer
        if cfg.task_type.value == "classification":
            outputs = Dense(
                cfg.num_classes,
                activation='softmax',
                name='output'
            )(x)
            loss = 'sparse_categorical_crossentropy'
            metrics = ['accuracy']
        else:
            outputs = Dense(
                output_dim,
                activation=cfg.output_activation,
                name='output'
            )(x)
            loss = 'mse'
            metrics = ['mae']

        # Build model
        self.model = Model(inputs=inputs, outputs=outputs, name=self.name)

        # Compile
        optimizer = Adam(learning_rate=cfg.training.learning_rate)
        self.model.compile(optimizer=optimizer, loss=loss, metrics=metrics)

        # Build attention extraction model (if using attention)
        if cfg.use_attention:
            self.attention_model = Model(
                inputs=inputs,
                outputs=[outputs, attention_layer.output[1]],
                name=f'{self.name}_attention'
            )

        logger.info(f"Built model with {self.model.count_params():,} parameters")
        self.model.summary(print_fn=logger.info)

        return self.model

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        callbacks: Optional[List] = None,
        verbose: int = 1,
    ) -> Dict[str, List[float]]:
        """
        Train the model.

        Args:
            X_train: Training features (n_samples, seq_len, n_features).
            y_train: Training targets.
            X_val: Validation features.
            y_val: Validation targets.
            callbacks: Additional Keras callbacks.
            verbose: Verbosity level.

        Returns:
            Training history dictionary.
        """
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")

        cfg = self.config.training

        # Setup callbacks
        default_callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=cfg.early_stopping_patience,
                restore_best_weights=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=cfg.reduce_lr_factor,
                patience=cfg.reduce_lr_patience,
                min_lr=cfg.min_lr,
                verbose=1
            ),
        ]

        if callbacks:
            default_callbacks.extend(callbacks)

        # Prepare validation data
        validation_data = None
        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)

        # Train
        history = self.model.fit(
            X_train,
            y_train,
            validation_data=validation_data,
            epochs=cfg.epochs,
            batch_size=cfg.batch_size,
            callbacks=default_callbacks,
            shuffle=cfg.shuffle,
            verbose=verbose,
        )

        self.history = history.history
        logger.info(f"Training completed. Best val_loss: {min(history.history.get('val_loss', [float('inf')])):.4f}")

        return self.history

    def predict(
        self,
        X: np.ndarray,
        return_attention: bool = False
    ) -> Union[np.ndarray, AttentionLSTMOutput]:
        """
        Make predictions.

        Args:
            X: Input features (n_samples, seq_len, n_features).
            return_attention: Whether to return attention weights.

        Returns:
            Predictions or AttentionLSTMOutput with attention weights.
        """
        if self.model is None:
            raise ValueError("Model not built or loaded.")

        if return_attention and self.attention_model is not None:
            predictions, attention_weights = self.attention_model.predict(X, verbose=0)
            return AttentionLSTMOutput(
                predictions=predictions,
                attention_weights=attention_weights,
            )

        predictions = self.model.predict(X, verbose=0)
        return predictions

    def get_attention_weights(self, X: np.ndarray) -> np.ndarray:
        """
        Get attention weights for input sequences.

        Args:
            X: Input features (n_samples, seq_len, n_features).

        Returns:
            Attention weights (n_samples, seq_len).
        """
        if self.attention_model is None:
            raise ValueError("Attention model not available.")

        _, attention_weights = self.attention_model.predict(X, verbose=0)
        return attention_weights

    def save(self, path: str) -> None:
        """
        Save model and configuration.

        Args:
            path: Directory path for saving.
        """
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = save_dir / f"{self.name}.keras"
        self.model.save(model_path)

        # Save config and scalers
        meta = {
            'config': self.config.to_dict(),
            'name': self.name,
            'history': self.history,
        }
        joblib.dump(meta, save_dir / f"{self.name}_meta.pkl")

        if self.feature_scaler:
            joblib.dump(self.feature_scaler, save_dir / f"{self.name}_feature_scaler.pkl")
        if self.target_scaler:
            joblib.dump(self.target_scaler, save_dir / f"{self.name}_target_scaler.pkl")

        logger.info(f"Model saved to {save_dir}")

    @classmethod
    def load(cls, path: str) -> "AttentionLSTM":
        """
        Load model from directory.

        Args:
            path: Directory path containing saved model.

        Returns:
            Loaded AttentionLSTM instance.
        """
        from ..config.model_config import LSTMConfig

        load_dir = Path(path)

        # Find model file
        model_files = list(load_dir.glob("*.keras")) + list(load_dir.glob("*.h5"))
        if not model_files:
            raise FileNotFoundError(f"No model file found in {load_dir}")

        model_path = model_files[0]
        name = model_path.stem

        # Load metadata
        meta_path = load_dir / f"{name}_meta.pkl"
        if meta_path.exists():
            meta = joblib.load(meta_path)
            config = LSTMConfig.from_dict(meta['config'])
        else:
            config = LSTMConfig()

        # Create instance
        instance = cls(config=config, name=name)

        # Load model with custom objects
        custom_objects = {
            'TemporalAttention': TemporalAttention,
            'MultiHeadAttention': MultiHeadAttention,
        }
        instance.model = load_model(model_path, custom_objects=custom_objects)

        # Load scalers
        feature_scaler_path = load_dir / f"{name}_feature_scaler.pkl"
        target_scaler_path = load_dir / f"{name}_target_scaler.pkl"

        if feature_scaler_path.exists():
            instance.feature_scaler = joblib.load(feature_scaler_path)
        if target_scaler_path.exists():
            instance.target_scaler = joblib.load(target_scaler_path)

        if meta_path.exists():
            instance.history = meta.get('history')

        logger.info(f"Model loaded from {load_dir}")
        return instance

    def summary(self) -> None:
        """Print model summary."""
        if self.model:
            self.model.summary()
        else:
            logger.warning("Model not built yet.")
