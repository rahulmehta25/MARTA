"""
Temporal Data Splitting Module

Implements time-aware train/validation/test splitting to prevent data leakage
in time series forecasting tasks.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Iterator, Union
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class SplitInfo:
    """
    Information about a data split.

    Attributes:
        name: Split name (train, validation, test).
        start_date: Start date of the split.
        end_date: End date of the split.
        num_samples: Number of samples in split.
        indices: Array indices for this split.
    """
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    num_samples: int = 0
    indices: np.ndarray = field(default_factory=lambda: np.array([]))

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "num_samples": self.num_samples,
        }


@dataclass
class TimeSeriesSplit:
    """
    Results of temporal train/val/test split.

    Attributes:
        X_train: Training features.
        X_val: Validation features.
        X_test: Test features.
        y_train: Training targets.
        y_val: Validation targets.
        y_test: Test targets.
        train_info: Information about training split.
        val_info: Information about validation split.
        test_info: Information about test split.
    """
    X_train: np.ndarray
    X_val: np.ndarray
    X_test: np.ndarray
    y_train: np.ndarray
    y_val: np.ndarray
    y_test: np.ndarray
    train_info: SplitInfo
    val_info: SplitInfo
    test_info: SplitInfo

    def get_sizes(self) -> Dict[str, int]:
        """Get sizes of each split."""
        return {
            "train": len(self.X_train),
            "validation": len(self.X_val),
            "test": len(self.X_test),
            "total": len(self.X_train) + len(self.X_val) + len(self.X_test),
        }

    def get_ratios(self) -> Dict[str, float]:
        """Get ratios of each split."""
        total = len(self.X_train) + len(self.X_val) + len(self.X_test)
        if total == 0:
            return {"train": 0, "validation": 0, "test": 0}
        return {
            "train": len(self.X_train) / total,
            "validation": len(self.X_val) / total,
            "test": len(self.X_test) / total,
        }


class TemporalSplitter:
    """
    Time-aware data splitter for time series forecasting.

    Ensures no data leakage by splitting data chronologically and respecting
    the temporal order. Supports multiple splitting strategies:
    - Simple chronological split
    - Gap-based split (with gap between train/val/test)
    - Walk-forward validation
    - Expanding window

    Example:
        >>> splitter = TemporalSplitter(
        ...     train_ratio=0.7,
        ...     val_ratio=0.15,
        ...     test_ratio=0.15,
        ...     gap_hours=24
        ... )
        >>> split = splitter.split(df, timestamp_col='timestamp', feature_cols=['f1', 'f2'], target_col='target')
    """

    def __init__(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        gap_hours: int = 0,
        min_train_samples: int = 100,
        sequence_length: int = 1,
    ):
        """
        Initialize temporal splitter.

        Args:
            train_ratio: Fraction of data for training.
            val_ratio: Fraction of data for validation.
            test_ratio: Fraction of data for testing.
            gap_hours: Hours of gap between splits to prevent leakage.
            min_train_samples: Minimum required training samples.
            sequence_length: Sequence length for LSTM (affects split boundaries).
        """
        total = train_ratio + val_ratio + test_ratio
        if not np.isclose(total, 1.0, atol=0.01):
            raise ValueError(f"Ratios must sum to 1.0, got {total}")

        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.gap_hours = gap_hours
        self.min_train_samples = min_train_samples
        self.sequence_length = sequence_length

        logger.info(
            f"TemporalSplitter initialized: train={train_ratio:.0%}, "
            f"val={val_ratio:.0%}, test={test_ratio:.0%}, gap={gap_hours}h"
        )

    def split(
        self,
        df: pd.DataFrame,
        timestamp_col: str,
        feature_cols: List[str],
        target_col: str,
        group_col: Optional[str] = None,
    ) -> TimeSeriesSplit:
        """
        Split data chronologically into train/val/test sets.

        Args:
            df: Input DataFrame.
            timestamp_col: Name of timestamp column.
            feature_cols: List of feature column names.
            target_col: Name of target column.
            group_col: Optional column for grouped splitting (e.g., by stop_id).

        Returns:
            TimeSeriesSplit with train/val/test data.
        """
        # Sort by timestamp
        df_sorted = df.sort_values(timestamp_col).reset_index(drop=True)

        # Parse timestamps
        timestamps = pd.to_datetime(df_sorted[timestamp_col])

        # Calculate split points
        n = len(df_sorted)
        train_end = int(n * self.train_ratio)
        val_end = int(n * (self.train_ratio + self.val_ratio))

        # Adjust for gap
        if self.gap_hours > 0:
            gap_samples = self._estimate_gap_samples(timestamps, self.gap_hours)
            train_end = max(self.min_train_samples, train_end - gap_samples)
            val_start = train_end + gap_samples
            val_end = min(val_end, n - gap_samples)
            test_start = val_end + gap_samples
        else:
            val_start = train_end
            test_start = val_end

        # Ensure minimum samples
        if train_end < self.min_train_samples:
            logger.warning(
                f"Training set too small ({train_end} < {self.min_train_samples}). "
                f"Adjusting ratios."
            )
            train_end = self.min_train_samples
            remaining = n - train_end
            val_samples = int(remaining * self.val_ratio / (self.val_ratio + self.test_ratio))
            val_start = train_end
            val_end = train_end + val_samples
            test_start = val_end

        # Create indices
        train_idx = np.arange(0, train_end)
        val_idx = np.arange(val_start, val_end)
        test_idx = np.arange(test_start, n)

        # Extract features and targets
        X = df_sorted[feature_cols].values
        y = df_sorted[target_col].values

        # Handle any remaining NaN values
        X = np.nan_to_num(X, nan=0.0)

        # Create split info
        train_info = SplitInfo(
            name="train",
            start_date=timestamps.iloc[0] if len(train_idx) > 0 else None,
            end_date=timestamps.iloc[train_end - 1] if len(train_idx) > 0 else None,
            num_samples=len(train_idx),
            indices=train_idx,
        )

        val_info = SplitInfo(
            name="validation",
            start_date=timestamps.iloc[val_start] if len(val_idx) > 0 else None,
            end_date=timestamps.iloc[val_end - 1] if len(val_idx) > 0 else None,
            num_samples=len(val_idx),
            indices=val_idx,
        )

        test_info = SplitInfo(
            name="test",
            start_date=timestamps.iloc[test_start] if len(test_idx) > 0 else None,
            end_date=timestamps.iloc[-1] if len(test_idx) > 0 else None,
            num_samples=len(test_idx),
            indices=test_idx,
        )

        logger.info(
            f"Split complete: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}"
        )

        return TimeSeriesSplit(
            X_train=X[train_idx],
            X_val=X[val_idx],
            X_test=X[test_idx],
            y_train=y[train_idx],
            y_val=y[val_idx],
            y_test=y[test_idx],
            train_info=train_info,
            val_info=val_info,
            test_info=test_info,
        )

    def create_sequences(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sequence_length: Optional[int] = None,
        prediction_horizon: int = 1,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM training.

        Args:
            X: Feature array of shape (n_samples, n_features).
            y: Target array of shape (n_samples,).
            sequence_length: Number of timesteps per sequence.
            prediction_horizon: Steps ahead to predict.

        Returns:
            Tuple of (X_sequences, y_sequences).
        """
        if sequence_length is None:
            sequence_length = self.sequence_length

        n_samples = len(X)
        n_sequences = n_samples - sequence_length - prediction_horizon + 1

        if n_sequences <= 0:
            raise ValueError(
                f"Not enough samples ({n_samples}) for sequence_length={sequence_length} "
                f"and prediction_horizon={prediction_horizon}"
            )

        n_features = X.shape[1] if len(X.shape) > 1 else 1

        X_sequences = np.zeros((n_sequences, sequence_length, n_features))
        y_sequences = np.zeros(n_sequences)

        for i in range(n_sequences):
            X_sequences[i] = X[i:i + sequence_length]
            y_sequences[i] = y[i + sequence_length + prediction_horizon - 1]

        logger.info(
            f"Created {n_sequences} sequences of length {sequence_length}"
        )

        return X_sequences, y_sequences

    def walk_forward_split(
        self,
        df: pd.DataFrame,
        timestamp_col: str,
        feature_cols: List[str],
        target_col: str,
        n_splits: int = 5,
        test_size: float = 0.1,
        expanding: bool = True,
    ) -> Iterator[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """
        Generate walk-forward validation splits.

        Args:
            df: Input DataFrame.
            timestamp_col: Name of timestamp column.
            feature_cols: List of feature column names.
            target_col: Name of target column.
            n_splits: Number of train/test splits.
            test_size: Size of each test set as fraction.
            expanding: If True, use expanding window; otherwise sliding window.

        Yields:
            Tuple of (X_train, X_test, y_train, y_test) for each split.
        """
        df_sorted = df.sort_values(timestamp_col).reset_index(drop=True)
        X = df_sorted[feature_cols].values
        y = df_sorted[target_col].values

        n = len(df_sorted)
        test_samples = int(n * test_size)

        for i in range(n_splits):
            # Calculate split points
            test_end = n - (n_splits - i - 1) * test_samples
            test_start = test_end - test_samples

            if expanding:
                train_start = 0
            else:
                # Sliding window: fixed training size
                train_size = int(n * (1 - n_splits * test_size))
                train_start = max(0, test_start - train_size)

            train_end = test_start - self.gap_hours if self.gap_hours > 0 else test_start

            if train_end <= train_start or train_end < self.min_train_samples:
                logger.warning(f"Skipping split {i}: insufficient training data")
                continue

            X_train = X[train_start:train_end]
            X_test = X[test_start:test_end]
            y_train = y[train_start:train_end]
            y_test = y[test_start:test_end]

            logger.info(
                f"Walk-forward split {i + 1}/{n_splits}: "
                f"train={len(X_train)}, test={len(X_test)}"
            )

            yield X_train, X_test, y_train, y_test

    def group_temporal_split(
        self,
        df: pd.DataFrame,
        timestamp_col: str,
        group_col: str,
        feature_cols: List[str],
        target_col: str,
    ) -> Dict[str, TimeSeriesSplit]:
        """
        Perform temporal split within each group.

        Useful for splitting data by stop_id or route_id while maintaining
        temporal order within each group.

        Args:
            df: Input DataFrame.
            timestamp_col: Name of timestamp column.
            group_col: Column to group by.
            feature_cols: List of feature column names.
            target_col: Name of target column.

        Returns:
            Dictionary mapping group values to TimeSeriesSplit.
        """
        splits = {}

        for group_value, group_df in df.groupby(group_col):
            if len(group_df) < self.min_train_samples:
                logger.warning(
                    f"Skipping group '{group_value}': insufficient samples ({len(group_df)})"
                )
                continue

            split = self.split(
                group_df,
                timestamp_col=timestamp_col,
                feature_cols=feature_cols,
                target_col=target_col,
            )
            splits[group_value] = split

        logger.info(f"Created splits for {len(splits)} groups")
        return splits

    def _estimate_gap_samples(
        self,
        timestamps: pd.Series,
        gap_hours: int
    ) -> int:
        """Estimate number of samples in gap period."""
        if len(timestamps) < 2:
            return 0

        # Calculate median time delta between samples
        time_diffs = timestamps.diff().dropna()
        median_diff = time_diffs.median()

        if pd.isna(median_diff):
            return 0

        # Convert gap hours to number of samples
        gap_duration = timedelta(hours=gap_hours)
        gap_samples = int(gap_duration / median_diff) if median_diff.total_seconds() > 0 else 0

        return max(0, gap_samples)

    @staticmethod
    def validate_no_leakage(
        train_timestamps: pd.Series,
        val_timestamps: pd.Series,
        test_timestamps: pd.Series,
    ) -> bool:
        """
        Validate that there's no temporal data leakage between splits.

        Args:
            train_timestamps: Training set timestamps.
            val_timestamps: Validation set timestamps.
            test_timestamps: Test set timestamps.

        Returns:
            True if no leakage detected, False otherwise.
        """
        train_max = train_timestamps.max()
        val_min = val_timestamps.min()
        val_max = val_timestamps.max()
        test_min = test_timestamps.min()

        # Check temporal ordering
        train_before_val = train_max < val_min if pd.notna(train_max) and pd.notna(val_min) else True
        val_before_test = val_max < test_min if pd.notna(val_max) and pd.notna(test_min) else True

        if not train_before_val:
            logger.error(
                f"Data leakage detected: train_max ({train_max}) >= val_min ({val_min})"
            )
            return False

        if not val_before_test:
            logger.error(
                f"Data leakage detected: val_max ({val_max}) >= test_min ({test_min})"
            )
            return False

        logger.info("No temporal data leakage detected")
        return True
