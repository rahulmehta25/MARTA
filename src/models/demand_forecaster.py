"""
Demand Forecasting Model
Implements LSTM and XGBoost models for predicting rider demand at stop-level
"""
import os
import logging
import pickle
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import psycopg2

# Machine Learning imports
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam

# SHAP for explainability
import shap

from config.settings import settings

logger = logging.getLogger(__name__)


class DemandForecaster:
    """Main demand forecasting model class"""
    
    def __init__(self):
        self.db_connection = None
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        
        # Create models directory
        os.makedirs(settings.MODELS_DIR, exist_ok=True)
    
    def create_db_connection(self):
        """Create database connection"""
        try:
            self.db_connection = psycopg2.connect(
                host=settings.DB_HOST,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                port=settings.DB_PORT
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def load_training_data(self, days_back: int = 30) -> pd.DataFrame:
        """Load training data from the unified database"""
        if not self.db_connection:
            self.create_db_connection()
        
        query = """
            SELECT 
                timestamp,
                stop_id,
                route_id,
                trip_id,
                delay_minutes,
                day_of_week,
                hour_of_day,
                is_weekend,
                is_holiday,
                -- Use delay_minutes as proxy for demand (longer delays = higher demand)
                CASE 
                    WHEN delay_minutes > 5 THEN 'High'
                    WHEN delay_minutes > 2 THEN 'Medium'
                    ELSE 'Low'
                END as demand_level,
                -- Create a demand proxy based on delay patterns
                GREATEST(0, delay_minutes) as demand_proxy
            FROM unified_realtime_historical_data
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            AND delay_minutes IS NOT NULL
            ORDER BY stop_id, timestamp
        """
        
        try:
            df = pd.read_sql_query(query, self.db_connection, params=(days_back,))
            logger.info(f"Loaded {len(df)} training records")
            return df
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return pd.DataFrame()
    
    def create_sequences(self, data: np.ndarray, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        xs, ys = [], []
        for i in range(len(data) - sequence_length):
            x = data[i:(i + sequence_length)]
            y = data[i + sequence_length]
            xs.append(x)
            ys.append(y)
        return np.array(xs), np.array(ys)
    
    def prepare_lstm_data(self, df: pd.DataFrame, target_column: str, 
                         features_columns: List[str], sequence_length: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, MinMaxScaler]:
        """Prepare data for LSTM model"""
        logger.info("Preparing LSTM data...")
        
        # Ensure data is sorted by stop_id and timestamp
        df = df.sort_values(by=["stop_id", "timestamp"])
        
        all_sequences_X = []
        all_sequences_y = []
        
        # Process each stop_id separately
        for stop_id in df["stop_id"].unique():
            stop_df = df[df["stop_id"] == stop_id].copy()
            
            # Select features and target
            data = stop_df[features_columns + [target_column]].values
            
            # Scale features
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(data)
            
            # Create sequences
            X, y = self.create_sequences(scaled_data, sequence_length)
            
            if len(X) > 0:
                all_sequences_X.append(X)
                all_sequences_y.append(y)
        
        if not all_sequences_X:
            raise ValueError("No valid sequences created")
        
        X_combined = np.concatenate(all_sequences_X, axis=0)
        y_combined = np.concatenate(all_sequences_y, axis=0)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, y_combined, test_size=0.2, random_state=settings.RANDOM_SEED
        )
        
        logger.info(f"LSTM data prepared: X_train shape {X_train.shape}, y_train shape {y_train.shape}")
        
        return X_train, X_test, y_train, y_test, scaler
    
    def build_lstm_model(self, input_shape: Tuple[int, int], output_features: int) -> Sequential:
        """Build LSTM model architecture"""
        model = Sequential([
            LSTM(units=50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(units=50, return_sequences=False),
            Dropout(0.2),
            Dense(units=25, activation='relu'),
            Dense(units=output_features)
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def train_lstm_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train LSTM model"""
        logger.info("Training LSTM model...")
        
        # Define features and target
        target_column = "demand_proxy"
        features_columns = [
            "delay_minutes", "hour_of_day", "is_weekend", "is_holiday"
        ]
        
        # Prepare data
        X_train, X_test, y_train, y_test, scaler = self.prepare_lstm_data(
            df, target_column, features_columns, settings.SEQUENCE_LENGTH
        )
        
        # Build model
        model = self.build_lstm_model(
            input_shape=(X_train.shape[1], X_train.shape[2]),
            output_features=y_train.shape[1]
        )
        
        # Callbacks
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        model_checkpoint = ModelCheckpoint(
            filepath=os.path.join(settings.MODELS_DIR, 'lstm_best_model.h5'),
            monitor='val_loss',
            save_best_only=True
        )
        
        # Train model
        history = model.fit(
            X_train, y_train,
            epochs=100,
            batch_size=32,
            validation_split=0.2,
            callbacks=[early_stopping, model_checkpoint],
            verbose=1
        )
        
        # Evaluate model
        predictions = model.predict(X_test)
        
        # Calculate metrics
        mse = mean_squared_error(y_test, predictions)
        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)
        
        metrics = {
            'mse': mse,
            'mae': mae,
            'r2': r2,
            'rmse': np.sqrt(mse)
        }
        
        # Store model and scaler
        self.models['lstm'] = model
        self.scalers['lstm'] = scaler
        
        logger.info(f"LSTM training completed. Metrics: {metrics}")
        
        return {
            'model': model,
            'scaler': scaler,
            'metrics': metrics,
            'history': history.history
        }
    
    def prepare_xgboost_data(self, df: pd.DataFrame, target_column: str, 
                           features_columns: List[str]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for XGBoost model"""
        logger.info("Preparing XGBoost data...")
        
        # Create lag features
        df = df.sort_values(by=["stop_id", "timestamp"])
        
        # Add lag features for each stop
        for lag in [1, 2, 3, 6, 12, 24]:  # Hours
            df[f'delay_lag_{lag}h'] = df.groupby('stop_id')['delay_minutes'].shift(lag)
        
        # Add rolling features
        for window in [3, 6, 12]:  # Hours
            df[f'delay_rolling_mean_{window}h'] = df.groupby('stop_id')['delay_minutes'].rolling(window=window, min_periods=1).mean().reset_index(0, drop=True)
            df[f'delay_rolling_std_{window}h'] = df.groupby('stop_id')['delay_minutes'].rolling(window=window, min_periods=1).std().reset_index(0, drop=True)
        
        # Add cyclical features
        df['hour_sin'] = np.sin(2 * np.pi * df['hour_of_day'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour_of_day'] / 24)
        
        # Day of week encoding
        day_mapping = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 
                      'Friday': 4, 'Saturday': 5, 'Sunday': 6}
        df['day_of_week_num'] = df['day_of_week'].map(day_mapping)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week_num'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week_num'] / 7)
        
        # Select final features
        final_features = [
            'delay_minutes', 'hour_of_day', 'is_weekend', 'is_holiday',
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos'
        ] + [col for col in df.columns if col.startswith(('delay_lag_', 'delay_rolling_'))]
        
        # Remove rows with NaN values
        df_clean = df.dropna(subset=final_features + [target_column])
        
        X = df_clean[final_features].values
        y = df_clean[target_column].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=settings.RANDOM_SEED
        )
        
        logger.info(f"XGBoost data prepared: X_train shape {X_train.shape}, y_train shape {y_train.shape}")
        
        return X_train, X_test, y_train, y_test, final_features
    
    def train_xgboost_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train XGBoost model"""
        logger.info("Training XGBoost model...")
        
        # Define features and target
        target_column = "demand_proxy"
        features_columns = [
            "delay_minutes", "hour_of_day", "is_weekend", "is_holiday"
        ]
        
        # Prepare data
        X_train, X_test, y_train, y_test, feature_names = self.prepare_xgboost_data(
            df, target_column, features_columns
        )
        
        # Build model
        model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=1000,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.7,
            colsample_bytree=0.7,
            random_state=settings.RANDOM_SEED,
            n_jobs=-1
        )
        
        # Train model
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_test, y_test)],
            early_stopping_rounds=50,
            verbose=False
        )
        
        # Evaluate model
        predictions = model.predict(X_test)
        
        # Calculate metrics
        mse = mean_squared_error(y_test, predictions)
        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)
        
        metrics = {
            'mse': mse,
            'mae': mae,
            'r2': r2,
            'rmse': np.sqrt(mse)
        }
        
        # Feature importance
        feature_importance = dict(zip(feature_names, model.feature_importances_))
        
        # Store model and feature importance
        self.models['xgboost'] = model
        self.feature_importance['xgboost'] = feature_importance
        
        logger.info(f"XGBoost training completed. Metrics: {metrics}")
        
        return {
            'model': model,
            'metrics': metrics,
            'feature_importance': feature_importance,
            'feature_names': feature_names
        }
    
    def train_models(self, days_back: int = 30) -> Dict[str, Any]:
        """Train both LSTM and XGBoost models"""
        logger.info("Starting model training...")
        
        # Load training data
        df = self.load_training_data(days_back)
        
        if df.empty:
            raise ValueError("No training data available")
        
        results = {}
        
        # Train LSTM model
        try:
            lstm_results = self.train_lstm_model(df)
            results['lstm'] = lstm_results
        except Exception as e:
            logger.error(f"LSTM training failed: {e}")
            results['lstm'] = {'error': str(e)}
        
        # Train XGBoost model
        try:
            xgb_results = self.train_xgboost_model(df)
            results['xgboost'] = xgb_results
        except Exception as e:
            logger.error(f"XGBoost training failed: {e}")
            results['xgboost'] = {'error': str(e)}
        
        # Save models
        self.save_models()
        
        return results
    
    def save_models(self):
        """Save trained models to disk"""
        for model_name, model in self.models.items():
            if model_name == 'lstm':
                model_path = os.path.join(settings.MODELS_DIR, f'{model_name}_model.h5')
                model.save(model_path)
            else:
                model_path = os.path.join(settings.MODELS_DIR, f'{model_name}_model.pkl')
                with open(model_path, 'wb') as f:
                    pickle.dump(model, f)
            
            logger.info(f"Saved {model_name} model to {model_path}")
        
        # Save scalers
        for scaler_name, scaler in self.scalers.items():
            scaler_path = os.path.join(settings.MODELS_DIR, f'{scaler_name}_scaler.pkl')
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
            logger.info(f"Saved {scaler_name} scaler to {scaler_path}")
    
    def load_models(self):
        """Load trained models from disk"""
        # Load LSTM model
        lstm_path = os.path.join(settings.MODELS_DIR, 'lstm_model.h5')
        if os.path.exists(lstm_path):
            self.models['lstm'] = tf.keras.models.load_model(lstm_path)
            logger.info("Loaded LSTM model")
        
        # Load XGBoost model
        xgb_path = os.path.join(settings.MODELS_DIR, 'xgboost_model.pkl')
        if os.path.exists(xgb_path):
            with open(xgb_path, 'rb') as f:
                self.models['xgboost'] = pickle.load(f)
            logger.info("Loaded XGBoost model")
        
        # Load scalers
        lstm_scaler_path = os.path.join(settings.MODELS_DIR, 'lstm_scaler.pkl')
        if os.path.exists(lstm_scaler_path):
            with open(lstm_scaler_path, 'rb') as f:
                self.scalers['lstm'] = pickle.load(f)
            logger.info("Loaded LSTM scaler")
    
    def predict_demand(self, stop_id: str, timestamp: datetime, 
                      model_type: str = 'xgboost') -> Dict[str, Any]:
        """Predict demand for a specific stop and time"""
        if model_type not in self.models:
            raise ValueError(f"Model {model_type} not available")
        
        # Get recent data for the stop
        recent_data = self.get_stop_recent_data(stop_id, hours=24)
        
        if recent_data.empty:
            return {
                'stop_id': stop_id,
                'timestamp': timestamp,
                'predicted_demand': 0,
                'demand_level': 'Low',
                'confidence': 0.0
            }
        
        if model_type == 'lstm':
            return self._predict_lstm(recent_data, stop_id, timestamp)
        else:
            return self._predict_xgboost(recent_data, stop_id, timestamp)
    
    def _predict_lstm(self, data: pd.DataFrame, stop_id: str, timestamp: datetime) -> Dict[str, Any]:
        """Make LSTM prediction"""
        # Prepare sequence data
        features = ['delay_minutes', 'hour_of_day', 'is_weekend', 'is_holiday']
        sequence_data = data[features].values
        
        if len(sequence_data) < settings.SEQUENCE_LENGTH:
            # Pad with zeros if not enough data
            padding = np.zeros((settings.SEQUENCE_LENGTH - len(sequence_data), len(features)))
            sequence_data = np.vstack([padding, sequence_data])
        
        # Take the last sequence_length samples
        sequence_data = sequence_data[-settings.SEQUENCE_LENGTH:]
        
        # Scale data
        scaled_data = self.scalers['lstm'].transform(sequence_data)
        
        # Reshape for LSTM (batch_size, timesteps, features)
        X = scaled_data.reshape(1, settings.SEQUENCE_LENGTH, len(features))
        
        # Make prediction
        prediction = self.models['lstm'].predict(X)[0]
        
        # Inverse transform
        prediction_original = self.scalers['lstm'].inverse_transform(
            np.zeros((1, len(features) + 1))
        )[0, -1]  # Get the target column
        
        return {
            'stop_id': stop_id,
            'timestamp': timestamp,
            'predicted_demand': float(prediction_original),
            'demand_level': self._classify_demand_level(prediction_original),
            'confidence': 0.8  # Placeholder
        }
    
    def _predict_xgboost(self, data: pd.DataFrame, stop_id: str, timestamp: datetime) -> Dict[str, Any]:
        """Make XGBoost prediction"""
        # Prepare features
        features = self._prepare_xgboost_features(data, timestamp)
        
        # Make prediction
        prediction = self.models['xgboost'].predict([features])[0]
        
        return {
            'stop_id': stop_id,
            'timestamp': timestamp,
            'predicted_demand': float(prediction),
            'demand_level': self._classify_demand_level(prediction),
            'confidence': 0.9  # Placeholder
        }
    
    def _prepare_xgboost_features(self, data: pd.DataFrame, timestamp: datetime) -> List[float]:
        """Prepare features for XGBoost prediction"""
        # This is a simplified version - in production, you'd use the same feature engineering as training
        features = [
            data['delay_minutes'].mean() if not data.empty else 0,
            timestamp.hour,
            1 if timestamp.weekday() >= 5 else 0,  # is_weekend
            0,  # is_holiday (simplified)
            np.sin(2 * np.pi * timestamp.hour / 24),
            np.cos(2 * np.pi * timestamp.hour / 24),
            np.sin(2 * np.pi * timestamp.weekday() / 7),
            np.cos(2 * np.pi * timestamp.weekday() / 7)
        ]
        
        # Add lag features (simplified)
        for lag in [1, 2, 3, 6, 12, 24]:
            features.append(data['delay_minutes'].iloc[-lag] if len(data) >= lag else 0)
        
        # Add rolling features (simplified)
        for window in [3, 6, 12]:
            features.append(data['delay_minutes'].rolling(window=window, min_periods=1).mean().iloc[-1] if not data.empty else 0)
            features.append(data['delay_minutes'].rolling(window=window, min_periods=1).std().iloc[-1] if not data.empty else 0)
        
        return features
    
    def _classify_demand_level(self, demand_value: float) -> str:
        """Classify demand level based on predicted value"""
        if demand_value > 5:
            return 'High'
        elif demand_value > 2:
            return 'Medium'
        else:
            return 'Low'
    
    def get_stop_recent_data(self, stop_id: str, hours: int = 24) -> pd.DataFrame:
        """Get recent data for a specific stop"""
        if not self.db_connection:
            self.create_db_connection()
        
        query = """
            SELECT * FROM unified_realtime_historical_data
            WHERE stop_id = %s
            AND timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC
        """
        
        try:
            df = pd.read_sql_query(query, self.db_connection, params=(stop_id, hours))
            return df
        except Exception as e:
            logger.error(f"Error fetching stop data: {e}")
            return pd.DataFrame()
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get performance metrics for all models"""
        performance = {}
        
        for model_name, model in self.models.items():
            if hasattr(model, 'best_score_'):
                performance[model_name] = {
                    'best_score': model.best_score_,
                    'n_estimators': model.n_estimators if hasattr(model, 'n_estimators') else None
                }
        
        return performance


def main():
    """Main function for model training"""
    logging.basicConfig(level=logging.INFO)
    
    forecaster = DemandForecaster()
    
    # Train models
    results = forecaster.train_models(days_back=30)
    
    # Print results
    for model_name, result in results.items():
        if 'error' not in result:
            logger.info(f"{model_name.upper()} Results:")
            logger.info(f"  MSE: {result['metrics']['mse']:.4f}")
            logger.info(f"  MAE: {result['metrics']['mae']:.4f}")
            logger.info(f"  R²: {result['metrics']['r2']:.4f}")
            logger.info(f"  RMSE: {result['metrics']['rmse']:.4f}")
        else:
            logger.error(f"{model_name.upper()} Error: {result['error']}")


if __name__ == "__main__":
    main() 