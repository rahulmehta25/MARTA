# src/services/data_validator.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Validates and cleans data from external sources.
    Ensures data quality before storage and ML processing.
    """

    def __init__(self):
        # Define validation rules
        self.apc_rules = {
            "passenger_count": {"min": 0, "max": 200},
            "occupancy_percentage": {"min": 0, "max": 150},  # Allow some overflow
            "boarding_count": {"min": 0, "max": 50},
            "alighting_count": {"min": 0, "max": 50},
        }

        self.weather_rules = {
            "temperature_c": {"min": -50, "max": 60},
            "humidity_percent": {"min": 0, "max": 100},
            "wind_speed_ms": {"min": 0, "max": 100},
            "visibility_m": {"min": 0, "max": 50000},
        }

        self.traffic_rules = {
            "current_speed_kmh": {"min": 0, "max": 200},
            "congestion_ratio": {"min": 0, "max": 1},
            "confidence": {"min": 0, "max": 1},
        }

    def validate_apc_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate APC data record.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        required_fields = ["vehicle_id", "timestamp"]
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")

        # Validate timestamp
        if "timestamp" in data:
            if not self._validate_timestamp(data["timestamp"]):
                errors.append("Invalid timestamp")

        # Validate numeric ranges
        for field, rules in self.apc_rules.items():
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"{field} must be numeric")
                elif value < rules["min"] or value > rules["max"]:
                    errors.append(f"{field} out of range: {value}")

        # Cross-field validation
        if "boarding_count" in data and "alighting_count" in data and "passenger_count" in data:
            net_change = data.get("boarding_count", 0) - data.get("alighting_count", 0)
            if abs(net_change) > data.get("passenger_count", 0) * 2:
                errors.append("Inconsistent passenger flow data")

        return len(errors) == 0, errors

    def validate_weather_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate weather data record.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        required_fields = ["lat", "lon", "timestamp"]
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")

        # Validate coordinates
        if "lat" in data and "lon" in data:
            if not self._validate_coordinates(data["lat"], data["lon"]):
                errors.append("Invalid coordinates")

        # Validate numeric ranges
        for field, rules in self.weather_rules.items():
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"{field} must be numeric")
                elif value < rules["min"] or value > rules["max"]:
                    errors.append(f"{field} out of range: {value}")

        # Validate weather condition
        if "weather_main" in data:
            valid_conditions = ["Clear", "Clouds", "Rain", "Snow", "Thunderstorm",
                              "Drizzle", "Mist", "Fog", "Haze", "Dust", "Sand"]
            if data["weather_main"] not in valid_conditions:
                errors.append(f"Invalid weather condition: {data['weather_main']}")

        return len(errors) == 0, errors

    def validate_traffic_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate traffic data record.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        required_fields = ["timestamp"]
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")

        # Validate numeric ranges
        for field, rules in self.traffic_rules.items():
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"{field} must be numeric")
                elif value < rules["min"] or value > rules["max"]:
                    errors.append(f"{field} out of range: {value}")

        # Validate speed relationship
        if "current_speed_kmh" in data and "free_flow_speed_kmh" in data:
            if data["current_speed_kmh"] > data["free_flow_speed_kmh"] * 1.2:
                errors.append("Current speed exceeds free flow speed by too much")

        # Validate congestion level
        if "congestion_level" in data:
            valid_levels = ["free_flow", "light", "moderate", "heavy", "severe"]
            if data["congestion_level"] not in valid_levels:
                errors.append(f"Invalid congestion level: {data['congestion_level']}")

        return len(errors) == 0, errors

    def clean_apc_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize APC data.
        """
        cleaned = data.copy()

        # Handle missing values
        if "passenger_count" not in cleaned or cleaned["passenger_count"] is None:
            cleaned["passenger_count"] = 0

        # Cap extreme values
        for field, rules in self.apc_rules.items():
            if field in cleaned and cleaned[field] is not None:
                cleaned[field] = max(rules["min"], min(rules["max"], cleaned[field]))

        # Ensure consistency
        if "occupancy_percentage" in cleaned and "passenger_count" in cleaned:
            if cleaned["passenger_count"] == 0:
                cleaned["occupancy_percentage"] = 0

        # Normalize timestamp
        if "timestamp" in cleaned:
            cleaned["timestamp"] = self._normalize_timestamp(cleaned["timestamp"])

        return cleaned

    def clean_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize weather data.
        """
        cleaned = data.copy()

        # Handle missing values with defaults
        defaults = {
            "humidity_percent": 50,
            "wind_speed_ms": 0,
            "cloudiness_percent": 50,
            "visibility_m": 10000
        }

        for field, default_value in defaults.items():
            if field not in cleaned or cleaned[field] is None:
                cleaned[field] = default_value

        # Cap extreme values
        for field, rules in self.weather_rules.items():
            if field in cleaned and cleaned[field] is not None:
                cleaned[field] = max(rules["min"], min(rules["max"], cleaned[field]))

        # Normalize timestamp
        if "timestamp" in cleaned:
            cleaned["timestamp"] = self._normalize_timestamp(cleaned["timestamp"])

        return cleaned

    def clean_traffic_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize traffic data.
        """
        cleaned = data.copy()

        # Handle missing values
        if "confidence" not in cleaned or cleaned["confidence"] is None:
            cleaned["confidence"] = 0.5

        # Cap extreme values
        for field, rules in self.traffic_rules.items():
            if field in cleaned and cleaned[field] is not None:
                cleaned[field] = max(rules["min"], min(rules["max"], cleaned[field]))

        # Calculate derived fields
        if "current_speed_kmh" in cleaned and "free_flow_speed_kmh" in cleaned:
            free_flow = cleaned["free_flow_speed_kmh"]
            if free_flow > 0:
                cleaned["congestion_ratio"] = 1 - (cleaned["current_speed_kmh"] / free_flow)
            else:
                cleaned["congestion_ratio"] = 0

        # Normalize timestamp
        if "timestamp" in cleaned:
            cleaned["timestamp"] = self._normalize_timestamp(cleaned["timestamp"])

        return cleaned

    def detect_anomalies(self, data_series: List[float], method: str = "zscore") -> List[int]:
        """
        Detect anomalies in a data series.

        Args:
            data_series: List of numeric values
            method: Detection method ("zscore", "iqr", "isolation")

        Returns:
            List of indices where anomalies are detected
        """
        anomaly_indices = []

        if method == "zscore":
            # Z-score method
            mean = np.mean(data_series)
            std = np.std(data_series)
            threshold = 3

            for i, value in enumerate(data_series):
                z_score = abs((value - mean) / std) if std > 0 else 0
                if z_score > threshold:
                    anomaly_indices.append(i)

        elif method == "iqr":
            # Interquartile range method
            q1 = np.percentile(data_series, 25)
            q3 = np.percentile(data_series, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            for i, value in enumerate(data_series):
                if value < lower_bound or value > upper_bound:
                    anomaly_indices.append(i)

        return anomaly_indices

    def _validate_timestamp(self, timestamp: Any) -> bool:
        """Validate timestamp is reasonable."""
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, datetime):
                dt = timestamp
            else:
                return False

            # Check if timestamp is within reasonable range (not future, not too old)
            now = datetime.now()
            if dt > now + timedelta(hours=1):  # Allow 1 hour future for timezone issues
                return False
            if dt < now - timedelta(days=365):  # Not older than 1 year
                return False

            return True
        except:
            return False

    def _validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate coordinates are within Atlanta area."""
        # Rough bounds for Atlanta metro area
        return (33.5 <= lat <= 34.1) and (-84.7 <= lon <= -84.1)

    def _normalize_timestamp(self, timestamp: Any) -> str:
        """Normalize timestamp to ISO format."""
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, datetime):
                dt = timestamp
            else:
                dt = datetime.now()

            return dt.isoformat()
        except:
            return datetime.now().isoformat()

    def generate_quality_report(self,
                               data_source: str,
                               total_records: int,
                               valid_records: int,
                               errors: List[str]) -> Dict[str, Any]:
        """
        Generate data quality report.
        """
        return {
            "source": data_source,
            "timestamp": datetime.now().isoformat(),
            "total_records": total_records,
            "valid_records": valid_records,
            "invalid_records": total_records - valid_records,
            "validity_rate": valid_records / total_records if total_records > 0 else 0,
            "error_summary": self._summarize_errors(errors),
            "recommendations": self._generate_recommendations(errors)
        }

    def _summarize_errors(self, errors: List[str]) -> Dict[str, int]:
        """Summarize error types and counts."""
        summary = {}
        for error in errors:
            error_type = error.split(":")[0] if ":" in error else error
            summary[error_type] = summary.get(error_type, 0) + 1
        return summary

    def _generate_recommendations(self, errors: List[str]) -> List[str]:
        """Generate recommendations based on errors."""
        recommendations = []

        if any("Missing required field" in e for e in errors):
            recommendations.append("Check API response format and field mapping")

        if any("out of range" in e for e in errors):
            recommendations.append("Review data validation thresholds")

        if any("Invalid timestamp" in e for e in errors):
            recommendations.append("Synchronize system clocks and check timezone handling")

        return recommendations