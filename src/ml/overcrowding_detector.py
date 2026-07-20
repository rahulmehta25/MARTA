"""Real-time overcrowding detection and alert system."""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class CrowdingLevel(Enum):
    """Enumeration of crowding severity levels."""
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"
    SEVERE = "severe"

@dataclass
class CrowdingAlert:
    """Container for overcrowding alerts."""
    stop_id: str
    route_id: str
    timestamp: datetime
    current_occupancy: int
    capacity: int
    crowding_level: CrowdingLevel
    predicted_duration_minutes: int
    recommended_actions: List[str]
    affected_stops_downstream: List[str]
    alternative_routes: List[str]

class OvercrowdingDetector:
    """Detect and predict overcrowding patterns in real-time."""

    def __init__(self, capacity_config: Optional[Dict] = None):
        self.capacity_config = capacity_config or self._default_capacity()
        self.historical_patterns = {}
        self.current_alerts = {}
        self.crowding_thresholds = {
            CrowdingLevel.NORMAL: 0.5,      # < 50% capacity
            CrowdingLevel.ELEVATED: 0.7,    # 50-70% capacity
            CrowdingLevel.HIGH: 0.85,       # 70-85% capacity
            CrowdingLevel.CRITICAL: 0.95,   # 85-95% capacity
            CrowdingLevel.SEVERE: 1.0       # > 95% capacity
        }

    def _default_capacity(self) -> Dict:
        """Default capacity configuration."""
        return {
            "bus_standard": 60,
            "bus_articulated": 90,
            "rail_car": 150,
            "platform_small": 100,
            "platform_medium": 200,
            "platform_large": 400
        }

    def detect_crowding(self,
                       occupancy_data: Dict,
                       stop_id: str,
                       route_id: str) -> Optional[CrowdingAlert]:
        """Detect overcrowding at a specific stop/vehicle."""

        current_occupancy = occupancy_data.get("passenger_count", 0)
        vehicle_type = occupancy_data.get("vehicle_type", "bus_standard")
        capacity = self.capacity_config.get(vehicle_type, 60)

        # Calculate occupancy ratio
        occupancy_ratio = current_occupancy / capacity if capacity > 0 else 0

        # Determine crowding level
        crowding_level = self._classify_crowding(occupancy_ratio)

        # Only generate alert for elevated or higher levels
        if crowding_level in [CrowdingLevel.NORMAL]:
            return None

        # Predict duration based on historical patterns
        predicted_duration = self._predict_crowding_duration(
            stop_id, route_id, crowding_level
        )

        # Generate recommended actions
        actions = self._generate_recommendations(
            crowding_level, occupancy_ratio, route_id
        )

        # Identify affected downstream stops
        affected_stops = self._get_affected_stops(stop_id, route_id)

        # Find alternative routes
        alternatives = self._find_alternative_routes(stop_id, route_id)

        alert = CrowdingAlert(
            stop_id=stop_id,
            route_id=route_id,
            timestamp=datetime.now(),
            current_occupancy=current_occupancy,
            capacity=capacity,
            crowding_level=crowding_level,
            predicted_duration_minutes=predicted_duration,
            recommended_actions=actions,
            affected_stops_downstream=affected_stops,
            alternative_routes=alternatives
        )

        # Store alert
        alert_key = f"{stop_id}_{route_id}"
        self.current_alerts[alert_key] = alert

        return alert

    def predict_crowding_propagation(self,
                                    initial_stop: str,
                                    route_id: str,
                                    time_horizon_minutes: int = 30) -> List[Dict]:
        """Predict how crowding will propagate along a route."""

        predictions = []
        current_time = datetime.now()

        # Get route stops
        route_stops = self._get_route_stops(route_id)
        initial_idx = route_stops.index(initial_stop) if initial_stop in route_stops else 0

        # Simulate crowding propagation
        for i, stop_id in enumerate(route_stops[initial_idx:]):
            # Estimate arrival time at this stop
            travel_time = i * 3  # Assume 3 minutes between stops
            arrival_time = current_time + timedelta(minutes=travel_time)

            if travel_time > time_horizon_minutes:
                break

            # Predict occupancy at this stop
            boarding_rate = self._get_boarding_rate(stop_id, arrival_time)
            alighting_rate = self._get_alighting_rate(stop_id, arrival_time)

            # Simple propagation model
            if i == 0:
                predicted_occupancy = self._get_current_occupancy(stop_id, route_id)
            else:
                prev_occupancy = predictions[-1]["predicted_occupancy"]
                predicted_occupancy = prev_occupancy * (1 - alighting_rate) + boarding_rate

            predictions.append({
                "stop_id": stop_id,
                "arrival_time": arrival_time.isoformat(),
                "predicted_occupancy": predicted_occupancy,
                "crowding_risk": self._calculate_risk_score(predicted_occupancy),
                "confidence": 0.8 - (i * 0.05)  # Confidence decreases with distance
            })

        return predictions

    def analyze_patterns(self,
                        historical_data: List[Dict],
                        stop_id: str) -> Dict:
        """Analyze historical crowding patterns."""

        patterns = {
            "peak_hours": [],
            "peak_days": [],
            "average_duration": 0,
            "frequency": 0,
            "seasonal_trends": []
        }

        if not historical_data:
            return patterns

        # Analyze by hour
        hourly_crowding = {}
        daily_crowding = {}
        durations = []

        for record in historical_data:
            timestamp = datetime.fromisoformat(record["timestamp"])
            hour = timestamp.hour
            day = timestamp.weekday()
            duration = record.get("duration_minutes", 0)

            if hour not in hourly_crowding:
                hourly_crowding[hour] = []
            hourly_crowding[hour].append(record["occupancy_ratio"])

            if day not in daily_crowding:
                daily_crowding[day] = []
            daily_crowding[day].append(record["occupancy_ratio"])

            if duration > 0:
                durations.append(duration)

        # Find peak hours (top 3)
        hour_averages = {h: np.mean(v) for h, v in hourly_crowding.items()}
        patterns["peak_hours"] = sorted(
            hour_averages.keys(),
            key=lambda h: hour_averages[h],
            reverse=True
        )[:3]

        # Find peak days
        day_averages = {d: np.mean(v) for d, v in daily_crowding.items()}
        patterns["peak_days"] = sorted(
            day_averages.keys(),
            key=lambda d: day_averages[d],
            reverse=True
        )[:2]

        # Calculate average duration
        patterns["average_duration"] = int(np.mean(durations)) if durations else 0

        # Calculate frequency (crowding events per day)
        patterns["frequency"] = len(historical_data) / 30  # Assume 30 days of data

        # Store for future use
        self.historical_patterns[stop_id] = patterns

        return patterns

    def _classify_crowding(self, occupancy_ratio: float) -> CrowdingLevel:
        """Classify crowding level based on occupancy ratio."""
        if occupancy_ratio < 0.5:
            return CrowdingLevel.NORMAL
        elif occupancy_ratio < 0.7:
            return CrowdingLevel.ELEVATED
        elif occupancy_ratio < 0.85:
            return CrowdingLevel.HIGH
        elif occupancy_ratio < 0.95:
            return CrowdingLevel.CRITICAL
        else:
            return CrowdingLevel.SEVERE

    def _predict_crowding_duration(self,
                                  stop_id: str,
                                  route_id: str,
                                  level: CrowdingLevel) -> int:
        """Predict how long crowding will last."""

        # Use historical patterns if available
        if stop_id in self.historical_patterns:
            return self.historical_patterns[stop_id].get("average_duration", 15)

        # Default predictions based on crowding level
        default_durations = {
            CrowdingLevel.NORMAL: 0,
            CrowdingLevel.ELEVATED: 10,
            CrowdingLevel.HIGH: 20,
            CrowdingLevel.CRITICAL: 30,
            CrowdingLevel.SEVERE: 45
        }

        return default_durations.get(level, 15)

    def _generate_recommendations(self,
                                 level: CrowdingLevel,
                                 occupancy_ratio: float,
                                 route_id: str) -> List[str]:
        """Generate recommended actions based on crowding level."""

        recommendations = []

        if level == CrowdingLevel.ELEVATED:
            recommendations.append("Monitor situation - may require intervention")
            recommendations.append("Prepare backup vehicle if available")

        elif level == CrowdingLevel.HIGH:
            recommendations.append("Dispatch additional vehicle to route")
            recommendations.append("Alert passengers of delays via app/signs")
            recommendations.append("Consider express service to clear backlog")

        elif level == CrowdingLevel.CRITICAL:
            recommendations.append("URGENT: Deploy reserve vehicles immediately")
            recommendations.append("Implement skip-stop service pattern")
            recommendations.append("Station staff to manage passenger flow")
            recommendations.append("Activate crowd control measures")

        elif level == CrowdingLevel.SEVERE:
            recommendations.append("EMERGENCY: Multiple reserve vehicles required")
            recommendations.append("Consider temporary service suspension")
            recommendations.append("Deploy security/crowd control personnel")
            recommendations.append("Activate emergency response protocol")
            recommendations.append("Coordinate with adjacent routes for support")

        return recommendations

    def _get_affected_stops(self, stop_id: str, route_id: str) -> List[str]:
        """Get list of stops that will be affected by crowding."""
        # Simplified - would use actual route data
        route_stops = self._get_route_stops(route_id)
        try:
            current_idx = route_stops.index(stop_id)
            # Return next 5 stops
            return route_stops[current_idx + 1:current_idx + 6]
        except (ValueError, IndexError):
            return []

    def _find_alternative_routes(self, stop_id: str, route_id: str) -> List[str]:
        """Find alternative routes serving the same stop."""
        # Simplified - would query route database
        all_routes = ["1", "2", "3", "4", "5", "10", "20", "30"]
        return [r for r in all_routes if r != route_id][:3]

    def _get_route_stops(self, route_id: str) -> List[str]:
        """Get ordered list of stops for a route."""
        # Simplified - would query actual route data
        return [f"stop_{i}" for i in range(1, 21)]

    def _get_boarding_rate(self, stop_id: str, timestamp: datetime) -> float:
        """Get expected boarding rate at a stop."""
        # Simplified - would use ML predictions
        hour = timestamp.hour
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # Peak hours
            return np.random.uniform(5, 15)
        else:
            return np.random.uniform(1, 5)

    def _get_alighting_rate(self, stop_id: str, timestamp: datetime) -> float:
        """Get expected alighting rate at a stop."""
        # Simplified - would use ML predictions
        return np.random.uniform(0.1, 0.3)

    def _get_current_occupancy(self, stop_id: str, route_id: str) -> float:
        """Get current occupancy for a stop/route."""
        # Would query real-time data
        alert_key = f"{stop_id}_{route_id}"
        if alert_key in self.current_alerts:
            return self.current_alerts[alert_key].current_occupancy
        return np.random.uniform(20, 60)

    def _calculate_risk_score(self, occupancy: float) -> float:
        """Calculate risk score (0-1) based on occupancy."""
        capacity = self.capacity_config.get("bus_standard", 60)
        ratio = occupancy / capacity
        return min(ratio, 1.0)

    def get_system_status(self) -> Dict:
        """Get overall system crowding status."""
        active_alerts = len(self.current_alerts)

        if active_alerts == 0:
            system_level = "normal"
        elif active_alerts < 5:
            system_level = "elevated"
        elif active_alerts < 10:
            system_level = "high"
        else:
            system_level = "critical"

        critical_alerts = [
            alert for alert in self.current_alerts.values()
            if alert.crowding_level in [CrowdingLevel.CRITICAL, CrowdingLevel.SEVERE]
        ]

        return {
            "system_level": system_level,
            "active_alerts": active_alerts,
            "critical_alerts": len(critical_alerts),
            "affected_routes": list(set(
                alert.route_id for alert in self.current_alerts.values()
            )),
            "timestamp": datetime.now().isoformat()
        }