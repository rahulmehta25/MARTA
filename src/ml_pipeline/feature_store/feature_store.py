"""
Feature Store Module

Centralized feature computation, versioning, and serving for ML models.
Supports offline batch feature computation and online feature serving.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import json
import hashlib
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Feature data types."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    EMBEDDING = "embedding"


class AggregationType(Enum):
    """Aggregation types for feature computation."""
    MEAN = "mean"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    STD = "std"
    COUNT = "count"
    LAST = "last"
    FIRST = "first"


@dataclass
class FeatureDefinition:
    """
    Definition of a single feature.

    Attributes:
        name: Feature name.
        feature_type: Data type of feature.
        description: Feature description.
        computation: Computation logic (column name or function).
        dependencies: List of dependent features.
        aggregations: Aggregation windows for time-based features.
        default_value: Default value for missing data.
        tags: Feature tags for organization.
    """
    name: str
    feature_type: FeatureType = FeatureType.NUMERIC
    description: str = ""
    computation: Optional[Union[str, Callable]] = None
    dependencies: List[str] = field(default_factory=list)
    aggregations: Dict[str, Any] = field(default_factory=dict)
    default_value: Any = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "feature_type": self.feature_type.value,
            "description": self.description,
            "dependencies": self.dependencies,
            "aggregations": self.aggregations,
            "default_value": self.default_value,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeatureDefinition":
        """Create from dictionary."""
        d = d.copy()
        d["feature_type"] = FeatureType(d.get("feature_type", "numeric"))
        return cls(**d)


@dataclass
class FeatureSet:
    """
    Collection of features for a specific ML use case.

    Attributes:
        name: Feature set name.
        version: Version string.
        features: List of feature definitions.
        entity_keys: Entity key columns (e.g., stop_id, route_id).
        timestamp_key: Timestamp column name.
        description: Feature set description.
        created_at: Creation timestamp.
        tags: Feature set tags.
    """
    name: str
    version: str = "1.0.0"
    features: List[FeatureDefinition] = field(default_factory=list)
    entity_keys: List[str] = field(default_factory=list)
    timestamp_key: str = "timestamp"
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)

    @property
    def feature_names(self) -> List[str]:
        """Get list of feature names."""
        return [f.name for f in self.features]

    def add_feature(self, feature: FeatureDefinition) -> None:
        """Add feature to set."""
        if feature.name in self.feature_names:
            raise ValueError(f"Feature '{feature.name}' already exists")
        self.features.append(feature)

    def get_feature(self, name: str) -> Optional[FeatureDefinition]:
        """Get feature by name."""
        for f in self.features:
            if f.name == name:
                return f
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "features": [f.to_dict() for f in self.features],
            "entity_keys": self.entity_keys,
            "timestamp_key": self.timestamp_key,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeatureSet":
        """Create from dictionary."""
        d = d.copy()
        d["features"] = [FeatureDefinition.from_dict(f) for f in d.get("features", [])]
        d["created_at"] = datetime.fromisoformat(d.get("created_at", datetime.now().isoformat()))
        return cls(**d)

    def save(self, path: str) -> None:
        """Save feature set to JSON."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load(cls, path: str) -> "FeatureSet":
        """Load feature set from JSON."""
        with open(path, 'r') as f:
            return cls.from_dict(json.load(f))


class FeatureStore:
    """
    Centralized feature store for ML models.

    Features:
    - Feature definition and versioning
    - Batch feature computation
    - Online feature serving
    - Point-in-time correct joins
    - Feature caching

    Example:
        >>> store = FeatureStore("./feature_store")
        >>> feature_set = store.create_feature_set(
        ...     name="demand_features",
        ...     entity_keys=["stop_id"],
        ...     features=[
        ...         FeatureDefinition("hour_of_day", FeatureType.NUMERIC),
        ...         FeatureDefinition("is_weekend", FeatureType.BOOLEAN),
        ...     ]
        ... )
        >>> features = store.compute_features(df, feature_set)
    """

    # Standard transit feature definitions
    STANDARD_FEATURES = {
        "temporal": [
            FeatureDefinition("hour_of_day", FeatureType.NUMERIC, "Hour of day (0-23)"),
            FeatureDefinition("day_of_week", FeatureType.CATEGORICAL, "Day of week (0-6)"),
            FeatureDefinition("month", FeatureType.NUMERIC, "Month (1-12)"),
            FeatureDefinition("day_of_month", FeatureType.NUMERIC, "Day of month (1-31)"),
            FeatureDefinition("is_weekend", FeatureType.BOOLEAN, "Weekend flag"),
            FeatureDefinition("is_holiday", FeatureType.BOOLEAN, "Holiday flag"),
            FeatureDefinition("sin_hour", FeatureType.NUMERIC, "Cyclical hour (sin)"),
            FeatureDefinition("cos_hour", FeatureType.NUMERIC, "Cyclical hour (cos)"),
            FeatureDefinition("sin_day_of_week", FeatureType.NUMERIC, "Cyclical day (sin)"),
            FeatureDefinition("cos_day_of_week", FeatureType.NUMERIC, "Cyclical day (cos)"),
        ],
        "demand": [
            FeatureDefinition("historical_dwell_time_avg", FeatureType.NUMERIC, "Historical avg dwell time"),
            FeatureDefinition("lag_dwell_time_1hr", FeatureType.NUMERIC, "Dwell time 1 hour ago"),
            FeatureDefinition("lag_dwell_time_24hr", FeatureType.NUMERIC, "Dwell time 24 hours ago"),
            FeatureDefinition("rolling_avg_dwell_time_3hr", FeatureType.NUMERIC, "3-hour rolling avg"),
            FeatureDefinition("rolling_avg_dwell_time_24hr", FeatureType.NUMERIC, "24-hour rolling avg"),
            FeatureDefinition("rolling_std_dwell_time_3hr", FeatureType.NUMERIC, "3-hour rolling std"),
        ],
        "contextual": [
            FeatureDefinition("weather_condition", FeatureType.CATEGORICAL, "Weather condition"),
            FeatureDefinition("temperature_celsius", FeatureType.NUMERIC, "Temperature in Celsius"),
            FeatureDefinition("precipitation_mm", FeatureType.NUMERIC, "Precipitation in mm"),
            FeatureDefinition("event_flag", FeatureType.BOOLEAN, "Special event nearby"),
        ],
        "transit": [
            FeatureDefinition("delay_minutes", FeatureType.NUMERIC, "Current delay in minutes"),
            FeatureDefinition("stop_sequence", FeatureType.NUMERIC, "Stop sequence in trip"),
            FeatureDefinition("route_type", FeatureType.CATEGORICAL, "Route type (bus/rail)"),
            FeatureDefinition("headway_avg", FeatureType.NUMERIC, "Average headway"),
        ],
    }

    def __init__(self, store_path: str = "./feature_store"):
        """
        Initialize feature store.

        Args:
            store_path: Path to feature store directory.
        """
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)

        self.feature_sets_path = self.store_path / "feature_sets"
        self.feature_sets_path.mkdir(exist_ok=True)

        self.cache_path = self.store_path / "cache"
        self.cache_path.mkdir(exist_ok=True)

        self.feature_sets: Dict[str, FeatureSet] = {}
        self._load_feature_sets()

        # Feature computation functions
        self._feature_functions: Dict[str, Callable] = {}
        self._register_default_functions()

        logger.info(f"FeatureStore initialized at {self.store_path}")

    def _load_feature_sets(self) -> None:
        """Load feature sets from disk."""
        for fs_file in self.feature_sets_path.glob("*.json"):
            try:
                feature_set = FeatureSet.load(str(fs_file))
                key = f"{feature_set.name}:{feature_set.version}"
                self.feature_sets[key] = feature_set
            except Exception as e:
                logger.error(f"Failed to load feature set {fs_file}: {e}")

        logger.info(f"Loaded {len(self.feature_sets)} feature sets")

    def _register_default_functions(self) -> None:
        """Register default feature computation functions."""

        def compute_temporal_features(df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
            """Compute temporal features."""
            ts = pd.to_datetime(df[ts_col])
            df["hour_of_day"] = ts.dt.hour
            df["day_of_week"] = ts.dt.dayofweek
            df["month"] = ts.dt.month
            df["day_of_month"] = ts.dt.day
            df["is_weekend"] = ts.dt.dayofweek.isin([5, 6]).astype(int)

            # Cyclical encoding
            df["sin_hour"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
            df["cos_hour"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
            df["sin_day_of_week"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
            df["cos_day_of_week"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

            return df

        def compute_lag_features(
            df: pd.DataFrame,
            value_col: str,
            group_col: str,
            lags: List[int]
        ) -> pd.DataFrame:
            """Compute lag features."""
            df_sorted = df.sort_values([group_col, "timestamp"])
            for lag in lags:
                df[f"lag_{value_col}_{lag}hr"] = (
                    df_sorted.groupby(group_col)[value_col].shift(lag)
                )
            return df

        def compute_rolling_features(
            df: pd.DataFrame,
            value_col: str,
            group_col: str,
            windows: List[int]
        ) -> pd.DataFrame:
            """Compute rolling window features."""
            df_sorted = df.sort_values([group_col, "timestamp"])
            for window in windows:
                rolling = df_sorted.groupby(group_col)[value_col].transform(
                    lambda x: x.rolling(window=window, min_periods=1).mean().shift(1)
                )
                df[f"rolling_avg_{value_col}_{window}hr"] = rolling

                rolling_std = df_sorted.groupby(group_col)[value_col].transform(
                    lambda x: x.rolling(window=window, min_periods=1).std().shift(1)
                )
                df[f"rolling_std_{value_col}_{window}hr"] = rolling_std

            return df

        self._feature_functions["temporal"] = compute_temporal_features
        self._feature_functions["lag"] = compute_lag_features
        self._feature_functions["rolling"] = compute_rolling_features

    def create_feature_set(
        self,
        name: str,
        features: List[FeatureDefinition],
        entity_keys: List[str],
        timestamp_key: str = "timestamp",
        version: str = "1.0.0",
        description: str = "",
    ) -> FeatureSet:
        """
        Create a new feature set.

        Args:
            name: Feature set name.
            features: List of feature definitions.
            entity_keys: Entity key columns.
            timestamp_key: Timestamp column name.
            version: Version string.
            description: Description.

        Returns:
            Created FeatureSet.
        """
        feature_set = FeatureSet(
            name=name,
            version=version,
            features=features,
            entity_keys=entity_keys,
            timestamp_key=timestamp_key,
            description=description,
        )

        # Save to disk
        key = f"{name}:{version}"
        self.feature_sets[key] = feature_set

        fs_path = self.feature_sets_path / f"{name}_v{version.replace('.', '_')}.json"
        feature_set.save(str(fs_path))

        logger.info(f"Created feature set: {key}")
        return feature_set

    def get_feature_set(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[FeatureSet]:
        """
        Get feature set by name and version.

        Args:
            name: Feature set name.
            version: Version (None for latest).

        Returns:
            FeatureSet or None.
        """
        if version:
            return self.feature_sets.get(f"{name}:{version}")

        # Get latest version
        matching = [
            (key, fs) for key, fs in self.feature_sets.items()
            if key.startswith(f"{name}:")
        ]
        if not matching:
            return None

        return max(matching, key=lambda x: x[1].version)[1]

    def compute_features(
        self,
        df: pd.DataFrame,
        feature_set: Union[str, FeatureSet],
        compute_all: bool = True,
    ) -> pd.DataFrame:
        """
        Compute features for a dataset.

        Args:
            df: Input DataFrame.
            feature_set: FeatureSet or name of feature set.
            compute_all: Whether to compute all feature types.

        Returns:
            DataFrame with computed features.
        """
        if isinstance(feature_set, str):
            fs = self.get_feature_set(feature_set)
            if not fs:
                raise ValueError(f"Feature set not found: {feature_set}")
            feature_set = fs

        result_df = df.copy()

        # Compute temporal features
        if compute_all and feature_set.timestamp_key in result_df.columns:
            result_df = self._feature_functions["temporal"](
                result_df, feature_set.timestamp_key
            )

        # Compute each feature
        for feature_def in feature_set.features:
            if feature_def.computation and callable(feature_def.computation):
                try:
                    result_df = feature_def.computation(result_df)
                except Exception as e:
                    logger.error(f"Failed to compute feature {feature_def.name}: {e}")
                    result_df[feature_def.name] = feature_def.default_value

            # Handle aggregations
            if feature_def.aggregations:
                agg_type = feature_def.aggregations.get("type")
                if agg_type == "lag":
                    lags = feature_def.aggregations.get("lags", [1, 24])
                    value_col = feature_def.aggregations.get("value_col")
                    group_col = feature_def.aggregations.get("group_col")
                    if value_col and group_col and value_col in result_df.columns:
                        result_df = self._feature_functions["lag"](
                            result_df, value_col, group_col, lags
                        )
                elif agg_type == "rolling":
                    windows = feature_def.aggregations.get("windows", [3, 24])
                    value_col = feature_def.aggregations.get("value_col")
                    group_col = feature_def.aggregations.get("group_col")
                    if value_col and group_col and value_col in result_df.columns:
                        result_df = self._feature_functions["rolling"](
                            result_df, value_col, group_col, windows
                        )

        # Fill missing values
        for feature_def in feature_set.features:
            if feature_def.name in result_df.columns:
                result_df[feature_def.name] = result_df[feature_def.name].fillna(
                    feature_def.default_value or 0
                )

        logger.info(f"Computed {len(feature_set.features)} features")
        return result_df

    def get_feature_vector(
        self,
        feature_set: Union[str, FeatureSet],
        entity_values: Dict[str, Any],
        timestamp: datetime,
    ) -> Dict[str, Any]:
        """
        Get feature vector for online serving.

        Args:
            feature_set: FeatureSet or name.
            entity_values: Entity key values (e.g., {"stop_id": "123"}).
            timestamp: Point-in-time for feature lookup.

        Returns:
            Feature dictionary.
        """
        if isinstance(feature_set, str):
            fs = self.get_feature_set(feature_set)
            if not fs:
                raise ValueError(f"Feature set not found: {feature_set}")
            feature_set = fs

        # Check cache
        cache_key = self._get_cache_key(feature_set.name, entity_values, timestamp)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Compute features (simplified for online serving)
        features = {}

        # Temporal features from timestamp
        features["hour_of_day"] = timestamp.hour
        features["day_of_week"] = timestamp.weekday()
        features["month"] = timestamp.month
        features["is_weekend"] = 1 if timestamp.weekday() in [5, 6] else 0
        features["sin_hour"] = np.sin(2 * np.pi * timestamp.hour / 24)
        features["cos_hour"] = np.cos(2 * np.pi * timestamp.hour / 24)

        # Fill defaults for other features
        for feature_def in feature_set.features:
            if feature_def.name not in features:
                features[feature_def.name] = feature_def.default_value or 0

        # Cache result
        self._save_to_cache(cache_key, features)

        return features

    def create_training_dataset(
        self,
        feature_set: Union[str, FeatureSet],
        df: pd.DataFrame,
        target_col: str,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Create training dataset from feature set.

        Args:
            feature_set: FeatureSet to use.
            df: Source DataFrame.
            target_col: Target column name.

        Returns:
            Tuple of (features_df, target_series).
        """
        if isinstance(feature_set, str):
            fs = self.get_feature_set(feature_set)
            if not fs:
                raise ValueError(f"Feature set not found: {feature_set}")
            feature_set = fs

        # Compute features
        features_df = self.compute_features(df, feature_set)

        # Extract feature columns
        feature_cols = [f.name for f in feature_set.features if f.name in features_df.columns]
        X = features_df[feature_cols]
        y = features_df[target_col] if target_col in features_df.columns else df[target_col]

        logger.info(f"Created training dataset: {X.shape} features, {len(y)} samples")
        return X, y

    def _get_cache_key(
        self,
        feature_set_name: str,
        entity_values: Dict[str, Any],
        timestamp: datetime
    ) -> str:
        """Generate cache key."""
        key_parts = [
            feature_set_name,
            json.dumps(entity_values, sort_keys=True),
            timestamp.strftime("%Y%m%d%H"),
        ]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from cache."""
        cache_file = self.cache_path / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _save_to_cache(self, cache_key: str, features: Dict[str, Any]) -> None:
        """Save to cache."""
        cache_file = self.cache_path / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(features, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def clear_cache(self) -> int:
        """Clear feature cache."""
        count = 0
        for cache_file in self.cache_path.glob("*.json"):
            cache_file.unlink()
            count += 1
        logger.info(f"Cleared {count} cache entries")
        return count

    def get_standard_feature_set(
        self,
        categories: Optional[List[str]] = None,
        name: str = "standard_features",
    ) -> FeatureSet:
        """
        Get standard transit feature set.

        Args:
            categories: Feature categories to include.
            name: Feature set name.

        Returns:
            FeatureSet with standard features.
        """
        if categories is None:
            categories = ["temporal", "demand", "contextual", "transit"]

        features = []
        for category in categories:
            if category in self.STANDARD_FEATURES:
                features.extend(self.STANDARD_FEATURES[category])

        return FeatureSet(
            name=name,
            version="1.0.0",
            features=features,
            entity_keys=["stop_id"],
            timestamp_key="timestamp",
            description="Standard transit demand forecasting features",
        )

    def list_feature_sets(self) -> List[Dict[str, Any]]:
        """List all feature sets."""
        return [
            {
                "name": fs.name,
                "version": fs.version,
                "features": len(fs.features),
                "created_at": fs.created_at.isoformat(),
            }
            for fs in self.feature_sets.values()
        ]
