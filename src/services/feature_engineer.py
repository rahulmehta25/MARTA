# src/services/feature_engineer.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Performs feature engineering for ML models.
    Transforms raw data into features suitable for prediction.
    """

    def __init__(self):
        # Special dates for Atlanta
        self.holidays = [
            "01-01",  # New Year's Day
            "01-15",  # MLK Day (approximate)
            "05-27",  # Memorial Day (approximate)
            "07-04",  # Independence Day
            "09-02",  # Labor Day (approximate)
            "11-28",  # Thanksgiving (approximate)
            "12-25",  # Christmas
        ]

        # Major events that affect transit
        self.major_events = {
            "dragon_con": {"month": 9, "duration_days": 4},
            "peach_bowl": {"month": 12, "duration_days": 1},
            "atlanta_marathon": {"month": 11, "duration_days": 1},
        }

    def extract_temporal_features(self, timestamp: datetime) -> Dict[str, Any]:
        """
        Extract time-based features from timestamp.
        """
        features = {
            # Basic time features
            "hour": timestamp.hour,
            "day_of_week": timestamp.weekday(),  # 0=Monday, 6=Sunday
            "day_of_month": timestamp.day,
            "month": timestamp.month,
            "year": timestamp.year,
            "quarter": (timestamp.month - 1) // 3 + 1,

            # Derived features
            "is_weekend": timestamp.weekday() >= 5,
            "is_weekday": timestamp.weekday() < 5,

            # Time of day categories
            "is_morning_rush": 7 <= timestamp.hour <= 9,
            "is_evening_rush": 17 <= timestamp.hour <= 19,
            "is_midday": 10 <= timestamp.hour <= 16,
            "is_night": timestamp.hour < 6 or timestamp.hour >= 22,

            # Special periods
            "is_holiday": self._is_holiday(timestamp),
            "days_to_weekend": self._days_to_weekend(timestamp),
            "is_month_start": timestamp.day <= 3,
            "is_month_end": timestamp.day >= 28,
        }

        # Cyclical encoding for periodic features
        features.update(self._cyclical_encode_time(timestamp))

        return features

    def extract_weather_features(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract ML features from weather data.
        """
        features = {}

        # Basic weather metrics
        if "main" in weather_data:
            main = weather_data["main"]
            features["temperature_c"] = main.get("temp")
            features["feels_like_c"] = main.get("feels_like")
            features["humidity_percent"] = main.get("humidity")
            features["pressure_hpa"] = main.get("pressure")

        # Weather condition
        if "weather" in weather_data and weather_data["weather"]:
            weather = weather_data["weather"][0]
            features["weather_main"] = weather.get("main")
            features["weather_id"] = weather.get("id")

            # Categorize weather impact
            features["weather_impact"] = self._categorize_weather_impact(weather.get("id", 800))

        # Wind
        if "wind" in weather_data:
            features["wind_speed_ms"] = weather_data["wind"].get("speed", 0)
            features["wind_direction_deg"] = weather_data["wind"].get("deg", 0)

        # Precipitation
        features["rain_1h_mm"] = weather_data.get("rain", {}).get("1h", 0)
        features["snow_1h_mm"] = weather_data.get("snow", {}).get("1h", 0)
        features["total_precipitation"] = features["rain_1h_mm"] + features["snow_1h_mm"]

        # Visibility
        features["visibility_m"] = weather_data.get("visibility", 10000)
        features["visibility_impaired"] = features["visibility_m"] < 5000

        # Calculated features
        features["weather_severity"] = self._calculate_weather_severity(features)
        features["transit_impact_score"] = self._calculate_transit_impact(features)

        return features

    def extract_traffic_features(self, traffic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract ML features from traffic data.
        """
        features = {}

        # Flow segment data
        if "flowSegmentData" in traffic_data:
            flow = traffic_data["flowSegmentData"]
            features["current_speed_kmh"] = flow.get("currentSpeed", 0)
            features["free_flow_speed_kmh"] = flow.get("freeFlowSpeed", 60)
            features["current_travel_time_sec"] = flow.get("currentTravelTime", 0)
            features["free_flow_travel_time_sec"] = flow.get("freeFlowTravelTime", 0)

            # Calculate congestion metrics
            if features["free_flow_speed_kmh"] > 0:
                features["speed_ratio"] = features["current_speed_kmh"] / features["free_flow_speed_kmh"]
                features["congestion_ratio"] = 1 - features["speed_ratio"]
            else:
                features["speed_ratio"] = 1
                features["congestion_ratio"] = 0

            # Travel time delay
            if features["free_flow_travel_time_sec"] > 0:
                features["delay_ratio"] = (
                    features["current_travel_time_sec"] / features["free_flow_travel_time_sec"]
                ) - 1
            else:
                features["delay_ratio"] = 0

        # Categorize traffic level
        features["traffic_category"] = self._categorize_traffic(features.get("congestion_ratio", 0))
        features["traffic_index"] = self._calculate_traffic_index(features)

        # Binary features
        features["is_congested"] = features.get("congestion_ratio", 0) > 0.3
        features["is_heavily_congested"] = features.get("congestion_ratio", 0) > 0.6

        return features

    def extract_passenger_features(self, apc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract ML features from APC passenger data.
        """
        features = {}

        # Basic counts
        features["passenger_count"] = apc_data.get("passenger_count", 0)
        features["boarding_count"] = apc_data.get("boarding_count", 0)
        features["alighting_count"] = apc_data.get("alighting_count", 0)

        # Occupancy metrics
        features["occupancy_percentage"] = apc_data.get("occupancy_percentage", 0)
        capacity = apc_data.get("vehicle_capacity", 60)
        features["seats_available"] = max(0, capacity - features["passenger_count"])

        # Flow metrics
        features["net_passenger_change"] = features["boarding_count"] - features["alighting_count"]
        features["passenger_turnover"] = (
            features["boarding_count"] + features["alighting_count"]
        ) / 2 if features["passenger_count"] > 0 else 0

        # Crowding categories
        features["crowding_level"] = self._categorize_crowding(features["occupancy_percentage"])
        features["is_crowded"] = features["occupancy_percentage"] > 80
        features["is_at_capacity"] = features["occupancy_percentage"] >= 95

        # Dwell time
        features["dwell_time_seconds"] = apc_data.get("dwell_time_seconds", 30)
        features["extended_dwell"] = features["dwell_time_seconds"] > 60

        return features

    def create_lag_features(self,
                           data_series: pd.Series,
                           lag_periods: List[int] = [1, 2, 3, 24, 168]) -> pd.DataFrame:
        """
        Create lag features for time series prediction.

        Args:
            data_series: Time series data
            lag_periods: List of lag periods to create

        Returns:
            DataFrame with lag features
        """
        lag_features = pd.DataFrame()

        for lag in lag_periods:
            lag_features[f"lag_{lag}"] = data_series.shift(lag)

        # Rolling statistics
        lag_features["rolling_mean_24h"] = data_series.rolling(window=24).mean()
        lag_features["rolling_std_24h"] = data_series.rolling(window=24).std()
        lag_features["rolling_mean_7d"] = data_series.rolling(window=168).mean()
        lag_features["rolling_max_24h"] = data_series.rolling(window=24).max()
        lag_features["rolling_min_24h"] = data_series.rolling(window=24).min()

        # Difference features
        lag_features["diff_1h"] = data_series.diff(1)
        lag_features["diff_24h"] = data_series.diff(24)

        # Percentage change
        lag_features["pct_change_1h"] = data_series.pct_change(1)
        lag_features["pct_change_24h"] = data_series.pct_change(24)

        return lag_features

    def create_interaction_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create interaction features between different data sources.
        """
        interaction_features = {}

        # Weather-Traffic interactions
        if "weather_severity" in features and "traffic_index" in features:
            interaction_features["weather_traffic_impact"] = (
                features["weather_severity"] * features["traffic_index"] / 10
            )

        # Time-Weather interactions
        if "is_rush_hour" in features and "weather_severity" in features:
            interaction_features["rush_hour_weather_impact"] = (
                features.get("is_morning_rush", False) or features.get("is_evening_rush", False)
            ) * features["weather_severity"]

        # Passenger-Time interactions
        if "passenger_count" in features and "hour" in features:
            interaction_features["hourly_passenger_rate"] = (
                features["passenger_count"] / max(1, features["hour"])
            )

        # Crowding-Weather interaction
        if "is_crowded" in features and "weather_impact" in features:
            interaction_features["crowding_weather_factor"] = (
                features["is_crowded"] * features.get("weather_impact", 0)
            )

        return interaction_features

    def _cyclical_encode_time(self, timestamp: datetime) -> Dict[str, float]:
        """
        Apply cyclical encoding to time features.
        """
        hour = timestamp.hour
        day = timestamp.day
        month = timestamp.month
        day_of_week = timestamp.weekday()

        return {
            "hour_sin": np.sin(2 * np.pi * hour / 24),
            "hour_cos": np.cos(2 * np.pi * hour / 24),
            "day_sin": np.sin(2 * np.pi * day / 31),
            "day_cos": np.cos(2 * np.pi * day / 31),
            "month_sin": np.sin(2 * np.pi * month / 12),
            "month_cos": np.cos(2 * np.pi * month / 12),
            "dow_sin": np.sin(2 * np.pi * day_of_week / 7),
            "dow_cos": np.cos(2 * np.pi * day_of_week / 7),
        }

    def _is_holiday(self, timestamp: datetime) -> bool:
        """Check if date is a holiday."""
        date_str = timestamp.strftime("%m-%d")
        return date_str in self.holidays

    def _days_to_weekend(self, timestamp: datetime) -> int:
        """Calculate days until weekend."""
        dow = timestamp.weekday()
        if dow >= 5:  # Already weekend
            return 0
        return 5 - dow

    def _categorize_weather_impact(self, weather_id: int) -> str:
        """
        Categorize weather impact on transit based on weather ID.
        https://openweathermap.org/weather-conditions
        """
        if weather_id == 800:  # Clear
            return "none"
        elif 801 <= weather_id <= 804:  # Clouds
            return "minimal"
        elif 300 <= weather_id < 600:  # Drizzle and Rain
            if weather_id >= 502:  # Heavy rain
                return "high"
            return "moderate"
        elif 600 <= weather_id < 700:  # Snow
            return "severe"
        elif 200 <= weather_id < 300:  # Thunderstorm
            return "severe"
        elif 700 <= weather_id < 800:  # Atmosphere (fog, etc.)
            return "moderate"
        else:
            return "minimal"

    def _calculate_weather_severity(self, features: Dict[str, Any]) -> int:
        """
        Calculate weather severity score (0-10).
        """
        severity = 0

        # Temperature extremes
        temp = features.get("temperature_c", 20)
        if temp is not None:
            if temp < 0 or temp > 35:
                severity += 3
            elif temp < 5 or temp > 30:
                severity += 1

        # Precipitation
        precip = features.get("total_precipitation", 0)
        if precip > 10:
            severity += 4
        elif precip > 5:
            severity += 2
        elif precip > 0:
            severity += 1

        # Wind
        wind = features.get("wind_speed_ms", 0)
        if wind > 15:
            severity += 2
        elif wind > 10:
            severity += 1

        # Visibility
        if features.get("visibility_impaired", False):
            severity += 2

        return min(10, severity)

    def _calculate_transit_impact(self, features: Dict[str, Any]) -> float:
        """
        Calculate weather impact on transit operations (0-1).
        """
        impact = 0

        # Weather severity contribution
        severity = features.get("weather_severity", 0)
        impact += severity * 0.05

        # Precipitation impact
        if features.get("total_precipitation", 0) > 0:
            impact += 0.2

        # Visibility impact
        if features.get("visibility_impaired", False):
            impact += 0.15

        # Wind impact
        wind = features.get("wind_speed_ms", 0)
        if wind > 10:
            impact += 0.1

        return min(1.0, impact)

    def _categorize_traffic(self, congestion_ratio: float) -> str:
        """Categorize traffic congestion level."""
        if congestion_ratio < 0.1:
            return "free_flow"
        elif congestion_ratio < 0.3:
            return "light"
        elif congestion_ratio < 0.5:
            return "moderate"
        elif congestion_ratio < 0.7:
            return "heavy"
        else:
            return "severe"

    def _calculate_traffic_index(self, features: Dict[str, Any]) -> float:
        """Calculate overall traffic index (0-10)."""
        index = 0

        # Congestion contribution
        congestion = features.get("congestion_ratio", 0)
        index += congestion * 7

        # Delay contribution
        delay = features.get("delay_ratio", 0)
        index += min(3, delay * 3)

        return min(10, index)

    def _categorize_crowding(self, occupancy_percentage: float) -> str:
        """Categorize vehicle crowding level."""
        if occupancy_percentage < 30:
            return "low"
        elif occupancy_percentage < 60:
            return "moderate"
        elif occupancy_percentage < 85:
            return "high"
        elif occupancy_percentage < 100:
            return "very_high"
        else:
            return "overcapacity"

    def prepare_ml_dataset(self,
                           temporal_features: Dict[str, Any],
                           weather_features: Dict[str, Any],
                           traffic_features: Dict[str, Any],
                           passenger_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine all features into ML-ready dataset.
        """
        ml_features = {}

        # Combine all feature sets
        ml_features.update(temporal_features)
        ml_features.update(weather_features)
        ml_features.update(traffic_features)
        ml_features.update(passenger_features)

        # Add interaction features
        interaction_features = self.create_interaction_features(ml_features)
        ml_features.update(interaction_features)

        # Remove non-numeric features for ML
        numeric_features = {}
        for key, value in ml_features.items():
            if isinstance(value, (int, float, bool, np.number)):
                numeric_features[key] = float(value) if isinstance(value, bool) else value
            elif isinstance(value, str) and key in ["weather_main", "traffic_category", "crowding_level"]:
                # Keep categorical features for encoding
                numeric_features[key] = value

        return numeric_features