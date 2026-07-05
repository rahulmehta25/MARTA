"""
Data Validation Module

Comprehensive data validation for GTFS and ML training data including schema
validation, quality checks, anomaly detection, and data profiling.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """
    Represents a single validation issue.

    Attributes:
        field: The field/column with the issue.
        issue_type: Type of validation issue.
        message: Human-readable description.
        severity: Severity level.
        count: Number of affected records.
        sample_values: Sample of problematic values.
    """
    field: str
    issue_type: str
    message: str
    severity: ValidationSeverity
    count: int = 0
    sample_values: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "issue_type": self.issue_type,
            "message": self.message,
            "severity": self.severity.value,
            "count": self.count,
            "sample_values": [str(v) for v in self.sample_values[:5]],
        }


@dataclass
class ValidationResult:
    """
    Complete validation result for a dataset.

    Attributes:
        is_valid: Whether all critical validations passed.
        issues: List of validation issues found.
        stats: Dataset statistics.
        validated_at: Timestamp of validation.
    """
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    validated_at: datetime = field(default_factory=datetime.now)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL])

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
            "validated_at": self.validated_at.isoformat(),
        }

    def save_report(self, path: str) -> None:
        """Save validation report to JSON file."""
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


@dataclass
class DataQualityReport:
    """
    Comprehensive data quality report.

    Attributes:
        dataset_name: Name of the dataset.
        row_count: Total number of rows.
        column_count: Total number of columns.
        missing_value_stats: Missing value statistics per column.
        duplicate_stats: Duplicate row statistics.
        outlier_stats: Outlier statistics per numeric column.
        distribution_stats: Distribution statistics per column.
        temporal_stats: Time-series specific statistics.
        quality_score: Overall quality score (0-100).
    """
    dataset_name: str
    row_count: int
    column_count: int
    missing_value_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    duplicate_stats: Dict[str, Any] = field(default_factory=dict)
    outlier_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    distribution_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    temporal_stats: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "missing_value_stats": self.missing_value_stats,
            "duplicate_stats": self.duplicate_stats,
            "outlier_stats": self.outlier_stats,
            "distribution_stats": self.distribution_stats,
            "temporal_stats": self.temporal_stats,
            "quality_score": self.quality_score,
        }


class DataValidator:
    """
    Comprehensive data validator for ML pipeline data.

    Provides schema validation, quality checks, anomaly detection,
    and data profiling capabilities for GTFS and transit data.
    """

    # GTFS schema definitions
    GTFS_SCHEMAS = {
        "stops": {
            "required": ["stop_id", "stop_name", "stop_lat", "stop_lon"],
            "types": {
                "stop_id": str,
                "stop_name": str,
                "stop_lat": float,
                "stop_lon": float,
                "zone_id": str,
            },
            "ranges": {
                "stop_lat": (-90, 90),
                "stop_lon": (-180, 180),
            }
        },
        "routes": {
            "required": ["route_id", "route_short_name", "route_type"],
            "types": {
                "route_id": str,
                "route_short_name": str,
                "route_type": int,
            },
            "ranges": {
                "route_type": (0, 12),
            }
        },
        "trips": {
            "required": ["route_id", "service_id", "trip_id"],
            "types": {
                "route_id": str,
                "service_id": str,
                "trip_id": str,
                "direction_id": int,
            }
        },
        "stop_times": {
            "required": ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
            "types": {
                "trip_id": str,
                "stop_id": str,
                "stop_sequence": int,
            }
        },
    }

    # ML features schema
    ML_FEATURES_SCHEMA = {
        "required": ["timestamp", "stop_id"],
        "numeric_features": [
            "hour_of_day", "day_of_week", "month", "delay_minutes",
            "temperature_celsius", "precipitation_mm", "historical_dwell_time_avg",
            "rolling_avg_dwell_time_3hr", "lag_dwell_time_1hr",
        ],
        "categorical_features": [
            "stop_id", "route_id", "weather_condition", "day_of_week",
        ],
        "target_features": [
            "target_dwell_time_seconds", "target_demand_level",
        ],
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize data validator.

        Args:
            config: Optional configuration dictionary.
        """
        self.config = config or {}
        self.custom_validators: List[Callable] = []

        # Anomaly detection thresholds
        self.outlier_std_threshold = self.config.get("outlier_std_threshold", 3.0)
        self.outlier_iqr_multiplier = self.config.get("outlier_iqr_multiplier", 1.5)
        self.max_missing_ratio = self.config.get("max_missing_ratio", 0.3)
        self.max_duplicate_ratio = self.config.get("max_duplicate_ratio", 0.1)

        logger.info("DataValidator initialized")

    def validate_gtfs(self, df: pd.DataFrame, table_name: str) -> ValidationResult:
        """
        Validate GTFS data against schema.

        Args:
            df: DataFrame containing GTFS data.
            table_name: Name of GTFS table (stops, routes, trips, stop_times).

        Returns:
            ValidationResult with any issues found.
        """
        issues = []

        if table_name not in self.GTFS_SCHEMAS:
            issues.append(ValidationIssue(
                field="table",
                issue_type="unknown_table",
                message=f"Unknown GTFS table: {table_name}",
                severity=ValidationSeverity.WARNING,
            ))
            return ValidationResult(is_valid=True, issues=issues)

        schema = self.GTFS_SCHEMAS[table_name]

        # Check required columns
        for col in schema.get("required", []):
            if col not in df.columns:
                issues.append(ValidationIssue(
                    field=col,
                    issue_type="missing_required_column",
                    message=f"Required column '{col}' is missing",
                    severity=ValidationSeverity.ERROR,
                ))
            elif df[col].isna().any():
                null_count = df[col].isna().sum()
                issues.append(ValidationIssue(
                    field=col,
                    issue_type="null_in_required_column",
                    message=f"Required column '{col}' has {null_count} null values",
                    severity=ValidationSeverity.ERROR,
                    count=null_count,
                ))

        # Check value ranges
        for col, (min_val, max_val) in schema.get("ranges", {}).items():
            if col in df.columns:
                out_of_range = df[(df[col] < min_val) | (df[col] > max_val)]
                if len(out_of_range) > 0:
                    issues.append(ValidationIssue(
                        field=col,
                        issue_type="out_of_range",
                        message=f"Column '{col}' has {len(out_of_range)} values outside range [{min_val}, {max_val}]",
                        severity=ValidationSeverity.ERROR,
                        count=len(out_of_range),
                        sample_values=out_of_range[col].head().tolist(),
                    ))

        # Calculate stats
        stats = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "memory_mb": df.memory_usage(deep=True).sum() / 1024**2,
        }

        is_valid = not any(i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] for i in issues)

        return ValidationResult(is_valid=is_valid, issues=issues, stats=stats)

    def validate_ml_features(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate ML feature data for training.

        Args:
            df: DataFrame containing ML features.

        Returns:
            ValidationResult with any issues found.
        """
        issues = []
        schema = self.ML_FEATURES_SCHEMA

        # Check required columns
        for col in schema.get("required", []):
            if col not in df.columns:
                issues.append(ValidationIssue(
                    field=col,
                    issue_type="missing_required_column",
                    message=f"Required column '{col}' is missing",
                    severity=ValidationSeverity.ERROR,
                ))

        # Check numeric features
        for col in schema.get("numeric_features", []):
            if col in df.columns:
                # Check for non-numeric values
                non_numeric = pd.to_numeric(df[col], errors='coerce').isna() & df[col].notna()
                if non_numeric.any():
                    issues.append(ValidationIssue(
                        field=col,
                        issue_type="non_numeric_values",
                        message=f"Numeric column '{col}' contains non-numeric values",
                        severity=ValidationSeverity.ERROR,
                        count=non_numeric.sum(),
                    ))

                # Check for infinity values
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                inf_count = np.isinf(numeric_col.fillna(0)).sum()
                if inf_count > 0:
                    issues.append(ValidationIssue(
                        field=col,
                        issue_type="infinite_values",
                        message=f"Column '{col}' contains {inf_count} infinite values",
                        severity=ValidationSeverity.ERROR,
                        count=inf_count,
                    ))

        # Check for target variable presence
        target_cols = schema.get("target_features", [])
        has_target = any(col in df.columns and df[col].notna().any() for col in target_cols)
        if not has_target:
            issues.append(ValidationIssue(
                field="target",
                issue_type="missing_target",
                message="No valid target variable found",
                severity=ValidationSeverity.ERROR,
            ))

        # Check missing value ratios
        for col in df.columns:
            missing_ratio = df[col].isna().mean()
            if missing_ratio > self.max_missing_ratio:
                issues.append(ValidationIssue(
                    field=col,
                    issue_type="excessive_missing_values",
                    message=f"Column '{col}' has {missing_ratio:.1%} missing values (threshold: {self.max_missing_ratio:.1%})",
                    severity=ValidationSeverity.WARNING,
                    count=int(df[col].isna().sum()),
                ))

        stats = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "missing_total": df.isna().sum().sum(),
            "memory_mb": df.memory_usage(deep=True).sum() / 1024**2,
        }

        is_valid = not any(i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] for i in issues)

        return ValidationResult(is_valid=is_valid, issues=issues, stats=stats)

    def detect_outliers(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        method: str = "iqr"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect outliers in numeric columns.

        Args:
            df: Input DataFrame.
            columns: Columns to check (None = all numeric).
            method: Detection method ('iqr', 'zscore', or 'both').

        Returns:
            Dictionary mapping column names to outlier statistics.
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        outlier_stats = {}

        for col in columns:
            if col not in df.columns:
                continue

            numeric_col = pd.to_numeric(df[col], errors='coerce').dropna()
            if len(numeric_col) == 0:
                continue

            stats = {
                "count": 0,
                "indices": [],
                "lower_bound": None,
                "upper_bound": None,
            }

            if method in ["iqr", "both"]:
                q1 = numeric_col.quantile(0.25)
                q3 = numeric_col.quantile(0.75)
                iqr = q3 - q1
                lower = q1 - self.outlier_iqr_multiplier * iqr
                upper = q3 + self.outlier_iqr_multiplier * iqr

                iqr_outliers = (numeric_col < lower) | (numeric_col > upper)
                stats["iqr_outliers"] = int(iqr_outliers.sum())
                stats["lower_bound"] = float(lower)
                stats["upper_bound"] = float(upper)
                stats["count"] = max(stats["count"], int(iqr_outliers.sum()))

            if method in ["zscore", "both"]:
                mean = numeric_col.mean()
                std = numeric_col.std()
                if std > 0:
                    z_scores = np.abs((numeric_col - mean) / std)
                    zscore_outliers = z_scores > self.outlier_std_threshold
                    stats["zscore_outliers"] = int(zscore_outliers.sum())
                    stats["count"] = max(stats["count"], int(zscore_outliers.sum()))

            stats["percentage"] = stats["count"] / len(numeric_col) * 100 if len(numeric_col) > 0 else 0
            outlier_stats[col] = stats

        return outlier_stats

    def detect_anomalies(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        value_cols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect anomalies in time series data.

        Args:
            df: Input DataFrame with time series data.
            timestamp_col: Name of timestamp column.
            value_cols: Columns to check for anomalies.

        Returns:
            Dictionary with anomaly detection results.
        """
        anomalies = {}

        if timestamp_col not in df.columns:
            return {"error": f"Timestamp column '{timestamp_col}' not found"}

        df_sorted = df.sort_values(timestamp_col).copy()

        # Check for gaps in time series
        if pd.api.types.is_datetime64_any_dtype(df_sorted[timestamp_col]):
            time_diffs = df_sorted[timestamp_col].diff()
            median_gap = time_diffs.median()
            if pd.notna(median_gap):
                large_gaps = time_diffs > median_gap * 3
                anomalies["time_gaps"] = {
                    "count": int(large_gaps.sum()),
                    "median_gap_seconds": median_gap.total_seconds() if hasattr(median_gap, 'total_seconds') else float(median_gap),
                    "max_gap_seconds": time_diffs.max().total_seconds() if hasattr(time_diffs.max(), 'total_seconds') else float(time_diffs.max()),
                }

        # Check value columns for sudden changes
        if value_cols is None:
            value_cols = df_sorted.select_dtypes(include=[np.number]).columns.tolist()

        for col in value_cols:
            if col not in df_sorted.columns:
                continue

            numeric_col = pd.to_numeric(df_sorted[col], errors='coerce')
            if numeric_col.isna().all():
                continue

            # Calculate rolling statistics
            rolling_mean = numeric_col.rolling(window=24, min_periods=1).mean()
            rolling_std = numeric_col.rolling(window=24, min_periods=1).std()

            # Detect sudden changes (beyond 3 std from rolling mean)
            with np.errstate(invalid='ignore'):
                deviations = np.abs(numeric_col - rolling_mean) / (rolling_std + 1e-8)
            sudden_changes = deviations > 3

            if sudden_changes.any():
                anomalies[f"{col}_sudden_changes"] = {
                    "count": int(sudden_changes.sum()),
                    "percentage": float(sudden_changes.mean() * 100),
                }

        return anomalies

    def generate_quality_report(
        self,
        df: pd.DataFrame,
        dataset_name: str = "dataset",
        timestamp_col: Optional[str] = None
    ) -> DataQualityReport:
        """
        Generate comprehensive data quality report.

        Args:
            df: Input DataFrame.
            dataset_name: Name for the dataset.
            timestamp_col: Name of timestamp column for temporal analysis.

        Returns:
            DataQualityReport with complete analysis.
        """
        # Missing value statistics
        missing_stats = {}
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_stats[col] = {
                "missing_count": int(missing_count),
                "missing_percentage": float(missing_count / len(df) * 100) if len(df) > 0 else 0,
                "dtype": str(df[col].dtype),
            }

        # Duplicate statistics
        duplicate_rows = df.duplicated().sum()
        duplicate_stats = {
            "duplicate_rows": int(duplicate_rows),
            "duplicate_percentage": float(duplicate_rows / len(df) * 100) if len(df) > 0 else 0,
        }

        # Outlier statistics
        outlier_stats = self.detect_outliers(df, method="both")

        # Distribution statistics for numeric columns
        distribution_stats = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            numeric_col = df[col].dropna()
            if len(numeric_col) > 0:
                distribution_stats[col] = {
                    "mean": float(numeric_col.mean()),
                    "std": float(numeric_col.std()),
                    "min": float(numeric_col.min()),
                    "max": float(numeric_col.max()),
                    "median": float(numeric_col.median()),
                    "q25": float(numeric_col.quantile(0.25)),
                    "q75": float(numeric_col.quantile(0.75)),
                    "skewness": float(numeric_col.skew()),
                    "kurtosis": float(numeric_col.kurtosis()),
                }

        # Temporal statistics
        temporal_stats = {}
        if timestamp_col and timestamp_col in df.columns:
            ts = pd.to_datetime(df[timestamp_col], errors='coerce')
            if ts.notna().any():
                temporal_stats = {
                    "min_timestamp": ts.min().isoformat() if pd.notna(ts.min()) else None,
                    "max_timestamp": ts.max().isoformat() if pd.notna(ts.max()) else None,
                    "time_span_days": (ts.max() - ts.min()).days if pd.notna(ts.min()) and pd.notna(ts.max()) else None,
                    "unique_dates": ts.dt.date.nunique(),
                }

        # Calculate quality score
        quality_score = 100.0

        # Deduct for missing values
        avg_missing = np.mean([s["missing_percentage"] for s in missing_stats.values()])
        quality_score -= min(avg_missing * 2, 30)  # Max 30 point deduction

        # Deduct for duplicates
        quality_score -= min(duplicate_stats["duplicate_percentage"] * 2, 20)  # Max 20 point deduction

        # Deduct for outliers
        if outlier_stats:
            avg_outlier_pct = np.mean([s.get("percentage", 0) for s in outlier_stats.values()])
            quality_score -= min(avg_outlier_pct, 20)  # Max 20 point deduction

        quality_score = max(0, quality_score)

        return DataQualityReport(
            dataset_name=dataset_name,
            row_count=len(df),
            column_count=len(df.columns),
            missing_value_stats=missing_stats,
            duplicate_stats=duplicate_stats,
            outlier_stats=outlier_stats,
            distribution_stats=distribution_stats,
            temporal_stats=temporal_stats,
            quality_score=quality_score,
        )

    def add_custom_validator(self, validator: Callable[[pd.DataFrame], List[ValidationIssue]]) -> None:
        """
        Add a custom validation function.

        Args:
            validator: Function that takes DataFrame and returns list of ValidationIssues.
        """
        self.custom_validators.append(validator)

    def run_all_validations(
        self,
        df: pd.DataFrame,
        validation_type: str = "ml_features"
    ) -> ValidationResult:
        """
        Run all validations including custom validators.

        Args:
            df: Input DataFrame.
            validation_type: Type of validation ('gtfs_stops', 'gtfs_routes', 'ml_features').

        Returns:
            Combined ValidationResult.
        """
        # Run standard validation
        if validation_type.startswith("gtfs_"):
            table_name = validation_type.replace("gtfs_", "")
            result = self.validate_gtfs(df, table_name)
        else:
            result = self.validate_ml_features(df)

        # Run custom validators
        for validator in self.custom_validators:
            try:
                custom_issues = validator(df)
                result.issues.extend(custom_issues)
            except Exception as e:
                logger.error(f"Custom validator failed: {e}")
                result.issues.append(ValidationIssue(
                    field="custom_validator",
                    issue_type="validator_error",
                    message=str(e),
                    severity=ValidationSeverity.WARNING,
                ))

        # Update validity
        result.is_valid = not any(
            i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for i in result.issues
        )

        return result
