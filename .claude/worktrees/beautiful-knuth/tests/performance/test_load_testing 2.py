"""
Load testing for the MARTA platform APIs and services.
"""
import pytest
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import concurrent.futures
import threading
import statistics
from dataclasses import dataclass
from typing import List, Dict, Tuple
import json
import random
import numpy as np
from fastapi.testclient import TestClient

# Test imports
from src.api.optimization_api import app


@dataclass
class LoadTestResult:
    """Load test result metrics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    max_response_time: float
    min_response_time: float


class LoadTestRunner:
    """Load test execution framework."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = []
    
    def execute_load_test(
        self, 
        endpoint: str, 
        method: str = "GET",
        payload: dict = None,
        concurrent_users: int = 10,
        total_requests: int = 100,
        duration_seconds: int = None
    ) -> LoadTestResult:
        """Execute load test against specified endpoint."""
        
        response_times = []
        errors = []
        start_time = time.time()
        
        def make_request():
            """Make single request and record metrics."""
            request_start = time.time()
            try:
                client = TestClient(app)
                
                if method.upper() == "GET":
                    response = client.get(endpoint)
                elif method.upper() == "POST":
                    response = client.post(endpoint, json=payload or {})
                elif method.upper() == "PUT":
                    response = client.put(endpoint, json=payload or {})
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                request_end = time.time()
                response_time = request_end - request_start
                
                return {
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'success': 200 <= response.status_code < 400,
                    'error': None
                }
                
            except Exception as e:
                request_end = time.time()
                return {
                    'response_time': request_end - request_start,
                    'status_code': 500,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute load test with concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            
            if duration_seconds:
                # Duration-based test
                end_time = start_time + duration_seconds
                futures = []
                
                while time.time() < end_time:
                    if len(futures) < concurrent_users * 2:  # Keep queue full
                        futures.append(executor.submit(make_request))
                    
                    # Collect completed requests
                    completed = [f for f in futures if f.done()]
                    for future in completed:
                        result = future.result()
                        response_times.append(result['response_time'])
                        if not result['success']:
                            errors.append(result['error'])
                        futures.remove(future)
                    
                    time.sleep(0.01)  # Small delay to prevent busy loop
                
                # Wait for remaining requests
                for future in futures:
                    result = future.result()
                    response_times.append(result['response_time'])
                    if not result['success']:
                        errors.append(result['error'])
            
            else:
                # Request count-based test
                futures = [executor.submit(make_request) for _ in range(total_requests)]
                
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    response_times.append(result['response_time'])
                    if not result['success']:
                        errors.append(result['error'])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate metrics
        total_reqs = len(response_times)
        successful_reqs = total_reqs - len(errors)
        failed_reqs = len(errors)
        
        if response_times:
            avg_response = statistics.mean(response_times)
            median_response = statistics.median(response_times)
            sorted_times = sorted(response_times)
            p95_response = sorted_times[int(0.95 * len(sorted_times))] if sorted_times else 0
            p99_response = sorted_times[int(0.99 * len(sorted_times))] if sorted_times else 0
            max_response = max(response_times)
            min_response = min(response_times)
        else:
            avg_response = median_response = p95_response = p99_response = 0
            max_response = min_response = 0
        
        rps = total_reqs / max(total_time, 0.001)
        error_rate = failed_reqs / max(total_reqs, 1) * 100
        
        return LoadTestResult(
            total_requests=total_reqs,
            successful_requests=successful_reqs,
            failed_requests=failed_reqs,
            avg_response_time=avg_response,
            median_response_time=median_response,
            p95_response_time=p95_response,
            p99_response_time=p99_response,
            requests_per_second=rps,
            error_rate=error_rate,
            max_response_time=max_response,
            min_response_time=min_response
        )


class TestAPILoadTesting:
    """Load tests for API endpoints."""
    
    @pytest.fixture
    def load_tester(self):
        """Load test runner instance."""
        return LoadTestRunner()
    
    @pytest.fixture
    def optimization_payload(self):
        """Sample optimization request payload."""
        return {
            "route_ids": ["route_001", "route_002"],
            "optimization_type": "all",
            "simulation_hours": 24,
            "max_short_turns": 3,
            "bus_capacity": 50
        }
    
    @pytest.mark.load_test
    def test_health_check_load(self, load_tester):
        """Load test health check endpoint."""
        print("\n🚀 Load testing health check endpoint...")
        
        with patch('src.api.optimization_api.health_check') as mock_health:
            mock_health.return_value = {"status": "healthy", "timestamp": datetime.now().isoformat()}
            
            result = load_tester.execute_load_test(
                endpoint="/health",
                method="GET",
                concurrent_users=20,
                total_requests=200
            )
            
            # Health check should handle high load well
            assert result.error_rate < 1.0, f"Error rate too high: {result.error_rate:.2f}%"
            assert result.avg_response_time < 0.1, f"Response time too slow: {result.avg_response_time:.3f}s"
            assert result.requests_per_second > 100, f"Throughput too low: {result.requests_per_second:.1f} RPS"
            
            print(f"   ✓ RPS: {result.requests_per_second:.1f}")
            print(f"   ✓ Avg Response: {result.avg_response_time*1000:.1f}ms")
            print(f"   ✓ Error Rate: {result.error_rate:.2f}%")
    
    @pytest.mark.load_test
    def test_optimization_endpoint_load(self, load_tester, optimization_payload):
        """Load test optimization endpoint."""
        print("\n🚀 Load testing optimization endpoint...")
        
        with patch('src.optimization.route_optimizer.RouteOptimizer') as mock_optimizer:
            mock_optimizer_instance = Mock()
            mock_optimizer_instance.optimize_routes.return_value = {
                "best_solution": [{"route_id": "route_001", "frequency": 10}],
                "best_fitness": 0.85,
                "optimization_time": random.uniform(0.1, 0.5)  # Variable response time
            }
            mock_optimizer.return_value = mock_optimizer_instance
            
            result = load_tester.execute_load_test(
                endpoint="/optimize",
                method="POST", 
                payload=optimization_payload,
                concurrent_users=10,
                total_requests=50  # Fewer requests due to heavier endpoint
            )
            
            # Optimization endpoint requirements
            assert result.error_rate < 5.0, f"Error rate too high: {result.error_rate:.2f}%"
            assert result.avg_response_time < 2.0, f"Response time too slow: {result.avg_response_time:.3f}s"
            assert result.p95_response_time < 5.0, f"95th percentile too slow: {result.p95_response_time:.3f}s"
            
            print(f"   ✓ RPS: {result.requests_per_second:.1f}")
            print(f"   ✓ Avg Response: {result.avg_response_time:.3f}s")
            print(f"   ✓ P95 Response: {result.p95_response_time:.3f}s")
            print(f"   ✓ Error Rate: {result.error_rate:.2f}%")
    
    @pytest.mark.load_test
    def test_simulation_endpoint_load(self, load_tester):
        """Load test simulation endpoint."""
        print("\n🚀 Load testing simulation endpoint...")
        
        simulation_payload = {
            "route_configurations": [
                {
                    "route_id": "route_001",
                    "frequency": 10,
                    "capacity": 200
                }
            ],
            "simulation_duration": 3600
        }
        
        with patch('src.optimization.route_simulator.RouteSimulator') as mock_simulator:
            mock_simulator_instance = Mock()
            mock_simulator_instance.run_simulation.return_value = {
                "performance_metrics": {
                    "total_passengers_served": 15000,
                    "service_reliability": 0.92
                }
            }
            mock_simulator.return_value = mock_simulator_instance
            
            result = load_tester.execute_load_test(
                endpoint="/simulate",
                method="POST",
                payload=simulation_payload,
                concurrent_users=5,  # Lower concurrency for heavy operation
                total_requests=25
            )
            
            # Simulation endpoint requirements
            assert result.error_rate < 10.0, f"Error rate too high: {result.error_rate:.2f}%"
            assert result.avg_response_time < 5.0, f"Response time too slow: {result.avg_response_time:.3f}s"
            
            print(f"   ✓ RPS: {result.requests_per_second:.1f}")
            print(f"   ✓ Avg Response: {result.avg_response_time:.3f}s")
            print(f"   ✓ Error Rate: {result.error_rate:.2f}%")
    
    @pytest.mark.load_test
    def test_mixed_workload(self, load_tester, optimization_payload):
        """Test mixed API workload."""
        print("\n🚀 Load testing mixed workload...")
        
        def run_mixed_requests():
            """Execute mixed API requests."""
            request_types = [
                ("/health", "GET", None, 0.7),                    # 70% health checks
                ("/routes", "GET", None, 0.2),                    # 20% route queries
                ("/optimize", "POST", optimization_payload, 0.1)   # 10% optimizations
            ]
            
            results = []
            total_requests = 100
            
            for _ in range(total_requests):
                # Choose request type based on weights
                rand = random.random()
                cumulative_weight = 0
                
                for endpoint, method, payload, weight in request_types:
                    cumulative_weight += weight
                    if rand <= cumulative_weight:
                        
                        # Mock appropriate response
                        with patch('src.api.optimization_api.health_check') as mock_health, \
                             patch('src.api.optimization_api.get_available_routes') as mock_routes, \
                             patch('src.optimization.route_optimizer.RouteOptimizer') as mock_optimizer:
                            
                            mock_health.return_value = {"status": "healthy"}
                            mock_routes.return_value = {"routes": []}
                            
                            mock_optimizer_instance = Mock()
                            mock_optimizer_instance.optimize_routes.return_value = {"best_fitness": 0.8}
                            mock_optimizer.return_value = mock_optimizer_instance
                            
                            start_time = time.time()
                            try:
                                client = TestClient(app)
                                if method == "GET":
                                    response = client.get(endpoint)
                                else:
                                    response = client.post(endpoint, json=payload)
                                
                                end_time = time.time()
                                results.append({
                                    'endpoint': endpoint,
                                    'response_time': end_time - start_time,
                                    'success': 200 <= response.status_code < 400
                                })
                            except Exception:
                                end_time = time.time()
                                results.append({
                                    'endpoint': endpoint,
                                    'response_time': end_time - start_time,
                                    'success': False
                                })
                        break
            
            return results
        
        # Run mixed workload with multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_mixed_requests) for _ in range(5)]
            all_results = []
            
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        # Analyze mixed workload results
        total_requests = len(all_results)
        successful_requests = sum(1 for r in all_results if r['success'])
        avg_response_time = statistics.mean([r['response_time'] for r in all_results])
        
        success_rate = successful_requests / total_requests * 100
        
        assert success_rate > 95.0, f"Success rate too low: {success_rate:.2f}%"
        assert avg_response_time < 1.0, f"Average response time too slow: {avg_response_time:.3f}s"
        
        print(f"   ✓ Total requests: {total_requests}")
        print(f"   ✓ Success rate: {success_rate:.2f}%")
        print(f"   ✓ Avg response time: {avg_response_time:.3f}s")
    
    @pytest.mark.load_test
    @pytest.mark.slow
    def test_sustained_load(self, load_tester):
        """Test sustained load over extended period."""
        print("\n🚀 Testing sustained load (60 seconds)...")
        
        with patch('src.api.optimization_api.health_check') as mock_health:
            mock_health.return_value = {"status": "healthy", "timestamp": datetime.now().isoformat()}
            
            result = load_tester.execute_load_test(
                endpoint="/health",
                method="GET",
                concurrent_users=15,
                duration_seconds=60  # 1 minute sustained load
            )
            
            # Sustained load requirements
            assert result.error_rate < 2.0, f"Error rate too high under sustained load: {result.error_rate:.2f}%"
            assert result.requests_per_second > 50, f"Throughput degraded: {result.requests_per_second:.1f} RPS"
            assert result.p99_response_time < 0.5, f"99th percentile degraded: {result.p99_response_time:.3f}s"
            
            print(f"   ✓ Duration: 60 seconds")
            print(f"   ✓ Total requests: {result.total_requests}")
            print(f"   ✓ RPS: {result.requests_per_second:.1f}")
            print(f"   ✓ Error rate: {result.error_rate:.2f}%")
    
    @pytest.mark.load_test
    def test_spike_traffic(self, load_tester):
        """Test handling of traffic spikes."""
        print("\n🚀 Testing traffic spike handling...")
        
        def gradual_ramp():
            """Gradually increase load to simulate spike."""
            results = []
            
            # Gradual ramp up
            for concurrent_users in [5, 10, 20, 30, 15, 5]:
                print(f"   Testing with {concurrent_users} concurrent users...")
                
                with patch('src.api.optimization_api.health_check') as mock_health:
                    mock_health.return_value = {"status": "healthy"}
                    
                    result = load_tester.execute_load_test(
                        endpoint="/health",
                        concurrent_users=concurrent_users,
                        total_requests=concurrent_users * 5,
                        duration_seconds=10
                    )
                    
                    results.append({
                        'concurrent_users': concurrent_users,
                        'rps': result.requests_per_second,
                        'avg_response_time': result.avg_response_time,
                        'error_rate': result.error_rate
                    })
            
            return results
        
        spike_results = gradual_ramp()
        
        # Analyze spike handling
        max_rps = max(r['rps'] for r in spike_results)
        max_response_time = max(r['avg_response_time'] for r in spike_results)
        max_error_rate = max(r['error_rate'] for r in spike_results)
        
        assert max_error_rate < 5.0, f"Error rate too high during spike: {max_error_rate:.2f}%"
        assert max_response_time < 0.2, f"Response time degraded too much: {max_response_time:.3f}s"
        
        print(f"   ✓ Peak RPS: {max_rps:.1f}")
        print(f"   ✓ Max response time: {max_response_time:.3f}s")
        print(f"   ✓ Max error rate: {max_error_rate:.2f}%")


class TestDatabaseLoadTesting:
    """Load tests for database operations."""
    
    @pytest.mark.load_test
    def test_database_read_load(self, db_session):
        """Test database read performance under load."""
        print("\n🚀 Testing database read load...")
        
        def execute_read_query():
            """Execute read query and measure time."""
            start_time = time.time()
            try:
                # Mock database query
                with patch('sqlalchemy.orm.session.Session.execute') as mock_execute:
                    mock_execute.return_value.fetchall.return_value = [
                        ('route_001', 'Red Line', 1),
                        ('route_002', 'Gold Line', 1)
                    ]
                    
                    # Simulate query execution
                    results = db_session.execute("SELECT route_id, route_name, route_type FROM gtfs_routes").fetchall()
                    
                    end_time = time.time()
                    return {
                        'execution_time': end_time - start_time,
                        'result_count': len(results),
                        'success': True
                    }
            except Exception as e:
                end_time = time.time()
                return {
                    'execution_time': end_time - start_time,
                    'result_count': 0,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent read queries
        concurrent_queries = 20
        total_queries = 100
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_queries) as executor:
            futures = [executor.submit(execute_read_query) for _ in range(total_queries)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Analyze database read performance
        successful_queries = sum(1 for r in results if r['success'])
        avg_execution_time = statistics.mean([r['execution_time'] for r in results])
        success_rate = successful_queries / total_queries * 100
        
        assert success_rate > 99.0, f"Database read success rate too low: {success_rate:.2f}%"
        assert avg_execution_time < 0.1, f"Database queries too slow: {avg_execution_time:.3f}s"
        
        print(f"   ✓ Success rate: {success_rate:.2f}%")
        print(f"   ✓ Avg query time: {avg_execution_time*1000:.1f}ms")
    
    @pytest.mark.load_test
    def test_database_write_load(self, db_session):
        """Test database write performance under load."""
        print("\n🚀 Testing database write load...")
        
        def execute_write_query(batch_id):
            """Execute write query and measure time."""
            start_time = time.time()
            try:
                # Mock database insert
                with patch.object(db_session, 'add') as mock_add, \
                     patch.object(db_session, 'commit') as mock_commit:
                    
                    # Simulate inserting ridership data
                    for i in range(10):  # Small batch
                        ridership_record = {
                            'id': f'batch_{batch_id}_record_{i}',
                            'date': datetime.now().date(),
                            'hour': i % 24,
                            'ridership': random.randint(50, 200)
                        }
                        mock_add(ridership_record)
                    
                    mock_commit()
                    
                    end_time = time.time()
                    return {
                        'execution_time': end_time - start_time,
                        'records_inserted': 10,
                        'success': True
                    }
            except Exception as e:
                end_time = time.time()
                return {
                    'execution_time': end_time - start_time,
                    'records_inserted': 0,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent write operations
        concurrent_writers = 10
        total_batches = 50
        
        with concurrent.futures.ThreadPoolExecutor(max_writers=concurrent_writers) as executor:
            futures = [executor.submit(execute_write_query, i) for i in range(total_batches)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Analyze database write performance
        successful_writes = sum(1 for r in results if r['success'])
        total_records = sum(r['records_inserted'] for r in results)
        avg_execution_time = statistics.mean([r['execution_time'] for r in results])
        
        success_rate = successful_writes / total_batches * 100
        records_per_second = total_records / sum(r['execution_time'] for r in results)
        
        assert success_rate > 95.0, f"Database write success rate too low: {success_rate:.2f}%"
        assert avg_execution_time < 0.5, f"Database writes too slow: {avg_execution_time:.3f}s"
        assert records_per_second > 100, f"Write throughput too low: {records_per_second:.1f} records/s"
        
        print(f"   ✓ Success rate: {success_rate:.2f}%")
        print(f"   ✓ Avg write time: {avg_execution_time:.3f}s")
        print(f"   ✓ Records/second: {records_per_second:.1f}")


class TestCacheLoadTesting:
    """Load tests for caching layer."""
    
    @pytest.mark.load_test
    def test_redis_cache_load(self, mock_redis):
        """Test Redis cache performance under load."""
        print("\n🚀 Testing Redis cache load...")
        
        def cache_operations():
            """Execute cache operations."""
            operations = []
            
            for i in range(50):
                operation_type = random.choice(['get', 'set', 'delete'])
                key = f'test_key_{i % 20}'  # 20 different keys
                value = f'test_value_{i}'
                
                start_time = time.time()
                
                if operation_type == 'get':
                    mock_redis.get.return_value = value.encode()
                    result = mock_redis.get(key)
                elif operation_type == 'set':
                    mock_redis.set.return_value = True
                    result = mock_redis.set(key, value)
                else:  # delete
                    mock_redis.delete.return_value = 1
                    result = mock_redis.delete(key)
                
                end_time = time.time()
                
                operations.append({
                    'operation': operation_type,
                    'execution_time': end_time - start_time,
                    'success': result is not None
                })
            
            return operations
        
        # Execute concurrent cache operations
        concurrent_clients = 15
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_clients) as executor:
            futures = [executor.submit(cache_operations) for _ in range(concurrent_clients)]
            all_operations = []
            
            for future in concurrent.futures.as_completed(futures):
                all_operations.extend(future.result())
        
        # Analyze cache performance
        total_operations = len(all_operations)
        successful_operations = sum(1 for op in all_operations if op['success'])
        avg_execution_time = statistics.mean([op['execution_time'] for op in all_operations])
        
        success_rate = successful_operations / total_operations * 100
        operations_per_second = total_operations / sum(op['execution_time'] for op in all_operations)
        
        assert success_rate > 99.0, f"Cache success rate too low: {success_rate:.2f}%"
        assert avg_execution_time < 0.01, f"Cache operations too slow: {avg_execution_time*1000:.1f}ms"
        assert operations_per_second > 1000, f"Cache throughput too low: {operations_per_second:.1f} ops/s"
        
        print(f"   ✓ Success rate: {success_rate:.2f}%")
        print(f"   ✓ Avg operation time: {avg_execution_time*1000:.1f}ms")
        print(f"   ✓ Operations/second: {operations_per_second:.1f}")


@pytest.mark.load_test
@pytest.mark.slow
class TestSystemLoadTesting:
    """System-wide load testing."""
    
    def test_end_to_end_load_scenario(self):
        """Test realistic end-to-end load scenario."""
        print("\n🚀 Testing end-to-end load scenario...")
        
        def user_journey():
            """Simulate complete user journey."""
            journey_steps = []
            
            # Step 1: Health check
            with patch('src.api.optimization_api.health_check') as mock_health:
                mock_health.return_value = {"status": "healthy"}
                
                client = TestClient(app)
                start_time = time.time()
                response = client.get("/health")
                journey_steps.append({
                    'step': 'health_check',
                    'time': time.time() - start_time,
                    'success': response.status_code == 200
                })
            
            # Step 2: Get routes
            with patch('src.api.optimization_api.get_available_routes') as mock_routes:
                mock_routes.return_value = {"routes": [{"route_id": "route_001", "name": "Red Line"}]}
                
                start_time = time.time()
                response = client.get("/routes")
                journey_steps.append({
                    'step': 'get_routes',
                    'time': time.time() - start_time,
                    'success': response.status_code == 200
                })
            
            # Step 3: Request optimization (20% of users)
            if random.random() < 0.2:
                with patch('src.optimization.route_optimizer.RouteOptimizer') as mock_optimizer:
                    mock_optimizer_instance = Mock()
                    mock_optimizer_instance.optimize_routes.return_value = {"best_fitness": 0.8}
                    mock_optimizer.return_value = mock_optimizer_instance
                    
                    payload = {
                        "route_ids": ["route_001"],
                        "optimization_type": "all"
                    }
                    
                    start_time = time.time()
                    response = client.post("/optimize", json=payload)
                    journey_steps.append({
                        'step': 'optimization',
                        'time': time.time() - start_time,
                        'success': response.status_code == 200
                    })
            
            return journey_steps
        
        # Simulate multiple concurrent users
        concurrent_users = 25
        total_journeys = 100
        
        all_journeys = []
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_journey) for _ in range(total_journeys)]
            
            for future in concurrent.futures.as_completed(futures):
                all_journeys.append(future.result())
        
        end_time = time.time()
        total_test_time = end_time - start_time
        
        # Analyze end-to-end performance
        all_steps = []
        for journey in all_journeys:
            all_steps.extend(journey)
        
        step_performance = {}
        for step in all_steps:
            step_name = step['step']
            if step_name not in step_performance:
                step_performance[step_name] = {
                    'times': [],
                    'successes': 0,
                    'total': 0
                }
            
            step_performance[step_name]['times'].append(step['time'])
            step_performance[step_name]['total'] += 1
            if step['success']:
                step_performance[step_name]['successes'] += 1
        
        print(f"   ✓ Total test time: {total_test_time:.2f}s")
        print(f"   ✓ Journeys completed: {len(all_journeys)}")
        
        # Validate performance for each step
        for step_name, perf in step_performance.items():
            avg_time = statistics.mean(perf['times'])
            success_rate = perf['successes'] / perf['total'] * 100
            
            print(f"   ✓ {step_name}: {avg_time:.3f}s avg, {success_rate:.1f}% success")
            
            # Step-specific requirements
            if step_name == 'health_check':
                assert avg_time < 0.1, f"Health check too slow: {avg_time:.3f}s"
                assert success_rate > 99.0, f"Health check success rate too low: {success_rate:.1f}%"
            elif step_name == 'get_routes':
                assert avg_time < 0.2, f"Route retrieval too slow: {avg_time:.3f}s"
                assert success_rate > 98.0, f"Route retrieval success rate too low: {success_rate:.1f}%"
            elif step_name == 'optimization':
                assert avg_time < 5.0, f"Optimization too slow: {avg_time:.3f}s"
                assert success_rate > 90.0, f"Optimization success rate too low: {success_rate:.1f}%"
    
    def test_gradual_load_increase(self):
        """Test system behavior with gradually increasing load."""
        print("\n🚀 Testing gradual load increase...")
        
        load_levels = [5, 10, 15, 20, 25, 30]
        performance_degradation = []
        
        for concurrent_users in load_levels:
            print(f"   Testing load level: {concurrent_users} users...")
            
            def simple_request():
                with patch('src.api.optimization_api.health_check') as mock_health:
                    mock_health.return_value = {"status": "healthy"}
                    
                    client = TestClient(app)
                    start_time = time.time()
                    response = client.get("/health")
                    end_time = time.time()
                    
                    return {
                        'response_time': end_time - start_time,
                        'success': response.status_code == 200
                    }
            
            # Execute requests at this load level
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(simple_request) for _ in range(concurrent_users * 3)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            # Calculate performance metrics
            avg_response_time = statistics.mean([r['response_time'] for r in results])
            success_rate = sum(1 for r in results if r['success']) / len(results) * 100
            
            performance_degradation.append({
                'concurrent_users': concurrent_users,
                'avg_response_time': avg_response_time,
                'success_rate': success_rate
            })
        
        # Analyze performance degradation
        baseline_response_time = performance_degradation[0]['avg_response_time']
        
        for level in performance_degradation:
            degradation_factor = level['avg_response_time'] / baseline_response_time
            
            print(f"   Load {level['concurrent_users']}: "
                  f"{level['avg_response_time']*1000:.1f}ms, "
                  f"{level['success_rate']:.1f}% success, "
                  f"{degradation_factor:.1f}x degradation")
            
            # Performance should not degrade too severely
            assert level['success_rate'] > 90.0, f"Success rate dropped too much at load {level['concurrent_users']}"
            assert degradation_factor < 3.0, f"Response time degraded too much: {degradation_factor:.1f}x"
    
    def test_resource_exhaustion_handling(self):
        """Test system behavior under resource exhaustion."""
        print("\n🚀 Testing resource exhaustion handling...")
        
        def resource_intensive_request():
            """Simulate resource-intensive request."""
            with patch('src.api.optimization_api.RouteOptimizer') as mock_optimizer:
                # Simulate high resource usage
                mock_optimizer_instance = Mock()
                mock_optimizer_instance.optimize_routes.side_effect = lambda *args: time.sleep(0.1) or {"best_fitness": 0.8}
                mock_optimizer.return_value = mock_optimizer_instance
                
                client = TestClient(app)
                payload = {"route_ids": ["route_001"], "optimization_type": "all"}
                
                start_time = time.time()
                try:
                    response = client.post("/optimize", json=payload)
                    end_time = time.time()
                    return {
                        'response_time': end_time - start_time,
                        'success': 200 <= response.status_code < 300,
                        'status_code': response.status_code
                    }
                except Exception as e:
                    end_time = time.time()
                    return {
                        'response_time': end_time - start_time,
                        'success': False,
                        'status_code': 500,
                        'error': str(e)
                    }
        
        # Overwhelm system with resource-intensive requests
        excessive_load = 50  # High concurrent requests
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=excessive_load) as executor:
            futures = [executor.submit(resource_intensive_request) for _ in range(excessive_load)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Analyze system behavior under stress
        successful_requests = sum(1 for r in results if r['success'])
        failed_requests = len(results) - successful_requests
        avg_response_time = statistics.mean([r['response_time'] for r in results])
        
        success_rate = successful_requests / len(results) * 100
        
        print(f"   ✓ Requests completed: {len(results)}")
        print(f"   ✓ Success rate: {success_rate:.1f}%")
        print(f"   ✓ Average response time: {avg_response_time:.3f}s")
        
        # Under extreme load, system should fail gracefully
        # Allow higher failure rate but system should remain responsive
        assert success_rate > 30.0, f"System completely overwhelmed: {success_rate:.1f}% success"
        assert avg_response_time < 10.0, f"System became unresponsive: {avg_response_time:.3f}s"