"""
MARTA Platform - Application Performance Monitoring (APM)
Integrates with Prometheus, Grafana, New Relic, DataDog, and custom monitoring
"""
import os
import time
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from collections import defaultdict, deque
import logging

# Prometheus metrics
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    CollectorRegistry, generate_latest,
    start_http_server, push_to_gateway
)

# OpenTelemetry for distributed tracing
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Centralized metrics collection"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        
        # Request metrics
        self.request_count = Counter(
            'marta_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'marta_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        self.request_size = Summary(
            'marta_request_size_bytes',
            'Request size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.response_size = Summary(
            'marta_response_size_bytes',
            'Response size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # System metrics
        self.cpu_usage = Gauge(
            'marta_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'marta_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'marta_active_connections',
            'Number of active connections',
            ['type'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_query_count = Counter(
            'marta_db_queries_total',
            'Total number of database queries',
            ['query_type', 'table'],
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'marta_db_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type', 'table'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=self.registry
        )
        
        self.db_connection_pool = Gauge(
            'marta_db_connection_pool',
            'Database connection pool status',
            ['status'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'marta_cache_hits_total',
            'Total number of cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            'marta_cache_misses_total',
            'Total number of cache misses',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_size = Gauge(
            'marta_cache_size_bytes',
            'Cache size in bytes',
            ['cache_type'],
            registry=self.registry
        )
        
        # Business metrics
        self.prediction_requests = Counter(
            'marta_prediction_requests_total',
            'Total number of prediction requests',
            ['model_type'],
            registry=self.registry
        )
        
        self.optimization_runs = Counter(
            'marta_optimization_runs_total',
            'Total number of optimization runs',
            ['optimization_type'],
            registry=self.registry
        )
        
        self.active_users = Gauge(
            'marta_active_users',
            'Number of active users',
            ['platform'],
            registry=self.registry
        )
        
        # Error metrics
        self.error_count = Counter(
            'marta_errors_total',
            'Total number of errors',
            ['error_type', 'component'],
            registry=self.registry
        )
        
        # Custom metrics storage
        self.custom_metrics = {}
        
    def record_request(self, method: str, endpoint: str, status: int, duration: float, 
                      request_size: int = 0, response_size: int = 0):
        """Record HTTP request metrics"""
        self.request_count.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        
        if request_size:
            self.request_size.labels(method=method, endpoint=endpoint).observe(request_size)
        if response_size:
            self.response_size.labels(method=method, endpoint=endpoint).observe(response_size)
            
    def record_db_query(self, query_type: str, table: str, duration: float):
        """Record database query metrics"""
        self.db_query_count.labels(query_type=query_type, table=table).inc()
        self.db_query_duration.labels(query_type=query_type, table=table).observe(duration)
        
    def record_cache_access(self, cache_type: str, hit: bool):
        """Record cache access metrics"""
        if hit:
            self.cache_hits.labels(cache_type=cache_type).inc()
        else:
            self.cache_misses.labels(cache_type=cache_type).inc()
            
    def record_error(self, error_type: str, component: str):
        """Record error metrics"""
        self.error_count.labels(error_type=error_type, component=component).inc()
        
    def update_system_metrics(self, cpu_percent: float, memory_bytes: Dict[str, int], 
                            connections: Dict[str, int]):
        """Update system metrics"""
        self.cpu_usage.set(cpu_percent)
        
        for mem_type, value in memory_bytes.items():
            self.memory_usage.labels(type=mem_type).set(value)
            
        for conn_type, count in connections.items():
            self.active_connections.labels(type=conn_type).set(count)
            
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format"""
        return generate_latest(self.registry)


class APMIntegration:
    """Integration with various APM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers = []
        
        # Initialize providers based on config
        if config.get('prometheus_enabled'):
            self._init_prometheus()
            
        if config.get('opentelemetry_enabled'):
            self._init_opentelemetry()
            
        if config.get('newrelic_enabled'):
            self._init_newrelic()
            
        if config.get('datadog_enabled'):
            self._init_datadog()
            
    def _init_prometheus(self):
        """Initialize Prometheus monitoring"""
        try:
            # Start metrics server
            port = self.config.get('prometheus_port', 9090)
            start_http_server(port)
            logger.info(f"Prometheus metrics server started on port {port}")
            
            # Setup push gateway if configured
            if self.config.get('pushgateway_url'):
                self.pushgateway_url = self.config['pushgateway_url']
                self._start_push_thread()
                
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus: {e}")
            
    def _init_opentelemetry(self):
        """Initialize OpenTelemetry tracing and metrics"""
        try:
            # Setup tracing
            trace.set_tracer_provider(TracerProvider())
            tracer_provider = trace.get_tracer_provider()
            
            # Add OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config.get('otlp_endpoint', 'localhost:4317'),
                insecure=True
            )
            
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            # Setup metrics
            metric_reader = PeriodicExportingMetricReader(
                exporter=OTLPMetricExporter(
                    endpoint=self.config.get('otlp_endpoint', 'localhost:4317'),
                    insecure=True
                ),
                export_interval_millis=10000
            )
            
            metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
            
            # Auto-instrument libraries
            FastAPIInstrumentor().instrument()
            RequestsInstrumentor().instrument()
            Psycopg2Instrumentor().instrument()
            RedisInstrumentor().instrument()
            
            logger.info("OpenTelemetry instrumentation initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            
    def _init_newrelic(self):
        """Initialize New Relic monitoring"""
        try:
            import newrelic.agent
            
            config_file = self.config.get('newrelic_config', 'newrelic.ini')
            environment = self.config.get('environment', 'production')
            
            newrelic.agent.initialize(config_file, environment)
            logger.info("New Relic agent initialized")
            
        except ImportError:
            logger.warning("New Relic package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize New Relic: {e}")
            
    def _init_datadog(self):
        """Initialize DataDog monitoring"""
        try:
            from ddtrace import tracer, patch_all
            
            tracer.configure(
                hostname=self.config.get('datadog_host', 'localhost'),
                port=self.config.get('datadog_port', 8126),
                service_name='marta-platform',
                env=self.config.get('environment', 'production')
            )
            
            # Auto-patch libraries
            patch_all()
            
            logger.info("DataDog APM initialized")
            
        except ImportError:
            logger.warning("DataDog package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize DataDog: {e}")
            
    def _start_push_thread(self):
        """Start thread to push metrics to Prometheus pushgateway"""
        def push_metrics():
            while True:
                try:
                    push_to_gateway(
                        self.pushgateway_url,
                        job='marta-platform',
                        registry=self.metrics_collector.registry
                    )
                except Exception as e:
                    logger.error(f"Failed to push metrics: {e}")
                time.sleep(10)
                
        thread = threading.Thread(target=push_metrics, daemon=True)
        thread.start()


class DistributedTracing:
    """Distributed tracing implementation"""
    
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)
        
    def trace(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a trace span"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.tracer.start_as_current_span(name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, str(value))
                            
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(trace.Status(trace.StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(
                            trace.Status(trace.StatusCode.ERROR, str(e))
                        )
                        span.record_exception(e)
                        raise
                        
            return wrapper
        return decorator
        
    def trace_async(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a trace span for async functions"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with self.tracer.start_as_current_span(name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, str(value))
                            
                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(trace.Status(trace.StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(
                            trace.Status(trace.StatusCode.ERROR, str(e))
                        )
                        span.record_exception(e)
                        raise
                        
            return wrapper
        return decorator


class HealthChecker:
    """Application health checking"""
    
    def __init__(self):
        self.checks = {}
        self.last_check_results = {}
        
    def register_check(self, name: str, check_func: Callable, critical: bool = False):
        """Register a health check"""
        self.checks[name] = {
            'func': check_func,
            'critical': critical
        }
        
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        for name, check in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check['func']):
                    result = await check['func']()
                else:
                    result = check['func']()
                    
                results['checks'][name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'critical': check['critical']
                }
                
                if not result and check['critical']:
                    results['status'] = 'unhealthy'
                    
            except Exception as e:
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(e),
                    'critical': check['critical']
                }
                
                if check['critical']:
                    results['status'] = 'unhealthy'
                    
        self.last_check_results = results
        return results
        
    def get_status(self) -> Dict[str, Any]:
        """Get last health check results"""
        return self.last_check_results


class AlertManager:
    """Alert management and notification"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_rules = []
        self.alert_history = deque(maxlen=1000)
        
    def add_rule(self, name: str, condition: Callable, 
                 severity: str = 'warning', cooldown: int = 300):
        """Add an alert rule"""
        self.alert_rules.append({
            'name': name,
            'condition': condition,
            'severity': severity,
            'cooldown': cooldown,
            'last_fired': None
        })
        
    async def check_alerts(self, metrics: Dict[str, Any]):
        """Check alert conditions"""
        alerts_fired = []
        
        for rule in self.alert_rules:
            # Check cooldown
            if rule['last_fired']:
                elapsed = (datetime.now() - rule['last_fired']).total_seconds()
                if elapsed < rule['cooldown']:
                    continue
                    
            # Check condition
            try:
                if rule['condition'](metrics):
                    alert = {
                        'name': rule['name'],
                        'severity': rule['severity'],
                        'timestamp': datetime.now(),
                        'metrics': metrics
                    }
                    
                    alerts_fired.append(alert)
                    self.alert_history.append(alert)
                    rule['last_fired'] = datetime.now()
                    
                    await self._send_alert(alert)
                    
            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {e}")
                
        return alerts_fired
        
    async def _send_alert(self, alert: Dict[str, Any]):
        """Send alert notification"""
        # Send to various channels based on config
        if self.config.get('slack_webhook'):
            await self._send_slack_alert(alert)
            
        if self.config.get('email_enabled'):
            await self._send_email_alert(alert)
            
        if self.config.get('pagerduty_key'):
            await self._send_pagerduty_alert(alert)
            
    async def _send_slack_alert(self, alert: Dict[str, Any]):
        """Send alert to Slack"""
        import aiohttp
        
        webhook_url = self.config['slack_webhook']
        
        color = {
            'critical': 'danger',
            'warning': 'warning',
            'info': 'good'
        }.get(alert['severity'], 'warning')
        
        payload = {
            'attachments': [{
                'color': color,
                'title': f"Alert: {alert['name']}",
                'text': f"Severity: {alert['severity']}",
                'timestamp': alert['timestamp'].timestamp(),
                'fields': [
                    {
                        'title': key,
                        'value': str(value),
                        'short': True
                    }
                    for key, value in alert.get('metrics', {}).items()
                ]
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json=payload)
            
    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Send alert via email"""
        # Implement email sending
        pass
        
    async def _send_pagerduty_alert(self, alert: Dict[str, Any]):
        """Send alert to PagerDuty"""
        # Implement PagerDuty integration
        pass


# Global instances
_metrics_collector: Optional[MetricsCollector] = None
_apm_integration: Optional[APMIntegration] = None
_health_checker: Optional[HealthChecker] = None
_alert_manager: Optional[AlertManager] = None
_distributed_tracing: Optional[DistributedTracing] = None


def initialize_monitoring(config: Dict[str, Any]):
    """Initialize all monitoring components"""
    global _metrics_collector, _apm_integration, _health_checker, _alert_manager, _distributed_tracing
    
    _metrics_collector = MetricsCollector()
    _apm_integration = APMIntegration(config)
    _health_checker = HealthChecker()
    _alert_manager = AlertManager(config)
    _distributed_tracing = DistributedTracing()
    
    # Register default health checks
    _health_checker.register_check('database', check_database_health, critical=True)
    _health_checker.register_check('redis', check_redis_health, critical=False)
    _health_checker.register_check('disk_space', check_disk_space, critical=False)
    
    # Add default alert rules
    _alert_manager.add_rule(
        'high_cpu',
        lambda m: m.get('cpu_percent', 0) > 80,
        severity='warning'
    )
    
    _alert_manager.add_rule(
        'high_memory',
        lambda m: m.get('memory_percent', 0) > 90,
        severity='critical'
    )
    
    _alert_manager.add_rule(
        'high_error_rate',
        lambda m: m.get('error_rate', 0) > 0.05,
        severity='warning'
    )
    
    logger.info("Monitoring initialized successfully")


# Health check functions
def check_database_health() -> bool:
    """Check database health"""
    try:
        from src.database.connection_pool import health_check
        result = health_check()
        return result['status'] == 'healthy'
    except:
        return False
        
def check_redis_health() -> bool:
    """Check Redis health"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379)
        return client.ping()
    except:
        return False
        
def check_disk_space() -> bool:
    """Check disk space"""
    import shutil
    stat = shutil.disk_usage('/')
    percent_used = (stat.used / stat.total) * 100
    return percent_used < 90


# Convenience functions
def get_metrics_collector() -> MetricsCollector:
    """Get metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

def get_health_checker() -> HealthChecker:
    """Get health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

def get_distributed_tracing() -> DistributedTracing:
    """Get distributed tracing instance"""
    global _distributed_tracing
    if _distributed_tracing is None:
        _distributed_tracing = DistributedTracing()
    return _distributed_tracing