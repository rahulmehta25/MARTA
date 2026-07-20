#!/usr/bin/env python3
"""
MARTA LSTM Demand Forecaster
LSTM-based time-series model for demand forecasting
"""
import os
import sys
import logging
import numpy as np
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# ML libraries
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, classification_report, confusion_matrix
import joblib

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Model configuration
MODEL_CONFIG = {
    'sequence_length': 24,  # Use last 24 hours to predict next hour
    'prediction_horizon': 1,  # Predict 1 hour ahead
    'lstm_units': [128, 64, 32],
    'dropout_rate': 0.2,
    'learning_rate': 0.001,
    'batch_size': 32,
    'epochs': 100,
    'validation_split': 0.2,
    'early_stopping_patience': 10
}

# Model storage
MODELS_DIR = 'models/lstm'
SCALERS_DIR = 'models/scalers'

class LSTMDemandForecaster:
    """LSTM-based demand forecasting model"""
    
    def __init__(self, target_type: str = 'dwell_time'):
        """
        Initialize LSTM forecaster
        
        Args:
            target_type: 'dwell_time' for regression or 'demand_level' for classification
        """
        self.target_type = target_type
        self.sequence_length = MODEL_CONFIG['sequence_length']
        self.prediction_horizon = MODEL_CONFIG['prediction_horizon']
        
        # Model components
        self.model = None
        self.feature_scaler = MinMaxScaler()
        self.target_scaler = MinMaxScaler()
        self.label_encoder = LabelEncoder()
        
        # Data storage
        self.feature_columns = []
        self.target_column = ''
        
        # Create directories
        os.makedirs(MODELS_DIR, exist_ok=True)
        os.makedirs(SCALERS_DIR, exist_ok=True)
        
        logging.info(f"Initialized LSTM Demand Forecaster for {target_type}")
    
    def create_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    
    def load_features_data(self, days_back: int = 90) -> pd.DataFrame:
        """Load engineered features from database"""
        logging.info(f"Loading features data from last {days_back} days...")
        
        conn = self.create_db_connection()
        cutoff_time = datetime.now() - timedelta(days=days_back)
        
        # Select features based on target type
        if self.target_type == 'dwell_time':
            target_col = 'target_dwell_time_seconds'
            # Remove NaN target values
            query = f"""
            SELECT * FROM ml_features 
            WHERE timestamp >= %s 
            AND {target_col} IS NOT NULL 
            AND {target_col} > 0
            ORDER BY stop_id, timestamp
            """
        else:  # demand_level
            target_col = 'target_demand_level'
            query = f"""
            SELECT * FROM ml_features 
            WHERE timestamp >= %s 
            AND {target_col} IS NOT NULL
            ORDER BY stop_id, timestamp
            """
        
        df = pd.read_sql(query, conn, params=[cutoff_time])
        conn.close()
        
        logging.info(f"Loaded {len(df)} feature records")
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and target for LSTM"""
        logging.info("Preparing features for LSTM...")
        
        # Define feature columns (exclude metadata and target)
        exclude_columns = [
            'feature_id', 'timestamp', 'stop_id', 'route_id', 'trip_id',
            'target_demand_level', 'target_dwell_time_seconds', 'created_at'
        ]
        
        self.feature_columns = [col for col in df.columns if col not in exclude_columns]
        self.target_column = f'target_{self.target_type}' if self.target_type == 'dwell_time' else 'target_demand_level'
        
        logging.info(f"Using {len(self.feature_columns)} feature columns")
        logging.info(f"Target column: {self.target_column}")
        
        # Prepare features
        X = df[self.feature_columns].values
        y = df[self.target_column].values
        
        # Handle missing values
        X = np.nan_to_num(X, nan=0.0)
        
        # Scale features
        X_scaled = self.feature_scaler.fit_transform(X)
        
        # Handle target based on type
        if self.target_type == 'dwell_time':
            # Regression: scale target
            y_scaled = self.target_scaler.fit_transform(y.reshape(-1, 1)).flatten()
        else:
            # Classification: encode labels
            y_scaled = self.label_encoder.fit_transform(y)
        
        return X_scaled, y_scaled
    
    def create_sequences(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create time-series sequences for LSTM"""
        logging.info(f"Creating sequences with length {self.sequence_length}...")
        
        X_sequences, y_sequences = [], []
        
        # Process each stop separately to avoid mixing sequences
        unique_stops = np.unique(X[:, 0]) if len(X.shape) > 1 else [0]
        
        for stop_idx in unique_stops:
            if len(X.shape) > 1:
                stop_mask = X[:, 0] == stop_idx
                X_stop = X[stop_mask]
                y_stop = y[stop_mask]
            else:
                X_stop = X
                y_stop = y
            
            # Create sequences
            for i in range(len(X_stop) - self.sequence_length - self.prediction_horizon + 1):
                X_seq = X_stop[i:(i + self.sequence_length)]
                y_seq = y_stop[i + self.sequence_length + self.prediction_horizon - 1]
                
                X_sequences.append(X_seq)
                y_sequences.append(y_seq)
        
        X_sequences = np.array(X_sequences)
        y_sequences = np.array(y_sequences)
        
        logging.info(f"Created {len(X_sequences)} sequences")
        logging.info(f"X shape: {X_sequences.shape}, y shape: {y_sequences.shape}")
        
        return X_sequences, y_sequences
    
    def build_model(self, input_shape: Tuple[int, int]) -> Sequential:
        """Build LSTM model architecture"""
        logging.info("Building LSTM model...")
        
        model = Sequential()
        
        # First LSTM layer
        model.add(LSTM(
            units=MODEL_CONFIG['lstm_units'][0],
            return_sequences=True,
            input_shape=input_shape
        ))
        model.add(BatchNormalization())
        model.add(Dropout(MODEL_CONFIG['dropout_rate']))
        
        # Additional LSTM layers
        for units in MODEL_CONFIG['lstm_units'][1:]:
            model.add(LSTM(units=units, return_sequences=True))
            model.add(BatchNormalization())
            model.add(Dropout(MODEL_CONFIG['dropout_rate']))
        
        # Final LSTM layer
        model.add(LSTM(units=MODEL_CONFIG['lstm_units'][-1], return_sequences=False))
        model.add(BatchNormalization())
        model.add(Dropout(MODEL_CONFIG['dropout_rate']))
        
        # Output layer
        if self.target_type == 'dwell_time':
            # Regression: single output
            model.add(Dense(1, activation='linear'))
            model.compile(
                optimizer=Adam(learning_rate=MODEL_CONFIG['learning_rate']),
                loss='mse',
                metrics=['mae']
            )
        else:
            # Classification: multiple outputs
            num_classes = len(self.label_encoder.classes_)
            model.add(Dense(num_classes, activation='softmax'))
            model.compile(
                optimizer=Adam(learning_rate=MODEL_CONFIG['learning_rate']),
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy']
            )
        
        model.summary()
        return model
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray, 
                   X_val: np.ndarray, y_val: np.ndarray) -> Dict:
        """Train the LSTM model"""
        logging.info("Training LSTM model...")
        
        # Build model
        self.model = self.build_model((X_train.shape[1], X_train.shape[2]))
        
        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=MODEL_CONFIG['early_stopping_patience'],
                restore_best_weights=True,
                verbose=1
            ),
            ModelCheckpoint(
                filepath=f'{MODELS_DIR}/lstm_{self.target_type}_best.h5',
                monitor='val_loss',
                save_best_only=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1
            )
        ]
        
        # Train model
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=MODEL_CONFIG['epochs'],
            batch_size=MODEL_CONFIG['batch_size'],
            callbacks=callbacks,
            verbose=1
        )
        
        # Save final model
        self.model.save(f'{MODELS_DIR}/lstm_{self.target_type}_final.h5')
        
        # Save scalers
        joblib.dump(self.feature_scaler, f'{SCALERS_DIR}/feature_scaler_{self.target_type}.pkl')
        if self.target_type == 'dwell_time':
            joblib.dump(self.target_scaler, f'{SCALERS_DIR}/target_scaler_{self.target_type}.pkl')
        else:
            joblib.dump(self.label_encoder, f'{SCALERS_DIR}/label_encoder_{self.target_type}.pkl')
        
        return {
            'history': history.history,
            'best_epoch': np.argmin(history.history['val_loss']) + 1,
            'best_val_loss': min(history.history['val_loss'])
        }
    
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Evaluate model performance"""
        logging.info("Evaluating model...")
        
        # Make predictions
        y_pred = self.model.predict(X_test)
        
        if self.target_type == 'dwell_time':
            # Regression metrics
            y_pred_original = self.target_scaler.inverse_transform(y_pred).flatten()
            y_test_original = self.target_scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
            
            mse = mean_squared_error(y_test_original, y_pred_original)
            mae = mean_absolute_error(y_test_original, y_pred_original)
            rmse = np.sqrt(mse)
            
            metrics = {
                'mse': mse,
                'mae': mae,
                'rmse': rmse,
                'r2_score': 1 - (mse / np.var(y_test_original))
            }
            
            logging.info(f"Regression Metrics:")
            logging.info(f"  MSE: {mse:.2f}")
            logging.info(f"  MAE: {mae:.2f}")
            logging.info(f"  RMSE: {rmse:.2f}")
            logging.info(f"  R² Score: {metrics['r2_score']:.3f}")
            
        else:
            # Classification metrics
            y_pred_classes = np.argmax(y_pred, axis=1)
            y_test_classes = y_test
            
            accuracy = np.mean(y_pred_classes == y_test_classes)
            
            # Classification report
            class_names = self.label_encoder.classes_
            report = classification_report(y_test_classes, y_pred_classes, 
                                        target_names=class_names, output_dict=True)
            
            metrics = {
                'accuracy': accuracy,
                'classification_report': report,
                'confusion_matrix': confusion_matrix(y_test_classes, y_pred_classes)
            }
            
            logging.info(f"Classification Metrics:")
            logging.info(f"  Accuracy: {accuracy:.3f}")
            logging.info(f"  Classification Report:")
            for class_name in class_names:
                precision = report[class_name]['precision']
                recall = report[class_name]['recall']
                f1 = report[class_name]['f1-score']
                logging.info(f"    {class_name}: Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}")
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions on new data"""
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        
        # Ensure correct shape
        if len(X.shape) == 2:
            X = X.reshape(1, X.shape[0], X.shape[1])
        
        # Make prediction
        y_pred = self.model.predict(X)
        
        # Transform back to original scale
        if self.target_type == 'dwell_time':
            y_pred = self.target_scaler.inverse_transform(y_pred).flatten()
        else:
            y_pred_classes = np.argmax(y_pred, axis=1)
            y_pred = self.label_encoder.inverse_transform(y_pred_classes)
        
        return y_pred
    
    def save_model_info(self, training_info: Dict, evaluation_metrics: Dict):
        """Save model information and metrics"""
        model_info = {
            'target_type': self.target_type,
            'sequence_length': self.sequence_length,
            'prediction_horizon': self.prediction_horizon,
            'feature_columns': self.feature_columns,
            'model_config': MODEL_CONFIG,
            'training_info': training_info,
            'evaluation_metrics': evaluation_metrics,
            'created_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_info, f'{MODELS_DIR}/lstm_{self.target_type}_info.pkl')
        logging.info(f"Model info saved to {MODELS_DIR}/lstm_{self.target_type}_info.pkl")
    
    def load_model(self, model_path: str):
        """Load a trained model"""
        self.model = load_model(model_path)
        
        # Load scalers
        self.feature_scaler = joblib.load(f'{SCALERS_DIR}/feature_scaler_{self.target_type}.pkl')
        if self.target_type == 'dwell_time':
            self.target_scaler = joblib.load(f'{SCALERS_DIR}/target_scaler_{self.target_type}.pkl')
        else:
            self.label_encoder = joblib.load(f'{SCALERS_DIR}/label_encoder_{self.target_type}.pkl')
        
        logging.info(f"Model loaded from {model_path}")

def main():
    """Main training function"""
    logging.info("🚀 Starting LSTM Demand Forecaster Training")
    
    # Train dwell time regression model
    logging.info("\n" + "="*60)
    logging.info("TRAINING DWELL TIME REGRESSION MODEL")
    logging.info("="*60)
    
    dwell_forecaster = LSTMDemandForecaster(target_type='dwell_time')
    
    # Load and prepare data
    df = dwell_forecaster.load_features_data(days_back=90)
    if df.empty:
        logging.error("❌ No data available for training")
        return
    
    X_scaled, y_scaled = dwell_forecaster.prepare_features(df)
    X_sequences, y_sequences = dwell_forecaster.create_sequences(X_scaled, y_scaled)
    
    # Split data
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_sequences, y_sequences, test_size=0.3, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )
    
    logging.info(f"Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    
    # Train model
    training_info = dwell_forecaster.train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate model
    evaluation_metrics = dwell_forecaster.evaluate_model(X_test, y_test)
    
    # Save model info
    dwell_forecaster.save_model_info(training_info, evaluation_metrics)
    
    # Train demand level classification model
    logging.info("\n" + "="*60)
    logging.info("TRAINING DEMAND LEVEL CLASSIFICATION MODEL")
    logging.info("="*60)
    
    demand_forecaster = LSTMDemandForecaster(target_type='demand_level')
    
    # Load and prepare data
    df = demand_forecaster.load_features_data(days_back=90)
    X_scaled, y_scaled = demand_forecaster.prepare_features(df)
    X_sequences, y_sequences = demand_forecaster.create_sequences(X_scaled, y_scaled)
    
    # Split data
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_sequences, y_sequences, test_size=0.3, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )
    
    # Train model
    training_info = demand_forecaster.train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate model
    evaluation_metrics = demand_forecaster.evaluate_model(X_test, y_test)
    
    # Save model info
    demand_forecaster.save_model_info(training_info, evaluation_metrics)
    
    logging.info("🎉 LSTM model training completed successfully!")

if __name__ == "__main__":
    main() 