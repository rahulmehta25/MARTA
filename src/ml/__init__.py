"""Machine Learning module for MARTA demand forecasting and optimization."""

from typing import Dict, Any

__version__ = "1.0.0"

def get_ml_config() -> Dict[str, Any]:
    """Get ML configuration settings."""
    return {
        "model_version": __version__,
        "features": [
            "hour_of_day",
            "day_of_week",
            "month",
            "is_weekend",
            "is_holiday",
            "weather_temp",
            "weather_precipitation",
            "previous_hour_demand",
            "rolling_avg_7d",
            "rolling_avg_30d",
            "special_events",
            "traffic_index"
        ],
        "target": "passenger_count",
        "forecast_horizon": 24,  # hours
        "update_frequency": 900,  # seconds (15 minutes)
        "confidence_level": 0.95
    }