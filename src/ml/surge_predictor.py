"""Real-time surge prediction and early warning system."""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from collections import deque
import json

logger = logging.getLogger(__name__)

@dataclass
class SurgePrediction:
    """Container for surge predictions."""
    location_id: str
    location_type: str  # stop, route, zone
    prediction_time: datetime
    surge_start_time: datetime
    surge_magnitude: float  # multiplier over normal demand
    confidence: float
    contributing_factors: List[str]
    affected_areas: List[str]
    recommended_actions: List[str]

class SurgePredictor:
    """Predict and detect demand surges with lead time."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.historical_surges = {}
        self.real_time_buffer = {}
        self.event_calendar = {}
        self.surge_patterns = {}
        self._initialize_buffers()

    def _default_config(self) -> Dict:
        """Default surge prediction configuration."""
        return {
            "prediction_horizon_minutes": 60,
            "update_frequency_seconds": 30,
            "surge_threshold": 1.5,  # 50% above normal
            "min_confidence": 0.7,
            "buffer_size": 120,  # 2 hours of data points
            "feature_window_minutes": 30,
            "alert_lead_time_minutes": 15
        }

    def _initialize_buffers(self):
        """Initialize real-time data buffers."""
        self.real_time_buffer = {
            "demand": deque(maxlen=self.config["buffer_size"]),
            "speed": deque(maxlen=self.config["buffer_size"]),
            "weather": deque(maxlen=self.config["buffer_size"]),
            "events": deque(maxlen=self.config["buffer_size"])
        }

    def predict_surge(self,
                     location_id: str,
                     current_demand: float,
                     historical_baseline: float,
                     external_factors: Optional[Dict] = None) -> Optional[SurgePrediction]:
        """Predict if a surge will occur at a location."""

        # Calculate current surge ratio
        surge_ratio = current_demand / historical_baseline if historical_baseline > 0 else 1.0

        # Extract features for prediction
        features = self._extract_features(
            location_id, current_demand, external_factors
        )

        # Calculate surge probability
        surge_probability = self._calculate_surge_probability(features)

        # Predict surge magnitude if likely
        if surge_probability > self.config["min_confidence"]:
            surge_magnitude = self._predict_magnitude(features, surge_ratio)
            surge_timing = self._predict_timing(features)

            # Identify contributing factors
            factors = self._identify_factors(features, external_factors)

            # Determine affected areas
            affected = self._predict_affected_areas(location_id, surge_magnitude)

            # Generate recommendations
            actions = self._generate_recommendations(
                surge_magnitude, surge_timing, factors
            )

            return SurgePrediction(
                location_id=location_id,
                location_type=self._get_location_type(location_id),
                prediction_time=datetime.now(),
                surge_start_time=surge_timing,
                surge_magnitude=surge_magnitude,
                confidence=surge_probability,
                contributing_factors=factors,
                affected_areas=affected,
                recommended_actions=actions
            )

        return None

    def detect_emerging_surge(self,
                             real_time_data: Dict,
                             threshold_multiplier: float = 1.3) -> List[Dict]:
        """Detect emerging surges from real-time data streams."""

        emerging_surges = []

        for location_id, data_stream in real_time_data.items():
            # Add to buffer
            self._update_buffer(location_id, data_stream)

            # Analyze trend
            trend = self._analyze_trend(location_id)

            if trend["is_surging"]:
                # Calculate surge characteristics
                surge_info = {
                    "location_id": location_id,
                    "detection_time": datetime.now().isoformat(),
                    "current_rate": trend["current_rate"],
                    "baseline_rate": trend["baseline_rate"],
                    "surge_ratio": trend["surge_ratio"],
                    "trend_direction": trend["direction"],
                    "acceleration": trend["acceleration"],
                    "estimated_peak_time": self._estimate_peak_time(trend),
                    "confidence": trend["confidence"]
                }

                emerging_surges.append(surge_info)

        return emerging_surges

    def analyze_surge_patterns(self,
                              historical_data: List[Dict],
                              location_id: str) -> Dict:
        """Analyze historical surge patterns for a location."""

        patterns = {
            "recurring_surges": [],
            "surge_triggers": [],
            "typical_duration_minutes": 0,
            "typical_magnitude": 0,
            "recovery_time_minutes": 0,
            "correlation_factors": {}
        }

        if not historical_data:
            return patterns

        # Group surges by characteristics
        time_based = {"hour": {}, "day": {}, "month": {}}
        event_based = {}
        weather_based = {}

        for surge in historical_data:
            timestamp = datetime.fromisoformat(surge["timestamp"])

            # Time-based patterns
            hour = timestamp.hour
            day = timestamp.weekday()
            month = timestamp.month

            for key, value in [("hour", hour), ("day", day), ("month", month)]:
                if value not in time_based[key]:
                    time_based[key][value] = []
                time_based[key][value].append(surge["magnitude"])

            # Event-based patterns
            if "event_type" in surge:
                event_type = surge["event_type"]
                if event_type not in event_based:
                    event_based[event_type] = []
                event_based[event_type].append(surge["magnitude"])

            # Weather-based patterns
            if "weather_condition" in surge:
                condition = surge["weather_condition"]
                if condition not in weather_based:
                    weather_based[condition] = []
                weather_based[condition].append(surge["magnitude"])

        # Identify recurring patterns
        for hour, magnitudes in time_based["hour"].items():
            if len(magnitudes) > 5:  # Minimum occurrences
                patterns["recurring_surges"].append({
                    "type": "hourly",
                    "value": hour,
                    "frequency": len(magnitudes),
                    "avg_magnitude": np.mean(magnitudes)
                })

        # Identify triggers
        for event_type, magnitudes in event_based.items():
            patterns["surge_triggers"].append({
                "type": "event",
                "trigger": event_type,
                "avg_magnitude": np.mean(magnitudes),
                "occurrences": len(magnitudes)
            })

        # Calculate typical characteristics
        all_durations = [s.get("duration_minutes", 30) for s in historical_data]
        all_magnitudes = [s.get("magnitude", 1.5) for s in historical_data]

        patterns["typical_duration_minutes"] = int(np.mean(all_durations))
        patterns["typical_magnitude"] = float(np.mean(all_magnitudes))
        patterns["recovery_time_minutes"] = int(np.mean(all_durations) * 1.5)

        # Store patterns for future use
        self.surge_patterns[location_id] = patterns

        return patterns

    def _extract_features(self,
                         location_id: str,
                         current_demand: float,
                         external_factors: Dict) -> Dict:
        """Extract features for surge prediction."""

        features = {
            "current_demand": current_demand,
            "time_of_day": datetime.now().hour,
            "day_of_week": datetime.now().weekday(),
            "is_weekend": datetime.now().weekday() >= 5,
            "is_holiday": self._is_holiday(datetime.now())
        }

        # Add historical patterns if available
        if location_id in self.surge_patterns:
            patterns = self.surge_patterns[location_id]
            features["historical_surge_frequency"] = len(patterns.get("recurring_surges", []))
            features["typical_surge_magnitude"] = patterns.get("typical_magnitude", 1.5)

        # Add external factors
        if external_factors:
            features.update({
                "weather_severity": external_factors.get("weather_severity", 0),
                "traffic_index": external_factors.get("traffic_index", 1.0),
                "event_proximity": external_factors.get("event_proximity", 0),
                "social_media_buzz": external_factors.get("social_media_buzz", 0)
            })

        # Add buffer statistics
        if location_id in self.real_time_buffer:
            buffer_data = self.real_time_buffer[location_id]
            if len(buffer_data) > 0:
                recent_data = list(buffer_data)[-10:]  # Last 10 data points
                features["recent_trend"] = np.mean(np.diff(recent_data)) if len(recent_data) > 1 else 0
                features["recent_volatility"] = np.std(recent_data) if len(recent_data) > 1 else 0

        return features

    def _calculate_surge_probability(self, features: Dict) -> float:
        """Calculate probability of surge occurrence."""

        probability = 0.0

        # Time-based probability
        hour = features.get("time_of_day", 12)
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hours
            probability += 0.3

        # Trend-based probability
        trend = features.get("recent_trend", 0)
        if trend > 0:
            probability += min(0.3, trend / 10)

        # External factors
        if features.get("event_proximity", 0) > 0:
            probability += 0.2
        if features.get("weather_severity", 0) > 3:
            probability += 0.15
        if features.get("traffic_index", 1.0) > 1.5:
            probability += 0.1

        # Historical patterns
        hist_freq = features.get("historical_surge_frequency", 0)
        if hist_freq > 10:
            probability += 0.2

        return min(1.0, probability)

    def _predict_magnitude(self, features: Dict, current_ratio: float) -> float:
        """Predict surge magnitude."""

        base_magnitude = features.get("typical_surge_magnitude", 1.5)

        # Adjust based on current conditions
        if features.get("is_holiday", False):
            base_magnitude *= 1.2
        if features.get("weather_severity", 0) > 5:
            base_magnitude *= 1.3
        if features.get("event_proximity", 0) > 0:
            base_magnitude *= 1.4

        # Consider current trend
        trend = features.get("recent_trend", 0)
        if trend > 0:
            base_magnitude *= (1 + trend / 100)

        # Blend with current observation
        predicted_magnitude = 0.7 * base_magnitude + 0.3 * current_ratio

        return max(1.0, min(5.0, predicted_magnitude))  # Cap between 1x and 5x

    def _predict_timing(self, features: Dict) -> datetime:
        """Predict when surge will begin/peak."""

        # Default: surge starts in 10-20 minutes
        lead_time = 15

        # Adjust based on trend acceleration
        trend = features.get("recent_trend", 0)
        if trend > 5:
            lead_time = 10  # Faster surge
        elif trend < 1:
            lead_time = 25  # Slower surge

        # Adjust for known patterns
        hour = features.get("time_of_day", 12)
        if hour in [6, 7, 16, 17]:  # Pre-rush hour
            lead_time = 30  # More predictable

        return datetime.now() + timedelta(minutes=lead_time)

    def _identify_factors(self, features: Dict, external: Optional[Dict]) -> List[str]:
        """Identify contributing factors to surge."""

        factors = []

        # Time-based factors
        hour = features.get("time_of_day", 12)
        if 7 <= hour <= 9:
            factors.append("Morning rush hour")
        elif 17 <= hour <= 19:
            factors.append("Evening rush hour")

        if features.get("is_holiday", False):
            factors.append("Holiday travel")

        # External factors
        if external:
            if external.get("weather_severity", 0) > 3:
                factors.append(f"Weather: {external.get('weather_type', 'severe')}")
            if external.get("event_name"):
                factors.append(f"Event: {external['event_name']}")
            if external.get("incident_type"):
                factors.append(f"Incident: {external['incident_type']}")

        # Pattern-based factors
        if features.get("historical_surge_frequency", 0) > 10:
            factors.append("Recurring pattern detected")

        return factors if factors else ["Demand fluctuation"]

    def _predict_affected_areas(self, location_id: str, magnitude: float) -> List[str]:
        """Predict which areas will be affected by surge."""

        affected = [location_id]

        # Add neighboring stops/routes based on magnitude
        if magnitude > 2.0:
            # Would query actual network topology
            affected.extend([
                f"{location_id}_upstream_1",
                f"{location_id}_downstream_1"
            ])

        if magnitude > 3.0:
            affected.extend([
                f"{location_id}_upstream_2",
                f"{location_id}_downstream_2",
                f"{location_id}_parallel_route"
            ])

        return affected

    def _generate_recommendations(self,
                                 magnitude: float,
                                 timing: datetime,
                                 factors: List[str]) -> List[str]:
        """Generate actionable recommendations."""

        recommendations = []
        lead_time = (timing - datetime.now()).total_seconds() / 60

        if magnitude > 3.0:
            recommendations.append(f"URGENT: Deploy 2-3 additional vehicles within {int(lead_time)} minutes")
            recommendations.append("Activate express service pattern")
            recommendations.append("Alert passengers via app and station displays")
        elif magnitude > 2.0:
            recommendations.append(f"Deploy 1-2 additional vehicles within {int(lead_time)} minutes")
            recommendations.append("Consider skip-stop service")
            recommendations.append("Increase service frequency")
        else:
            recommendations.append("Monitor situation closely")
            recommendations.append("Prepare reserve vehicles")

        # Factor-specific recommendations
        if "Weather" in str(factors):
            recommendations.append("Account for slower travel speeds")
        if "Event" in str(factors):
            recommendations.append("Coordinate with event venue")
        if "Morning rush" in str(factors) or "Evening rush" in str(factors):
            recommendations.append("Ensure all peak vehicles are deployed")

        return recommendations

    def _get_location_type(self, location_id: str) -> str:
        """Determine location type from ID."""
        if "stop" in location_id.lower():
            return "stop"
        elif "route" in location_id.lower():
            return "route"
        elif "zone" in location_id.lower():
            return "zone"
        return "unknown"

    def _is_holiday(self, date: datetime) -> bool:
        """Check if date is a holiday."""
        # Simplified - would use actual holiday calendar
        holidays = [
            (1, 1),   # New Year's Day
            (7, 4),   # Independence Day
            (12, 25), # Christmas
        ]
        return (date.month, date.day) in holidays

    def _update_buffer(self, location_id: str, data: Dict):
        """Update real-time data buffer."""
        if location_id not in self.real_time_buffer:
            self.real_time_buffer[location_id] = deque(maxlen=self.config["buffer_size"])

        self.real_time_buffer[location_id].append({
            "timestamp": datetime.now(),
            "value": data.get("demand", 0),
            "metadata": data
        })

    def _analyze_trend(self, location_id: str) -> Dict:
        """Analyze trend from buffered data."""

        if location_id not in self.real_time_buffer:
            return {"is_surging": False}

        buffer = list(self.real_time_buffer[location_id])
        if len(buffer) < 5:
            return {"is_surging": False}

        # Extract values
        values = [b["value"] for b in buffer]
        recent_values = values[-5:]
        baseline = np.mean(values[:-5]) if len(values) > 10 else np.mean(values)

        # Calculate metrics
        current_rate = np.mean(recent_values)
        surge_ratio = current_rate / baseline if baseline > 0 else 1.0

        # Calculate trend direction and acceleration
        if len(recent_values) > 1:
            differences = np.diff(recent_values)
            direction = "increasing" if np.mean(differences) > 0 else "decreasing"
            acceleration = np.diff(differences).mean() if len(differences) > 1 else 0
        else:
            direction = "stable"
            acceleration = 0

        is_surging = surge_ratio > self.config["surge_threshold"]

        return {
            "is_surging": is_surging,
            "current_rate": current_rate,
            "baseline_rate": baseline,
            "surge_ratio": surge_ratio,
            "direction": direction,
            "acceleration": acceleration,
            "confidence": min(0.95, len(buffer) / 20)  # More data = higher confidence
        }

    def _estimate_peak_time(self, trend: Dict) -> str:
        """Estimate when surge will peak."""

        if trend["acceleration"] > 0:
            # Accelerating - peak in 10-15 minutes
            peak_time = datetime.now() + timedelta(minutes=12)
        elif trend["direction"] == "increasing":
            # Steady increase - peak in 20-30 minutes
            peak_time = datetime.now() + timedelta(minutes=25)
        else:
            # Already peaking or decreasing
            peak_time = datetime.now() + timedelta(minutes=5)

        return peak_time.isoformat()

    def get_surge_forecast(self, horizon_hours: int = 4) -> List[Dict]:
        """Get surge forecast for next N hours."""

        forecast = []
        current_time = datetime.now()

        for hour_offset in range(horizon_hours):
            forecast_time = current_time + timedelta(hours=hour_offset)
            hour = forecast_time.hour

            # Predict surge likelihood based on time
            if 7 <= hour <= 9:
                surge_probability = 0.8
                expected_magnitude = 2.5
            elif 17 <= hour <= 19:
                surge_probability = 0.85
                expected_magnitude = 2.8
            elif 12 <= hour <= 13:
                surge_probability = 0.4
                expected_magnitude = 1.5
            else:
                surge_probability = 0.1
                expected_magnitude = 1.2

            forecast.append({
                "forecast_time": forecast_time.isoformat(),
                "surge_probability": surge_probability,
                "expected_magnitude": expected_magnitude,
                "confidence": 0.9 - (hour_offset * 0.1)  # Confidence decreases with time
            })

        return forecast