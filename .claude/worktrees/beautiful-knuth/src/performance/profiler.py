"""
MARTA Platform - Advanced Performance Profiler
Comprehensive profiling with CPU, memory, I/O, and database analysis
"""
import os
import sys
import time
import tracemalloc
import psutil
import cProfile
import pstats
import io
import json
import asyncio
import functools
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from contextlib import contextmanager
import threading
from collections import defaultdict, deque
import logging
import pandas as pd
import numpy as np

# Memory profiling
import pympler.tracker
from memory_profiler import profile as memory_profile
from line_profiler import LineProfiler

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
from pyflame import FlameGraph

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """Advanced performance profiler with real-time monitoring"""
    
    def __init__(self, sample_interval: float = 0.1):
        self.sample_interval = sample_interval
        self.is_profiling = False
        self.profile_data = defaultdict(list)
        self.memory_tracker = pympler.tracker.SummaryTracker()
        self.line_profiler = LineProfiler()
        
        # Metrics storage
        self.metrics = {
            'cpu': deque(maxlen=1000),
            'memory': deque(maxlen=1000),
            'io': deque(maxlen=1000),
            'network': deque(maxlen=1000),
            'database': deque(maxlen=1000),
            'requests': deque(maxlen=1000),
            'cache_hits': deque(maxlen=1000)
        }
        
        # Initialize system monitoring
        self.process = psutil.Process()
        self.start_time = time.time()
        
        # Database query tracking
        self.query_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0,
            'max_time': 0,
            'min_time': float('inf')
        })
        
        # API endpoint tracking
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0,
            'p50': 0,
            'p95': 0,
            'p99': 0,
            'response_times': deque(maxlen=1000)
        })
        
    def start_profiling(self):
        """Start continuous profiling"""
        self.is_profiling = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        tracemalloc.start()
        logger.info("Performance profiling started")
        
    def stop_profiling(self):
        """Stop profiling and generate report"""
        self.is_profiling = False
        tracemalloc.stop()
        if hasattr(self, 'monitoring_thread'):
            self.monitoring_thread.join(timeout=1)
        logger.info("Performance profiling stopped")
        return self.generate_report()
        
    def _monitor_system(self):
        """Continuous system monitoring thread"""
        while self.is_profiling:
            try:
                timestamp = datetime.now()
                
                # CPU metrics
                cpu_percent = self.process.cpu_percent(interval=None)
                cpu_times = self.process.cpu_times()
                
                # Memory metrics
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()
                
                # I/O metrics
                io_counters = self.process.io_counters()
                
                # Network metrics (system-wide)
                net_io = psutil.net_io_counters()
                
                # Store metrics
                self.metrics['cpu'].append({
                    'timestamp': timestamp,
                    'percent': cpu_percent,
                    'user_time': cpu_times.user,
                    'system_time': cpu_times.system
                })
                
                self.metrics['memory'].append({
                    'timestamp': timestamp,
                    'rss': memory_info.rss,
                    'vms': memory_info.vms,
                    'percent': memory_percent,
                    'available': psutil.virtual_memory().available
                })
                
                self.metrics['io'].append({
                    'timestamp': timestamp,
                    'read_count': io_counters.read_count,
                    'write_count': io_counters.write_count,
                    'read_bytes': io_counters.read_bytes,
                    'write_bytes': io_counters.write_bytes
                })
                
                self.metrics['network'].append({
                    'timestamp': timestamp,
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                })
                
                time.sleep(self.sample_interval)
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                
    @contextmanager
    def profile_function(self, name: str):
        """Context manager for profiling specific functions"""
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss
        
        try:
            yield
        finally:
            elapsed_time = time.perf_counter() - start_time
            memory_delta = self.process.memory_info().rss - start_memory
            
            self.profile_data[name].append({
                'timestamp': datetime.now(),
                'elapsed_time': elapsed_time,
                'memory_delta': memory_delta
            })
            
    def profile_database_query(self, query: str, execution_time: float):
        """Track database query performance"""
        query_key = self._normalize_query(query)
        stats = self.query_stats[query_key]
        
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['max_time'] = max(stats['max_time'], execution_time)
        stats['min_time'] = min(stats['min_time'], execution_time)
        
        self.metrics['database'].append({
            'timestamp': datetime.now(),
            'query': query_key,
            'execution_time': execution_time
        })
        
    def profile_api_endpoint(self, endpoint: str, method: str, response_time: float, status_code: int):
        """Track API endpoint performance"""
        endpoint_key = f"{method} {endpoint}"
        stats = self.endpoint_stats[endpoint_key]
        
        stats['count'] += 1
        stats['total_time'] += response_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['response_times'].append(response_time)
        
        # Calculate percentiles
        if len(stats['response_times']) > 0:
            times = sorted(stats['response_times'])
            stats['p50'] = np.percentile(times, 50)
            stats['p95'] = np.percentile(times, 95)
            stats['p99'] = np.percentile(times, 99)
        
        self.metrics['requests'].append({
            'timestamp': datetime.now(),
            'endpoint': endpoint_key,
            'response_time': response_time,
            'status_code': status_code
        })
        
    def track_cache_hit(self, cache_name: str, hit: bool):
        """Track cache hit rate"""
        self.metrics['cache_hits'].append({
            'timestamp': datetime.now(),
            'cache_name': cache_name,
            'hit': hit
        })
        
    def _normalize_query(self, query: str) -> str:
        """Normalize SQL query for grouping similar queries"""
        # Remove specific values to group similar queries
        import re
        normalized = re.sub(r'\b\d+\b', '?', query)  # Replace numbers
        normalized = re.sub(r"'[^']*'", '?', normalized)  # Replace string literals
        normalized = ' '.join(normalized.split())  # Normalize whitespace
        return normalized[:200]  # Truncate for display
        
    def analyze_memory_leaks(self):
        """Analyze potential memory leaks"""
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        memory_leaks = []
        for stat in top_stats[:20]:
            memory_leaks.append({
                'file': stat.traceback.format()[0],
                'size': stat.size,
                'count': stat.count,
                'average': stat.size / stat.count if stat.count > 0 else 0
            })
            
        return memory_leaks
        
    def analyze_bottlenecks(self) -> Dict[str, Any]:
        """Identify performance bottlenecks"""
        bottlenecks = {
            'cpu_intensive': [],
            'memory_intensive': [],
            'io_intensive': [],
            'slow_queries': [],
            'slow_endpoints': []
        }
        
        # Analyze CPU bottlenecks
        if self.metrics['cpu']:
            cpu_data = pd.DataFrame(self.metrics['cpu'])
            high_cpu = cpu_data[cpu_data['percent'] > 80]
            if not high_cpu.empty:
                bottlenecks['cpu_intensive'] = high_cpu.to_dict('records')
        
        # Analyze memory bottlenecks
        if self.metrics['memory']:
            memory_data = pd.DataFrame(self.metrics['memory'])
            high_memory = memory_data[memory_data['percent'] > 80]
            if not high_memory.empty:
                bottlenecks['memory_intensive'] = high_memory.to_dict('records')
        
        # Analyze slow queries
        for query, stats in self.query_stats.items():
            if stats['avg_time'] > 1.0:  # Queries taking more than 1 second
                bottlenecks['slow_queries'].append({
                    'query': query,
                    'avg_time': stats['avg_time'],
                    'count': stats['count'],
                    'total_time': stats['total_time']
                })
        
        # Analyze slow endpoints
        for endpoint, stats in self.endpoint_stats.items():
            if stats['p95'] > 2.0:  # 95th percentile > 2 seconds
                bottlenecks['slow_endpoints'].append({
                    'endpoint': endpoint,
                    'avg_time': stats['avg_time'],
                    'p95': stats['p95'],
                    'p99': stats['p99'],
                    'count': stats['count']
                })
        
        return bottlenecks
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        runtime = time.time() - self.start_time
        
        # Calculate cache hit rates
        cache_hit_rate = {}
        if self.metrics['cache_hits']:
            cache_df = pd.DataFrame(self.metrics['cache_hits'])
            for cache_name in cache_df['cache_name'].unique():
                cache_data = cache_df[cache_df['cache_name'] == cache_name]
                hit_rate = cache_data['hit'].mean() * 100
                cache_hit_rate[cache_name] = hit_rate
        
        # Generate report
        report = {
            'summary': {
                'runtime_seconds': runtime,
                'total_requests': sum(s['count'] for s in self.endpoint_stats.values()),
                'total_queries': sum(s['count'] for s in self.query_stats.values()),
                'avg_cpu_percent': np.mean([m['percent'] for m in self.metrics['cpu']]) if self.metrics['cpu'] else 0,
                'avg_memory_mb': np.mean([m['rss'] / 1024 / 1024 for m in self.metrics['memory']]) if self.metrics['memory'] else 0,
                'cache_hit_rates': cache_hit_rate
            },
            'bottlenecks': self.analyze_bottlenecks(),
            'memory_leaks': self.analyze_memory_leaks(),
            'database_stats': dict(self.query_stats),
            'endpoint_stats': dict(self.endpoint_stats),
            'recommendations': self.generate_recommendations()
        }
        
        return report
        
    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Analyze CPU usage
        if self.metrics['cpu']:
            avg_cpu = np.mean([m['percent'] for m in self.metrics['cpu']])
            if avg_cpu > 70:
                recommendations.append({
                    'category': 'CPU',
                    'severity': 'high',
                    'issue': f'High CPU usage detected (avg: {avg_cpu:.1f}%)',
                    'recommendation': 'Consider implementing worker pools, async processing, or optimizing CPU-intensive algorithms'
                })
        
        # Analyze memory usage
        if self.metrics['memory']:
            memory_data = pd.DataFrame(self.metrics['memory'])
            memory_growth = memory_data['rss'].iloc[-1] - memory_data['rss'].iloc[0]
            if memory_growth > 100 * 1024 * 1024:  # 100MB growth
                recommendations.append({
                    'category': 'Memory',
                    'severity': 'medium',
                    'issue': f'Memory growth detected ({memory_growth / 1024 / 1024:.1f}MB)',
                    'recommendation': 'Check for memory leaks, implement object pooling, or optimize data structures'
                })
        
        # Analyze slow queries
        slow_queries = [q for q, s in self.query_stats.items() if s['avg_time'] > 1.0]
        if slow_queries:
            recommendations.append({
                'category': 'Database',
                'severity': 'high',
                'issue': f'{len(slow_queries)} slow queries detected',
                'recommendation': 'Add indexes, optimize query structure, or implement query caching',
                'details': slow_queries[:5]  # Top 5 slow queries
            })
        
        # Analyze cache hit rates
        if self.metrics['cache_hits']:
            cache_df = pd.DataFrame(self.metrics['cache_hits'])
            for cache_name in cache_df['cache_name'].unique():
                cache_data = cache_df[cache_df['cache_name'] == cache_name]
                hit_rate = cache_data['hit'].mean() * 100
                if hit_rate < 70:
                    recommendations.append({
                        'category': 'Cache',
                        'severity': 'medium',
                        'issue': f'Low cache hit rate for {cache_name} ({hit_rate:.1f}%)',
                        'recommendation': 'Review cache key strategy, TTL settings, or cache warming procedures'
                    })
        
        # Analyze endpoint performance
        slow_endpoints = [(e, s) for e, s in self.endpoint_stats.items() if s['p95'] > 2.0]
        if slow_endpoints:
            recommendations.append({
                'category': 'API',
                'severity': 'high',
                'issue': f'{len(slow_endpoints)} slow endpoints detected',
                'recommendation': 'Implement pagination, add caching layers, or optimize backend processing',
                'details': [(e, f"p95: {s["p95"]:.2f}s") for e, s in slow_endpoints[:5]]
            })
        
        return recommendations
        
    def export_flamegraph(self, output_file: str = 'flamegraph.svg'):
        """Export CPU flamegraph for visualization"""
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Run sample workload
        time.sleep(0.1)
        
        profiler.disable()
        
        # Generate flamegraph
        stats = pstats.Stats(profiler)
        FlameGraph(stats).render(output_file)
        logger.info(f"Flamegraph exported to {output_file}")
        
    def export_metrics(self, output_dir: str = 'performance_metrics'):
        """Export detailed metrics for analysis"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Export each metric type
        for metric_type, data in self.metrics.items():
            if data:
                df = pd.DataFrame(list(data))
                df.to_csv(f"{output_dir}/{metric_type}_metrics.csv", index=False)
        
        # Export summary report
        report = self.generate_report()
        with open(f"{output_dir}/performance_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {output_dir}")


# Decorator for automatic profiling
def profile_performance(profiler: Optional[PerformanceProfiler] = None):
    """Decorator for automatic performance profiling"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if profiler:
                with profiler.profile_function(func.__name__):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Async version of the decorator
def profile_async_performance(profiler: Optional[PerformanceProfiler] = None):
    """Decorator for async function performance profiling"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if profiler:
                with profiler.profile_function(func.__name__):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# Global profiler instance
_global_profiler: Optional[PerformanceProfiler] = None

def get_profiler() -> PerformanceProfiler:
    """Get or create global profiler instance"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler

def start_profiling():
    """Start global profiling"""
    get_profiler().start_profiling()

def stop_profiling() -> Dict[str, Any]:
    """Stop profiling and get report"""
    return get_profiler().stop_profiling()

def get_performance_report() -> Dict[str, Any]:
    """Get current performance report"""
    return get_profiler().generate_report()