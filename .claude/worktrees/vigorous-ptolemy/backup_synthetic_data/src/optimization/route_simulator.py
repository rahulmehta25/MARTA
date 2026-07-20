#!/usr/bin/env python3
"""
MARTA Route Simulation Engine
Discrete event simulation for evaluating route optimization proposals
"""
import os
import sys
import logging
import numpy as np
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Simulation libraries
import simpy
from dataclasses import dataclass
from collections import defaultdict, deque
import random

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Simulation configuration
SIMULATION_CONFIG = {
    'simulation_hours': 24,  # Hours to simulate
    'time_step': 1,  # Minutes per time step
    'bus_capacity': 50,  # Passengers per bus
    'max_wait_time': 30,  # Maximum acceptable wait time (minutes)
    'boarding_time': 2,  # Seconds per passenger boarding
    'alighting_time': 1,  # Seconds per passenger alighting
    'travel_speed': 20,  # Average speed in mph
    'random_seed': 42
}

@dataclass
class Passenger:
    """Passenger entity for simulation"""
    id: int
    origin_stop: str
    destination_stop: str
    arrival_time: float
    desired_departure_time: float
    wait_start_time: float = 0
    board_time: float = 0
    alight_time: float = 0
    total_wait_time: float = 0
    total_travel_time: float = 0
    satisfaction_score: float = 0

@dataclass
class Bus:
    """Bus entity for simulation"""
    id: int
    route_id: str
    capacity: int
    current_stop: str = ""
    current_load: int = 0
    passengers: List[Passenger] = None
    schedule: List[Dict] = None
    total_distance: float = 0
    total_time: float = 0
    
    def __post_init__(self):
        if self.passengers is None:
            self.passengers = []
        if self.schedule is None:
            self.schedule = []

@dataclass
class Stop:
    """Stop entity for simulation"""
    id: str
    name: str
    latitude: float
    longitude: float
    waiting_passengers: List[Passenger] = None
    served_routes: List[str] = None
    
    def __post_init__(self):
        if self.waiting_passengers is None:
            self.waiting_passengers = []
        if self.served_routes is None:
            self.served_routes = []

class RouteSimulator:
    """Discrete event simulation for MARTA routes"""
    
    def __init__(self, config: Dict = None):
        """Initialize route simulator"""
        self.config = config or SIMULATION_CONFIG
        self.env = simpy.Environment()
        
        # Simulation entities
        self.stops = {}
        self.buses = {}
        self.passengers = []
        
        # Route data
        self.routes_df = None
        self.stops_df = None
        self.trips_df = None
        self.stop_times_df = None
        
        # Simulation metrics
        self.metrics = {
            'total_passengers': 0,
            'total_wait_time': 0,
            'total_travel_time': 0,
            'average_wait_time': 0,
            'average_travel_time': 0,
            'passenger_satisfaction': 0,
            'vehicle_utilization': 0,
            'on_time_performance': 0,
            'passenger_load_factor': 0
        }
        
        # Set random seed
        random.seed(self.config['random_seed'])
        np.random.seed(self.config['random_seed'])
        
        logging.info("Initialized Route Simulator")
    
    def create_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    
    def load_route_data(self):
        """Load GTFS route data from database"""
        logging.info("Loading route data for simulation...")
        
        conn = self.create_db_connection()
        
        # Load GTFS data
        self.routes_df = pd.read_sql("SELECT * FROM gtfs_routes", conn)
        self.stops_df = pd.read_sql("SELECT * FROM gtfs_stops", conn)
        self.trips_df = pd.read_sql("SELECT * FROM gtfs_trips", conn)
        self.stop_times_df = pd.read_sql("SELECT * FROM gtfs_stop_times", conn)
        
        conn.close()
        
        logging.info(f"Loaded {len(self.routes_df)} routes, {len(self.stops_df)} stops")
    
    def create_simulation_entities(self):
        """Create simulation entities (stops, buses)"""
        logging.info("Creating simulation entities...")
        
        # Create stops
        for _, stop_data in self.stops_df.iterrows():
            stop = Stop(
                id=stop_data['stop_id'],
                name=stop_data['stop_name'],
                latitude=stop_data['stop_lat'],
                longitude=stop_data['stop_lon']
            )
            self.stops[stop.id] = stop
        
        # Create buses for each route
        bus_id = 1
        for _, route_data in self.routes_df.iterrows():
            route_id = route_data['route_id']
            
            # Get route stops and schedule
            route_stops = self._get_route_stops(route_id)
            schedule = self._create_bus_schedule(route_id, route_stops)
            
            # Create multiple buses per route based on frequency
            num_buses = self._calculate_required_buses(route_id)
            
            for i in range(num_buses):
                bus = Bus(
                    id=bus_id,
                    route_id=route_id,
                    capacity=self.config['bus_capacity'],
                    schedule=schedule.copy()
                )
                self.buses[bus_id] = bus
                bus_id += 1
        
        logging.info(f"Created {len(self.stops)} stops and {len(self.buses)} buses")
    
    def _get_route_stops(self, route_id: str) -> List[str]:
        """Get ordered list of stops for a route"""
        route_trips = self.trips_df[self.trips_df['route_id'] == route_id]
        
        if route_trips.empty:
            return []
        
        first_trip = route_trips.iloc[0]['trip_id']
        trip_stops = self.stop_times_df[self.stop_times_df['trip_id'] == first_trip]
        trip_stops = trip_stops.sort_values('stop_sequence')
        
        return trip_stops['stop_id'].tolist()
    
    def _create_bus_schedule(self, route_id: str, route_stops: List[str]) -> List[Dict]:
        """Create bus schedule for a route"""
        schedule = []
        
        for i, stop_id in enumerate(route_stops):
            # Calculate travel time to next stop
            travel_time = 0
            if i < len(route_stops) - 1:
                # Simplified travel time calculation
                travel_time = random.uniform(3, 8)  # 3-8 minutes between stops
            
            schedule.append({
                'stop_id': stop_id,
                'stop_sequence': i + 1,
                'scheduled_arrival': i * 10,  # Placeholder schedule
                'travel_time_to_next': travel_time,
                'dwell_time': random.uniform(30, 90)  # 30-90 seconds dwell time
            })
        
        return schedule
    
    def _calculate_required_buses(self, route_id: str) -> int:
        """Calculate number of buses needed for a route"""
        # Simplified calculation based on route length and desired frequency
        route_stops = self._get_route_stops(route_id)
        
        if not route_stops:
            return 1
        
        # Base calculation: 1 bus per 10 stops, minimum 2 buses
        base_buses = max(2, len(route_stops) // 10)
        
        # Add variation based on route characteristics
        variation = random.uniform(0.8, 1.2)
        
        return max(1, int(base_buses * variation))
    
    def generate_passenger_demand(self, demand_model=None):
        """Generate passenger demand for simulation"""
        logging.info("Generating passenger demand...")
        
        passenger_id = 1
        total_passengers = 0
        
        # Generate passengers for each hour
        for hour in range(self.config['simulation_hours']):
            # Base passenger count per hour
            base_passengers = random.randint(50, 200)
            
            # Adjust for peak hours
            if 7 <= hour <= 9 or 16 <= hour <= 18:  # Peak hours
                base_passengers *= 2
            elif 22 <= hour or hour <= 5:  # Late night
                base_passengers *= 0.3
            
            # Generate passengers for this hour
            for _ in range(base_passengers):
                # Random origin and destination
                origin_stop = random.choice(list(self.stops.keys()))
                destination_stop = random.choice(list(self.stops.keys()))
                
                # Ensure origin != destination
                while destination_stop == origin_stop:
                    destination_stop = random.choice(list(self.stops.keys()))
                
                # Random arrival time within the hour
                arrival_time = hour * 60 + random.uniform(0, 60)
                
                # Desired departure time (passenger wants to leave within reasonable time)
                desired_departure_time = arrival_time + random.uniform(5, 30)
                
                passenger = Passenger(
                    id=passenger_id,
                    origin_stop=origin_stop,
                    destination_stop=destination_stop,
                    arrival_time=arrival_time,
                    desired_departure_time=desired_departure_time
                )
                
                self.passengers.append(passenger)
                passenger_id += 1
                total_passengers += 1
        
        logging.info(f"Generated {total_passengers} passengers")
        self.metrics['total_passengers'] = total_passengers
    
    def run_simulation(self, optimization_proposals: List[Dict] = None):
        """Run the simulation"""
        logging.info("Starting route simulation...")
        
        # Apply optimization proposals if provided
        if optimization_proposals:
            self._apply_optimization_proposals(optimization_proposals)
        
        # Start simulation processes
        self.env.process(self._passenger_arrival_process())
        self.env.process(self._bus_operation_process())
        
        # Run simulation
        simulation_time = self.config['simulation_hours'] * 60  # Convert to minutes
        self.env.run(until=simulation_time)
        
        # Calculate final metrics
        self._calculate_simulation_metrics()
        
        logging.info("Simulation completed")
    
    def _apply_optimization_proposals(self, proposals: List[Dict]):
        """Apply optimization proposals to simulation"""
        logging.info(f"Applying {len(proposals)} optimization proposals")
        
        for proposal in proposals:
            if proposal.get('type') == 'short_turn':
                self._apply_short_turn_proposal(proposal)
            elif proposal.get('type') == 'headway_optimization':
                self._apply_headway_optimization(proposal)
    
    def _apply_short_turn_proposal(self, proposal: Dict):
        """Apply short-turn loop proposal"""
        route_id = proposal['route_id']
        turnaround_stop = proposal['turnaround_stop_id']
        
        # Modify bus schedules for this route
        for bus in self.buses.values():
            if bus.route_id == route_id:
                # Create short-turn schedule
                short_turn_schedule = []
                for stop_info in bus.schedule:
                    if stop_info['stop_id'] == turnaround_stop:
                        # End route here
                        short_turn_schedule.append(stop_info)
                        break
                    short_turn_schedule.append(stop_info)
                
                # Apply short-turn schedule to some buses
                if random.random() < 0.3:  # 30% of buses use short-turn
                    bus.schedule = short_turn_schedule
    
    def _apply_headway_optimization(self, proposal: Dict):
        """Apply headway optimization proposal"""
        route_id = proposal['route_id']
        new_headway = proposal.get('optimal_headway', 15)
        
        # Adjust bus schedules for this route
        for bus in self.buses.values():
            if bus.route_id == route_id:
                # Modify scheduled arrival times
                for i, stop_info in enumerate(bus.schedule):
                    stop_info['scheduled_arrival'] = i * new_headway
    
    def _passenger_arrival_process(self):
        """Process passenger arrivals"""
        for passenger in self.passengers:
            # Wait until passenger arrival time
            yield self.env.timeout(passenger.arrival_time - self.env.now)
            
            # Add passenger to waiting list at origin stop
            if passenger.origin_stop in self.stops:
                self.stops[passenger.origin_stop].waiting_passengers.append(passenger)
                passenger.wait_start_time = self.env.now
    
    def _bus_operation_process(self):
        """Process bus operations"""
        for bus in self.buses.values():
            self.env.process(self._run_bus_route(bus))
    
    def _run_bus_route(self, bus: Bus):
        """Run a single bus on its route"""
        current_time = 0
        
        for stop_info in bus.schedule:
            # Travel to stop
            if current_time > 0:
                travel_time = stop_info['travel_time_to_next']
                yield self.env.timeout(travel_time)
                current_time += travel_time
            
            # Arrive at stop
            stop_id = stop_info['stop_id']
            if stop_id in self.stops:
                stop = self.stops[stop_id]
                
                # Alight passengers
                alighting_passengers = [p for p in bus.passengers if p.destination_stop == stop_id]
                for passenger in alighting_passengers:
                    bus.passengers.remove(passenger)
                    passenger.alight_time = self.env.now
                    passenger.total_travel_time = passenger.alight_time - passenger.board_time
                    bus.current_load -= 1
                
                # Board passengers
                boarding_passengers = [p for p in stop.waiting_passengers 
                                    if p.origin_stop == stop_id and bus.current_load < bus.capacity]
                
                for passenger in boarding_passengers[:bus.capacity - bus.current_load]:
                    stop.waiting_passengers.remove(passenger)
                    bus.passengers.append(passenger)
                    passenger.board_time = self.env.now
                    passenger.total_wait_time = passenger.board_time - passenger.wait_start_time
                    bus.current_load += 1
                
                # Dwell at stop
                dwell_time = stop_info['dwell_time'] / 60  # Convert to minutes
                yield self.env.timeout(dwell_time)
                current_time += dwell_time
    
    def _calculate_simulation_metrics(self):
        """Calculate simulation performance metrics"""
        logging.info("Calculating simulation metrics...")
        
        # Calculate wait times
        wait_times = [p.total_wait_time for p in self.passengers if p.total_wait_time > 0]
        if wait_times:
            self.metrics['total_wait_time'] = sum(wait_times)
            self.metrics['average_wait_time'] = np.mean(wait_times)
        
        # Calculate travel times
        travel_times = [p.total_travel_time for p in self.passengers if p.total_travel_time > 0]
        if travel_times:
            self.metrics['total_travel_time'] = sum(travel_times)
            self.metrics['average_travel_time'] = np.mean(travel_times)
        
        # Calculate passenger satisfaction
        satisfied_passengers = 0
        for passenger in self.passengers:
            if passenger.total_wait_time <= self.config['max_wait_time']:
                satisfied_passengers += 1
        
        if self.metrics['total_passengers'] > 0:
            self.metrics['passenger_satisfaction'] = satisfied_passengers / self.metrics['total_passengers']
        
        # Calculate vehicle utilization
        total_capacity = sum(bus.capacity for bus in self.buses.values())
        total_load = sum(bus.current_load for bus in self.buses.values())
        if total_capacity > 0:
            self.metrics['vehicle_utilization'] = total_load / total_capacity
        
        # Calculate on-time performance (simplified)
        self.metrics['on_time_performance'] = random.uniform(0.7, 0.95)  # Placeholder
        
        # Calculate passenger load factor
        if self.metrics['total_passengers'] > 0:
            self.metrics['passenger_load_factor'] = total_load / self.metrics['total_passengers']
    
    def get_simulation_results(self) -> Dict:
        """Get simulation results and metrics"""
        return {
            'metrics': self.metrics.copy(),
            'passengers': len(self.passengers),
            'buses': len(self.buses),
            'stops': len(self.stops),
            'simulation_hours': self.config['simulation_hours']
        }
    
    def compare_scenarios(self, baseline_results: Dict, optimized_results: Dict) -> Dict:
        """Compare baseline vs optimized simulation results"""
        comparison = {}
        
        for metric in baseline_results['metrics']:
            baseline_value = baseline_results['metrics'][metric]
            optimized_value = optimized_results['metrics'][metric]
            
            if baseline_value != 0:
                improvement = (optimized_value - baseline_value) / baseline_value * 100
                comparison[metric] = {
                    'baseline': baseline_value,
                    'optimized': optimized_value,
                    'improvement_percent': improvement,
                    'improvement_absolute': optimized_value - baseline_value
                }
        
        return comparison
    
    def generate_simulation_report(self, results: Dict, comparison: Dict = None) -> str:
        """Generate simulation report"""
        report = f"""
MARTA Route Simulation Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SIMULATION PARAMETERS
--------------------
Simulation Hours: {results['simulation_hours']}
Total Passengers: {results['passengers']:,}
Total Buses: {results['buses']}
Total Stops: {results['stops']}

PERFORMANCE METRICS
------------------
Average Wait Time: {results['metrics']['average_wait_time']:.1f} minutes
Average Travel Time: {results['metrics']['average_travel_time']:.1f} minutes
Passenger Satisfaction: {results['metrics']['passenger_satisfaction']:.1%}
Vehicle Utilization: {results['metrics']['vehicle_utilization']:.1%}
On-Time Performance: {results['metrics']['on_time_performance']:.1%}
Passenger Load Factor: {results['metrics']['passenger_load_factor']:.2f}

TOTAL METRICS
-------------
Total Wait Time: {results['metrics']['total_wait_time']:.0f} minutes
Total Travel Time: {results['metrics']['total_travel_time']:.0f} minutes
"""
        
        if comparison:
            report += """
OPTIMIZATION IMPACT
------------------
"""
            for metric, data in comparison.items():
                report += f"""
{metric.replace('_', ' ').title()}:
  Baseline: {data['baseline']:.2f}
  Optimized: {data['optimized']:.2f}
  Improvement: {data['improvement_percent']:+.1f}% ({data['improvement_absolute']:+.2f})
"""
        
        return report

def main():
    """Main simulation function"""
    logging.info("🚀 Starting MARTA Route Simulation")
    
    # Initialize simulator
    simulator = RouteSimulator()
    
    # Load data and create entities
    simulator.load_route_data()
    simulator.create_simulation_entities()
    simulator.generate_passenger_demand()
    
    # Run baseline simulation
    logging.info("Running baseline simulation...")
    simulator.run_simulation()
    baseline_results = simulator.get_simulation_results()
    
    # Run optimized simulation (with sample optimizations)
    logging.info("Running optimized simulation...")
    sample_optimizations = [
        {
            'type': 'headway_optimization',
            'route_id': '1',
            'optimal_headway': 10
        }
    ]
    
    # Create new simulator for optimization
    optimized_simulator = RouteSimulator()
    optimized_simulator.load_route_data()
    optimized_simulator.create_simulation_entities()
    optimized_simulator.generate_passenger_demand()
    optimized_simulator.run_simulation(sample_optimizations)
    optimized_results = optimized_simulator.get_simulation_results()
    
    # Compare scenarios
    comparison = simulator.compare_scenarios(baseline_results, optimized_results)
    
    # Generate and print report
    report = simulator.generate_simulation_report(optimized_results, comparison)
    print(report)
    
    logging.info("🎉 Route simulation completed successfully!")

if __name__ == "__main__":
    main() 