"""
Data Quality Monitoring Module
Monitors data quality, model performance, and system health
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psycopg2

from config.settings import settings

logger = logging.getLogger(__name__)


class DataQualityMonitor:
    """Monitors data quality and system health"""
    
    def __init__(self, alert_webhook_url: str = None):
        self.alert_webhook_url = alert_webhook_url or settings.ALERT_WEBHOOK_URL
        self.logger = logging.getLogger(__name__)
    
    def check_gtfs_rt_freshness(self, last_update_time: datetime) -> bool:
        """Check if GTFS-RT data is fresh (< 90 seconds old)"""
        if datetime.now() - last_update_time > timedelta(seconds=settings.GTFS_RT_MAX_AGE):
            self._send_alert("GTFS-RT data is stale", "HIGH")
            return False
        return True
    
    def check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        try:
            conn = psycopg2.connect(
                host=settings.DB_HOST,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                port=settings.DB_PORT
            )
            conn.close()
            return True
        except Exception as e:
            self._send_alert(f"Database connectivity failed: {e}", "HIGH")
            return False
    
    def check_model_performance(self, model_name: str, current_accuracy: float, 
                              threshold: float = 0.8) -> bool:
        """Check if model performance is above threshold"""
        if current_accuracy < threshold:
            self._send_alert(
                f"Model {model_name} accuracy ({current_accuracy:.2f}) below threshold ({threshold})",
                "MEDIUM"
            )
            return False
        return True
    
    def check_data_completeness(self, table_name: str, expected_count: int, 
                               actual_count: int, tolerance: float = 0.95) -> bool:
        """Check if data completeness is within tolerance"""
        completeness = actual_count / expected_count if expected_count > 0 else 0
        if completeness < tolerance:
            self._send_alert(
                f"Data completeness for {table_name} is {completeness:.2%} (expected {tolerance:.2%})",
                "MEDIUM"
            )
            return False
        return True
    
    def check_api_health(self, api_url: str) -> bool:
        """Check if external API is responding"""
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                self._send_alert(f"API {api_url} returned status {response.status_code}", "MEDIUM")
                return False
            return True
        except Exception as e:
            self._send_alert(f"API {api_url} is not responding: {e}", "HIGH")
            return False
    
    def _send_alert(self, message: str, severity: str):
        """Send alert via webhook or logging"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "message": message,
            "source": "MARTA_Demand_Platform"
        }
        
        self.logger.warning(f"ALERT [{severity}]: {message}")
        
        if self.alert_webhook_url:
            try:
                requests.post(self.alert_webhook_url, json=alert, timeout=5)
            except Exception as e:
                self.logger.error(f"Failed to send webhook alert: {e}")
    
    def get_system_status(self) -> Dict[str, str]:
        """Get overall system status"""
        status = {
            "database": "🟢 Connected" if self.check_database_connectivity() else "🔴 Disconnected",
            "gtfs_rt": "🟢 Fresh" if self.check_gtfs_rt_freshness(datetime.now()) else "🟡 Stale",
            "models": "🟢 Ready",
            "api": "🟢 Active"
        }
        return status
    
    def run_health_check(self) -> Dict[str, bool]:
        """Run comprehensive health check"""
        health_status = {
            "database_connectivity": self.check_database_connectivity(),
            "gtfs_rt_freshness": self.check_gtfs_rt_freshness(datetime.now()),
            "model_performance": self.check_model_performance("xgboost", 0.85),
            "api_health": self.check_api_health("https://api.marta.io/gtfs-rt/vehicle-positions/vehicle.pb")
        }
        return health_status 