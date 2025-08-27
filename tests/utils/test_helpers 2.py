"""
Test helper utilities and common testing functions.
"""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import asyncio
import json


class TestDataBuilder:
    """Builder class for creating test data."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to initial state."""
        self._data = {}
        return self
    
    def with_gtfs_data(self, num_routes: int = 5, num_stops: int = 20) -> 'TestDataBuilder':
        """Add GTFS data to the test dataset."""
        stops = []
        for i in range(num_stops):
            stops.append({
                'stop_id': f'stop_{i+1:03d}',
                'stop_name': f'Test Stop {i+1}',
                'stop_lat': 33.7490 + np.random.uniform(-0.05, 0.05),
                'stop_lon': -84.3880 + np.random.uniform(-0.05, 0.05),
                'location_type': 0,
                'parent_station': ''
            })
        
        routes = []
        for i in range(num_routes):
            routes.append({
                'route_id': f'route_{i+1:03d}',
                'agency_id': 'TEST',
                'route_short_name': f'R{i+1}',
                'route_long_name': f'Test Route {i+1}',
                'route_type': np.random.choice([1, 3]),  # Rail or Bus
                'route_color': f'{np.random.randint(0, 16777215):06X}'
            })
        
        self._data['gtfs_stops'] = pd.DataFrame(stops)
        self._data['gtfs_routes'] = pd.DataFrame(routes)
        return self
    
    def with_ridership_data(self, num_days: int = 30) -> 'TestDataBuilder':
        """Add ridership data to the test dataset."""
        ridership_data = []
        
        for day in range(num_days):
            date = datetime.now().date() - timedelta(days=day)
            
            for hour in range(24):
                for route_num in range(1, 6):  # 5 routes
                    # Realistic ridership patterns
                    base_ridership = 50
                    if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hours
                        ridership = base_ridership * 2
                    elif 22 <= hour or hour <= 5:  # Night
                        ridership = base_ridership * 0.3
                    else:
                        ridership = base_ridership
                    
                    # Weekend adjustment
                    if date.weekday() >= 5:
                        ridership *= 0.7
                    
                    # Add randomness
                    ridership = max(0, int(ridership + np.random.normal(0, ridership * 0.2)))
                    
                    ridership_data.append({
                        'date': date,
                        'hour': hour,
                        'route': f'route_{route_num:03d}',
                        'ridership': ridership,
                        'day_of_week': date.weekday(),
                        'is_weekend': date.weekday() >= 5
                    })
        
        self._data['ridership_data'] = pd.DataFrame(ridership_data)
        return self
    
    def with_weather_data(self, num_days: int = 30) -> 'TestDataBuilder':
        """Add weather data to the test dataset."""
        weather_data = []
        
        for day in range(num_days):
            date = datetime.now().date() - timedelta(days=day)
            
            # Atlanta-like weather patterns
            base_temp = 70  # Fahrenheit
            seasonal_temp = base_temp + np.sin((date.timetuple().tm_yday / 365.0) * 2 * np.pi) * 15
            daily_temp = seasonal_temp + np.random.normal(0, 8)
            
            weather_data.append({
                'date': date,
                'temperature': round(daily_temp, 1),
                'humidity': round(np.random.uniform(40, 90), 1),
                'precipitation': max(0, round(np.random.exponential(0.1), 2)),
                'wind_speed': round(np.random.uniform(0, 20), 1),
                'weather_condition': np.random.choice(['Clear', 'Cloudy', 'Rain', 'Partly Cloudy'])
            })
        
        self._data['weather_data'] = pd.DataFrame(weather_data)
        return self
    
    def with_optimization_results(self, num_results: int = 10) -> 'TestDataBuilder':
        """Add optimization results to the test dataset."""
        optimization_results = []
        
        for i in range(num_results):
            result = {
                'optimization_id': f'opt_{i+1:03d}',
                'timestamp': datetime.now() - timedelta(hours=i),
                'method': np.random.choice(['genetic_algorithm', 'simulated_annealing']),
                'fitness_score': np.random.uniform(0.6, 0.95),
                'execution_time': np.random.uniform(30, 300),
                'parameters': {
                    'population_size': np.random.choice([20, 50, 100]),
                    'generations': np.random.choice([50, 100, 200])
                },
                'solution': {
                    'routes': [
                        {
                            'route_id': f'route_{j+1:03d}',
                            'frequency': np.random.randint(5, 20)
                        }
                        for j in range(np.random.randint(3, 8))
                    ]
                }
            }
            optimization_results.append(result)
        
        self._data['optimization_results'] = optimization_results
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the test dataset."""
        return self._data.copy()


class MockServiceManager:
    """Manager for creating and managing mock services."""
    
    def __init__(self):
        self.active_mocks = {}
        self.patches = {}
    
    def mock_database_service(self, responses: Optional[Dict] = None):
        """Mock database service responses."""
        if responses is None:
            responses = {
                'query_result': [{'id': 1, 'name': 'test'}],
                'insert_result': {'success': True, 'id': 1},
                'update_result': {'success': True, 'affected_rows': 1}
            }
        
        mock_db = Mock()
        mock_db.execute.return_value = responses.get('query_result', [])
        mock_db.insert.return_value = responses.get('insert_result', {'success': True})
        mock_db.update.return_value = responses.get('update_result', {'success': True})
        
        self.active_mocks['database'] = mock_db
        return mock_db
    
    def mock_redis_service(self, cache_data: Optional[Dict] = None):
        """Mock Redis cache service."""
        if cache_data is None:
            cache_data = {}
        
        mock_redis = Mock()
        mock_redis.get.side_effect = lambda key: cache_data.get(key, None)
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.exists.side_effect = lambda key: key in cache_data
        
        self.active_mocks['redis'] = mock_redis
        return mock_redis
    
    def mock_external_api(self, api_name: str, responses: Dict):
        """Mock external API responses."""
        mock_api = Mock()
        
        for method, response in responses.items():
            if hasattr(mock_api, method):
                getattr(mock_api, method).return_value = response
            else:
                setattr(mock_api, method, Mock(return_value=response))
        
        self.active_mocks[api_name] = mock_api
        return mock_api
    
    def start_patches(self, patches: Dict[str, str]):
        """Start patches for specified modules."""
        for name, module_path in patches.items():
            if name in self.active_mocks:
                self.patches[name] = patch(module_path, self.active_mocks[name])
                self.patches[name].start()
    
    def stop_patches(self):
        """Stop all active patches."""
        for patch_obj in self.patches.values():
            patch_obj.stop()
        self.patches.clear()
    
    def reset_mocks(self):
        """Reset all mock objects."""
        for mock_obj in self.active_mocks.values():
            if hasattr(mock_obj, 'reset_mock'):
                mock_obj.reset_mock()


class TestEnvironmentManager:
    """Manager for test environment setup and teardown."""
    
    def __init__(self):
        self.temp_dirs = []
        self.temp_files = []
        self.env_vars = {}
    
    def create_temp_directory(self, prefix: str = "test_") -> str:
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_temp_file(self, content: str = "", suffix: str = ".txt") -> str:
        """Create temporary file with content."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix)
        temp_file.write(content)
        temp_file.close()
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def set_env_var(self, name: str, value: str):
        """Set environment variable for testing."""
        original_value = os.environ.get(name)
        self.env_vars[name] = original_value
        os.environ[name] = value
    
    def create_test_config_file(self, config: Dict[str, Any]) -> str:
        """Create test configuration file."""
        config_content = json.dumps(config, indent=2)
        return self.create_temp_file(config_content, suffix=".json")
    
    def cleanup(self):
        """Clean up test environment."""
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
        # Remove temporary files
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # Restore environment variables
        for name, original_value in self.env_vars.items():
            if original_value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = original_value
        
        # Clear lists
        self.temp_dirs.clear()
        self.temp_files.clear()
        self.env_vars.clear()


class PerformanceProfiler:
    """Utility for performance profiling in tests."""
    
    def __init__(self):
        self.measurements = {}
    
    def time_function(self, func, *args, **kwargs):
        """Time function execution and return result and timing."""
        import time
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        func_name = getattr(func, '__name__', 'anonymous')
        
        if func_name not in self.measurements:
            self.measurements[func_name] = []
        
        self.measurements[func_name].append(execution_time)
        
        return result, execution_time
    
    def memory_usage(self, func, *args, **kwargs):
        """Measure memory usage of function execution."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            result = func(*args, **kwargs)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            return result, memory_increase
        except ImportError:
            # psutil not available, return function result only
            return func(*args, **kwargs), 0
    
    def get_statistics(self, func_name: str) -> Dict[str, float]:
        """Get statistics for function performance."""
        if func_name not in self.measurements:
            return {}
        
        times = self.measurements[func_name]
        return {
            'count': len(times),
            'total': sum(times),
            'average': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'median': sorted(times)[len(times) // 2] if times else 0
        }
    
    def generate_report(self) -> str:
        """Generate performance report."""
        report = ["Performance Report", "=" * 20, ""]
        
        for func_name, times in self.measurements.items():
            stats = self.get_statistics(func_name)
            report.append(f"Function: {func_name}")
            report.append(f"  Executions: {stats['count']}")
            report.append(f"  Average time: {stats['average']:.4f}s")
            report.append(f"  Min time: {stats['min']:.4f}s")
            report.append(f"  Max time: {stats['max']:.4f}s")
            report.append(f"  Total time: {stats['total']:.4f}s")
            report.append("")
        
        return "\n".join(report)


def assert_dataframes_equal(df1: pd.DataFrame, df2: pd.DataFrame, **kwargs):
    """Enhanced dataframe equality assertion with better error messages."""
    try:
        pd.testing.assert_frame_equal(df1, df2, **kwargs)
    except AssertionError as e:
        print(f"\nDataFrame comparison failed:")
        print(f"Left shape: {df1.shape}, Right shape: {df2.shape}")
        print(f"Left columns: {list(df1.columns)}")
        print(f"Right columns: {list(df2.columns)}")
        print(f"Detailed error: {str(e)}")
        raise


def assert_within_tolerance(actual: float, expected: float, tolerance: float = 0.01):
    """Assert that actual value is within tolerance of expected value."""
    diff = abs(actual - expected)
    assert diff <= tolerance, f"Value {actual} not within {tolerance} of {expected} (diff: {diff})"


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to become true with timeout."""
    import time
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    
    return False


async def async_wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Async version of wait_for_condition."""
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
            return True
        await asyncio.sleep(interval)
    
    return False


def generate_test_report(test_results: List[Dict[str, Any]], output_file: str = "test_report.html"):
    """Generate HTML test report."""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MARTA Test Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
            .summary { margin: 20px 0; }
            .test-result { margin: 10px 0; padding: 10px; border-left: 4px solid #ccc; }
            .passed { border-left-color: #28a745; }
            .failed { border-left-color: #dc3545; }
            .skipped { border-left-color: #ffc107; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>MARTA Platform Test Report</h1>
            <p>Generated: {timestamp}</p>
        </div>
        
        <div class="summary">
            <h2>Summary</h2>
            <table>
                <tr><th>Total Tests</th><td>{total_tests}</td></tr>
                <tr><th>Passed</th><td style="color: green;">{passed}</td></tr>
                <tr><th>Failed</th><td style="color: red;">{failed}</td></tr>
                <tr><th>Skipped</th><td style="color: orange;">{skipped}</td></tr>
                <tr><th>Success Rate</th><td>{success_rate:.1f}%</td></tr>
            </table>
        </div>
        
        <div class="results">
            <h2>Test Results</h2>
            {test_details}
        </div>
    </body>
    </html>
    """
    
    # Calculate summary
    total_tests = len(test_results)
    passed = sum(1 for r in test_results if r['status'] == 'passed')
    failed = sum(1 for r in test_results if r['status'] == 'failed')
    skipped = sum(1 for r in test_results if r['status'] == 'skipped')
    success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
    
    # Generate test details
    test_details = []
    for result in test_results:
        status_class = result['status']
        test_details.append(f"""
            <div class="test-result {status_class}">
                <strong>{result['name']}</strong> - {result['status'].upper()}
                <br>Duration: {result.get('duration', 'N/A')}s
                {f'<br>Error: {result["error"]}' if result.get('error') else ''}
            </div>
        """)
    
    # Generate HTML
    html_content = html_template.format(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        total_tests=total_tests,
        passed=passed,
        failed=failed,
        skipped=skipped,
        success_rate=success_rate,
        test_details=''.join(test_details)
    )
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Test report generated: {output_file}")


# Global instances for common use
test_data_builder = TestDataBuilder()
mock_service_manager = MockServiceManager()
test_env_manager = TestEnvironmentManager()
performance_profiler = PerformanceProfiler()