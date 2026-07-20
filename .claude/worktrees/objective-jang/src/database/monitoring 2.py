"""
MARTA Platform - Database Monitoring and Query Performance Tracking
Comprehensive monitoring solution for database performance, query optimization, and health checks
"""
import time
import json
import asyncio
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import statistics

import psutil
import structlog
import pandas as pd
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from .connection_pool import get_db_pool, execute_query, execute_to_dataframe
from .redis_cache import get_cache_manager
from config.settings import settings

# Configure logging
logger = structlog.get_logger(__name__)

@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_hash: str
    query_pattern: str
    execution_count: int
    total_time: float
    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    p95_time: float
    p99_time: float
    error_count: int
    last_executed: datetime
    tables_accessed: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DatabaseHealth:
    """Database health metrics"""
    timestamp: datetime
    connection_count: int
    active_queries: int
    blocked_queries: int
    database_size_mb: float
    buffer_hit_ratio: float
    transaction_rate: float
    deadlock_count: int
    slow_query_count: int
    cache_hit_ratio: float
    disk_usage_percent: float
    cpu_usage_percent: float
    memory_usage_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

class QueryPerformanceTracker:
    """Tracks query performance metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._query_metrics: Dict[str, Dict[str, Any]] = {}
        self._query_history: deque = deque(maxlen=max_history)
        self._lock = threading.Lock()
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.query_duration = Histogram(
            'marta_query_duration_seconds',
            'Time spent executing database queries',
            ['query_type', 'table'],
            registry=self.registry
        )
        self.query_counter = Counter(
            'marta_queries_total',
            'Total number of database queries',
            ['query_type', 'status'],
            registry=self.registry
        )
        self.connection_gauge = Gauge(
            'marta_db_connections',
            'Number of database connections',
            ['type'],
            registry=self.registry
        )
    
    def record_query(self, query: str, execution_time: float, 
                    error: Optional[str] = None, tables: Optional[List[str]] = None):
        """Record a query execution"""
        query_hash = self._hash_query(query)
        query_pattern = self._extract_query_pattern(query)
        
        with self._lock:
            if query_hash not in self._query_metrics:
                self._query_metrics[query_hash] = {
                    'query_pattern': query_pattern,
                    'execution_times': [],
                    'error_count': 0,
                    'tables_accessed': tables or [],
                    'first_seen': datetime.now(),
                    'last_executed': datetime.now()
                }
            
            metrics = self._query_metrics[query_hash]
            metrics['execution_times'].append(execution_time)
            metrics['last_executed'] = datetime.now()
            
            if error:
                metrics['error_count'] += 1
                self.query_counter.labels(
                    query_type=query_pattern.split()[0].upper(),
                    status='error'
                ).inc()
            else:
                self.query_counter.labels(
                    query_type=query_pattern.split()[0].upper(),
                    status='success'
                ).inc()
            
            # Update Prometheus metrics
            primary_table = tables[0] if tables else 'unknown'
            self.query_duration.labels(
                query_type=query_pattern.split()[0].upper(),
                table=primary_table
            ).observe(execution_time)
            
            # Maintain history size
            if len(metrics['execution_times']) > self.max_history:
                metrics['execution_times'] = metrics['execution_times'][-self.max_history:]
        
        # Add to history
        self._query_history.append({
            'timestamp': datetime.now(),
            'query_hash': query_hash,
            'execution_time': execution_time,
            'error': error,
            'tables': tables or []
        })
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query"""
        import hashlib
        # Normalize query for consistent hashing
        normalized = ' '.join(query.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def _extract_query_pattern(self, query: str) -> str:
        """Extract query pattern (e.g., SELECT FROM table_name)"""
        words = query.strip().split()
        if not words:
            return "UNKNOWN"
        
        query_type = words[0].upper()
        
        # Extract table names for common query types
        if query_type == 'SELECT':
            try:
                from_idx = [i for i, word in enumerate(words) if word.upper() == 'FROM']
                if from_idx:
                    table_name = words[from_idx[0] + 1].split()[0]
                    return f"SELECT FROM {table_name}"
            except (IndexError, AttributeError):
                pass
            return "SELECT"
        
        elif query_type in ['INSERT', 'UPDATE', 'DELETE']:
            try:
                if query_type == 'INSERT':
                    into_idx = [i for i, word in enumerate(words) if word.upper() == 'INTO']
                    if into_idx:
                        table_name = words[into_idx[0] + 1].split()[0]
                        return f"INSERT INTO {table_name}"
                elif query_type == 'UPDATE':
                    table_name = words[1].split()[0]
                    return f"UPDATE {table_name}"
                elif query_type == 'DELETE':
                    from_idx = [i for i, word in enumerate(words) if word.upper() == 'FROM']
                    if from_idx:
                        table_name = words[from_idx[0] + 1].split()[0]
                        return f"DELETE FROM {table_name}"
            except (IndexError, AttributeError):
                pass
        
        return query_type
    
    def get_query_metrics(self, limit: int = 20) -> List[QueryMetrics]:
        """Get top queries by various metrics"""
        with self._lock:
            metrics_list = []
            
            for query_hash, data in self._query_metrics.items():
                times = data['execution_times']
                if not times:
                    continue
                
                metrics = QueryMetrics(
                    query_hash=query_hash,
                    query_pattern=data['query_pattern'],
                    execution_count=len(times),
                    total_time=sum(times),
                    min_time=min(times),
                    max_time=max(times),
                    avg_time=statistics.mean(times),
                    median_time=statistics.median(times),
                    p95_time=self._percentile(times, 95),
                    p99_time=self._percentile(times, 99),
                    error_count=data['error_count'],
                    last_executed=data['last_executed'],
                    tables_accessed=data['tables_accessed']
                )
                metrics_list.append(metrics)
            
            # Sort by total time and return top queries
            return sorted(metrics_list, key=lambda x: x.total_time, reverse=True)[:limit]
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        if f + 1 < len(sorted_data):
            return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
        else:
            return sorted_data[f]
    
    def get_slow_queries(self, threshold_seconds: float = 1.0) -> List[QueryMetrics]:
        """Get queries slower than threshold"""
        all_metrics = self.get_query_metrics(limit=1000)
        return [m for m in all_metrics if m.avg_time > threshold_seconds]
    
    def get_frequent_queries(self, min_count: int = 10) -> List[QueryMetrics]:
        """Get most frequently executed queries"""
        all_metrics = self.get_query_metrics(limit=1000)
        return [m for m in all_metrics if m.execution_count >= min_count]
    
    def get_error_queries(self) -> List[QueryMetrics]:
        """Get queries with errors"""
        all_metrics = self.get_query_metrics(limit=1000)
        return [m for m in all_metrics if m.error_count > 0]
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self._query_metrics.clear()
            self._query_history.clear()
        logger.info("Query performance metrics reset")

class DatabaseHealthMonitor:
    """Monitors overall database health and performance"""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self._health_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self._is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.db_connections = Gauge(
            'marta_db_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        self.db_size = Gauge(
            'marta_db_size_bytes',
            'Database size in bytes',
            registry=self.registry
        )
        self.buffer_hit_ratio = Gauge(
            'marta_db_buffer_hit_ratio',
            'Database buffer hit ratio',
            registry=self.registry
        )
        self.query_rate = Gauge(
            'marta_db_queries_per_second',
            'Database queries per second',
            registry=self.registry
        )
    
    def start_monitoring(self):
        """Start background monitoring"""
        if not self._is_monitoring:
            self._is_monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            logger.info("Database health monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._is_monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Database health monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._is_monitoring:
            try:
                health = self.check_health()
                self._health_history.append(health)
                
                # Update Prometheus metrics
                self.db_connections.set(health.connection_count)
                self.db_size.set(health.database_size_mb * 1024 * 1024)
                self.buffer_hit_ratio.set(health.buffer_hit_ratio)
                self.query_rate.set(health.transaction_rate)
                
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error("Error in health monitoring loop", error=str(e))
                time.sleep(self.check_interval)
    
    def check_health(self) -> DatabaseHealth:
        """Perform comprehensive health check"""
        try:
            # Database metrics
            db_stats = self._get_database_stats()
            
            # System metrics
            system_stats = self._get_system_stats()
            
            # Cache metrics
            cache_stats = self._get_cache_stats()
            
            return DatabaseHealth(
                timestamp=datetime.now(),
                connection_count=db_stats.get('connection_count', 0),
                active_queries=db_stats.get('active_queries', 0),
                blocked_queries=db_stats.get('blocked_queries', 0),
                database_size_mb=db_stats.get('database_size_mb', 0),
                buffer_hit_ratio=db_stats.get('buffer_hit_ratio', 0),
                transaction_rate=db_stats.get('transaction_rate', 0),
                deadlock_count=db_stats.get('deadlock_count', 0),
                slow_query_count=db_stats.get('slow_query_count', 0),
                cache_hit_ratio=cache_stats.get('hit_rate', 0),
                disk_usage_percent=system_stats.get('disk_usage_percent', 0),
                cpu_usage_percent=system_stats.get('cpu_usage_percent', 0),
                memory_usage_percent=system_stats.get('memory_usage_percent', 0)
            )
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return DatabaseHealth(
                timestamp=datetime.now(),
                connection_count=0, active_queries=0, blocked_queries=0,
                database_size_mb=0, buffer_hit_ratio=0, transaction_rate=0,
                deadlock_count=0, slow_query_count=0, cache_hit_ratio=0,
                disk_usage_percent=0, cpu_usage_percent=0, memory_usage_percent=0
            )
    
    def _get_database_stats(self) -> Dict[str, Any]:
        """Get database-specific statistics"""
        try:
            # Connection and activity stats
            stats_query = """
            SELECT 
                (SELECT count(*) FROM pg_stat_activity) as connection_count,
                (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_queries,
                (SELECT count(*) FROM pg_stat_activity WHERE wait_event_type IS NOT NULL) as blocked_queries,
                (SELECT pg_database_size(current_database()) / (1024*1024))::numeric as database_size_mb,
                (SELECT 100.0 * blks_hit / (blks_hit + blks_read) 
                 FROM pg_stat_database WHERE datname = current_database()) as buffer_hit_ratio,
                (SELECT xact_commit + xact_rollback 
                 FROM pg_stat_database WHERE datname = current_database()) as total_transactions
            """
            
            result = execute_query(stats_query, fetch='one')
            if result:
                return {
                    'connection_count': result.connection_count or 0,
                    'active_queries': result.active_queries or 0,
                    'blocked_queries': result.blocked_queries or 0,
                    'database_size_mb': float(result.database_size_mb or 0),
                    'buffer_hit_ratio': float(result.buffer_hit_ratio or 0),
                    'transaction_rate': float(result.total_transactions or 0),
                    'deadlock_count': 0,  # Will be enhanced with pg_stat_database
                    'slow_query_count': 0  # Will be enhanced with pg_stat_statements
                }
            return {}
        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))
            return {}
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system resource statistics"""
        try:
            return {
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'cpu_usage_percent': psutil.cpu_percent(interval=1),
                'memory_usage_percent': psutil.virtual_memory().percent
            }
        except Exception as e:
            logger.error("Failed to get system stats", error=str(e))
            return {'disk_usage_percent': 0, 'cpu_usage_percent': 0, 'memory_usage_percent': 0}
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            cache_manager = get_cache_manager()
            cache_info = cache_manager.get_cache_info()
            return {
                'hit_rate': cache_info.get('hit_rate', 0),
                'used_memory': cache_info.get('used_memory', '0'),
                'connected_clients': cache_info.get('connected_clients', 0)
            }
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {'hit_rate': 0, 'used_memory': '0', 'connected_clients': 0}
    
    def get_health_history(self, hours: int = 24) -> List[DatabaseHealth]:
        """Get health history for specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [h for h in self._health_history if h.timestamp >= cutoff_time]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary statistics"""
        if not self._health_history:
            return {'status': 'no_data'}
        
        recent_health = list(self._health_history)[-60:]  # Last hour
        
        return {
            'status': 'healthy' if recent_health[-1].buffer_hit_ratio > 80 else 'warning',
            'avg_buffer_hit_ratio': statistics.mean([h.buffer_hit_ratio for h in recent_health]),
            'avg_connection_count': statistics.mean([h.connection_count for h in recent_health]),
            'max_active_queries': max([h.active_queries for h in recent_health]),
            'avg_database_size_mb': statistics.mean([h.database_size_mb for h in recent_health]),
            'trend_connection_count': self._calculate_trend([h.connection_count for h in recent_health]),
            'trend_buffer_hit_ratio': self._calculate_trend([h.buffer_hit_ratio for h in recent_health]),
            'last_updated': recent_health[-1].timestamp.isoformat()
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 2:
            return 'stable'
        
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        if statistics.mean(second_half) > statistics.mean(first_half) * 1.1:
            return 'increasing'
        elif statistics.mean(second_half) < statistics.mean(first_half) * 0.9:
            return 'decreasing'
        else:
            return 'stable'

class DatabaseMonitoringManager:
    """Main monitoring manager that coordinates all monitoring components"""
    
    def __init__(self):
        self.query_tracker = QueryPerformanceTracker()
        self.health_monitor = DatabaseHealthMonitor()
        self._setup_sqlalchemy_listeners()
    
    def _setup_sqlalchemy_listeners(self):
        """Setup SQLAlchemy event listeners for automatic query tracking"""
        db_pool = get_db_pool()
        
        if db_pool._sync_engine:
            @event.listens_for(db_pool._sync_engine, "before_cursor_execute")
            def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                context._query_start_time = time.time()
                context._query_statement = statement
            
            @event.listens_for(db_pool._sync_engine, "after_cursor_execute")
            def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                if hasattr(context, '_query_start_time'):
                    execution_time = time.time() - context._query_start_time
                    self.query_tracker.record_query(
                        query=statement,
                        execution_time=execution_time,
                        tables=self._extract_table_names(statement)
                    )
    
    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from SQL query"""
        # Simple regex-based extraction - can be enhanced
        import re
        
        # Common patterns for table names
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'DELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        ]
        
        tables = set()
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            tables.update(matches)
        
        return list(tables)
    
    def start_monitoring(self):
        """Start all monitoring components"""
        self.health_monitor.start_monitoring()
        logger.info("Database monitoring started")
    
    def stop_monitoring(self):
        """Stop all monitoring components"""
        self.health_monitor.stop_monitoring()
        logger.info("Database monitoring stopped")
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data"""
        return {
            'timestamp': datetime.now().isoformat(),
            'health': self.health_monitor.get_health_summary(),
            'current_health': self.health_monitor.check_health().to_dict(),
            'top_queries': [m.to_dict() for m in self.query_tracker.get_query_metrics(10)],
            'slow_queries': [m.to_dict() for m in self.query_tracker.get_slow_queries(1.0)],
            'error_queries': [m.to_dict() for m in self.query_tracker.get_error_queries()],
            'connection_stats': get_db_pool().get_connection_stats(),
            'cache_stats': get_cache_manager().get_metrics()
        }
    
    def generate_performance_report(self) -> str:
        """Generate a comprehensive performance report"""
        dashboard_data = self.get_monitoring_dashboard()
        
        report = f"""
MARTA Database Performance Report
Generated: {dashboard_data['timestamp']}

=== HEALTH SUMMARY ===
Status: {dashboard_data['health']['status']}
Avg Buffer Hit Ratio: {dashboard_data['health'].get('avg_buffer_hit_ratio', 0):.2f}%
Avg Connections: {dashboard_data['health'].get('avg_connection_count', 0):.0f}
Max Active Queries: {dashboard_data['health'].get('max_active_queries', 0)}
Database Size: {dashboard_data['health'].get('avg_database_size_mb', 0):.2f} MB

=== TOP QUERIES BY TOTAL TIME ===
"""
        
        for i, query in enumerate(dashboard_data['top_queries'][:5], 1):
            report += f"""
{i}. {query['query_pattern']}
   Total Time: {query['total_time']:.2f}s
   Avg Time: {query['avg_time']:.3f}s
   Executions: {query['execution_count']}
   P95 Time: {query['p95_time']:.3f}s
"""
        
        if dashboard_data['slow_queries']:
            report += "\n=== SLOW QUERIES (>1s avg) ==="
            for query in dashboard_data['slow_queries'][:3]:
                report += f"""
- {query['query_pattern']}
  Avg Time: {query['avg_time']:.3f}s
  P95 Time: {query['p95_time']:.3f}s
  Executions: {query['execution_count']}
"""
        
        report += f"""

=== CONNECTION POOL ===
Active Connections: {dashboard_data['connection_stats'].get('active_connections', 0)}
Pool Size: {dashboard_data['connection_stats'].get('pool_size', 0)}
Total Queries: {dashboard_data['connection_stats'].get('query_count', 0)}
Avg Query Time: {dashboard_data['connection_stats'].get('avg_query_time', 0):.3f}s

=== CACHE PERFORMANCE ===
Hit Rate: {dashboard_data['cache_stats'].get('hit_rate', 0):.2f}%
Total Operations: {dashboard_data['cache_stats'].get('total_operations', 0)}
Operations/sec: {dashboard_data['cache_stats'].get('operations_per_second', 0):.2f}
"""
        
        return report

# Global monitoring manager
_monitoring_manager: Optional[DatabaseMonitoringManager] = None

def get_monitoring_manager() -> DatabaseMonitoringManager:
    """Get or create global monitoring manager"""
    global _monitoring_manager
    if _monitoring_manager is None:
        _monitoring_manager = DatabaseMonitoringManager()
    return _monitoring_manager

# Convenience functions
def start_monitoring():
    """Start database monitoring"""
    get_monitoring_manager().start_monitoring()

def stop_monitoring():
    """Stop database monitoring"""
    get_monitoring_manager().stop_monitoring()

def get_monitoring_dashboard() -> Dict[str, Any]:
    """Get monitoring dashboard data"""
    return get_monitoring_manager().get_monitoring_dashboard()

def generate_performance_report() -> str:
    """Generate performance report"""
    return get_monitoring_manager().generate_performance_report()

def record_query_performance(query: str, execution_time: float, 
                           error: Optional[str] = None, tables: Optional[List[str]] = None):
    """Record query performance manually"""
    get_monitoring_manager().query_tracker.record_query(query, execution_time, error, tables)

@contextmanager
def query_performance_context(query: str):
    """Context manager for tracking query performance"""
    start_time = time.time()
    error = None
    try:
        yield
    except Exception as e:
        error = str(e)
        raise
    finally:
        execution_time = time.time() - start_time
        record_query_performance(query, execution_time, error)