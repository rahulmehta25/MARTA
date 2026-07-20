"""
Model Monitoring and Drift Detection for MARTA ML Models

This module implements comprehensive model monitoring including performance tracking,
data drift detection, concept drift detection, and automated alerting systems.
"""
import os
import logging
import json
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from scipy import stats
from scipy.spatial.distance import jensenshannon, wasserstein_distance
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import asyncpg
from prometheus_client import Gauge, Counter, Histogram, CollectorRegistry
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import mlflow
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from src.models.ml_experiment_tracker import get_experiment_tracker

logger = logging.getLogger(__name__)


class DriftType(Enum):
    """Types of drift detection."""
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    TARGET_DRIFT = "target_drift"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MonitoringAlert:
    """Monitoring alert data structure."""
    alert_id: str
    severity: AlertSeverity
    alert_type: str
    message: str
    model_name: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class DriftDetectionResult:
    """Drift detection result."""
    drift_type: DriftType
    detected: bool
    drift_score: float
    threshold: float
    p_value: Optional[float]
    feature_name: Optional[str]
    timestamp: datetime
    method: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Model performance monitoring system.
    
    Features:
    - Real-time performance tracking
    - Performance degradation detection
    - Threshold-based alerting
    - Historical performance analysis
    """
    
    def __init__(self, 
                 model_name: str,
                 performance_window: int = 1000,
                 degradation_threshold: float = 0.1):
        """
        Initialize performance monitor.
        
        Args:
            model_name: Name of the model to monitor
            performance_window: Size of the sliding window for performance calculation
            degradation_threshold: Threshold for performance degradation alert
        """
        self.model_name = model_name
        self.performance_window = performance_window
        self.degradation_threshold = degradation_threshold
        
        # Performance tracking
        self.predictions = deque(maxlen=performance_window)
        self.actuals = deque(maxlen=performance_window)
        self.timestamps = deque(maxlen=performance_window)
        
        # Baseline performance (established during initial training)
        self.baseline_metrics = {}
        self.current_metrics = {}
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.performance_gauge = Gauge(
            f'{model_name}_performance_score', 
            f'Current performance score for {model_name}',
            registry=self.registry
        )
        self.degradation_counter = Counter(
            f'{model_name}_performance_degradation_total',
            f'Total performance degradation alerts for {model_name}',
            registry=self.registry
        )
        
        logger.info(f"Performance monitor initialized for {model_name}")
    
    def set_baseline(self, 
                    predictions: np.ndarray, 
                    actuals: np.ndarray) -> None:
        """
        Set baseline performance metrics.
        
        Args:
            predictions: Baseline predictions
            actuals: Baseline actual values
        """
        self.baseline_metrics = {
            'mae': mean_absolute_error(actuals, predictions),
            'mse': mean_squared_error(actuals, predictions),
            'rmse': np.sqrt(mean_squared_error(actuals, predictions)),
            'r2': r2_score(actuals, predictions)
        }
        
        logger.info(f"Baseline metrics set for {self.model_name}: {self.baseline_metrics}")
    
    def add_prediction(self, 
                      prediction: float,
                      actual: Optional[float] = None,
                      timestamp: Optional[datetime] = None) -> None:
        """
        Add new prediction for monitoring.
        
        Args:
            prediction: Model prediction
            actual: Actual value (if available)
            timestamp: Timestamp of prediction
        """
        self.predictions.append(prediction)
        if actual is not None:
            self.actuals.append(actual)
        self.timestamps.append(timestamp or datetime.now())
        
        # Update current metrics if we have actuals
        if len(self.actuals) >= 10:  # Minimum samples for reliable metrics
            self._update_current_metrics()
    
    def _update_current_metrics(self) -> None:
        """Update current performance metrics."""
        if len(self.predictions) != len(self.actuals):
            # Only use samples where we have both prediction and actual
            min_len = min(len(self.predictions), len(self.actuals))
            preds = list(self.predictions)[-min_len:]
            acts = list(self.actuals)[-min_len:]
        else:
            preds = list(self.predictions)
            acts = list(self.actuals)
        
        if len(preds) > 0 and len(acts) > 0:
            self.current_metrics = {
                'mae': mean_absolute_error(acts, preds),
                'mse': mean_squared_error(acts, preds),
                'rmse': np.sqrt(mean_squared_error(acts, preds)),
                'r2': r2_score(acts, preds)
            }
            
            # Update Prometheus metrics
            self.performance_gauge.set(self.current_metrics['r2'])
    
    def detect_performance_degradation(self) -> List[MonitoringAlert]:
        """
        Detect performance degradation compared to baseline.
        
        Returns:
            List of alerts if degradation detected
        """
        alerts = []
        
        if not self.baseline_metrics or not self.current_metrics:
            return alerts
        
        for metric_name in ['mae', 'rmse']:  # Lower is better
            baseline_value = self.baseline_metrics[metric_name]
            current_value = self.current_metrics[metric_name]
            
            # Check if performance degraded
            degradation = (current_value - baseline_value) / baseline_value
            
            if degradation > self.degradation_threshold:
                severity = AlertSeverity.HIGH if degradation > 0.2 else AlertSeverity.MEDIUM
                
                alert = MonitoringAlert(
                    alert_id=f"perf_degradation_{self.model_name}_{metric_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    severity=severity,
                    alert_type="performance_degradation",
                    message=f"Performance degradation detected for {self.model_name}: {metric_name} increased by {degradation:.2%}",
                    model_name=self.model_name,
                    metric_name=metric_name,
                    current_value=current_value,
                    threshold=baseline_value * (1 + self.degradation_threshold),
                    timestamp=datetime.now(),
                    metadata={
                        "baseline_value": baseline_value,
                        "degradation_percentage": degradation,
                        "sample_size": len(self.current_metrics)
                    }
                )
                
                alerts.append(alert)
                self.degradation_counter.inc()
        
        return alerts
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance monitoring summary."""
        return {
            "model_name": self.model_name,
            "baseline_metrics": self.baseline_metrics,
            "current_metrics": self.current_metrics,
            "total_predictions": len(self.predictions),
            "predictions_with_actuals": len(self.actuals),
            "monitoring_window": self.performance_window,
            "last_update": self.timestamps[-1].isoformat() if self.timestamps else None
        }


class DataDriftDetector:
    """
    Data drift detection using statistical methods.
    
    Features:
    - Multiple drift detection methods
    - Feature-wise drift analysis
    - Population stability index (PSI)
    - Kolmogorov-Smirnov test
    - Jensen-Shannon divergence
    """
    
    def __init__(self, 
                 feature_names: List[str],
                 reference_data: Optional[np.ndarray] = None,
                 drift_threshold: float = 0.1):
        """
        Initialize data drift detector.
        
        Args:
            feature_names: List of feature names
            reference_data: Reference dataset for drift detection
            drift_threshold: Threshold for drift detection
        """
        self.feature_names = feature_names
        self.reference_data = reference_data
        self.drift_threshold = drift_threshold
        
        # Statistical properties of reference data
        self.reference_stats = {}
        
        if reference_data is not None:
            self.set_reference_data(reference_data)
        
        logger.info(f"Data drift detector initialized for {len(feature_names)} features")
    
    def set_reference_data(self, reference_data: np.ndarray) -> None:
        """
        Set reference data for drift detection.
        
        Args:
            reference_data: Reference dataset
        """
        self.reference_data = reference_data
        
        # Calculate reference statistics
        for i, feature_name in enumerate(self.feature_names):
            feature_data = reference_data[:, i]
            
            self.reference_stats[feature_name] = {
                'mean': np.mean(feature_data),
                'std': np.std(feature_data),
                'min': np.min(feature_data),
                'max': np.max(feature_data),
                'quantiles': np.quantile(feature_data, [0.25, 0.5, 0.75]),
                'distribution': feature_data  # Store for distribution comparisons
            }
        
        logger.info("Reference data statistics calculated")
    
    def detect_drift(self, current_data: np.ndarray) -> List[DriftDetectionResult]:
        """
        Detect data drift in current data.
        
        Args:
            current_data: Current dataset to check for drift
            
        Returns:
            List of drift detection results
        """
        if self.reference_data is None:
            raise ValueError("Reference data not set")
        
        drift_results = []
        
        for i, feature_name in enumerate(self.feature_names):
            reference_feature = self.reference_data[:, i]
            current_feature = current_data[:, i]
            
            # Kolmogorov-Smirnov test
            ks_result = self._ks_test(reference_feature, current_feature, feature_name)
            drift_results.append(ks_result)
            
            # Population Stability Index
            psi_result = self._psi_test(reference_feature, current_feature, feature_name)
            drift_results.append(psi_result)
            
            # Jensen-Shannon divergence
            js_result = self._jensen_shannon_test(reference_feature, current_feature, feature_name)
            drift_results.append(js_result)
            
            # Wasserstein distance
            wd_result = self._wasserstein_test(reference_feature, current_feature, feature_name)
            drift_results.append(wd_result)
        
        return drift_results
    
    def _ks_test(self, 
                reference: np.ndarray, 
                current: np.ndarray,
                feature_name: str) -> DriftDetectionResult:
        """Kolmogorov-Smirnov test for distribution comparison."""
        statistic, p_value = stats.ks_2samp(reference, current)
        
        return DriftDetectionResult(
            drift_type=DriftType.DATA_DRIFT,
            detected=p_value < 0.05,  # 5% significance level
            drift_score=float(statistic),
            threshold=self.drift_threshold,
            p_value=float(p_value),
            feature_name=feature_name,
            timestamp=datetime.now(),
            method="kolmogorov_smirnov",
            metadata={
                "statistic": float(statistic),
                "critical_value": 0.05
            }
        )
    
    def _psi_test(self,
                 reference: np.ndarray,
                 current: np.ndarray,
                 feature_name: str,
                 bins: int = 10) -> DriftDetectionResult:
        """Population Stability Index test."""
        try:
            # Create bins based on reference data
            bin_edges = np.histogram_bin_edges(reference, bins=bins)
            
            # Calculate frequencies
            ref_freq, _ = np.histogram(reference, bins=bin_edges)
            cur_freq, _ = np.histogram(current, bins=bin_edges)
            
            # Convert to percentages and add small constant to avoid division by zero
            ref_pct = (ref_freq + 1e-6) / (len(reference) + bins * 1e-6)
            cur_pct = (cur_freq + 1e-6) / (len(current) + bins * 1e-6)
            
            # Calculate PSI
            psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
            
            # PSI interpretation: <0.1: no change, 0.1-0.2: minor change, >0.2: major change
            detected = psi > 0.1
            
        except Exception as e:
            logger.error(f"PSI calculation failed for {feature_name}: {e}")
            psi = 0.0
            detected = False
        
        return DriftDetectionResult(
            drift_type=DriftType.DATA_DRIFT,
            detected=detected,
            drift_score=float(psi),
            threshold=0.1,
            p_value=None,
            feature_name=feature_name,
            timestamp=datetime.now(),
            method="population_stability_index",
            metadata={
                "bins": bins,
                "interpretation": "no_change" if psi < 0.1 else ("minor_change" if psi < 0.2 else "major_change")
            }
        )
    
    def _jensen_shannon_test(self,
                            reference: np.ndarray,
                            current: np.ndarray,
                            feature_name: str,
                            bins: int = 50) -> DriftDetectionResult:
        """Jensen-Shannon divergence test."""
        try:
            # Create histograms
            range_min = min(reference.min(), current.min())
            range_max = max(reference.max(), current.max())
            
            ref_hist, _ = np.histogram(reference, bins=bins, range=(range_min, range_max), density=True)
            cur_hist, _ = np.histogram(current, bins=bins, range=(range_min, range_max), density=True)
            
            # Normalize to probability distributions
            ref_hist = ref_hist / ref_hist.sum()
            cur_hist = cur_hist / cur_hist.sum()
            
            # Add small constant to avoid log(0)
            ref_hist = ref_hist + 1e-10
            cur_hist = cur_hist + 1e-10
            
            # Calculate Jensen-Shannon divergence
            js_distance = jensenshannon(ref_hist, cur_hist)
            
            # JS distance ranges from 0 to 1, where 0 means identical distributions
            detected = js_distance > self.drift_threshold
            
        except Exception as e:
            logger.error(f"Jensen-Shannon calculation failed for {feature_name}: {e}")
            js_distance = 0.0
            detected = False
        
        return DriftDetectionResult(
            drift_type=DriftType.DATA_DRIFT,
            detected=detected,
            drift_score=float(js_distance),
            threshold=self.drift_threshold,
            p_value=None,
            feature_name=feature_name,
            timestamp=datetime.now(),
            method="jensen_shannon_divergence",
            metadata={"bins": bins}
        )
    
    def _wasserstein_test(self,
                         reference: np.ndarray,
                         current: np.ndarray,
                         feature_name: str) -> DriftDetectionResult:
        """Wasserstein distance test."""
        try:
            # Calculate Wasserstein distance
            wd = wasserstein_distance(reference, current)
            
            # Normalize by the range of reference data
            ref_range = reference.max() - reference.min()
            normalized_wd = wd / (ref_range + 1e-10)
            
            detected = normalized_wd > self.drift_threshold
            
        except Exception as e:
            logger.error(f"Wasserstein distance calculation failed for {feature_name}: {e}")
            normalized_wd = 0.0
            detected = False
        
        return DriftDetectionResult(
            drift_type=DriftType.DATA_DRIFT,
            detected=detected,
            drift_score=float(normalized_wd),
            threshold=self.drift_threshold,
            p_value=None,
            feature_name=feature_name,
            timestamp=datetime.now(),
            method="wasserstein_distance",
            metadata={"raw_distance": float(wd) if 'wd' in locals() else 0.0}
        )


class ConceptDriftDetector:
    """
    Concept drift detection for model predictions and target variables.
    
    Features:
    - ADWIN (Adaptive Windowing) algorithm
    - Page-Hinkley test
    - CUSUM (Cumulative Sum) control chart
    - Drift magnitude estimation
    """
    
    def __init__(self, 
                 drift_threshold: float = 0.05,
                 window_size: int = 1000):
        """
        Initialize concept drift detector.
        
        Args:
            drift_threshold: Threshold for drift detection
            window_size: Window size for drift detection
        """
        self.drift_threshold = drift_threshold
        self.window_size = window_size
        
        # ADWIN parameters
        self.adwin_window = deque(maxlen=window_size)
        self.adwin_variance = 0.0
        self.adwin_mean = 0.0
        
        # Page-Hinkley parameters
        self.ph_cumsum = 0.0
        self.ph_min_cumsum = 0.0
        self.ph_threshold = 50.0
        
        # CUSUM parameters
        self.cusum_pos = 0.0
        self.cusum_neg = 0.0
        self.cusum_threshold = 5.0
        
        logger.info("Concept drift detector initialized")
    
    def detect_drift_adwin(self, new_value: float) -> DriftDetectionResult:
        """
        ADWIN drift detection algorithm.
        
        Args:
            new_value: New value to test for drift
            
        Returns:
            Drift detection result
        """
        self.adwin_window.append(new_value)
        
        if len(self.adwin_window) < 10:
            return DriftDetectionResult(
                drift_type=DriftType.CONCEPT_DRIFT,
                detected=False,
                drift_score=0.0,
                threshold=self.drift_threshold,
                p_value=None,
                feature_name=None,
                timestamp=datetime.now(),
                method="adwin"
            )
        
        # Calculate current statistics
        current_mean = np.mean(self.adwin_window)
        current_var = np.var(self.adwin_window)
        
        # Check for significant change in mean
        if len(self.adwin_window) >= 20:
            # Split window and compare
            mid_point = len(self.adwin_window) // 2
            window_list = list(self.adwin_window)
            
            first_half = window_list[:mid_point]
            second_half = window_list[mid_point:]
            
            if len(first_half) > 5 and len(second_half) > 5:
                # Perform t-test
                statistic, p_value = stats.ttest_ind(first_half, second_half)
                
                detected = p_value < 0.05
                drift_score = abs(statistic) if not np.isnan(statistic) else 0.0
            else:
                detected = False
                drift_score = 0.0
        else:
            detected = False
            drift_score = 0.0
        
        return DriftDetectionResult(
            drift_type=DriftType.CONCEPT_DRIFT,
            detected=detected,
            drift_score=float(drift_score),
            threshold=self.drift_threshold,
            p_value=float(p_value) if 'p_value' in locals() else None,
            feature_name=None,
            timestamp=datetime.now(),
            method="adwin",
            metadata={
                "window_size": len(self.adwin_window),
                "current_mean": float(current_mean),
                "current_variance": float(current_var)
            }
        )
    
    def detect_drift_page_hinkley(self, new_value: float) -> DriftDetectionResult:
        """
        Page-Hinkley test for drift detection.
        
        Args:
            new_value: New value to test
            
        Returns:
            Drift detection result
        """
        # Update cumulative sum
        self.ph_cumsum += new_value - self.drift_threshold
        
        # Update minimum
        if self.ph_cumsum < self.ph_min_cumsum:
            self.ph_min_cumsum = self.ph_cumsum
        
        # Check for drift
        drift_magnitude = self.ph_cumsum - self.ph_min_cumsum
        detected = drift_magnitude > self.ph_threshold
        
        if detected:
            # Reset after drift detection
            self.ph_cumsum = 0.0
            self.ph_min_cumsum = 0.0
        
        return DriftDetectionResult(
            drift_type=DriftType.CONCEPT_DRIFT,
            detected=detected,
            drift_score=float(drift_magnitude),
            threshold=self.ph_threshold,
            p_value=None,
            feature_name=None,
            timestamp=datetime.now(),
            method="page_hinkley",
            metadata={
                "cumsum": float(self.ph_cumsum),
                "min_cumsum": float(self.ph_min_cumsum)
            }
        )
    
    def detect_drift_cusum(self, new_value: float, target_mean: float = 0.0) -> DriftDetectionResult:
        """
        CUSUM control chart for drift detection.
        
        Args:
            new_value: New value to test
            target_mean: Target mean value
            
        Returns:
            Drift detection result
        """
        deviation = new_value - target_mean
        
        # Update CUSUM statistics
        self.cusum_pos = max(0, self.cusum_pos + deviation - self.drift_threshold)
        self.cusum_neg = max(0, self.cusum_neg - deviation - self.drift_threshold)
        
        # Check for drift
        detected = self.cusum_pos > self.cusum_threshold or self.cusum_neg > self.cusum_threshold
        drift_score = max(self.cusum_pos, self.cusum_neg)
        
        if detected:
            # Reset after detection
            self.cusum_pos = 0.0
            self.cusum_neg = 0.0
        
        return DriftDetectionResult(
            drift_type=DriftType.CONCEPT_DRIFT,
            detected=detected,
            drift_score=float(drift_score),
            threshold=self.cusum_threshold,
            p_value=None,
            feature_name=None,
            timestamp=datetime.now(),
            method="cusum",
            metadata={
                "cusum_positive": float(self.cusum_pos),
                "cusum_negative": float(self.cusum_neg),
                "deviation": float(deviation)
            }
        )


class AlertManager:
    """
    Alert management system for monitoring alerts.
    
    Features:
    - Multiple alert channels (email, Slack, webhook)
    - Alert deduplication
    - Severity-based routing
    - Alert history tracking
    """
    
    def __init__(self):
        """Initialize alert manager."""
        self.alert_history = deque(maxlen=10000)
        self.active_alerts = {}
        self.alert_channels = []
        
        logger.info("Alert manager initialized")
    
    def add_email_channel(self, 
                         smtp_server: str,
                         smtp_port: int,
                         username: str,
                         password: str,
                         recipients: List[str]) -> None:
        """Add email alert channel."""
        self.alert_channels.append({
            'type': 'email',
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'recipients': recipients
        })
        
        logger.info(f"Email alert channel added for {len(recipients)} recipients")
    
    def add_slack_channel(self, webhook_url: str, channel: str = None) -> None:
        """Add Slack alert channel."""
        self.alert_channels.append({
            'type': 'slack',
            'webhook_url': webhook_url,
            'channel': channel
        })
        
        logger.info("Slack alert channel added")
    
    def add_webhook_channel(self, webhook_url: str, headers: Dict[str, str] = None) -> None:
        """Add generic webhook alert channel."""
        self.alert_channels.append({
            'type': 'webhook',
            'webhook_url': webhook_url,
            'headers': headers or {}
        })
        
        logger.info("Webhook alert channel added")
    
    async def send_alert(self, alert: MonitoringAlert) -> None:
        """
        Send alert through configured channels.
        
        Args:
            alert: Alert to send
        """
        # Check for duplicate alerts
        if self._is_duplicate_alert(alert):
            logger.debug(f"Skipping duplicate alert: {alert.alert_id}")
            return
        
        # Store alert in history
        self.alert_history.append(alert)
        self.active_alerts[alert.alert_id] = alert
        
        # Send through all channels
        for channel in self.alert_channels:
            try:
                if channel['type'] == 'email':
                    await self._send_email_alert(alert, channel)
                elif channel['type'] == 'slack':
                    await self._send_slack_alert(alert, channel)
                elif channel['type'] == 'webhook':
                    await self._send_webhook_alert(alert, channel)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel['type']}: {e}")
        
        logger.info(f"Alert sent: {alert.alert_id} - {alert.message}")
    
    def _is_duplicate_alert(self, alert: MonitoringAlert) -> bool:
        """Check if alert is a duplicate of recent alerts."""
        # Check last 100 alerts for similar ones
        recent_alerts = list(self.alert_history)[-100:]
        
        for recent_alert in recent_alerts:
            if (recent_alert.alert_type == alert.alert_type and
                recent_alert.model_name == alert.model_name and
                recent_alert.metric_name == alert.metric_name and
                abs((alert.timestamp - recent_alert.timestamp).total_seconds()) < 3600):  # 1 hour
                return True
        
        return False
    
    async def _send_email_alert(self, alert: MonitoringAlert, channel: Dict[str, Any]) -> None:
        """Send email alert."""
        subject = f"[{alert.severity.value.upper()}] ML Model Alert: {alert.model_name}"
        
        body = f"""
        Alert ID: {alert.alert_id}
        Model: {alert.model_name}
        Severity: {alert.severity.value}
        Type: {alert.alert_type}
        
        Message: {alert.message}
        
        Metric: {alert.metric_name}
        Current Value: {alert.current_value:.4f}
        Threshold: {alert.threshold:.4f}
        
        Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        
        Metadata: {json.dumps(alert.metadata, indent=2)}
        """
        
        msg = MIMEMultipart()
        msg['From'] = channel['username']
        msg['To'] = ', '.join(channel['recipients'])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(channel['smtp_server'], channel['smtp_port'])
        server.starttls()
        server.login(channel['username'], channel['password'])
        server.send_message(msg)
        server.quit()
    
    async def _send_slack_alert(self, alert: MonitoringAlert, channel: Dict[str, Any]) -> None:
        """Send Slack alert."""
        color = {
            AlertSeverity.LOW: 'good',
            AlertSeverity.MEDIUM: 'warning', 
            AlertSeverity.HIGH: 'danger',
            AlertSeverity.CRITICAL: 'danger'
        }.get(alert.severity, 'good')
        
        payload = {
            'text': f'ML Model Alert: {alert.model_name}',
            'attachments': [{
                'color': color,
                'title': f'{alert.severity.value.upper()}: {alert.alert_type}',
                'text': alert.message,
                'fields': [
                    {'title': 'Model', 'value': alert.model_name, 'short': True},
                    {'title': 'Metric', 'value': alert.metric_name, 'short': True},
                    {'title': 'Current Value', 'value': f'{alert.current_value:.4f}', 'short': True},
                    {'title': 'Threshold', 'value': f'{alert.threshold:.4f}', 'short': True}
                ],
                'ts': int(alert.timestamp.timestamp())
            }]
        }
        
        if channel.get('channel'):
            payload['channel'] = channel['channel']
        
        async with asyncio.get_event_loop().run_in_executor(None, requests.post, channel['webhook_url']) as response:
            response = requests.post(channel['webhook_url'], json=payload)
            response.raise_for_status()
    
    async def _send_webhook_alert(self, alert: MonitoringAlert, channel: Dict[str, Any]) -> None:
        """Send webhook alert."""
        payload = {
            'alert_id': alert.alert_id,
            'severity': alert.severity.value,
            'alert_type': alert.alert_type,
            'message': alert.message,
            'model_name': alert.model_name,
            'metric_name': alert.metric_name,
            'current_value': alert.current_value,
            'threshold': alert.threshold,
            'timestamp': alert.timestamp.isoformat(),
            'metadata': alert.metadata
        }
        
        headers = channel.get('headers', {})
        headers.setdefault('Content-Type', 'application/json')
        
        response = requests.post(channel['webhook_url'], json=payload, headers=headers)
        response.raise_for_status()
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics."""
        if not self.alert_history:
            return {"total_alerts": 0}
        
        recent_alerts = [a for a in self.alert_history if (datetime.now() - a.timestamp).days < 7]
        
        severity_counts = defaultdict(int)
        type_counts = defaultdict(int)
        model_counts = defaultdict(int)
        
        for alert in recent_alerts:
            severity_counts[alert.severity.value] += 1
            type_counts[alert.alert_type] += 1
            model_counts[alert.model_name] += 1
        
        return {
            "total_alerts": len(self.alert_history),
            "recent_alerts_7d": len(recent_alerts),
            "active_alerts": len(self.active_alerts),
            "severity_distribution": dict(severity_counts),
            "type_distribution": dict(type_counts),
            "model_distribution": dict(model_counts)
        }


class ModelMonitoringOrchestrator:
    """
    Main orchestrator for comprehensive model monitoring.
    
    Features:
    - Performance monitoring
    - Data drift detection
    - Concept drift detection
    - Alert management
    - Dashboard creation
    - Database integration
    """
    
    def __init__(self, model_configs: Dict[str, Dict[str, Any]]):
        """
        Initialize monitoring orchestrator.
        
        Args:
            model_configs: Configuration for each model to monitor
        """
        self.model_configs = model_configs
        self.performance_monitors = {}
        self.data_drift_detectors = {}
        self.concept_drift_detectors = {}
        self.alert_manager = AlertManager()
        
        # Initialize monitors for each model
        for model_name, config in model_configs.items():
            self.performance_monitors[model_name] = PerformanceMonitor(
                model_name=model_name,
                performance_window=config.get('performance_window', 1000),
                degradation_threshold=config.get('degradation_threshold', 0.1)
            )
            
            feature_names = config.get('feature_names', [])
            if feature_names:
                self.data_drift_detectors[model_name] = DataDriftDetector(
                    feature_names=feature_names,
                    drift_threshold=config.get('drift_threshold', 0.1)
                )
            
            self.concept_drift_detectors[model_name] = ConceptDriftDetector(
                drift_threshold=config.get('concept_drift_threshold', 0.05),
                window_size=config.get('drift_window_size', 1000)
            )
        
        # Database connection
        self.db_pool = None
        
        self.experiment_tracker = get_experiment_tracker()
        
        logger.info(f"Model monitoring orchestrator initialized for {len(model_configs)} models")
    
    async def initialize_db_connection(self):
        """Initialize database connection."""
        try:
            connection_string = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            self.db_pool = await asyncpg.create_pool(connection_string, min_size=2, max_size=10)
            logger.info("Database connection pool initialized for monitoring")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
    
    def set_model_baseline(self, 
                          model_name: str, 
                          predictions: np.ndarray,
                          actuals: np.ndarray,
                          features: Optional[np.ndarray] = None) -> None:
        """
        Set baseline performance and reference data for a model.
        
        Args:
            model_name: Name of the model
            predictions: Baseline predictions
            actuals: Baseline actual values
            features: Baseline feature data
        """
        if model_name in self.performance_monitors:
            self.performance_monitors[model_name].set_baseline(predictions, actuals)
        
        if model_name in self.data_drift_detectors and features is not None:
            self.data_drift_detectors[model_name].set_reference_data(features)
        
        logger.info(f"Baseline set for model: {model_name}")
    
    async def monitor_prediction(self,
                                model_name: str,
                                prediction: float,
                                features: np.ndarray,
                                actual: Optional[float] = None,
                                user_id: Optional[str] = None) -> List[MonitoringAlert]:
        """
        Monitor a single prediction and check for issues.
        
        Args:
            model_name: Name of the model
            prediction: Model prediction
            features: Input features
            actual: Actual value (if available)
            user_id: User identifier
            
        Returns:
            List of alerts generated
        """
        alerts = []
        
        # Performance monitoring
        if model_name in self.performance_monitors:
            self.performance_monitors[model_name].add_prediction(prediction, actual)
            
            # Check for performance degradation
            perf_alerts = self.performance_monitors[model_name].detect_performance_degradation()
            alerts.extend(perf_alerts)
        
        # Concept drift detection (on prediction)
        if model_name in self.concept_drift_detectors:
            detector = self.concept_drift_detectors[model_name]
            
            # ADWIN drift detection
            adwin_result = detector.detect_drift_adwin(prediction)
            if adwin_result.detected:
                alert = MonitoringAlert(
                    alert_id=f"concept_drift_{model_name}_adwin_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    severity=AlertSeverity.HIGH,
                    alert_type="concept_drift",
                    message=f"Concept drift detected in {model_name} using ADWIN method",
                    model_name=model_name,
                    metric_name="prediction_drift",
                    current_value=adwin_result.drift_score,
                    threshold=adwin_result.threshold,
                    timestamp=datetime.now(),
                    metadata=adwin_result.metadata
                )
                alerts.append(alert)
            
            # Page-Hinkley test
            ph_result = detector.detect_drift_page_hinkley(prediction)
            if ph_result.detected:
                alert = MonitoringAlert(
                    alert_id=f"concept_drift_{model_name}_ph_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    severity=AlertSeverity.MEDIUM,
                    alert_type="concept_drift",
                    message=f"Concept drift detected in {model_name} using Page-Hinkley test",
                    model_name=model_name,
                    metric_name="prediction_drift",
                    current_value=ph_result.drift_score,
                    threshold=ph_result.threshold,
                    timestamp=datetime.now(),
                    metadata=ph_result.metadata
                )
                alerts.append(alert)
        
        # Send alerts
        for alert in alerts:
            await self.alert_manager.send_alert(alert)
        
        return alerts
    
    async def monitor_batch_predictions(self,
                                       model_name: str,
                                       predictions: np.ndarray,
                                       features: np.ndarray,
                                       actuals: Optional[np.ndarray] = None) -> List[MonitoringAlert]:
        """
        Monitor a batch of predictions.
        
        Args:
            model_name: Name of the model
            predictions: Model predictions
            features: Input features  
            actuals: Actual values (if available)
            
        Returns:
            List of alerts generated
        """
        alerts = []
        
        # Data drift detection
        if model_name in self.data_drift_detectors:
            drift_results = self.data_drift_detectors[model_name].detect_drift(features)
            
            for drift_result in drift_results:
                if drift_result.detected:
                    severity = AlertSeverity.HIGH if drift_result.drift_score > 0.2 else AlertSeverity.MEDIUM
                    
                    alert = MonitoringAlert(
                        alert_id=f"data_drift_{model_name}_{drift_result.feature_name}_{drift_result.method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        severity=severity,
                        alert_type="data_drift",
                        message=f"Data drift detected in feature '{drift_result.feature_name}' for {model_name} using {drift_result.method}",
                        model_name=model_name,
                        metric_name=f"drift_{drift_result.feature_name}",
                        current_value=drift_result.drift_score,
                        threshold=drift_result.threshold,
                        timestamp=datetime.now(),
                        metadata={
                            "feature_name": drift_result.feature_name,
                            "method": drift_result.method,
                            "drift_type": drift_result.drift_type.value,
                            **drift_result.metadata
                        }
                    )
                    alerts.append(alert)
        
        # Batch performance monitoring
        if actuals is not None:
            for pred, actual in zip(predictions, actuals):
                perf_alerts = await self.monitor_prediction(model_name, pred, None, actual)
                alerts.extend(perf_alerts)
        
        # Send alerts
        for alert in alerts:
            await self.alert_manager.send_alert(alert)
        
        return alerts
    
    async def start_continuous_monitoring(self, check_interval: int = 300):
        """
        Start continuous monitoring from database.
        
        Args:
            check_interval: Check interval in seconds
        """
        logger.info("Starting continuous model monitoring...")
        
        if not self.db_pool:
            await self.initialize_db_connection()
        
        last_check = {}
        for model_name in self.model_configs.keys():
            last_check[model_name] = datetime.now() - timedelta(minutes=10)
        
        while True:
            try:
                for model_name in self.model_configs.keys():
                    # Query recent predictions/data for this model
                    async with self.db_pool.acquire() as conn:
                        query = """
                            SELECT timestamp, prediction, actual, features
                            FROM model_predictions 
                            WHERE model_name = $1 AND timestamp > $2
                            ORDER BY timestamp
                            LIMIT 1000
                        """
                        
                        rows = await conn.fetch(query, model_name, last_check[model_name])
                    
                    if rows:
                        # Process monitoring for this model
                        for row in rows:
                            features = np.array(json.loads(row['features'])) if row['features'] else None
                            
                            alerts = await self.monitor_prediction(
                                model_name=model_name,
                                prediction=row['prediction'],
                                features=features,
                                actual=row['actual']
                            )
                        
                        last_check[model_name] = max(row['timestamp'] for row in rows)
                        logger.info(f"Processed {len(rows)} predictions for {model_name}")
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(check_interval * 2)
    
    def create_monitoring_dashboard(self) -> str:
        """
        Create comprehensive monitoring dashboard.
        
        Returns:
            Path to dashboard HTML file
        """
        try:
            # Create subplots
            fig = make_subplots(
                rows=4, cols=2,
                subplot_titles=[
                    "Model Performance Overview",
                    "Alert Summary",
                    "Performance Trends",
                    "Drift Detection Status",
                    "Alert Timeline",
                    "Model Comparison",
                    "System Health",
                    "Recent Alerts"
                ],
                specs=[
                    [{"type": "indicator"}, {"type": "bar"}],
                    [{"type": "scatter"}, {"type": "table"}],
                    [{"type": "scatter"}, {"type": "bar"}], 
                    [{"type": "indicator"}, {"type": "table"}]
                ]
            )
            
            # Model performance indicators
            row = 1
            for i, model_name in enumerate(self.performance_monitors.keys()):
                monitor = self.performance_monitors[model_name]
                current_r2 = monitor.current_metrics.get('r2', 0.0) if monitor.current_metrics else 0.0
                
                fig.add_trace(
                    go.Indicator(
                        mode="gauge+number",
                        value=current_r2,
                        title={'text': f"{model_name} R²"},
                        gauge={
                            'axis': {'range': [None, 1]},
                            'bar': {'color': "green" if current_r2 > 0.8 else "orange" if current_r2 > 0.6 else "red"},
                            'steps': [
                                {'range': [0, 0.6], 'color': "lightgray"},
                                {'range': [0.6, 0.8], 'color': "yellow"},
                                {'range': [0.8, 1], 'color': "lightgreen"}
                            ]
                        }
                    ),
                    row=1, col=1
                )
                break  # Show only first model for demo
            
            # Alert summary
            alert_summary = self.alert_manager.get_alert_summary()
            severity_dist = alert_summary.get('severity_distribution', {})
            
            if severity_dist:
                fig.add_trace(
                    go.Bar(
                        x=list(severity_dist.keys()),
                        y=list(severity_dist.values()),
                        name="Alerts by Severity"
                    ),
                    row=1, col=2
                )
            
            # Update layout
            fig.update_layout(
                title="Model Monitoring Dashboard",
                height=1600,
                showlegend=False
            )
            
            # Save dashboard
            dashboard_dir = os.path.join(settings.MODELS_DIR, "monitoring", "dashboards")
            os.makedirs(dashboard_dir, exist_ok=True)
            
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            dashboard_path = os.path.join(dashboard_dir, f"monitoring_dashboard_{timestamp_str}.html")
            
            fig.write_html(dashboard_path)
            logger.info(f"Monitoring dashboard saved to {dashboard_path}")
            
            return dashboard_path
            
        except Exception as e:
            logger.error(f"Failed to create monitoring dashboard: {e}")
            return ""
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system monitoring status."""
        status = {
            "timestamp": datetime.now().isoformat(),
            "models": {},
            "alert_summary": self.alert_manager.get_alert_summary(),
            "system_health": "healthy"
        }
        
        # Model-specific status
        for model_name in self.model_configs.keys():
            model_status = {"monitoring_active": True}
            
            # Performance monitoring status
            if model_name in self.performance_monitors:
                perf_summary = self.performance_monitors[model_name].get_performance_summary()
                model_status["performance"] = perf_summary
            
            # Drift detection status
            if model_name in self.data_drift_detectors:
                model_status["data_drift_detector"] = {
                    "reference_data_set": self.data_drift_detectors[model_name].reference_data is not None,
                    "feature_count": len(self.data_drift_detectors[model_name].feature_names)
                }
            
            if model_name in self.concept_drift_detectors:
                model_status["concept_drift_detector"] = {"initialized": True}
            
            status["models"][model_name] = model_status
        
        return status


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Model configurations
    model_configs = {
        "lstm": {
            "feature_names": ["delay_minutes", "hour_of_day", "is_weekend", "is_holiday"],
            "performance_window": 1000,
            "degradation_threshold": 0.1,
            "drift_threshold": 0.1
        },
        "xgboost": {
            "feature_names": ["delay_minutes", "hour_of_day", "is_weekend", "is_holiday"],
            "performance_window": 1000,
            "degradation_threshold": 0.15,
            "drift_threshold": 0.12
        }
    }
    
    # Initialize monitoring orchestrator
    monitoring = ModelMonitoringOrchestrator(model_configs)
    
    # Set up alert channels (example)
    monitoring.alert_manager.add_slack_channel("https://hooks.slack.com/your/webhook/url")
    
    # Simulate setting baseline data
    np.random.seed(42)
    baseline_features = np.random.randn(1000, 4)
    baseline_predictions = np.sum(baseline_features[:, :2], axis=1) + np.random.randn(1000) * 0.1
    baseline_actuals = baseline_predictions + np.random.randn(1000) * 0.05
    
    monitoring.set_model_baseline("lstm", baseline_predictions, baseline_actuals, baseline_features)
    
    # Simulate monitoring some predictions
    async def simulate_monitoring():
        for i in range(100):
            # Simulate slight distribution shift
            features = np.random.randn(4) + (0.1 if i > 50 else 0.0)  # Drift after 50 samples
            prediction = np.sum(features[:2]) + np.random.randn() * 0.1
            actual = prediction + np.random.randn() * 0.05
            
            alerts = await monitoring.monitor_prediction("lstm", prediction, features, actual)
            
            if alerts:
                print(f"Alerts generated at step {i}: {len(alerts)}")
                for alert in alerts:
                    print(f"  - {alert.alert_type}: {alert.message}")
    
    # Run simulation
    asyncio.run(simulate_monitoring())
    
    # Create dashboard
    dashboard_path = monitoring.create_monitoring_dashboard()
    print(f"Dashboard created: {dashboard_path}")
    
    # Get system status
    status = monitoring.get_system_status()
    print("\nSystem Status:")
    print(json.dumps(status, indent=2, default=str))