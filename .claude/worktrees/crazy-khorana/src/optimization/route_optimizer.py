#!/usr/bin/env python3
"""
MARTA Route Optimization Engine
Uses ML predictions to optimize routes and improve service efficiency
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

# Optimization libraries
from scipy.optimize import minimize, differential_evolution
from sklearn.cluster import KMeans
import networkx as nx
from shapely.geometry import Point, LineString
import joblib

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Optimization configuration
OPTIMIZATION_CONFIG = {
    'max_short_turns': 3,  # Maximum short-turn loops per route
    'max_detour_time': 15,  # Maximum detour time in minutes
    'min_headway': 5,  # Minimum headway in minutes
    'max_headway': 30,  # Maximum headway in minutes
    'bus_capacity': 50,  # Bus capacity (passengers)
    'overload_threshold': 0.8,  # 80% capacity threshold
    'optimization_timeout': 300,  # 5 minutes timeout
    'population_size': 50,  # For genetic algorithm
    'generations': 100  # For genetic algorithm
}

# Model storage
MODELS_DIR = 'models'

class RouteOptimizer:
    """Route optimization engine using ML predictions"""
    
    def __init__(self):
        """Initialize route optimizer"""
        self.config = OPTIMIZATION_CONFIG
        
        # Load ML models
        self.demand_model = None
        self.dwell_time_model = None
        
        # Route data
        self.routes_df = None
        self.stops_df = None
        self.trips_df = None
        self.stop_times_df = None
        
        # Optimization results
        self.optimization_results = {}
        
        logging.info("Initialized Route Optimizer")
    
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
        logging.info("Loading route data...")
        
        conn = self.create_db_connection()
        
        # Load GTFS data
        self.routes_df = pd.read_sql("SELECT * FROM gtfs_routes", conn)
        self.stops_df = pd.read_sql("SELECT * FROM gtfs_stops", conn)
        self.trips_df = pd.read_sql("SELECT * FROM gtfs_trips", conn)
        self.stop_times_df = pd.read_sql("SELECT * FROM gtfs_stop_times", conn)
        
        conn.close()
        
        logging.info(f"Loaded {len(self.routes_df)} routes, {len(self.stops_df)} stops")
    
    def load_ml_models(self):
        """Load trained ML models"""
        logging.info("Loading ML models...")
        
        try:
            # Load ensemble model for demand prediction
            ensemble_path = f'{MODELS_DIR}/ensemble/ensemble_demand_level_model.pkl'
            if os.path.exists(ensemble_path):
                self.demand_model = joblib.load(ensemble_path)
                logging.info("Loaded demand prediction model")
            
            # Load ensemble model for dwell time prediction
            dwell_path = f'{MODELS_DIR}/ensemble/ensemble_dwell_time_model.pkl'
            if os.path.exists(dwell_path):
                self.dwell_time_model = joblib.load(dwell_path)
                logging.info("Loaded dwell time prediction model")
                
        except Exception as e:
            logging.warning(f"Could not load ML models: {e}")
    
    def predict_demand(self, stop_id: str, timestamp: datetime) -> Dict:
        """Predict demand for a specific stop and time"""
        if self.demand_model is None:
            # Fallback to historical averages
            return self._get_historical_demand(stop_id, timestamp)
        
        try:
            # Prepare features for prediction
            features = self._prepare_prediction_features(stop_id, timestamp)
            
            # Make prediction
            prediction = self.demand_model.predict([features])
            
            return {
                'demand_level': prediction[0],
                'confidence': 0.8,  # Placeholder
                'timestamp': timestamp
            }
        except Exception as e:
            logging.warning(f"Demand prediction failed: {e}")
            return self._get_historical_demand(stop_id, timestamp)
    
    def predict_dwell_time(self, stop_id: str, timestamp: datetime) -> float:
        """Predict dwell time for a specific stop and time"""
        if self.dwell_time_model is None:
            # Fallback to historical averages
            return self._get_historical_dwell_time(stop_id, timestamp)
        
        try:
            # Prepare features for prediction
            features = self._prepare_prediction_features(stop_id, timestamp)
            
            # Make prediction
            prediction = self.dwell_time_model.predict([features])
            
            return max(0, prediction[0])  # Ensure non-negative
        except Exception as e:
            logging.warning(f"Dwell time prediction failed: {e}")
            return self._get_historical_dwell_time(stop_id, timestamp)
    
    def _prepare_prediction_features(self, stop_id: str, timestamp: datetime) -> np.ndarray:
        """Prepare features for ML prediction"""
        # This is a simplified version - in practice, you'd use the same
        # feature engineering pipeline as during training
        
        # Basic features
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        
        # Cyclical features
        sin_hour = np.sin(2 * np.pi * hour / 24)
        cos_hour = np.cos(2 * np.pi * hour / 24)
        sin_day = np.sin(2 * np.pi * day_of_week / 7)
        cos_day = np.cos(2 * np.pi * day_of_week / 7)
        
        # Placeholder features (would be replaced with actual engineered features)
        features = [
            hour, day_of_week, is_weekend,
            sin_hour, cos_hour, sin_day, cos_day,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  # Placeholder for other features
        ]
        
        return np.array(features)
    
    def _get_historical_demand(self, stop_id: str, timestamp: datetime) -> Dict:
        """Get historical demand as fallback"""
        # Simplified historical demand lookup
        hour = timestamp.hour
        
        # Basic demand patterns
        if 7 <= hour <= 9 or 16 <= hour <= 18:  # Peak hours
            demand_level = 'High'
        elif 10 <= hour <= 15:  # Mid-day
            demand_level = 'Normal'
        else:  # Off-peak
            demand_level = 'Low'
        
        return {
            'demand_level': demand_level,
            'confidence': 0.5,
            'timestamp': timestamp
        }
    
    def _get_historical_dwell_time(self, stop_id: str, timestamp: datetime) -> float:
        """Get historical dwell time as fallback"""
        # Simplified historical dwell time lookup
        hour = timestamp.hour
        
        if 7 <= hour <= 9 or 16 <= hour <= 18:  # Peak hours
            return 90.0  # 90 seconds
        elif 10 <= hour <= 15:  # Mid-day
            return 60.0  # 60 seconds
        else:  # Off-peak
            return 30.0  # 30 seconds
    
    def identify_overloaded_segments(self, route_id: str, timestamp: datetime) -> List[Dict]:
        """Identify overloaded segments on a route"""
        logging.info(f"Identifying overloaded segments for route {route_id}")
        
        # Get route stops
        route_stops = self._get_route_stops(route_id)
        overloaded_segments = []
        
        for i, stop_id in enumerate(route_stops):
            # Predict demand for this stop
            demand_pred = self.predict_demand(stop_id, timestamp)
            
            # Check if overloaded
            if demand_pred['demand_level'] in ['High', 'Overloaded']:
                segment = {
                    'route_id': route_id,
                    'stop_id': stop_id,
                    'stop_sequence': i + 1,
                    'demand_level': demand_pred['demand_level'],
                    'confidence': demand_pred['confidence'],
                    'timestamp': timestamp
                }
                overloaded_segments.append(segment)
        
        logging.info(f"Found {len(overloaded_segments)} overloaded segments")
        return overloaded_segments
    
    def _get_route_stops(self, route_id: str) -> List[str]:
        """Get ordered list of stops for a route"""
        # Get trips for this route
        route_trips = self.trips_df[self.trips_df['route_id'] == route_id]
        
        if route_trips.empty:
            return []
        
        # Get first trip's stops
        first_trip = route_trips.iloc[0]['trip_id']
        trip_stops = self.stop_times_df[self.stop_times_df['trip_id'] == first_trip]
        trip_stops = trip_stops.sort_values('stop_sequence')
        
        return trip_stops['stop_id'].tolist()
    
    def propose_short_turn_loops(self, route_id: str, overloaded_segments: List[Dict]) -> List[Dict]:
        """Propose short-turn loops to alleviate overloaded segments"""
        logging.info(f"Proposing short-turn loops for route {route_id}")
        
        route_stops = self._get_route_stops(route_id)
        if not route_stops:
            return []
        
        short_turn_proposals = []
        
        for segment in overloaded_segments:
            stop_id = segment['stop_id']
            stop_sequence = segment['stop_sequence']
            
            # Find suitable turnaround points
            turnaround_options = self._find_turnaround_points(route_stops, stop_sequence)
            
            for turnaround in turnaround_options:
                proposal = {
                    'route_id': route_id,
                    'original_trip_id': f"{route_id}_original",
                    'new_trip_id': f"{route_id}_short_turn_{len(short_turn_proposals)}",
                    'start_stop_id': turnaround['start_stop'],
                    'end_stop_id': turnaround['end_stop'],
                    'turnaround_stop_id': turnaround['turnaround_stop'],
                    'affected_segment': segment,
                    'estimated_impact': self._estimate_short_turn_impact(segment, turnaround),
                    'feasibility_score': turnaround['feasibility_score']
                }
                
                short_turn_proposals.append(proposal)
        
        # Sort by feasibility score
        short_turn_proposals.sort(key=lambda x: x['feasibility_score'], reverse=True)
        
        # Limit to maximum short turns
        short_turn_proposals = short_turn_proposals[:self.config['max_short_turns']]
        
        logging.info(f"Proposed {len(short_turn_proposals)} short-turn loops")
        return short_turn_proposals
    
    def _find_turnaround_points(self, route_stops: List[str], overloaded_sequence: int) -> List[Dict]:
        """Find suitable turnaround points for short-turn loops"""
        turnaround_options = []
        
        # Look for turnaround points before and after overloaded segment
        for i, stop_id in enumerate(route_stops):
            if i >= overloaded_sequence - 1:  # After overloaded segment
                break
            
            # Check if this stop is suitable for turnaround
            feasibility_score = self._calculate_turnaround_feasibility(stop_id)
            
            if feasibility_score > 0.5:  # Minimum feasibility threshold
                option = {
                    'start_stop': route_stops[0],  # Route start
                    'end_stop': route_stops[-1],   # Route end
                    'turnaround_stop': stop_id,
                    'feasibility_score': feasibility_score,
                    'detour_time': self._calculate_detour_time(route_stops, i)
                }
                
                # Check detour time constraint
                if option['detour_time'] <= self.config['max_detour_time']:
                    turnaround_options.append(option)
        
        return turnaround_options
    
    def _calculate_turnaround_feasibility(self, stop_id: str) -> float:
        """Calculate feasibility of using a stop for turnaround"""
        # Simplified feasibility calculation
        # In practice, this would consider:
        # - Physical space for buses to turn around
        # - Traffic conditions
        # - Proximity to depots
        # - Historical usage patterns
        
        # Placeholder: random feasibility score
        return np.random.uniform(0.3, 0.9)
    
    def _calculate_detour_time(self, route_stops: List[str], turnaround_index: int) -> float:
        """Calculate additional time due to short-turn detour"""
        # Simplified detour time calculation
        # In practice, this would use actual travel times and distances
        
        # Placeholder: 2-5 minutes per stop difference
        stops_difference = len(route_stops) - turnaround_index
        return stops_difference * 2.5  # 2.5 minutes per stop
    
    def _estimate_short_turn_impact(self, segment: Dict, turnaround: Dict) -> Dict:
        """Estimate the impact of a short-turn loop"""
        # Simplified impact estimation
        # In practice, this would use simulation or historical data
        
        original_demand = segment['demand_level']
        
        # Estimate demand reduction
        if original_demand == 'Overloaded':
            demand_reduction = 0.4  # 40% reduction
        elif original_demand == 'High':
            demand_reduction = 0.3  # 30% reduction
        else:
            demand_reduction = 0.1  # 10% reduction
        
        return {
            'demand_reduction': demand_reduction,
            'wait_time_reduction': demand_reduction * 5,  # 5 minutes per 100% reduction
            'vehicle_utilization_improvement': demand_reduction * 0.2,
            'passenger_satisfaction_improvement': demand_reduction * 0.3
        }
    
    def optimize_headways(self, route_id: str, timestamp: datetime) -> Dict:
        """Optimize headways for a route based on predicted demand"""
        logging.info(f"Optimizing headways for route {route_id}")
        
        route_stops = self._get_route_stops(route_id)
        if not route_stops:
            return {}
        
        # Predict demand for all stops
        total_demand = 0
        peak_demand = 0
        
        for stop_id in route_stops:
            demand_pred = self.predict_demand(stop_id, timestamp)
            
            # Convert demand level to numeric
            demand_value = self._demand_level_to_numeric(demand_pred['demand_level'])
            total_demand += demand_value
            
            if demand_value > peak_demand:
                peak_demand = demand_value
        
        avg_demand = total_demand / len(route_stops)
        
        # Calculate optimal headway based on demand
        if peak_demand > 0.8:  # High demand
            optimal_headway = self.config['min_headway']
        elif avg_demand > 0.5:  # Medium demand
            optimal_headway = (self.config['min_headway'] + self.config['max_headway']) / 2
        else:  # Low demand
            optimal_headway = self.config['max_headway']
        
        # Ensure headway is within bounds
        optimal_headway = max(self.config['min_headway'], 
                            min(self.config['max_headway'], optimal_headway))
        
        return {
            'route_id': route_id,
            'current_headway': 15,  # Placeholder - would get from actual schedule
            'optimal_headway': optimal_headway,
            'demand_level': self._numeric_to_demand_level(avg_demand),
            'peak_demand': peak_demand,
            'recommended_frequency': 60 / optimal_headway  # buses per hour
        }
    
    def _demand_level_to_numeric(self, demand_level: str) -> float:
        """Convert demand level to numeric value"""
        mapping = {
            'Low': 0.2,
            'Normal': 0.5,
            'High': 0.8,
            'Overloaded': 1.0
        }
        return mapping.get(demand_level, 0.5)
    
    def _numeric_to_demand_level(self, value: float) -> str:
        """Convert numeric value to demand level"""
        if value >= 0.8:
            return 'Overloaded'
        elif value >= 0.6:
            return 'High'
        elif value >= 0.3:
            return 'Normal'
        else:
            return 'Low'
    
    def optimize_route_network(self, timestamp: datetime) -> Dict:
        """Optimize the entire route network"""
        logging.info("Starting route network optimization")
        
        if self.routes_df is None:
            self.load_route_data()
        
        if self.demand_model is None:
            self.load_ml_models()
        
        optimization_results = {
            'timestamp': timestamp,
            'routes_analyzed': 0,
            'short_turn_proposals': [],
            'headway_optimizations': [],
            'overall_impact': {}
        }
        
        # Analyze each route
        for _, route in self.routes_df.iterrows():
            route_id = route['route_id']
            
            # Identify overloaded segments
            overloaded_segments = self.identify_overloaded_segments(route_id, timestamp)
            
            # Propose short-turn loops
            if overloaded_segments:
                short_turn_proposals = self.propose_short_turn_loops(route_id, overloaded_segments)
                optimization_results['short_turn_proposals'].extend(short_turn_proposals)
            
            # Optimize headways
            headway_optimization = self.optimize_headways(route_id, timestamp)
            optimization_results['headway_optimizations'].append(headway_optimization)
            
            optimization_results['routes_analyzed'] += 1
        
        # Calculate overall impact
        optimization_results['overall_impact'] = self._calculate_overall_impact(
            optimization_results['short_turn_proposals'],
            optimization_results['headway_optimizations']
        )
        
        self.optimization_results = optimization_results
        
        logging.info(f"Route network optimization completed")
        logging.info(f"  Routes analyzed: {optimization_results['routes_analyzed']}")
        logging.info(f"  Short-turn proposals: {len(optimization_results['short_turn_proposals'])}")
        logging.info(f"  Headway optimizations: {len(optimization_results['headway_optimizations'])}")
        
        return optimization_results
    
    def _calculate_overall_impact(self, short_turn_proposals: List[Dict], 
                                headway_optimizations: List[Dict]) -> Dict:
        """Calculate overall impact of optimizations"""
        total_demand_reduction = 0
        total_wait_time_reduction = 0
        total_vehicle_improvement = 0
        total_satisfaction_improvement = 0
        
        # Impact from short-turn loops
        for proposal in short_turn_proposals:
            impact = proposal['estimated_impact']
            total_demand_reduction += impact['demand_reduction']
            total_wait_time_reduction += impact['wait_time_reduction']
            total_vehicle_improvement += impact['vehicle_utilization_improvement']
            total_satisfaction_improvement += impact['passenger_satisfaction_improvement']
        
        # Impact from headway optimizations
        for optimization in headway_optimizations:
            if 'optimal_headway' in optimization and 'current_headway' in optimization:
                headway_improvement = (optimization['current_headway'] - optimization['optimal_headway']) / optimization['current_headway']
                total_wait_time_reduction += headway_improvement * 10  # 10 minutes per 100% improvement
        
        return {
            'total_demand_reduction': total_demand_reduction,
            'total_wait_time_reduction': total_wait_time_reduction,
            'total_vehicle_utilization_improvement': total_vehicle_improvement,
            'total_passenger_satisfaction_improvement': total_satisfaction_improvement,
            'estimated_cost_savings': total_wait_time_reduction * 100,  # $100 per minute saved
            'estimated_revenue_increase': total_satisfaction_improvement * 1000  # $1000 per satisfaction point
        }
    
    def save_optimization_results(self, filename: str = None):
        """Save optimization results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'optimization_results_{timestamp}.pkl'
        
        joblib.dump(self.optimization_results, filename)
        logging.info(f"Optimization results saved to {filename}")
    
    def generate_optimization_report(self) -> str:
        """Generate a text report of optimization results"""
        if not self.optimization_results:
            return "No optimization results available"
        
        results = self.optimization_results
        impact = results['overall_impact']
        
        report = f"""
MARTA Route Optimization Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Time: {results['timestamp']}

SUMMARY
-------
Routes Analyzed: {results['routes_analyzed']}
Short-Turn Proposals: {len(results['short_turn_proposals'])}
Headway Optimizations: {len(results['headway_optimizations'])}

IMPACT ANALYSIS
--------------
Demand Reduction: {impact['total_demand_reduction']:.2f}
Wait Time Reduction: {impact['total_wait_time_reduction']:.1f} minutes
Vehicle Utilization Improvement: {impact['total_vehicle_utilization_improvement']:.2f}
Passenger Satisfaction Improvement: {impact['total_passenger_satisfaction_improvement']:.2f}

FINANCIAL IMPACT
---------------
Estimated Cost Savings: ${impact['estimated_cost_savings']:.0f}
Estimated Revenue Increase: ${impact['estimated_revenue_increase']:.0f}

SHORT-TURN PROPOSALS
-------------------
"""
        
        for i, proposal in enumerate(results['short_turn_proposals'][:5]):  # Top 5
            report += f"""
{i+1}. Route {proposal['route_id']}
    Turnaround: {proposal['turnaround_stop_id']}
    Feasibility Score: {proposal['feasibility_score']:.2f}
    Demand Reduction: {proposal['estimated_impact']['demand_reduction']:.2f}
    Wait Time Reduction: {proposal['estimated_impact']['wait_time_reduction']:.1f} minutes
"""
        
        report += """
HEADWAY OPTIMIZATIONS
--------------------
"""
        
        for optimization in results['headway_optimizations'][:5]:  # Top 5
            if 'optimal_headway' in optimization:
                report += f"""
Route {optimization['route_id']}:
    Current Headway: {optimization.get('current_headway', 'N/A')} minutes
    Optimal Headway: {optimization['optimal_headway']:.1f} minutes
    Demand Level: {optimization.get('demand_level', 'N/A')}
    Recommended Frequency: {optimization.get('recommended_frequency', 0):.1f} buses/hour
"""
        
        return report

def main():
    """Main optimization function"""
    logging.info("🚀 Starting MARTA Route Optimization")
    
    # Initialize optimizer
    optimizer = RouteOptimizer()
    
    # Load data and models
    optimizer.load_route_data()
    optimizer.load_ml_models()
    
    # Run optimization for current time
    timestamp = datetime.now()
    results = optimizer.optimize_route_network(timestamp)
    
    # Save results
    optimizer.save_optimization_results()
    
    # Generate and print report
    report = optimizer.generate_optimization_report()
    print(report)
    
    logging.info("🎉 Route optimization completed successfully!")

if __name__ == "__main__":
    main() 