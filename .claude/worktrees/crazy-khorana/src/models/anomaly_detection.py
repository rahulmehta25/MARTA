"""
Anomaly Detection System for MARTA Demand Forecasting

This module implements comprehensive anomaly detection for identifying
unusual demand patterns, data quality issues, and operational anomalies.
"""
import os
import logging
import json
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.covariance import EllipticEnvelope
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor
from sklearn.decomposition import PCA
from sklearn.metrics import classification_report
import scipy.stats as stats
from scipy import signal
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import asyncpg
import mlflow
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from src.models.ml_experiment_tracker import get_experiment_tracker

logger = logging.getLogger(__name__)


class StatisticalAnomalyDetector:
    """
    Statistical anomaly detection using various statistical methods.
    
    Features:
    - Z-score based detection
    - Modified Z-score (MAD-based)
    - Interquartile range (IQR) method
    - Time series decomposition
    - Seasonal anomaly detection
    """
    
    def __init__(self, methods: List[str] = None):
        """
        Initialize statistical anomaly detector.
        
        Args:
            methods: List of methods to use ['zscore', 'modified_zscore', 'iqr', 'seasonal']
        """
        self.methods = methods or ['zscore', 'modified_zscore', 'iqr', 'seasonal']
        self.thresholds = {
            'zscore': 3.0,
            'modified_zscore': 3.5,
            'iqr': 1.5
        }
        self.seasonal_params = {}
        
        logger.info(f"Initialized statistical anomaly detector with methods: {self.methods}")
    
    def fit(self, data: pd.Series, seasonal_period: int = 24) -> 'StatisticalAnomalyDetector':
        """
        Fit the detector to historical data.
        
        Args:
            data: Time series data
            seasonal_period: Period for seasonal decomposition
            
        Returns:
            Self
        """
        self.seasonal_params = {
            'period': seasonal_period,
            'mean': data.rolling(window=seasonal_period).mean(),
            'std': data.rolling(window=seasonal_period).std()
        }
        
        return self
    
    def detect_anomalies(self, data: pd.Series) -> pd.DataFrame:
        """
        Detect anomalies using statistical methods.
        
        Args:
            data: Time series data to analyze
            
        Returns:
            DataFrame with anomaly flags for each method
        """
        results = pd.DataFrame(index=data.index)
        results['value'] = data
        
        # Z-score method
        if 'zscore' in self.methods:
            z_scores = np.abs(stats.zscore(data, nan_policy='omit'))
            results['zscore_anomaly'] = z_scores > self.thresholds['zscore']
            results['zscore_score'] = z_scores
        
        # Modified Z-score (MAD-based)
        if 'modified_zscore' in self.methods:
            median = np.median(data)
            mad = np.median(np.abs(data - median))
            modified_z_scores = 0.6745 * (data - median) / mad
            results['modified_zscore_anomaly'] = np.abs(modified_z_scores) > self.thresholds['modified_zscore']
            results['modified_zscore_score'] = np.abs(modified_z_scores)
        
        # IQR method
        if 'iqr' in self.methods:
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - self.thresholds['iqr'] * IQR
            upper_bound = Q3 + self.thresholds['iqr'] * IQR
            results['iqr_anomaly'] = (data < lower_bound) | (data > upper_bound)
            results['iqr_score'] = np.maximum(
                (lower_bound - data) / IQR,
                (data - upper_bound) / IQR
            ).clip(lower=0)
        
        # Seasonal anomaly detection
        if 'seasonal' in self.methods and self.seasonal_params:
            seasonal_mean = data.rolling(window=self.seasonal_params['period']).mean()
            seasonal_std = data.rolling(window=self.seasonal_params['period']).std()
            seasonal_z_scores = np.abs((data - seasonal_mean) / seasonal_std)
            results['seasonal_anomaly'] = seasonal_z_scores > 2.5
            results['seasonal_score'] = seasonal_z_scores
        
        # Ensemble decision
        anomaly_cols = [col for col in results.columns if col.endswith('_anomaly')]
        results['ensemble_anomaly'] = results[anomaly_cols].sum(axis=1) >= 2
        
        return results


class MLAnomalyDetector:
    """
    Machine learning based anomaly detection.
    
    Features:
    - Multiple ML algorithms
    - Ensemble detection
    - Automatic hyperparameter tuning
    - Feature importance analysis
    """
    
    def __init__(self, 
                 algorithms: List[str] = None,
                 contamination: float = 0.1):
        """
        Initialize ML anomaly detector.
        
        Args:
            algorithms: List of algorithms to use
            contamination: Expected proportion of anomalies
        """
        self.algorithms = algorithms or ['isolation_forest', 'elliptic_envelope', 'lof', 'one_class_svm']
        self.contamination = contamination
        self.models = {}
        self.scalers = {}
        self.is_fitted = False
        
        logger.info(f"Initialized ML anomaly detector with algorithms: {self.algorithms}")
    
    def _create_models(self) -> Dict[str, Any]:
        """Create anomaly detection models."""
        models = {}
        
        if 'isolation_forest' in self.algorithms:
            models['isolation_forest'] = IsolationForest(
                contamination=self.contamination,
                random_state=settings.RANDOM_SEED,
                n_jobs=-1
            )
        
        if 'elliptic_envelope' in self.algorithms:
            models['elliptic_envelope'] = EllipticEnvelope(
                contamination=self.contamination,
                random_state=settings.RANDOM_SEED
            )
        
        if 'lof' in self.algorithms:
            models['lof'] = LocalOutlierFactor(
                contamination=self.contamination,
                n_jobs=-1
            )
        
        if 'one_class_svm' in self.algorithms:
            models['one_class_svm'] = OneClassSVM(
                nu=self.contamination,
                gamma='scale'
            )
        
        return models
    
    def fit(self, X: np.ndarray) -> 'MLAnomalyDetector':
        """
        Fit anomaly detection models.
        
        Args:
            X: Training features
            
        Returns:
            Self
        """
        logger.info("Fitting ML anomaly detection models...")
        
        # Create and fit scalers
        self.scalers['standard'] = StandardScaler().fit(X)
        self.scalers['robust'] = RobustScaler().fit(X)
        
        # Create models
        self.models = self._create_models()
        
        # Fit models
        for name, model in self.models.items():
            try:
                # Use robust scaling for most models
                X_scaled = self.scalers['robust'].transform(X)
                
                if name == 'lof':
                    # LOF doesn't have separate fit/predict
                    continue
                else:
                    model.fit(X_scaled)
                
                logger.info(f"Fitted {name} model")
            except Exception as e:
                logger.error(f"Failed to fit {name}: {e}")
                del self.models[name]
        
        self.is_fitted = True
        return self
    
    def predict(self, X: np.ndarray) -> pd.DataFrame:
        """
        Predict anomalies using fitted models.
        
        Args:
            X: Features to analyze
            
        Returns:
            DataFrame with anomaly predictions and scores
        """
        if not self.is_fitted:
            raise ValueError("Models must be fitted before prediction")
        
        results = pd.DataFrame(index=range(len(X)))
        X_scaled = self.scalers['robust'].transform(X)
        
        for name, model in self.models.items():
            try:
                if name == 'lof':
                    # LOF requires fitting on the data to predict
                    lof_model = LocalOutlierFactor(
                        contamination=self.contamination,
                        n_jobs=-1
                    )
                    predictions = lof_model.fit_predict(X_scaled)
                    scores = -lof_model.negative_outlier_factor_
                else:
                    predictions = model.predict(X_scaled)
                    if hasattr(model, 'decision_function'):
                        scores = -model.decision_function(X_scaled)
                    else:
                        scores = np.ones(len(X))
                
                # Convert predictions to boolean (anomaly = True)
                results[f'{name}_anomaly'] = predictions == -1
                results[f'{name}_score'] = scores
                
            except Exception as e:
                logger.error(f"Failed to predict with {name}: {e}")
        
        # Ensemble prediction
        anomaly_cols = [col for col in results.columns if col.endswith('_anomaly')]
        if anomaly_cols:
            results['ensemble_anomaly'] = results[anomaly_cols].sum(axis=1) >= len(anomaly_cols) // 2
            
            # Ensemble score (average)
            score_cols = [col for col in results.columns if col.endswith('_score')]
            if score_cols:
                results['ensemble_score'] = results[score_cols].mean(axis=1)
        
        return results


class TimeSeriesAnomalyDetector:
    """
    Time series specific anomaly detection.
    
    Features:
    - Change point detection
    - Trend anomalies
    - Seasonality anomalies
    - Autocorrelation analysis
    - Signal processing methods
    """
    
    def __init__(self, 
                 window_size: int = 24,
                 seasonal_periods: List[int] = None):
        """
        Initialize time series anomaly detector.
        
        Args:
            window_size: Window size for rolling statistics
            seasonal_periods: List of seasonal periods to check
        """
        self.window_size = window_size
        self.seasonal_periods = seasonal_periods or [24, 168]  # Daily and weekly
        
        logger.info("Initialized time series anomaly detector")
    
    def detect_change_points(self, data: pd.Series, min_size: int = 10) -> List[int]:
        """
        Detect change points in time series using signal processing.
        
        Args:
            data: Time series data
            min_size: Minimum segment size
            
        Returns:
            List of change point indices
        """
        try:
            from ruptures import Pelt
            
            # Use Pelt algorithm for change point detection
            model = Pelt(model="rbf", min_size=min_size).fit(data.values)
            change_points = model.predict(pen=10)
            
            # Remove the last point (end of series)
            if change_points and change_points[-1] == len(data):
                change_points = change_points[:-1]
            
            return change_points
        except ImportError:
            logger.warning("ruptures package not available, using simple change point detection")
            return self._simple_change_point_detection(data)
        except Exception as e:
            logger.error(f"Change point detection failed: {e}")
            return []
    
    def _simple_change_point_detection(self, data: pd.Series) -> List[int]:
        """Simple change point detection using rolling statistics."""
        rolling_mean = data.rolling(window=self.window_size).mean()
        rolling_std = data.rolling(window=self.window_size).std()
        
        # Find points where statistics change significantly
        mean_changes = np.abs(rolling_mean.diff()) > rolling_std.rolling(window=self.window_size).mean()
        change_points = data.index[mean_changes].tolist()
        
        return change_points
    
    def detect_seasonal_anomalies(self, data: pd.Series) -> pd.DataFrame:
        """
        Detect anomalies in seasonal patterns.
        
        Args:
            data: Time series data with datetime index
            
        Returns:
            DataFrame with seasonal anomaly information
        """
        results = pd.DataFrame(index=data.index)
        results['value'] = data
        
        for period in self.seasonal_periods:
            if len(data) < period * 2:
                continue
            
            # Calculate seasonal baseline
            seasonal_data = []
            seasonal_indices = []
            
            for i in range(len(data)):
                season_idx = i % period
                seasonal_data.append(data.iloc[i])
                seasonal_indices.append(season_idx)
            
            seasonal_df = pd.DataFrame({
                'value': seasonal_data,
                'season_idx': seasonal_indices
            })
            
            # Calculate seasonal statistics
            seasonal_stats = seasonal_df.groupby('season_idx')['value'].agg(['mean', 'std'])
            
            # Detect anomalies
            anomalies = []
            scores = []
            
            for i, (idx, value) in enumerate(zip(seasonal_indices, seasonal_data)):
                expected_mean = seasonal_stats.loc[idx, 'mean']
                expected_std = seasonal_stats.loc[idx, 'std']
                
                if expected_std > 0:
                    z_score = abs((value - expected_mean) / expected_std)
                    is_anomaly = z_score > 2.5
                else:
                    z_score = 0
                    is_anomaly = False
                
                anomalies.append(is_anomaly)
                scores.append(z_score)
            
            results[f'seasonal_{period}_anomaly'] = anomalies
            results[f'seasonal_{period}_score'] = scores
        
        return results
    
    def detect_trend_anomalies(self, data: pd.Series) -> pd.DataFrame:
        """
        Detect trend anomalies using signal processing.
        
        Args:
            data: Time series data
            
        Returns:
            DataFrame with trend anomaly information
        """
        results = pd.DataFrame(index=data.index)
        results['value'] = data
        
        # Calculate trend using different methods
        # 1. Linear trend
        x = np.arange(len(data))
        trend_coef = np.polyfit(x, data.values, 1)[0]
        linear_trend = np.polyval([trend_coef, data.iloc[0]], x)
        trend_residuals = data.values - linear_trend
        
        # 2. Rolling trend
        rolling_trend = data.rolling(window=self.window_size).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) == self.window_size else 0
        )
        
        # Detect sudden trend changes
        trend_changes = np.abs(rolling_trend.diff()) > rolling_trend.std() * 2
        results['trend_change_anomaly'] = trend_changes
        
        # Detect residual anomalies
        residual_std = np.std(trend_residuals)
        results['trend_residual_anomaly'] = np.abs(trend_residuals) > 3 * residual_std
        results['trend_residual_score'] = np.abs(trend_residuals) / residual_std
        
        return results


class AnomalyDetectionOrchestrator:
    """
    Orchestrator for comprehensive anomaly detection system.
    
    Features:
    - Multiple detection methods
    - Real-time anomaly monitoring
    - Alert system
    - Performance tracking
    - Database integration
    """
    
    def __init__(self, 
                 feature_names: List[str],
                 detection_config: Dict[str, Any] = None):
        """
        Initialize anomaly detection orchestrator.
        
        Args:
            feature_names: List of feature names
            detection_config: Configuration for different detectors
        """
        self.feature_names = feature_names
        self.detection_config = detection_config or self._default_config()
        
        # Initialize detectors
        self.statistical_detector = StatisticalAnomalyDetector(
            methods=self.detection_config.get('statistical_methods', ['zscore', 'iqr'])
        )
        
        self.ml_detector = MLAnomalyDetector(
            algorithms=self.detection_config.get('ml_algorithms', ['isolation_forest']),
            contamination=self.detection_config.get('contamination', 0.1)
        )
        
        self.ts_detector = TimeSeriesAnomalyDetector(
            window_size=self.detection_config.get('window_size', 24),
            seasonal_periods=self.detection_config.get('seasonal_periods', [24, 168])
        )
        
        # Anomaly tracking
        self.anomaly_history = deque(maxlen=10000)
        self.alert_thresholds = self.detection_config.get('alert_thresholds', {
            'high_priority': 0.8,
            'medium_priority': 0.6,
            'low_priority': 0.4
        })
        
        # Database connection
        self.db_pool = None
        
        self.experiment_tracker = get_experiment_tracker()
        
        logger.info("Initialized anomaly detection orchestrator")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration."""
        return {
            'statistical_methods': ['zscore', 'modified_zscore', 'iqr'],
            'ml_algorithms': ['isolation_forest', 'elliptic_envelope'],
            'contamination': 0.05,
            'window_size': 24,
            'seasonal_periods': [24, 168],
            'alert_thresholds': {
                'high_priority': 0.8,
                'medium_priority': 0.6,
                'low_priority': 0.4
            }
        }
    
    async def initialize_db_connection(self):
        """Initialize database connection."""
        try:
            connection_string = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            self.db_pool = await asyncpg.create_pool(connection_string, min_size=2, max_size=10)
            logger.info("Database connection pool initialized for anomaly detection")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
    
    def train_detectors(self, df: pd.DataFrame) -> None:
        """
        Train all anomaly detectors on historical data.
        
        Args:
            df: Historical data with features and timestamps
        """
        logger.info("Training anomaly detectors...")
        
        with self.experiment_tracker.start_run(
            run_name="anomaly_detector_training",
            tags={"detection_type": "batch_training"}
        ) as run:
            
            # Prepare features
            feature_columns = [col for col in df.columns if col in self.feature_names]
            X = df[feature_columns].values
            
            # Train ML detector
            self.ml_detector.fit(X)
            
            # Train statistical detector on target variable (e.g., delay_minutes)
            if 'delay_minutes' in df.columns:
                target_series = df['delay_minutes'].dropna()
                self.statistical_detector.fit(target_series)
                
                # Log training statistics
                mlflow.log_param("training_samples", len(df))
                mlflow.log_param("features_count", len(feature_columns))
                mlflow.log_param("ml_algorithms", self.ml_detector.algorithms)
                mlflow.log_param("statistical_methods", self.statistical_detector.methods)
            
            logger.info("Anomaly detector training completed")
    
    def detect_anomalies(self, 
                        df: pd.DataFrame,
                        return_details: bool = True) -> Dict[str, Any]:
        """
        Comprehensive anomaly detection on given data.
        
        Args:
            df: Data to analyze
            return_details: Whether to return detailed results
            
        Returns:
            Dictionary with anomaly detection results
        """
        logger.info(f"Running anomaly detection on {len(df)} samples...")
        
        results = {
            'timestamp': datetime.now(),
            'total_samples': len(df),
            'anomalies_detected': 0,
            'detection_results': {}
        }
        
        # Prepare features
        feature_columns = [col for col in df.columns if col in self.feature_names]
        X = df[feature_columns].values
        
        # ML-based detection
        try:
            ml_results = self.ml_detector.predict(X)
            ml_anomalies = ml_results['ensemble_anomaly'].sum()
            results['detection_results']['ml'] = {
                'anomalies_count': int(ml_anomalies),
                'anomaly_rate': float(ml_anomalies / len(df)),
                'details': ml_results.to_dict() if return_details else None
            }
            logger.info(f"ML detection found {ml_anomalies} anomalies")
        except Exception as e:
            logger.error(f"ML detection failed: {e}")
            results['detection_results']['ml'] = {'error': str(e)}
        
        # Statistical detection on target variable
        if 'delay_minutes' in df.columns:
            try:
                target_series = df['delay_minutes'].dropna()
                stat_results = self.statistical_detector.detect_anomalies(target_series)
                stat_anomalies = stat_results['ensemble_anomaly'].sum()
                results['detection_results']['statistical'] = {
                    'anomalies_count': int(stat_anomalies),
                    'anomaly_rate': float(stat_anomalies / len(target_series)),
                    'details': stat_results.to_dict() if return_details else None
                }
                logger.info(f"Statistical detection found {stat_anomalies} anomalies")
            except Exception as e:
                logger.error(f"Statistical detection failed: {e}")
                results['detection_results']['statistical'] = {'error': str(e)}
        
        # Time series detection
        if 'timestamp' in df.columns and 'delay_minutes' in df.columns:
            try:
                df_ts = df.set_index('timestamp')['delay_minutes'].dropna()
                
                # Change point detection
                change_points = self.ts_detector.detect_change_points(df_ts)
                
                # Seasonal anomalies
                seasonal_results = self.ts_detector.detect_seasonal_anomalies(df_ts)
                seasonal_anomalies = seasonal_results[[col for col in seasonal_results.columns if col.endswith('_anomaly')]].any(axis=1).sum()
                
                # Trend anomalies
                trend_results = self.ts_detector.detect_trend_anomalies(df_ts)
                trend_anomalies = trend_results[[col for col in trend_results.columns if col.endswith('_anomaly')]].any(axis=1).sum()
                
                results['detection_results']['time_series'] = {
                    'change_points': len(change_points),
                    'seasonal_anomalies': int(seasonal_anomalies),
                    'trend_anomalies': int(trend_anomalies),
                    'change_point_indices': change_points if return_details else None,
                    'seasonal_details': seasonal_results.to_dict() if return_details else None,
                    'trend_details': trend_results.to_dict() if return_details else None
                }
                
                logger.info(f"Time series detection found {seasonal_anomalies} seasonal and {trend_anomalies} trend anomalies")
            except Exception as e:
                logger.error(f"Time series detection failed: {e}")
                results['detection_results']['time_series'] = {'error': str(e)}
        
        # Calculate total anomalies (ensemble)
        total_anomalies = 0
        for method_results in results['detection_results'].values():
            if isinstance(method_results, dict) and 'anomalies_count' in method_results:
                total_anomalies += method_results['anomalies_count']
        
        results['anomalies_detected'] = total_anomalies
        results['overall_anomaly_rate'] = total_anomalies / len(df) if len(df) > 0 else 0
        
        # Store in history
        self.anomaly_history.append(results)
        
        return results
    
    async def real_time_monitoring(self, check_interval: int = 300):
        """
        Real-time anomaly monitoring.
        
        Args:
            check_interval: Check interval in seconds
        """
        logger.info("Starting real-time anomaly monitoring...")
        
        if not self.db_pool:
            await self.initialize_db_connection()
        
        last_check = datetime.now() - timedelta(minutes=10)
        
        while True:
            try:
                # Query recent data
                async with self.db_pool.acquire() as conn:
                    query = """
                        SELECT timestamp, stop_id, route_id, delay_minutes,
                               hour_of_day, is_weekend, is_holiday
                        FROM unified_realtime_historical_data
                        WHERE timestamp > $1
                        AND delay_minutes IS NOT NULL
                        ORDER BY timestamp
                        LIMIT 5000
                    """
                    
                    rows = await conn.fetch(query, last_check)
                
                if rows:
                    df = pd.DataFrame(rows)
                    
                    # Run anomaly detection
                    anomaly_results = self.detect_anomalies(df, return_details=False)
                    
                    # Check for alerts
                    await self._check_and_send_alerts(anomaly_results, df)
                    
                    # Log results
                    with self.experiment_tracker.start_run(
                        run_name="real_time_anomaly_detection",
                        tags={"detection_type": "real_time", "samples": len(df)}
                    ) as run:
                        
                        mlflow.log_metric("total_samples", anomaly_results['total_samples'])
                        mlflow.log_metric("anomalies_detected", anomaly_results['anomalies_detected'])
                        mlflow.log_metric("anomaly_rate", anomaly_results['overall_anomaly_rate'])
                        
                        for method, results in anomaly_results['detection_results'].items():
                            if isinstance(results, dict) and 'anomaly_rate' in results:
                                mlflow.log_metric(f"{method}_anomaly_rate", results['anomaly_rate'])
                    
                    logger.info(f"Real-time detection completed: {anomaly_results['anomalies_detected']} anomalies in {len(df)} samples")
                    last_check = max(pd.to_datetime(df['timestamp']))
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in real-time monitoring: {e}")
                await asyncio.sleep(check_interval * 2)
    
    async def _check_and_send_alerts(self, anomaly_results: Dict[str, Any], data: pd.DataFrame):
        """Check anomaly results and send alerts if necessary."""
        anomaly_rate = anomaly_results['overall_anomaly_rate']
        
        alert_level = None
        if anomaly_rate >= self.alert_thresholds['high_priority']:
            alert_level = 'HIGH'
        elif anomaly_rate >= self.alert_thresholds['medium_priority']:
            alert_level = 'MEDIUM'
        elif anomaly_rate >= self.alert_thresholds['low_priority']:
            alert_level = 'LOW'
        
        if alert_level:
            alert_data = {
                'level': alert_level,
                'timestamp': anomaly_results['timestamp'].isoformat(),
                'anomaly_rate': anomaly_rate,
                'total_samples': anomaly_results['total_samples'],
                'anomalies_detected': anomaly_results['anomalies_detected'],
                'detection_summary': {
                    method: results.get('anomalies_count', 0) 
                    for method, results in anomaly_results['detection_results'].items()
                    if isinstance(results, dict)
                }
            }
            
            logger.warning(f"ANOMALY ALERT [{alert_level}]: {anomaly_rate:.2%} anomaly rate detected")
            
            # Here you would send the alert to your monitoring system
            # e.g., Slack, PagerDuty, email, etc.
            await self._send_alert_notification(alert_data)
    
    async def _send_alert_notification(self, alert_data: Dict[str, Any]):
        """Send alert notification (placeholder for actual implementation)."""
        # Implement your alert notification logic here
        # Examples: Slack webhook, email, SMS, PagerDuty, etc.
        logger.info(f"Alert notification would be sent: {alert_data}")
    
    def create_anomaly_dashboard(self, 
                                results: Dict[str, Any],
                                data: pd.DataFrame) -> str:
        """
        Create interactive anomaly dashboard.
        
        Args:
            results: Anomaly detection results
            data: Original data
            
        Returns:
            Path to dashboard HTML file
        """
        try:
            # Create subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=[
                    "Anomaly Detection Overview",
                    "Time Series with Anomalies",
                    "Detection Method Comparison",
                    "Anomaly Distribution",
                    "Feature Correlation",
                    "System Performance"
                ],
                specs=[
                    [{"type": "indicator"}, {"type": "scatter"}],
                    [{"type": "bar"}, {"type": "histogram"}],
                    [{"type": "heatmap"}, {"type": "scatter"}]
                ]
            )
            
            # Overview indicator
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=results['overall_anomaly_rate'] * 100,
                    title={'text': "Anomaly Rate (%)"},
                    gauge={
                        'axis': {'range': [None, 20]},
                        'bar': {'color': "red" if results['overall_anomaly_rate'] > 0.1 else "green"},
                        'steps': [
                            {'range': [0, 5], 'color': "lightgray"},
                            {'range': [5, 10], 'color': "yellow"},
                            {'range': [10, 20], 'color': "red"}
                        ],
                    }
                ),
                row=1, col=1
            )
            
            # Time series with anomalies
            if 'timestamp' in data.columns and 'delay_minutes' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data['timestamp'],
                        y=data['delay_minutes'],
                        mode='lines+markers',
                        name="Delay Minutes",
                        line=dict(color='blue')
                    ),
                    row=1, col=2
                )
                
                # Add anomaly points if available
                if 'ml' in results['detection_results'] and results['detection_results']['ml'].get('details'):
                    ml_details = results['detection_results']['ml']['details']
                    if 'ensemble_anomaly' in ml_details:
                        anomaly_mask = ml_details['ensemble_anomaly']
                        anomaly_data = data[anomaly_mask]
                        
                        fig.add_trace(
                            go.Scatter(
                                x=anomaly_data['timestamp'],
                                y=anomaly_data['delay_minutes'],
                                mode='markers',
                                name="Anomalies",
                                marker=dict(color='red', size=8, symbol='x')
                            ),
                            row=1, col=2
                        )
            
            # Detection method comparison
            methods = []
            anomaly_counts = []
            for method, method_results in results['detection_results'].items():
                if isinstance(method_results, dict) and 'anomalies_count' in method_results:
                    methods.append(method.capitalize())
                    anomaly_counts.append(method_results['anomalies_count'])
            
            if methods:
                fig.add_trace(
                    go.Bar(x=methods, y=anomaly_counts, name="Anomalies by Method"),
                    row=2, col=1
                )
            
            # Update layout
            fig.update_layout(
                title=f"Anomaly Detection Dashboard - {results['timestamp'].strftime('%Y-%m-%d %H:%M')}",
                height=1200,
                showlegend=True
            )
            
            # Save dashboard
            dashboard_dir = os.path.join(settings.MODELS_DIR, "anomaly_detection", "dashboards")
            os.makedirs(dashboard_dir, exist_ok=True)
            
            timestamp_str = results['timestamp'].strftime('%Y%m%d_%H%M%S')
            dashboard_path = os.path.join(dashboard_dir, f"anomaly_dashboard_{timestamp_str}.html")
            
            fig.write_html(dashboard_path)
            logger.info(f"Anomaly dashboard saved to {dashboard_path}")
            
            return dashboard_path
            
        except Exception as e:
            logger.error(f"Failed to create anomaly dashboard: {e}")
            return ""
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        status = {
            "detectors_initialized": {
                "statistical": hasattr(self.statistical_detector, 'seasonal_params'),
                "ml": self.ml_detector.is_fitted,
                "time_series": True
            },
            "anomaly_history_count": len(self.anomaly_history),
            "alert_thresholds": self.alert_thresholds,
            "detection_config": self.detection_config,
            "last_detection": self.anomaly_history[-1] if self.anomaly_history else None
        }
        
        # Recent performance
        if self.anomaly_history:
            recent_history = list(self.anomaly_history)[-10:]
            status["recent_performance"] = {
                "avg_anomaly_rate": np.mean([h['overall_anomaly_rate'] for h in recent_history]),
                "max_anomaly_rate": max([h['overall_anomaly_rate'] for h in recent_history]),
                "total_detections": len(recent_history)
            }
        
        return status


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Initialize orchestrator
    feature_names = ["delay_minutes", "hour_of_day", "is_weekend", "is_holiday"]
    orchestrator = AnomalyDetectionOrchestrator(feature_names)
    
    # Generate sample data with anomalies
    np.random.seed(42)
    n_samples = 1000
    
    normal_data = np.random.randn(n_samples - 50, len(feature_names))
    anomaly_data = np.random.randn(50, len(feature_names)) * 3 + 5  # Anomalous samples
    
    X = np.vstack([normal_data, anomaly_data])
    timestamps = pd.date_range(start='2024-01-01', periods=n_samples, freq='H')
    
    df = pd.DataFrame(X, columns=feature_names)
    df['timestamp'] = timestamps
    df['delay_minutes'] = df[feature_names[0]] * 2 + np.random.randn(n_samples) * 0.5
    
    # Train detectors
    orchestrator.train_detectors(df[:800])  # Train on first 800 samples
    
    # Detect anomalies on test data
    test_data = df[800:]
    results = orchestrator.detect_anomalies(test_data)
    
    print("Anomaly Detection Results:")
    print(json.dumps(results, indent=2, default=str))
    
    # Create dashboard
    dashboard_path = orchestrator.create_anomaly_dashboard(results, test_data)
    print(f"Dashboard created: {dashboard_path}")
    
    # Get system status
    status = orchestrator.get_system_status()
    print("\nSystem Status:")
    print(json.dumps(status, indent=2, default=str))