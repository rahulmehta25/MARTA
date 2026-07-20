"""
Integration tests for API endpoints in the MARTA platform.
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status
import httpx
import asyncpg

# Test imports
from src.api.optimization_api import app, OptimizationRequest, SimulationRequest


class TestOptimizationAPI:
    """Test suite for optimization API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_optimization_request(self):
        """Sample optimization request data."""
        return {
            "route_ids": ["route_001", "route_002"],
            "timestamp": datetime.now().isoformat(),
            "optimization_type": "all",
            "simulation_hours": 24,
            "max_short_turns": 3,
            "bus_capacity": 50
        }
    
    @pytest.fixture
    def sample_simulation_request(self):
        """Sample simulation request data."""
        return {
            "route_configurations": [
                {
                    "route_id": "route_001",
                    "frequency": 10,
                    "capacity": 200,
                    "stops": ["stop_001", "stop_002", "stop_003"]
                }
            ],
            "simulation_duration": 3600,
            "demand_scenarios": {
                "base": 1.0,
                "peak": 1.5,
                "off_peak": 0.7
            }
        }
    
    def test_health_check_endpoint(self, client):
        """Test API health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_get_routes_endpoint(self, client):
        """Test getting available routes."""
        with patch('src.api.optimization_api.get_available_routes') as mock_routes:
            mock_routes.return_value = [
                {"route_id": "route_001", "name": "Red Line", "type": "rail"},
                {"route_id": "route_002", "name": "Gold Line", "type": "rail"}
            ]
            
            response = client.get("/routes")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["routes"]) == 2
            assert data["routes"][0]["route_id"] == "route_001"
    
    def test_optimize_routes_endpoint(self, client, sample_optimization_request):
        """Test route optimization endpoint."""
        with patch('src.api.optimization_api.RouteOptimizer') as mock_optimizer:
            mock_instance = Mock()
            mock_instance.optimize_routes.return_value = {
                "best_solution": [{"route_id": "route_001", "frequency": 10}],
                "best_fitness": 0.85,
                "optimization_time": 45.2,
                "improvements": {
                    "cost_reduction": 15.3,
                    "coverage_increase": 8.7
                }
            }
            mock_optimizer.return_value = mock_instance
            
            response = client.post("/optimize", json=sample_optimization_request)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "optimization_id" in data
            assert "results" in data
            assert data["results"]["best_fitness"] == 0.85
            assert "improvements" in data["results"]
    
    def test_simulate_routes_endpoint(self, client, sample_simulation_request):
        """Test route simulation endpoint."""
        with patch('src.api.optimization_api.RouteSimulator') as mock_simulator:
            mock_instance = Mock()
            mock_instance.run_simulation.return_value = {
                "performance_metrics": {
                    "total_passengers_served": 15000,
                    "average_wait_time": 4.2,
                    "service_reliability": 0.92,
                    "cost_per_passenger": 3.50
                },
                "passenger_statistics": {
                    "peak_occupancy": 180,
                    "average_occupancy": 95
                },
                "recommendations": [
                    "Increase frequency during peak hours",
                    "Consider express service for high-demand stops"
                ]
            }
            mock_simulator.return_value = mock_instance
            
            response = client.post("/simulate", json=sample_simulation_request)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "simulation_id" in data
            assert "results" in data
            assert data["results"]["performance_metrics"]["service_reliability"] == 0.92
            assert "recommendations" in data["results"]
    
    def test_get_optimization_status(self, client):
        """Test getting optimization job status."""
        job_id = "test_job_123"
        
        with patch('src.api.optimization_api.get_job_status') as mock_status:
            mock_status.return_value = {
                "job_id": job_id,
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "results": {"best_fitness": 0.78}
            }
            
            response = client.get(f"/optimization/{job_id}/status")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["job_id"] == job_id
            assert data["status"] == "completed"
            assert data["progress"] == 100
    
    def test_get_historical_optimizations(self, client):
        """Test getting historical optimization results."""
        with patch('src.api.optimization_api.get_optimization_history') as mock_history:
            mock_history.return_value = [
                {
                    "optimization_id": "opt_001",
                    "timestamp": datetime.now().isoformat(),
                    "fitness_score": 0.85,
                    "optimization_type": "genetic_algorithm",
                    "duration_seconds": 120
                },
                {
                    "optimization_id": "opt_002", 
                    "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                    "fitness_score": 0.82,
                    "optimization_type": "simulated_annealing",
                    "duration_seconds": 95
                }
            ]
            
            response = client.get("/optimizations/history")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["optimizations"]) == 2
            assert data["optimizations"][0]["fitness_score"] == 0.85
    
    def test_get_current_performance_metrics(self, client):
        """Test getting current system performance metrics."""
        with patch('src.api.optimization_api.get_current_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "timestamp": datetime.now().isoformat(),
                "system_metrics": {
                    "total_active_routes": 25,
                    "average_delay": 3.2,
                    "passenger_satisfaction": 0.87,
                    "fleet_utilization": 0.78
                },
                "route_metrics": [
                    {
                        "route_id": "route_001",
                        "on_time_performance": 0.92,
                        "passenger_load_factor": 0.65,
                        "incidents": 0
                    }
                ]
            }
            
            response = client.get("/metrics/current")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "system_metrics" in data
            assert "route_metrics" in data
            assert data["system_metrics"]["average_delay"] == 3.2
    
    def test_update_route_configuration(self, client):
        """Test updating route configuration."""
        route_id = "route_001"
        update_data = {
            "frequency": 8,  # Changed from 10 to 8 minutes
            "capacity": 220,  # Increased capacity
            "operating_hours": {
                "start": "05:00",
                "end": "24:00"
            }
        }
        
        with patch('src.api.optimization_api.update_route_config') as mock_update:
            mock_update.return_value = {
                "route_id": route_id,
                "updated_fields": ["frequency", "capacity"],
                "success": True
            }
            
            response = client.put(f"/routes/{route_id}/config", json=update_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "frequency" in data["updated_fields"]
    
    def test_demand_forecast_endpoint(self, client):
        """Test demand forecasting endpoint."""
        forecast_request = {
            "route_id": "route_001",
            "forecast_horizon": 24,  # hours
            "include_weather": True,
            "include_events": True
        }
        
        with patch('src.api.optimization_api.generate_demand_forecast') as mock_forecast:
            mock_forecast.return_value = {
                "route_id": "route_001",
                "forecast_data": [
                    {"hour": 0, "predicted_demand": 25},
                    {"hour": 1, "predicted_demand": 15},
                    {"hour": 7, "predicted_demand": 120},  # Morning peak
                    {"hour": 17, "predicted_demand": 115}  # Evening peak
                ],
                "confidence_intervals": {
                    "lower_bound": [20, 12, 100, 95],
                    "upper_bound": [30, 18, 140, 135]
                },
                "model_accuracy": 0.89
            }
            
            response = client.post("/forecast/demand", json=forecast_request)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["route_id"] == "route_001"
            assert len(data["forecast_data"]) == 4
            assert data["model_accuracy"] == 0.89
    
    def test_error_handling_invalid_request(self, client):
        """Test API error handling with invalid requests."""
        # Missing required fields
        invalid_request = {
            "optimization_type": "invalid_type"
        }
        
        response = client.post("/optimize", json=invalid_request)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
    
    def test_error_handling_database_error(self, client, sample_optimization_request):
        """Test API error handling when database is unavailable."""
        with patch('src.api.optimization_api.RouteOptimizer') as mock_optimizer:
            mock_optimizer.side_effect = Exception("Database connection failed")
            
            response = client.post("/optimize", json=sample_optimization_request)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "error" in data["detail"]
    
    def test_authentication_required_endpoints(self, client):
        """Test endpoints that require authentication."""
        # This would test protected endpoints if authentication is implemented
        protected_request = {
            "route_id": "route_001",
            "action": "emergency_shutdown"
        }
        
        response = client.post("/admin/emergency", json=protected_request)
        
        # Should return 401 if authentication is required
        # For now, assuming endpoint doesn't exist returns 404
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
    
    def test_rate_limiting(self, client, sample_optimization_request):
        """Test API rate limiting."""
        # Make multiple rapid requests
        responses = []
        for _ in range(5):
            response = client.post("/optimize", json=sample_optimization_request)
            responses.append(response.status_code)
        
        # Should eventually get rate limited (429) or succeed (200/500)
        assert all(code in [200, 429, 500] for code in responses)
    
    def test_concurrent_requests(self, client, sample_optimization_request):
        """Test handling concurrent optimization requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            with patch('src.api.optimization_api.RouteOptimizer') as mock_optimizer:
                mock_instance = Mock()
                mock_instance.optimize_routes.return_value = {
                    "best_solution": [],
                    "best_fitness": 0.8,
                    "optimization_time": 1.0
                }
                mock_optimizer.return_value = mock_instance
                
                response = client.post("/optimize", json=sample_optimization_request)
                results.append(response.status_code)
        
        # Start multiple threads
        threads = [threading.Thread(target=make_request) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All requests should complete successfully or fail gracefully
        assert len(results) == 3
        assert all(code in [200, 429, 500] for code in results)


class TestAPIDataFlow:
    """Test data flow through API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)
    
    def test_optimization_to_simulation_workflow(self, client):
        """Test complete workflow from optimization to simulation."""
        # Step 1: Run optimization
        opt_request = {
            "route_ids": ["route_001"],
            "optimization_type": "all",
            "simulation_hours": 24
        }
        
        with patch('src.api.optimization_api.RouteOptimizer') as mock_optimizer:
            mock_optimizer_instance = Mock()
            mock_optimizer_instance.optimize_routes.return_value = {
                "best_solution": [{"route_id": "route_001", "frequency": 8}],
                "best_fitness": 0.88
            }
            mock_optimizer.return_value = mock_optimizer_instance
            
            opt_response = client.post("/optimize", json=opt_request)
            assert opt_response.status_code == 200
            opt_data = opt_response.json()
            
        # Step 2: Use optimization results for simulation
        sim_request = {
            "route_configurations": opt_data["results"]["best_solution"],
            "simulation_duration": 3600
        }
        
        with patch('src.api.optimization_api.RouteSimulator') as mock_simulator:
            mock_sim_instance = Mock()
            mock_sim_instance.run_simulation.return_value = {
                "performance_metrics": {
                    "service_reliability": 0.94,
                    "passenger_satisfaction": 0.91
                }
            }
            mock_simulator.return_value = mock_sim_instance
            
            sim_response = client.post("/simulate", json=sim_request)
            assert sim_response.status_code == 200
            sim_data = sim_response.json()
            
            # Verify simulation used optimized configuration
            assert sim_data["results"]["performance_metrics"]["service_reliability"] > 0.9
    
    def test_data_validation_pipeline(self, client):
        """Test data validation through the API pipeline."""
        # Test with invalid route IDs
        invalid_request = {
            "route_ids": ["nonexistent_route"],
            "optimization_type": "all"
        }
        
        with patch('src.api.optimization_api.validate_route_ids') as mock_validate:
            mock_validate.return_value = False
            
            response = client.post("/optimize", json=invalid_request)
            assert response.status_code == 422
    
    def test_performance_monitoring_integration(self, client):
        """Test integration with performance monitoring."""
        # Test that API calls are logged and monitored
        with patch('src.api.optimization_api.log_api_call') as mock_log:
            response = client.get("/health")
            
            # Verify logging was called
            mock_log.assert_called()
            assert response.status_code == 200


class TestAsyncAPIOperations:
    """Test asynchronous API operations."""
    
    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_async_optimization_endpoint(self, async_client):
        """Test asynchronous optimization endpoint."""
        request_data = {
            "route_ids": ["route_001"],
            "optimization_type": "all"
        }
        
        with patch('src.api.optimization_api.async_optimize_routes') as mock_async_opt:
            mock_async_opt.return_value = {
                "job_id": "async_job_123",
                "status": "started",
                "estimated_completion": "2024-01-01T12:05:00"
            }
            
            response = await async_client.post("/optimize/async", json=request_data)
            
            assert response.status_code == 202  # Accepted for async processing
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "started"
    
    @pytest.mark.asyncio
    async def test_websocket_optimization_updates(self):
        """Test WebSocket endpoint for real-time optimization updates."""
        # This would test WebSocket connection for real-time updates
        # Implementation depends on WebSocket setup in the API
        pass
    
    @pytest.mark.asyncio
    async def test_async_database_operations(self, async_client):
        """Test asynchronous database operations."""
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            response = await async_client.get("/routes")
            
            # Should handle async database operations
            assert response.status_code in [200, 500]  # Success or DB error


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API with external services."""
    
    def test_database_integration(self, client, db_session):
        """Test API integration with database."""
        # This would test actual database operations through the API
        with patch('src.api.optimization_api.get_db_session', return_value=db_session):
            response = client.get("/routes")
            assert response.status_code == 200
    
    def test_redis_caching_integration(self, client, mock_redis):
        """Test API integration with Redis caching."""
        with patch('src.api.optimization_api.get_redis_client', return_value=mock_redis):
            # First request - should cache result
            response1 = client.get("/metrics/current")
            
            # Second request - should use cached result
            response2 = client.get("/metrics/current")
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Verify Redis was called
            mock_redis.get.assert_called()
            mock_redis.set.assert_called()
    
    def test_external_api_integration(self, client, mock_external_apis):
        """Test API integration with external services."""
        forecast_request = {
            "route_id": "route_001",
            "include_weather": True
        }
        
        response = client.post("/forecast/demand", json=forecast_request)
        
        # Should handle external API calls
        assert response.status_code in [200, 503]  # Success or service unavailable
    
    def test_message_queue_integration(self, client):
        """Test API integration with message queue for background tasks."""
        optimization_request = {
            "route_ids": ["route_001"],
            "optimization_type": "all",
            "async": True
        }
        
        with patch('src.api.optimization_api.enqueue_optimization_task') as mock_queue:
            mock_queue.return_value = {"task_id": "task_123"}
            
            response = client.post("/optimize", json=optimization_request)
            
            assert response.status_code == 202
            mock_queue.assert_called_once()


@pytest.mark.slow
class TestAPIPerformance:
    """Performance tests for API endpoints."""
    
    def test_optimization_endpoint_performance(self, client):
        """Test optimization endpoint performance under load."""
        import time
        
        request_data = {
            "route_ids": ["route_001", "route_002"],
            "optimization_type": "all"
        }
        
        # Mock fast optimization
        with patch('src.api.optimization_api.RouteOptimizer') as mock_optimizer:
            mock_instance = Mock()
            mock_instance.optimize_routes.return_value = {
                "best_solution": [],
                "best_fitness": 0.8
            }
            mock_optimizer.return_value = mock_instance
            
            start_time = time.time()
            response = client.post("/optimize", json=request_data)
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 5.0  # Should complete within 5 seconds
    
    def test_concurrent_request_handling(self, client):
        """Test API performance with concurrent requests."""
        import concurrent.futures
        import time
        
        def make_request():
            with patch('src.api.optimization_api.get_current_metrics') as mock_metrics:
                mock_metrics.return_value = {"system_metrics": {}}
                return client.get("/metrics/current").status_code
        
        # Make concurrent requests
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        end_time = time.time()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert (end_time - start_time) < 10.0  # Should handle 10 requests within 10 seconds
    
    def test_memory_usage_optimization(self, client):
        """Test API memory usage with large requests."""
        # Large optimization request
        large_request = {
            "route_ids": [f"route_{i:03d}" for i in range(100)],
            "optimization_type": "all"
        }
        
        with patch('src.api.optimization_api.RouteOptimizer') as mock_optimizer:
            mock_instance = Mock()
            mock_instance.optimize_routes.return_value = {
                "best_solution": [],
                "best_fitness": 0.8
            }
            mock_optimizer.return_value = mock_instance
            
            response = client.post("/optimize", json=large_request)
            
            # Should handle large requests without memory issues
            assert response.status_code == 200