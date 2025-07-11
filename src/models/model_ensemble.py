#!/usr/bin/env python3
"""
MARTA Model Ensemble
Combines LSTM and XGBoost predictions for improved accuracy
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
import joblib
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import VotingRegressor, VotingClassifier
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, classification_report
import tensorflow as tf
from tensorflow.keras.models import load_model

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Model storage
MODELS_DIR = 'models'
ENSEMBLE_DIR = 'models/ensemble'
SCALERS_DIR = 'models/scalers'

class ModelEnsemble:
    """Ensemble model combining LSTM and XGBoost predictions"""
    
    def __init__(self, target_type: str = 'dwell_time'):
        """
        Initialize ensemble model
        
        Args:
            target_type: 'dwell_time' for regression or 'demand_level' for classification
        """
        self.target_type = target_type
        
        # Individual models
        self.lstm_model = None
        self.xgboost_model = None
        self.ensemble_model = None
        
        # Scalers and encoders
        self.feature_scaler = None
        self.target_scaler = None
        self.label_encoder = None
        
        # Data storage
        self.feature_columns = []
        
        # Create directories
        os.makedirs(ENSEMBLE_DIR, exist_ok=True)
        
        logging.info(f"Initialized Model Ensemble for {target_type}")
    
    def create_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    
    def load_individual_models(self):
        """Load trained LSTM and XGBoost models"""
        logging.info("Loading individual models...")
        
        # Load LSTM model
        lstm_model_path = f'{MODELS_DIR}/lstm/lstm_{self.target_type}_best.h5'
        if os.path.exists(lstm_model_path):
            self.lstm_model = load_model(lstm_model_path)
            logging.info(f"Loaded LSTM model from {lstm_model_path}")
        else:
            logging.warning(f"LSTM model not found at {lstm_model_path}")
        
        # Load XGBoost model
        xgb_model_path = f'{MODELS_DIR}/xgboost/xgboost_{self.target_type}_model.pkl'
        if os.path.exists(xgb_model_path):
            self.xgboost_model = joblib.load(xgb_model_path)
            logging.info(f"Loaded XGBoost model from {xgb_model_path}")
        else:
            logging.warning(f"XGBoost model not found at {xgb_model_path}")
        
        # Load scalers
        feature_scaler_path = f'{SCALERS_DIR}/feature_scaler_{self.target_type}.pkl'
        if os.path.exists(feature_scaler_path):
            self.feature_scaler = joblib.load(feature_scaler_path)
        
        if self.target_type == 'dwell_time':
            target_scaler_path = f'{SCALERS_DIR}/target_scaler_{self.target_type}.pkl'
            if os.path.exists(target_scaler_path):
                self.target_scaler = joblib.load(target_scaler_path)
        else:
            label_encoder_path = f'{SCALERS_DIR}/label_encoder_{self.target_type}.pkl'
            if os.path.exists(label_encoder_path):
                self.label_encoder = joblib.load(label_encoder_path)
    
    def load_features_data(self, days_back: int = 30) -> pd.DataFrame:
        """Load engineered features from database"""
        logging.info(f"Loading features data from last {days_back} days...")
        
        conn = self.create_db_connection()
        cutoff_time = datetime.now() - timedelta(days=days_back)
        
        # Select features based on target type
        if self.target_type == 'dwell_time':
            target_col = 'target_dwell_time_seconds'
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
        """Prepare features and target"""
        logging.info("Preparing features...")
        
        # Define feature columns (exclude metadata and target)
        exclude_columns = [
            'feature_id', 'timestamp', 'stop_id', 'route_id', 'trip_id',
            'target_demand_level', 'target_dwell_time_seconds', 'created_at'
        ]
        
        self.feature_columns = [col for col in df.columns if col not in exclude_columns]
        target_column = f'target_{self.target_type}' if self.target_type == 'dwell_time' else 'target_demand_level'
        
        # Prepare features
        X = df[self.feature_columns].values
        y = df[target_column].values
        
        # Handle missing values
        X = np.nan_to_num(X, nan=0.0)
        
        # Scale features
        if self.feature_scaler is not None:
            X_scaled = self.feature_scaler.transform(X)
        else:
            X_scaled = X
        
        # Handle target based on type
        if self.target_type == 'dwell_time':
            # Regression: scale target
            if self.target_scaler is not None:
                y_scaled = self.target_scaler.transform(y.reshape(-1, 1)).flatten()
            else:
                y_scaled = y
        else:
            # Classification: encode labels
            if self.label_encoder is not None:
                y_scaled = self.label_encoder.transform(y)
            else:
                y_scaled = y
        
        return X_scaled, y_scaled
    
    def create_lstm_sequences(self, X: np.ndarray, sequence_length: int = 24) -> np.ndarray:
        """Create sequences for LSTM model"""
        logging.info(f"Creating LSTM sequences with length {sequence_length}...")
        
        X_sequences = []
        
        # Create sequences
        for i in range(len(X) - sequence_length + 1):
            X_seq = X[i:(i + sequence_length)]
            X_sequences.append(X_seq)
        
        X_sequences = np.array(X_sequences)
        logging.info(f"Created {len(X_sequences)} LSTM sequences")
        
        return X_sequences
    
    def get_individual_predictions(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Get predictions from individual models"""
        logging.info("Getting individual model predictions...")
        
        lstm_pred = None
        xgb_pred = None
        
        # LSTM predictions
        if self.lstm_model is not None:
            try:
                # Create sequences for LSTM
                X_lstm = self.create_lstm_sequences(X)
                lstm_pred_raw = self.lstm_model.predict(X_lstm)
                
                # Transform back to original scale
                if self.target_type == 'dwell_time' and self.target_scaler is not None:
                    lstm_pred = self.target_scaler.inverse_transform(lstm_pred_raw).flatten()
                else:
                    lstm_pred = lstm_pred_raw.flatten()
                
                logging.info("LSTM predictions generated")
            except Exception as e:
                logging.warning(f"LSTM prediction failed: {e}")
        
        # XGBoost predictions
        if self.xgboost_model is not None:
            try:
                xgb_pred_raw = self.xgboost_model.predict(X)
                
                # Transform back to original scale
                if self.target_type == 'dwell_time' and self.target_scaler is not None:
                    xgb_pred = self.target_scaler.inverse_transform(xgb_pred_raw.reshape(-1, 1)).flatten()
                else:
                    xgb_pred = xgb_pred_raw
                
                logging.info("XGBoost predictions generated")
            except Exception as e:
                logging.warning(f"XGBoost prediction failed: {e}")
        
        return lstm_pred, xgb_pred
    
    def build_ensemble_model(self) -> object:
        """Build ensemble model"""
        logging.info("Building ensemble model...")
        
        if self.target_type == 'dwell_time':
            # Regression ensemble
            estimators = []
            
            if self.lstm_model is not None:
                estimators.append(('lstm', self.lstm_model))
            
            if self.xgboost_model is not None:
                estimators.append(('xgboost', self.xgboost_model))
            
            if len(estimators) >= 2:
                self.ensemble_model = VotingRegressor(estimators=estimators)
            else:
                # Use linear regression as meta-learner
                self.ensemble_model = LinearRegression()
        else:
            # Classification ensemble
            estimators = []
            
            if self.lstm_model is not None:
                estimators.append(('lstm', self.lstm_model))
            
            if self.xgboost_model is not None:
                estimators.append(('xgboost', self.xgboost_model))
            
            if len(estimators) >= 2:
                self.ensemble_model = VotingClassifier(estimators=estimators, voting='soft')
            else:
                # Use logistic regression as meta-learner
                self.ensemble_model = LogisticRegression(random_state=42)
        
        return self.ensemble_model
    
    def train_ensemble(self, X_train: np.ndarray, y_train: np.ndarray,
                      X_val: np.ndarray, y_val: np.ndarray) -> Dict:
        """Train ensemble model"""
        logging.info("Training ensemble model...")
        
        # Get individual predictions
        lstm_pred_train, xgb_pred_train = self.get_individual_predictions(X_train)
        lstm_pred_val, xgb_pred_val = self.get_individual_predictions(X_val)
        
        # Prepare ensemble features
        ensemble_features_train = []
        ensemble_features_val = []
        
        if lstm_pred_train is not None:
            ensemble_features_train.append(lstm_pred_train)
            ensemble_features_val.append(lstm_pred_val)
        
        if xgb_pred_train is not None:
            ensemble_features_train.append(xgb_pred_train)
            ensemble_features_val.append(xgb_pred_val)
        
        if len(ensemble_features_train) == 0:
            logging.error("No individual model predictions available")
            return {}
        
        # Stack predictions
        X_ensemble_train = np.column_stack(ensemble_features_train)
        X_ensemble_val = np.column_stack(ensemble_features_val)
        
        # Build and train ensemble
        self.ensemble_model = self.build_ensemble_model()
        self.ensemble_model.fit(X_ensemble_train, y_train)
        
        # Save ensemble model
        ensemble_path = f'{ENSEMBLE_DIR}/ensemble_{self.target_type}_model.pkl'
        joblib.dump(self.ensemble_model, ensemble_path)
        
        # Evaluate on validation set
        y_pred_val = self.ensemble_model.predict(X_ensemble_val)
        
        if self.target_type == 'dwell_time':
            mse = mean_squared_error(y_val, y_pred_val)
            mae = mean_absolute_error(y_val, y_pred_val)
            rmse = np.sqrt(mse)
            
            metrics = {
                'mse': mse,
                'mae': mae,
                'rmse': rmse,
                'r2_score': 1 - (mse / np.var(y_val))
            }
            
            logging.info(f"Ensemble Validation Metrics:")
            logging.info(f"  MSE: {mse:.2f}")
            logging.info(f"  MAE: {mae:.2f}")
            logging.info(f"  RMSE: {rmse:.2f}")
            logging.info(f"  R² Score: {metrics['r2_score']:.3f}")
        else:
            accuracy = accuracy_score(y_val, y_pred_val)
            metrics = {'accuracy': accuracy}
            
            logging.info(f"Ensemble Validation Accuracy: {accuracy:.3f}")
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make ensemble predictions"""
        if self.ensemble_model is None:
            raise ValueError("Ensemble model not trained. Call train_ensemble() first.")
        
        # Get individual predictions
        lstm_pred, xgb_pred = self.get_individual_predictions(X)
        
        # Prepare ensemble features
        ensemble_features = []
        
        if lstm_pred is not None:
            ensemble_features.append(lstm_pred)
        
        if xgb_pred is not None:
            ensemble_features.append(xgb_pred)
        
        if len(ensemble_features) == 0:
            raise ValueError("No individual model predictions available")
        
        # Stack predictions
        X_ensemble = np.column_stack(ensemble_features)
        
        # Make ensemble prediction
        y_pred = self.ensemble_model.predict(X_ensemble)
        
        return y_pred
    
    def compare_models(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Compare performance of individual models and ensemble"""
        logging.info("Comparing model performances...")
        
        results = {}
        
        # Individual model predictions
        lstm_pred, xgb_pred = self.get_individual_predictions(X_test)
        
        # Evaluate individual models
        if lstm_pred is not None:
            if self.target_type == 'dwell_time':
                mse = mean_squared_error(y_test, lstm_pred)
                mae = mean_absolute_error(y_test, lstm_pred)
                rmse = np.sqrt(mse)
                results['lstm'] = {
                    'mse': mse,
                    'mae': mae,
                    'rmse': rmse,
                    'r2_score': 1 - (mse / np.var(y_test))
                }
            else:
                accuracy = accuracy_score(y_test, lstm_pred)
                results['lstm'] = {'accuracy': accuracy}
        
        if xgb_pred is not None:
            if self.target_type == 'dwell_time':
                mse = mean_squared_error(y_test, xgb_pred)
                mae = mean_absolute_error(y_test, xgb_pred)
                rmse = np.sqrt(mse)
                results['xgboost'] = {
                    'mse': mse,
                    'mae': mae,
                    'rmse': rmse,
                    'r2_score': 1 - (mse / np.var(y_test))
                }
            else:
                accuracy = accuracy_score(y_test, xgb_pred)
                results['xgboost'] = {'accuracy': accuracy}
        
        # Ensemble predictions
        ensemble_pred = self.predict(X_test)
        
        if self.target_type == 'dwell_time':
            mse = mean_squared_error(y_test, ensemble_pred)
            mae = mean_absolute_error(y_test, ensemble_pred)
            rmse = np.sqrt(mse)
            results['ensemble'] = {
                'mse': mse,
                'mae': mae,
                'rmse': rmse,
                'r2_score': 1 - (mse / np.var(y_test))
            }
        else:
            accuracy = accuracy_score(y_test, ensemble_pred)
            results['ensemble'] = {'accuracy': accuracy}
        
        return results
    
    def save_ensemble_info(self, training_metrics: Dict, comparison_results: Dict):
        """Save ensemble model information"""
        ensemble_info = {
            'target_type': self.target_type,
            'feature_columns': self.feature_columns,
            'training_metrics': training_metrics,
            'comparison_results': comparison_results,
            'created_at': datetime.now().isoformat()
        }
        
        joblib.dump(ensemble_info, f'{ENSEMBLE_DIR}/ensemble_{self.target_type}_info.pkl')
        logging.info(f"Ensemble info saved to {ENSEMBLE_DIR}/ensemble_{self.target_type}_info.pkl")

def main():
    """Main ensemble training function"""
    logging.info("🚀 Starting Model Ensemble Training")
    
    # Train dwell time regression ensemble
    logging.info("\n" + "="*60)
    logging.info("TRAINING DWELL TIME REGRESSION ENSEMBLE")
    logging.info("="*60)
    
    dwell_ensemble = ModelEnsemble(target_type='dwell_time')
    
    # Load individual models
    dwell_ensemble.load_individual_models()
    
    # Load and prepare data
    df = dwell_ensemble.load_features_data(days_back=30)
    if df.empty:
        logging.error("❌ No data available for ensemble training")
        return
    
    X_scaled, y_scaled = dwell_ensemble.prepare_features(df)
    
    # Split data
    from sklearn.model_selection import train_test_split
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_scaled, y_scaled, test_size=0.3, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )
    
    logging.info(f"Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    
    # Train ensemble
    training_metrics = dwell_ensemble.train_ensemble(X_train, y_train, X_val, y_val)
    
    # Compare models
    comparison_results = dwell_ensemble.compare_models(X_test, y_test)
    
    # Save ensemble info
    dwell_ensemble.save_ensemble_info(training_metrics, comparison_results)
    
    # Print comparison results
    logging.info("\n" + "="*60)
    logging.info("MODEL COMPARISON RESULTS (DWELL TIME)")
    logging.info("="*60)
    
    for model_name, metrics in comparison_results.items():
        if 'rmse' in metrics:
            logging.info(f"{model_name.upper()}: RMSE={metrics['rmse']:.2f}, R²={metrics['r2_score']:.3f}")
        else:
            logging.info(f"{model_name.upper()}: Accuracy={metrics['accuracy']:.3f}")
    
    # Train demand level classification ensemble
    logging.info("\n" + "="*60)
    logging.info("TRAINING DEMAND LEVEL CLASSIFICATION ENSEMBLE")
    logging.info("="*60)
    
    demand_ensemble = ModelEnsemble(target_type='demand_level')
    
    # Load individual models
    demand_ensemble.load_individual_models()
    
    # Load and prepare data
    df = demand_ensemble.load_features_data(days_back=30)
    X_scaled, y_scaled = demand_ensemble.prepare_features(df)
    
    # Split data
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_scaled, y_scaled, test_size=0.3, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )
    
    # Train ensemble
    training_metrics = demand_ensemble.train_ensemble(X_train, y_train, X_val, y_val)
    
    # Compare models
    comparison_results = demand_ensemble.compare_models(X_test, y_test)
    
    # Save ensemble info
    demand_ensemble.save_ensemble_info(training_metrics, comparison_results)
    
    # Print comparison results
    logging.info("\n" + "="*60)
    logging.info("MODEL COMPARISON RESULTS (DEMAND LEVEL)")
    logging.info("="*60)
    
    for model_name, metrics in comparison_results.items():
        logging.info(f"{model_name.upper()}: Accuracy={metrics['accuracy']:.3f}")
    
    logging.info("🎉 Model ensemble training completed successfully!")

if __name__ == "__main__":
    main() 