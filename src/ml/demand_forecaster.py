"""Demand forecasting model using Prophet and LSTM for MARTA stops."""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json
import pickle
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class DemandPrediction:
    """Container for demand predictions."""
    stop_id: str
    timestamp: datetime
    predicted_demand: float
    confidence_lower: float
    confidence_upper: float
    surge_probability: float
    overcrowding_risk: float

class DemandForecaster:
    """ML model for forecasting passenger demand at stop level."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.models = {}  # Store models per stop
        self.historical_data = {}
        self.feature_importance = {}

    def _default_config(self) -> Dict:
        """Default model configuration."""
        return {
            "model_type": "ensemble",  # prophet, lstm, or ensemble
            "forecast_horizon": 24,  # hours
            "update_frequency": 900,  # 15 minutes
            "min_historical_days": 30,
            "seasonality": {
                "daily": True,
                "weekly": True,
                "yearly": False
            },
            "external_features": [
                "weather",
                "events",
                "traffic",
                "holidays"
            ]
        }

    def train(self, historical_data: pd.DataFrame, stop_id: str) -> Dict[str, Any]:
        """Train demand forecasting model for a specific stop."""
        try:
            # Prepare features
            features = self._prepare_features(historical_data)

            # Train ensemble model
            if self.config["model_type"] == "ensemble":
                prophet_model = self._train_prophet(features)
                lstm_model = self._train_lstm(features)

                self.models[stop_id] = {
                    "prophet": prophet_model,
                    "lstm": lstm_model,
                    "weights": [0.6, 0.4],  # Weighted ensemble
                    "last_trained": datetime.now(),
                    "metrics": self._calculate_metrics(features)
                }

            self.historical_data[stop_id] = features

            return {
                "status": "success",
                "stop_id": stop_id,
                "model_type": self.config["model_type"],
                "training_samples": len(features),
                "metrics": self.models[stop_id]["metrics"]
            }

        except Exception as e:
            logger.error(f"Training failed for stop {stop_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    def predict(self, stop_id: str,
                start_time: datetime,
                horizon_hours: int = 24) -> List[DemandPrediction]:
        """Generate demand predictions for a stop."""

        if stop_id not in self.models:
            raise ValueError(f"No model trained for stop {stop_id}")

        predictions = []
        model_data = self.models[stop_id]

        # Generate time series for prediction
        time_range = pd.date_range(
            start=start_time,
            periods=horizon_hours,
            freq='H'
        )

        for timestamp in time_range:
            # Get features for this timestamp
            features = self._get_realtime_features(stop_id, timestamp)

            # Ensemble prediction
            if self.config["model_type"] == "ensemble":
                prophet_pred = self._predict_prophet(
                    model_data["prophet"], features
                )
                lstm_pred = self._predict_lstm(
                    model_data["lstm"], features
                )

                # Weighted average
                weights = model_data["weights"]
                pred_demand = (
                    weights[0] * prophet_pred["yhat"] +
                    weights[1] * lstm_pred["prediction"]
                )

                # Calculate confidence intervals
                conf_lower = min(prophet_pred["yhat_lower"],
                               lstm_pred["lower_bound"])
                conf_upper = max(prophet_pred["yhat_upper"],
                               lstm_pred["upper_bound"])
            else:
                pred_demand = prophet_pred["yhat"]
                conf_lower = prophet_pred["yhat_lower"]
                conf_upper = prophet_pred["yhat_upper"]

            # Calculate surge and overcrowding metrics
            surge_prob = self._calculate_surge_probability(
                stop_id, pred_demand, timestamp
            )
            crowd_risk = self._calculate_overcrowding_risk(
                stop_id, pred_demand
            )

            predictions.append(DemandPrediction(
                stop_id=stop_id,
                timestamp=timestamp,
                predicted_demand=pred_demand,
                confidence_lower=conf_lower,
                confidence_upper=conf_upper,
                surge_probability=surge_prob,
                overcrowding_risk=crowd_risk
            ))

        return predictions

    def _prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for model training."""
        features = data.copy()

        # Time-based features
        features['hour'] = features['timestamp'].dt.hour
        features['day_of_week'] = features['timestamp'].dt.dayofweek
        features['month'] = features['timestamp'].dt.month
        features['is_weekend'] = features['day_of_week'].isin([5, 6]).astype(int)

        # Lag features
        features['demand_lag_1h'] = features['passenger_count'].shift(1)
        features['demand_lag_24h'] = features['passenger_count'].shift(24)
        features['demand_lag_168h'] = features['passenger_count'].shift(168)  # 1 week

        # Rolling statistics
        features['rolling_mean_24h'] = features['passenger_count'].rolling(24).mean()
        features['rolling_std_24h'] = features['passenger_count'].rolling(24).std()
        features['rolling_mean_168h'] = features['passenger_count'].rolling(168).mean()

        # Remove NaN rows
        features = features.dropna()

        return features

    def _train_prophet(self, data: pd.DataFrame) -> Dict:
        """Train Prophet model (simplified for now)."""
        # This would use Facebook Prophet in production
        # For now, using simplified time series model
        model = {
            "type": "prophet",
            "trained_at": datetime.now(),
            "seasonality": self.config["seasonality"],
            "data_points": len(data)
        }

        # Calculate basic statistics for prediction
        model["hourly_avg"] = data.groupby('hour')['passenger_count'].mean().to_dict()
        model["dow_avg"] = data.groupby('day_of_week')['passenger_count'].mean().to_dict()
        model["baseline"] = data['passenger_count'].mean()
        model["std"] = data['passenger_count'].std()

        return model

    def _train_lstm(self, data: pd.DataFrame) -> Dict:
        """Train LSTM model (simplified for now)."""
        # This would use TensorFlow/PyTorch LSTM in production
        # For now, using simplified approach
        model = {
            "type": "lstm",
            "trained_at": datetime.now(),
            "sequence_length": 24,
            "features": ['hour', 'day_of_week', 'demand_lag_1h', 'demand_lag_24h']
        }

        # Calculate patterns for prediction
        model["patterns"] = {
            "morning_peak": data[data['hour'].isin([7,8,9])]['passenger_count'].mean(),
            "evening_peak": data[data['hour'].isin([17,18,19])]['passenger_count'].mean(),
            "midday": data[data['hour'].isin([11,12,13,14])]['passenger_count'].mean(),
            "night": data[data['hour'].isin([22,23,0,1,2])]['passenger_count'].mean()
        }

        return model

    def _predict_prophet(self, model: Dict, features: Dict) -> Dict:
        """Generate Prophet prediction."""
        hour = features.get('hour', 12)
        dow = features.get('day_of_week', 1)

        # Simple prediction based on historical averages
        hourly_factor = model['hourly_avg'].get(hour, model['baseline'])
        dow_factor = model['dow_avg'].get(dow, model['baseline'])

        prediction = (hourly_factor * 0.6 + dow_factor * 0.4)

        return {
            "yhat": prediction,
            "yhat_lower": prediction - 1.96 * model['std'],
            "yhat_upper": prediction + 1.96 * model['std']
        }

    def _predict_lstm(self, model: Dict, features: Dict) -> Dict:
        """Generate LSTM prediction."""
        hour = features.get('hour', 12)

        # Determine time period
        if 7 <= hour <= 9:
            base_pred = model['patterns']['morning_peak']
        elif 17 <= hour <= 19:
            base_pred = model['patterns']['evening_peak']
        elif 11 <= hour <= 14:
            base_pred = model['patterns']['midday']
        else:
            base_pred = model['patterns']['night']

        # Add some variability
        prediction = base_pred * np.random.uniform(0.9, 1.1)

        return {
            "prediction": prediction,
            "lower_bound": prediction * 0.8,
            "upper_bound": prediction * 1.2
        }

    def _get_realtime_features(self, stop_id: str, timestamp: datetime) -> Dict:
        """Get real-time features for prediction."""
        return {
            "hour": timestamp.hour,
            "day_of_week": timestamp.weekday(),
            "month": timestamp.month,
            "is_weekend": timestamp.weekday() in [5, 6],
            "timestamp": timestamp
        }

    def _calculate_surge_probability(self, stop_id: str,
                                    predicted_demand: float,
                                    timestamp: datetime) -> float:
        """Calculate probability of demand surge."""
        if stop_id not in self.historical_data:
            return 0.0

        historical = self.historical_data[stop_id]
        hour_avg = historical[historical['hour'] == timestamp.hour]['passenger_count'].mean()

        if hour_avg == 0:
            return 0.0

        surge_ratio = predicted_demand / hour_avg

        # Sigmoid function to convert ratio to probability
        surge_prob = 1 / (1 + np.exp(-2 * (surge_ratio - 1.5)))

        return min(max(surge_prob, 0.0), 1.0)

    def _calculate_overcrowding_risk(self, stop_id: str,
                                    predicted_demand: float) -> float:
        """Calculate risk of overcrowding."""
        # Define capacity thresholds (would come from stop data)
        capacity_thresholds = {
            "low": 20,
            "medium": 50,
            "high": 100,
            "critical": 150
        }

        if predicted_demand < capacity_thresholds["low"]:
            return 0.0
        elif predicted_demand < capacity_thresholds["medium"]:
            return 0.25
        elif predicted_demand < capacity_thresholds["high"]:
            return 0.5
        elif predicted_demand < capacity_thresholds["critical"]:
            return 0.75
        else:
            return 1.0

    def _calculate_metrics(self, data: pd.DataFrame) -> Dict:
        """Calculate model performance metrics."""
        return {
            "mae": 0.0,  # Would calculate actual MAE in production
            "rmse": 0.0,  # Would calculate actual RMSE in production
            "mape": 0.0,  # Would calculate actual MAPE in production
            "training_samples": len(data),
            "date_range": {
                "start": data['timestamp'].min().isoformat(),
                "end": data['timestamp'].max().isoformat()
            }
        }

    def update_model(self, stop_id: str, new_data: pd.DataFrame):
        """Incrementally update model with new data."""
        if stop_id in self.historical_data:
            # Append new data
            self.historical_data[stop_id] = pd.concat([
                self.historical_data[stop_id],
                new_data
            ]).drop_duplicates().sort_values('timestamp')

            # Keep only recent data (e.g., last 90 days)
            cutoff_date = datetime.now() - timedelta(days=90)
            self.historical_data[stop_id] = self.historical_data[stop_id][
                self.historical_data[stop_id]['timestamp'] > cutoff_date
            ]

            # Retrain if enough new data
            if len(new_data) > 100:
                self.train(self.historical_data[stop_id], stop_id)

    def save_model(self, filepath: str):
        """Save trained models to disk."""
        with open(filepath, 'wb') as f:
            pickle.dump({
                "models": self.models,
                "config": self.config,
                "feature_importance": self.feature_importance
            }, f)

    def load_model(self, filepath: str):
        """Load trained models from disk."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.models = data["models"]
            self.config = data["config"]
            self.feature_importance = data.get("feature_importance", {})