#!/usr/bin/env python3
"""
MARTA XGBoost Demand Forecaster
XGBoost-based model for demand forecasting
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
import xgboost as xgb
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, classification_report, confusion_matrix, accuracy_score
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
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
XGBOOST_CONFIG = {
    'regression': {
        'objective': 'reg:squarederror',
        'n_estimators': 1000,
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'n_jobs': -1,
        'early_stopping_rounds': 50
    },
    'classification': {
        'objective': 'multi:softprob',
        'n_estimators': 1000,
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'n_jobs': -1,
        'early_stopping_rounds': 50
    }
}

# Model storage
MODELS_DIR = 'models/xgboost'
SCALERS_DIR = 'models/scalers'

class XGBoostDemandForecaster:
    """XGBoost-based demand forecasting model"""
    
    def __init__(self, target_type: str = 'dwell_time'):
        """
        Initialize XGBoost forecaster
        
        Args:
            target_type: 'dwell_time' for regression or 'demand_level' for classification
        """
        self.target_type = target_type
        self.config = XGBOOST_CONFIG['regression' if target_type == 'dwell_time' else 'classification']
        
        # Model components
        self.model = None
        self.feature_scaler = StandardScaler()
        self.target_scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        
        # Data storage
        self.feature_columns = []
        self.target_column = ''
        
        # Create directories
        os.makedirs(MODELS_DIR, exist_ok=True)
        os.makedirs(SCALERS_DIR, exist_ok=True)
        
        logging.info(f"Initialized XGBoost Demand Forecaster for {target_type}")
    
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
        """Prepare features and target for XGBoost"""
        logging.info("Preparing features for XGBoost...")
        
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
    
    def build_model(self) -> xgb.XGBModel:
        """Build XGBoost model"""
        logging.info("Building XGBoost model...")
        
        if self.target_type == 'dwell_time':
            # Regression model
            model = xgb.XGBRegressor(**self.config)
        else:
            # Classification model
            model = xgb.XGBClassifier(**self.config)
        
        return model
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray, 
                   X_val: np.ndarray, y_val: np.ndarray) -> Dict:
        """Train the XGBoost model"""
        logging.info("Training XGBoost model...")
        
        # Build model
        self.model = self.build_model()
        
        # Train model
        if self.target_type == 'dwell_time':
            # Regression
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=self.config['early_stopping_rounds'],
                verbose=False
            )
        else:
            # Classification
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=self.config['early_stopping_rounds'],
                verbose=False
            )
        
        # Save model
        model_path = f'{MODELS_DIR}/xgboost_{self.target_type}_model.pkl'
        joblib.dump(self.model, model_path)
        
        # Save scalers
        joblib.dump(self.feature_scaler, f'{SCALERS_DIR}/xgboost_feature_scaler_{self.target_type}.pkl')
        if self.target_type == 'dwell_time':
            joblib.dump(self.target_scaler, f'{SCALERS_DIR}/xgboost_target_scaler_{self.target_type}.pkl')
        else:
            joblib.dump(self.label_encoder, f'{SCALERS_DIR}/xgboost_label_encoder_{self.target_type}.pkl')
        
        return {
            'best_iteration': self.model.best_iteration if hasattr(self.model, 'best_iteration') else None,
            'feature_importance': self.model.feature_importances_.tolist()
        }
    
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Evaluate model performance"""
        logging.info("Evaluating XGBoost model...")
        
        # Make predictions
        y_pred = self.model.predict(X_test)
        
        if self.target_type == 'dwell_time':
            # Regression metrics
            y_pred_original = self.target_scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()
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
            y_pred_classes = y_pred
            y_test_classes = y_test
            
            accuracy = accuracy_score(y_test_classes, y_pred_classes)
            
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
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance scores"""
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        
        importance_df = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importance_df
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions on new data"""
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        
        # Scale features
        X_scaled = self.feature_scaler.transform(X)
        
        # Make prediction
        y_pred = self.model.predict(X_scaled)
        
        # Transform back to original scale
        if self.target_type == 'dwell_time':
            y_pred = self.target_scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()
        
        return y_pred
    
    def save_model_info(self, training_info: Dict, evaluation_metrics: Dict):
        """Save model information and metrics"""
        model_info = {
            'target_type': self.target_type,
            'feature_columns': self.feature_columns,
            'model_config': self.config,
            'training_info': training_info,
            'evaluation_metrics': evaluation_metrics,
            'feature_importance': self.get_feature_importance().to_dict('records'),
            'created_at': datetime.now().isoformat()
        }
        
        joblib.dump(model_info, f'{MODELS_DIR}/xgboost_{self.target_type}_info.pkl')
        logging.info(f"Model info saved to {MODELS_DIR}/xgboost_{self.target_type}_info.pkl")
    
    def load_model(self, model_path: str):
        """Load a trained model"""
        self.model = joblib.load(model_path)
        
        # Load scalers
        self.feature_scaler = joblib.load(f'{SCALERS_DIR}/xgboost_feature_scaler_{self.target_type}.pkl')
        if self.target_type == 'dwell_time':
            self.target_scaler = joblib.load(f'{SCALERS_DIR}/xgboost_target_scaler_{self.target_type}.pkl')
        else:
            self.label_encoder = joblib.load(f'{SCALERS_DIR}/xgboost_label_encoder_{self.target_type}.pkl')
        
        logging.info(f"Model loaded from {model_path}")

class RandomForestDemandForecaster:
    """Random Forest-based demand forecasting model (for comparison)"""
    
    def __init__(self, target_type: str = 'dwell_time'):
        self.target_type = target_type
        
        if target_type == 'dwell_time':
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        else:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict:
        """Train Random Forest model"""
        logging.info("Training Random Forest model...")
        
        self.model.fit(X_train, y_train)
        
        return {
            'feature_importance': self.model.feature_importances_.tolist()
        }
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        return self.model.predict(X)
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Evaluate model performance"""
        y_pred = self.model.predict(X_test)
        
        if self.target_type == 'dwell_time':
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            
            return {
                'mse': mse,
                'mae': mae,
                'rmse': rmse,
                'r2_score': 1 - (mse / np.var(y_test))
            }
        else:
            accuracy = accuracy_score(y_test, y_pred)
            return {'accuracy': accuracy}

def main():
    """Main training function"""
    logging.info("🚀 Starting XGBoost Demand Forecaster Training")
    
    # Train dwell time regression model
    logging.info("\n" + "="*60)
    logging.info("TRAINING DWELL TIME REGRESSION MODEL")
    logging.info("="*60)
    
    dwell_forecaster = XGBoostDemandForecaster(target_type='dwell_time')
    
    # Load and prepare data
    df = dwell_forecaster.load_features_data(days_back=90)
    if df.empty:
        logging.error("❌ No data available for training")
        return
    
    X_scaled, y_scaled = dwell_forecaster.prepare_features(df)
    
    # Split data
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_scaled, y_scaled, test_size=0.3, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )
    
    logging.info(f"Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    
    # Train XGBoost model
    training_info = dwell_forecaster.train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate XGBoost model
    evaluation_metrics = dwell_forecaster.evaluate_model(X_test, y_test)
    
    # Save XGBoost model info
    dwell_forecaster.save_model_info(training_info, evaluation_metrics)
    
    # Train Random Forest for comparison
    logging.info("\nTraining Random Forest for comparison...")
    rf_forecaster = RandomForestDemandForecaster(target_type='dwell_time')
    rf_training_info = rf_forecaster.train(X_train, y_train)
    rf_evaluation_metrics = rf_forecaster.evaluate(X_test, y_test)
    
    logging.info(f"Random Forest RMSE: {rf_evaluation_metrics['rmse']:.2f}")
    logging.info(f"XGBoost RMSE: {evaluation_metrics['rmse']:.2f}")
    
    # Train demand level classification model
    logging.info("\n" + "="*60)
    logging.info("TRAINING DEMAND LEVEL CLASSIFICATION MODEL")
    logging.info("="*60)
    
    demand_forecaster = XGBoostDemandForecaster(target_type='demand_level')
    
    # Load and prepare data
    df = demand_forecaster.load_features_data(days_back=90)
    X_scaled, y_scaled = demand_forecaster.prepare_features(df)
    
    # Split data
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_scaled, y_scaled, test_size=0.3, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )
    
    # Train XGBoost model
    training_info = demand_forecaster.train_model(X_train, y_train, X_val, y_val)
    
    # Evaluate XGBoost model
    evaluation_metrics = demand_forecaster.evaluate_model(X_test, y_test)
    
    # Save XGBoost model info
    demand_forecaster.save_model_info(training_info, evaluation_metrics)
    
    # Train Random Forest for comparison
    logging.info("\nTraining Random Forest for comparison...")
    rf_forecaster = RandomForestDemandForecaster(target_type='demand_level')
    rf_training_info = rf_forecaster.train(X_train, y_train)
    rf_evaluation_metrics = rf_forecaster.evaluate(X_test, y_test)
    
    logging.info(f"Random Forest Accuracy: {rf_evaluation_metrics['accuracy']:.3f}")
    logging.info(f"XGBoost Accuracy: {evaluation_metrics['accuracy']:.3f}")
    
    # Print feature importance
    logging.info("\n" + "="*60)
    logging.info("TOP 10 FEATURE IMPORTANCE (XGBoost)")
    logging.info("="*60)
    
    importance_df = demand_forecaster.get_feature_importance()
    for i, row in importance_df.head(10).iterrows():
        logging.info(f"  {row['feature']}: {row['importance']:.4f}")
    
    logging.info("🎉 XGBoost model training completed successfully!")

if __name__ == "__main__":
    main() 