"""
Forecast service for demand prediction.
"""
import os
import random
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np

from backend.api.core.config import settings
from backend.api.core.logging import get_logger
from backend.api.models.stops import ForecastDataPoint, DemandLevel

logger = get_logger(__name__)


class ForecastService:
    """Service for generating demand forecasts."""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.model_name = "ensemble_v2"
        self.model_version = "2.1.0"
        self._load_models()

    def _load_models(self):
        """Load ML models from disk."""
        try:
            import pickle

            # Try to load XGBoost model
            xgb_path = os.path.join(settings.models_dir, "xgboost_model.pkl")
            if os.path.exists(xgb_path):
                with open(xgb_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.info("Loaded XGBoost model")

            # Load scaler if available
            scaler_path = os.path.join(settings.models_dir, "lstm_scaler.pkl")
            if os.path.exists(scaler_path):
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                logger.info("Loaded scaler")

        except Exception as e:
            logger.warning(f"Could not load ML models: {e}")
            self.model = None
            self.scaler = None

    def _classify_demand(self, value: float) -> DemandLevel:
        """Classify demand value into level."""
        if value > 100:
            return DemandLevel.CRITICAL
        elif value > 60:
            return DemandLevel.HIGH
        elif value > 30:
            return DemandLevel.MEDIUM
        else:
            return DemandLevel.LOW

    def _get_time_features(self, dt: datetime) -> dict:
        """Extract time-based features."""
        hour = dt.hour
        day_of_week = dt.weekday()
        is_weekend = day_of_week >= 5

        # Cyclical features
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)

        return {
            "hour": hour,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "day_sin": day_sin,
            "day_cos": day_cos,
        }

    def _generate_base_demand(self, hour: int, is_weekend: bool) -> float:
        """Generate base demand based on typical patterns."""
        # Rush hour peaks
        if not is_weekend:
            if 7 <= hour <= 9:
                base = 80 + random.uniform(-10, 20)
            elif 16 <= hour <= 18:
                base = 75 + random.uniform(-10, 15)
            elif 10 <= hour <= 15:
                base = 45 + random.uniform(-10, 10)
            elif 6 <= hour <= 22:
                base = 30 + random.uniform(-5, 10)
            else:
                base = 10 + random.uniform(-3, 5)
        else:
            # Weekend patterns
            if 10 <= hour <= 18:
                base = 40 + random.uniform(-10, 15)
            elif 18 <= hour <= 22:
                base = 35 + random.uniform(-5, 10)
            else:
                base = 15 + random.uniform(-5, 5)

        return max(0, base)

    async def generate_forecast(
        self,
        stop_id: str,
        horizon_hours: int = 24,
        granularity_minutes: int = 60,
        include_confidence: bool = True,
    ) -> List[ForecastDataPoint]:
        """Generate demand forecast for a stop."""
        logger.info(
            "Generating forecast",
            stop_id=stop_id,
            horizon_hours=horizon_hours,
        )

        forecasts = []
        now = datetime.utcnow()
        intervals = horizon_hours * 60 // granularity_minutes

        for i in range(intervals):
            forecast_time = now + timedelta(minutes=i * granularity_minutes)
            features = self._get_time_features(forecast_time)

            # Try to use ML model
            if self.model is not None:
                try:
                    # Prepare features for model
                    X = np.array([[
                        features["hour"],
                        features["day_of_week"],
                        int(features["is_weekend"]),
                        0,  # is_holiday
                        features["hour_sin"],
                        features["hour_cos"],
                        features["day_sin"],
                        features["day_cos"],
                    ]])
                    predicted = self.model.predict(X)[0]
                except Exception as e:
                    logger.warning(f"Model prediction failed: {e}")
                    predicted = self._generate_base_demand(
                        features["hour"],
                        features["is_weekend"],
                    )
            else:
                # Use pattern-based prediction
                predicted = self._generate_base_demand(
                    features["hour"],
                    features["is_weekend"],
                )

            # Generate confidence intervals
            confidence_lower = None
            confidence_upper = None
            if include_confidence:
                # Wider intervals for further out predictions
                uncertainty = 0.15 + (i / intervals) * 0.15
                confidence_lower = max(0, predicted * (1 - uncertainty))
                confidence_upper = predicted * (1 + uncertainty)

            forecasts.append(ForecastDataPoint(
                timestamp=forecast_time,
                predicted_demand=round(predicted, 1),
                demand_level=self._classify_demand(predicted),
                confidence_lower=round(confidence_lower, 1) if confidence_lower else None,
                confidence_upper=round(confidence_upper, 1) if confidence_upper else None,
            ))

        return forecasts

    def generate_demo_forecast(
        self,
        horizon_hours: int,
        granularity_minutes: int,
    ) -> List[ForecastDataPoint]:
        """Generate demo forecast data."""
        forecasts = []
        now = datetime.utcnow()
        intervals = horizon_hours * 60 // granularity_minutes

        for i in range(intervals):
            forecast_time = now + timedelta(minutes=i * granularity_minutes)
            features = self._get_time_features(forecast_time)

            predicted = self._generate_base_demand(
                features["hour"],
                features["is_weekend"],
            )

            uncertainty = 0.15 + (i / intervals) * 0.15
            confidence_lower = max(0, predicted * (1 - uncertainty))
            confidence_upper = predicted * (1 + uncertainty)

            forecasts.append(ForecastDataPoint(
                timestamp=forecast_time,
                predicted_demand=round(predicted, 1),
                demand_level=self._classify_demand(predicted),
                confidence_lower=round(confidence_lower, 1),
                confidence_upper=round(confidence_upper, 1),
            ))

        return forecasts
