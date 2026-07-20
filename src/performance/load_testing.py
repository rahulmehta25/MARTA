"""
MARTA Platform - Advanced Load Testing Suite with Locust
Comprehensive load testing for API endpoints, database, and real-time features
"""
import os
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from locust import HttpUser, TaskSet, task, between, events, LoadTestShape
from locust.stats import stats_printer, stats_history
from locust.exception import RescheduleTask
import pandas as pd
import numpy as np
import gevent

logger = logging.getLogger(__name__)


class MARTAUserBehavior(TaskSet):
    """Realistic user behavior simulation for MARTA platform"""
    
    def on_start(self):
        """Initialize user session"""
        self.user_id = f"user_{random.randint(1000, 9999)}"
        self.favorite_stops = self._get_random_stops(5)
        self.favorite_routes = self._get_random_routes(3)
        self.session_start = datetime.now()
        
    def _get_random_stops(self, count: int) -> List[str]:
        """Get random stop IDs"""
        stops = [
            "STOP_001", "STOP_002", "STOP_003", "STOP_004", "STOP_005",
            "STOP_006", "STOP_007", "STOP_008", "STOP_009", "STOP_010"
        ]
        return random.sample(stops, min(count, len(stops)))
        
    def _get_random_routes(self, count: int) -> List[str]:
        """Get random route IDs"""
        routes = ["ROUTE_RED", "ROUTE_GOLD", "ROUTE_BLUE", "ROUTE_GREEN", "ROUTE_SILVER"]
        return random.sample(routes, min(count, len(routes)))
        
    @task(10)
    def get_stops(self):
        """Get all stops - most common operation"""
        with self.client.get(
            "/data/stops",
            name="Get Stops",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(8)
    def get_routes(self):
        """Get all routes"""
        with self.client.get(
            "/data/routes",
            name="Get Routes",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(6)
    def predict_demand(self):
        """Predict demand for a stop"""
        stop_id = random.choice(self.favorite_stops)
        timestamp = datetime.now().isoformat()
        
        with self.client.post(
            "/predict/demand",
            json={
                "stop_id": stop_id,
                "timestamp": timestamp
            },
            name="Predict Demand",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(5)
    def get_vehicle_positions(self):
        """Get real-time vehicle positions"""
        with self.client.get(
            "/data/vehicles/live",
            name="Get Vehicle Positions",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(4)
    def get_trip_updates(self):
        """Get real-time trip updates"""
        with self.client.get(
            "/data/trips/updates",
            name="Get Trip Updates",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(3)
    def search_stops(self):
        """Search for stops"""
        search_terms = ["Five Points", "Peachtree", "Airport", "Midtown", "Downtown"]
        query = random.choice(search_terms)
        
        with self.client.get(
            f"/search/stops?q={query}",
            name="Search Stops",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(3)
    def get_heatmap_data(self):
        """Get heatmap data for visualization"""
        bounds = {
            "north": 33.8,
            "south": 33.7,
            "east": -84.3,
            "west": -84.4
        }
        
        with self.client.get(
            "/data/heatmap",
            params={
                "time_window": "current",
                "zoom_level": 12,
                "bounds": json.dumps(bounds)
            },
            name="Get Heatmap",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(2)
    def optimize_routes(self):
        """Request route optimization"""
        with self.client.post(
            "/optimize/routes",
            json={
                "forecasted_demand_heatmap": {},
                "current_route_topology": {},
                "bus_capacity_assumptions": 50,
                "optimization_constraints": {}
            },
            name="Optimize Routes",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(2)
    def get_historical_trips(self):
        """Get historical trip data"""
        with self.client.get(
            "/data/historical_trips",
            params={
                "limit": 100,
                "offset": 0
            },
            name="Get Historical Trips",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
                
    @task(1)
    def complex_query(self):
        """Simulate complex analytical query"""
        # Simulate a user performing multiple operations in sequence
        stop_id = random.choice(self.favorite_stops)
        
        # Step 1: Get stop details
        self.client.get(f"/data/stops/{stop_id}", name="Complex: Get Stop")
        
        # Step 2: Predict demand
        self.client.post(
            "/predict/demand",
            json={"stop_id": stop_id, "timestamp": datetime.now().isoformat()},
            name="Complex: Predict"
        )
        
        # Step 3: Get nearby vehicles
        self.client.get(
            f"/data/vehicles/near/{stop_id}",
            name="Complex: Nearby Vehicles"
        )
        
    def on_stop(self):
        """Clean up user session"""
        session_duration = (datetime.now() - self.session_start).total_seconds()
        logger.info(f"User {self.user_id} session ended after {session_duration:.2f} seconds")


class MobileUserBehavior(MARTAUserBehavior):
    """Mobile app user behavior - more real-time focused"""
    
    @task(15)
    def get_vehicle_positions(self):
        """Mobile users check vehicle positions more frequently"""
        super().get_vehicle_positions()
        
    @task(12)
    def get_trip_updates(self):
        """Mobile users check trip updates more frequently"""
        super().get_trip_updates()
        
    @task(2)
    def optimize_routes(self):
        """Mobile users rarely request optimization"""
        super().optimize_routes()


class WebUserBehavior(MARTAUserBehavior):
    """Web dashboard user behavior - more analytical"""
    
    @task(5)
    def get_vehicle_positions(self):
        """Web users check vehicle positions less frequently"""
        super().get_vehicle_positions()
        
    @task(8)
    def optimize_routes(self):
        """Web users request optimization more frequently"""
        super().optimize_routes()
        
    @task(10)
    def get_historical_trips(self):
        """Web users analyze historical data more"""
        super().get_historical_trips()


class MARTAUser(HttpUser):
    """Standard MARTA platform user"""
    tasks = [MARTAUserBehavior]
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Set up user session"""
        # Add authentication headers if needed
        self.client.headers.update({
            "User-Agent": f"MARTA-LoadTest/{self.__class__.__name__}",
            "X-Session-ID": f"session_{random.randint(10000, 99999)}"
        })


class MobileMARTAUser(HttpUser):
    """Mobile app user"""
    tasks = [MobileUserBehavior]
    wait_time = between(0.5, 3)  # Mobile users are more active
    weight = 60  # 60% of users are mobile
    
    def on_start(self):
        self.client.headers.update({
            "User-Agent": "MARTA-Mobile/1.0",
            "X-Platform": "mobile"
        })


class WebMARTAUser(HttpUser):
    """Web dashboard user"""
    tasks = [WebUserBehavior]
    wait_time = between(2, 8)  # Web users spend more time analyzing
    weight = 40  # 40% of users are web
    
    def on_start(self):
        self.client.headers.update({
            "User-Agent": "Mozilla/5.0 MARTA-Web",
            "X-Platform": "web"
        })


class StagesShape(LoadTestShape):
    """
    Progressive load test shape that simulates daily traffic patterns
    """
    
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2, "name": "Warm-up"},
        {"duration": 300, "users": 50, "spawn_rate": 5, "name": "Morning ramp-up"},
        {"duration": 600, "users": 200, "spawn_rate": 10, "name": "Morning peak"},
        {"duration": 300, "users": 100, "spawn_rate": 5, "name": "Mid-day"},
        {"duration": 600, "users": 250, "spawn_rate": 10, "name": "Evening peak"},
        {"duration": 300, "users": 50, "spawn_rate": 5, "name": "Evening wind-down"},
        {"duration": 60, "users": 10, "spawn_rate": 2, "name": "Night"},
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
                
        return None


class SpikeTestShape(LoadTestShape):
    """
    Spike test to simulate sudden traffic surges
    """
    
    time_limit = 600
    spawn_rate = 20
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < self.time_limit:
            # Normal load
            if run_time < 120:
                user_count = 50
            # Spike
            elif run_time < 180:
                user_count = 500
            # Recovery
            elif run_time < 300:
                user_count = 100
            # Second spike
            elif run_time < 360:
                user_count = 750
            # Wind down
            else:
                user_count = 50
                
            return (user_count, self.spawn_rate)
            
        return None


class StressTestShape(LoadTestShape):
    """
    Stress test to find system breaking point
    """
    
    step_time = 60
    step_users = 50
    spawn_rate = 10
    max_users = 1000
    
    def tick(self):
        run_time = self.get_run_time()
        current_step = run_time // self.step_time
        
        if current_step * self.step_users >= self.max_users:
            return None
            
        return ((current_step + 1) * self.step_users, self.spawn_rate)


# Custom event handlers for detailed reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test metrics"""
    print("=" * 80)
    print("MARTA Platform Load Test Starting")
    print(f"Target Host: {environment.host}")
    print(f"Start Time: {datetime.now()}")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate final test report"""
    print("=" * 80)
    print("MARTA Platform Load Test Complete")
    print(f"End Time: {datetime.now()}")
    print("=" * 80)
    
    # Generate detailed report
    generate_performance_report(environment)


def generate_performance_report(environment):
    """Generate detailed performance report"""
    stats = environment.stats
    
    report = {
        "summary": {
            "total_requests": stats.total.num_requests,
            "total_failures": stats.total.num_failures,
            "failure_rate": (stats.total.num_failures / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0,
            "average_response_time": stats.total.avg_response_time,
            "min_response_time": stats.total.min_response_time,
            "max_response_time": stats.total.max_response_time,
            "rps": stats.total.current_rps,
            "peak_users": environment.runner.peak_users if hasattr(environment.runner, 'peak_users') else 0
        },
        "endpoints": {}
    }
    
    # Detailed endpoint statistics
    for name, entry in stats.entries.items():
        if name != "Aggregated":
            report["endpoints"][name] = {
                "requests": entry.num_requests,
                "failures": entry.num_failures,
                "avg_response_time": entry.avg_response_time,
                "min_response_time": entry.min_response_time,
                "max_response_time": entry.max_response_time,
                "median_response_time": entry.median_response_time,
                "p90_response_time": entry.get_response_time_percentile(0.9),
                "p95_response_time": entry.get_response_time_percentile(0.95),
                "p99_response_time": entry.get_response_time_percentile(0.99),
                "avg_content_length": entry.avg_content_length
            }
    
    # Performance thresholds and recommendations
    report["performance_analysis"] = analyze_performance(report)
    
    # Save report
    report_filename = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_filename}")
    print("\n" + "Performance Summary".center(80, "="))
    print(f"Total Requests: {report['summary']['total_requests']:,}")
    print(f"Failure Rate: {report['summary']['failure_rate']:.2f}%")
    print(f"Average Response Time: {report['summary']['average_response_time']:.2f}ms")
    print(f"Requests/Second: {report['summary']['rps']:.2f}")
    
    # Print recommendations
    if report["performance_analysis"]["recommendations"]:
        print("\n" + "Recommendations".center(80, "="))
        for rec in report["performance_analysis"]["recommendations"]:
            print(f"• {rec}")


def analyze_performance(report: Dict) -> Dict:
    """Analyze performance and generate recommendations"""
    analysis = {
        "status": "PASS",
        "issues": [],
        "recommendations": []
    }
    
    # Check failure rate
    if report["summary"]["failure_rate"] > 1:
        analysis["status"] = "FAIL"
        analysis["issues"].append(f"High failure rate: {report['summary']['failure_rate']:.2f}%")
        analysis["recommendations"].append("Investigate error logs and increase server capacity")
    
    # Check response times
    if report["summary"]["average_response_time"] > 1000:
        analysis["issues"].append(f"High average response time: {report['summary']['average_response_time']:.2f}ms")
        analysis["recommendations"].append("Implement caching and optimize database queries")
    
    # Check specific endpoints
    for endpoint, stats in report["endpoints"].items():
        if stats["p95_response_time"] > 2000:
            analysis["issues"].append(f"{endpoint} P95 > 2s")
            analysis["recommendations"].append(f"Optimize {endpoint} endpoint")
    
    return analysis


# Locust configuration for running tests
def run_load_test(
    host: str = "http://localhost:8000",
    users: int = 100,
    spawn_rate: int = 10,
    run_time: str = "5m",
    test_type: str = "standard"
):
    """Run load test programmatically"""
    
    from locust import main as locust_main
    
    # Select test shape
    shape_class = ""
    if test_type == "stages":
        shape_class = "StagesShape"
    elif test_type == "spike":
        shape_class = "SpikeTestShape"
    elif test_type == "stress":
        shape_class = "StressTestShape"
    
    # Prepare arguments
    args = [
        "locust",
        "-f", __file__,
        "--host", host,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", run_time,
        "--headless",
        "--print-stats",
        "--html", f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    ]
    
    if shape_class:
        args.extend(["--class", shape_class])
    
    # Run Locust
    locust_main.main(args)


if __name__ == "__main__":
    # Example: Run a standard load test
    run_load_test(
        host="http://localhost:8000",
        users=100,
        spawn_rate=10,
        run_time="5m",
        test_type="standard"
    )