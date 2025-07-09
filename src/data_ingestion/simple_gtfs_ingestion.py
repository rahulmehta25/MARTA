#!/usr/bin/env python3
"""
Simplified GTFS Data Ingestion for Demo
Creates realistic demo data for MARTA Demand Forecasting Platform
"""
import os
import sys
import logging
import pandas as pd
import psycopg2
from psycopg2 import extras
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleGTFSIngestion:
    """Simplified GTFS ingestion for demo purposes"""
    
    def __init__(self):
        self.db_config = {
            'host': settings.DB_HOST,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD
        }
    
    def create_demo_data(self):
        """Create comprehensive demo data for the platform"""
        logger.info("Creating demo data for MARTA Demand Forecasting Platform...")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            
            # Create demo stops (major MARTA stations)
            self._create_demo_stops(conn)
            
            # Create demo routes (major MARTA routes)
            self._create_demo_routes(conn)
            
            # Create demo trips
            self._create_demo_trips(conn)
            
            # Create demo stop times
            self._create_demo_stop_times(conn)
            
            # Create demo unified data (simulated real-time + historical)
            self._create_demo_unified_data(conn)
            
            conn.close()
            logger.info("Demo data creation completed successfully!")
            
        except Exception as e:
            logger.error(f"Error creating demo data: {e}")
            raise
    
    def _create_demo_stops(self, conn):
        """Create demo stops representing major MARTA stations"""
        stops_data = [
            ('STOP001', 'Five Points Station', 33.7537, -84.3917, 'ZONE1'),
            ('STOP002', 'Peachtree Center', 33.7597, -84.3887, 'ZONE1'),
            ('STOP003', 'Civic Center', 33.7657, -84.3857, 'ZONE1'),
            ('STOP004', 'North Avenue', 33.7717, -84.3827, 'ZONE2'),
            ('STOP005', 'Midtown', 33.7777, -84.3797, 'ZONE2'),
            ('STOP006', 'Arts Center', 33.7837, -84.3767, 'ZONE2'),
            ('STOP007', 'Lindbergh Center', 33.7897, -84.3737, 'ZONE3'),
            ('STOP008', 'Buckhead', 33.7957, -84.3707, 'ZONE3'),
            ('STOP009', 'Medical Center', 33.8017, -84.3677, 'ZONE3'),
            ('STOP010', 'Dunwoody', 33.8077, -84.3647, 'ZONE4'),
            ('STOP011', 'Sandy Springs', 33.8137, -84.3617, 'ZONE4'),
            ('STOP012', 'North Springs', 33.8197, -84.3587, 'ZONE4'),
            ('STOP013', 'Airport', 33.6407, -84.4277, 'ZONE5'),
            ('STOP014', 'College Park', 33.6467, -84.4247, 'ZONE5'),
            ('STOP015', 'East Point', 33.6527, -84.4217, 'ZONE5'),
        ]
        
        with conn.cursor() as cursor:
            extras.execute_values(
                cursor,
                "INSERT INTO gtfs_stops (stop_id, stop_name, stop_lat, stop_lon, zone_id) VALUES %s ON CONFLICT (stop_id) DO NOTHING",
                stops_data
            )
            conn.commit()
            logger.info(f"Created {len(stops_data)} demo stops")
    
    def _create_demo_routes(self, conn):
        """Create demo routes representing major MARTA lines"""
        routes_data = [
            ('ROUTE001', 'Red Line', 'North Springs to Airport', 1),
            ('ROUTE002', 'Gold Line', 'Doraville to Airport', 1),
            ('ROUTE003', 'Blue Line', 'Hamilton E Holmes to Indian Creek', 1),
            ('ROUTE004', 'Green Line', 'Bankhead to Edgewood/Candler Park', 1),
            ('ROUTE005', 'Bus Route 1', 'Five Points to Buckhead', 3),
            ('ROUTE006', 'Bus Route 2', 'Midtown to Decatur', 3),
            ('ROUTE007', 'Bus Route 3', 'Airport to Downtown', 3),
        ]
        
        with conn.cursor() as cursor:
            extras.execute_values(
                cursor,
                "INSERT INTO gtfs_routes (route_id, route_short_name, route_long_name, route_type) VALUES %s ON CONFLICT (route_id) DO NOTHING",
                routes_data
            )
            conn.commit()
            logger.info(f"Created {len(routes_data)} demo routes")
    
    def _create_demo_trips(self, conn):
        """Create demo trips for each route"""
        trips_data = []
        trip_id_counter = 1
        
        for route_id in ['ROUTE001', 'ROUTE002', 'ROUTE003', 'ROUTE004']:
            for direction in [0, 1]:  # 0 = outbound, 1 = inbound
                for hour in range(6, 22):  # 6 AM to 10 PM
                    for minute in [0, 15, 30, 45]:  # Every 15 minutes
                        trip_id = f"TRIP{trip_id_counter:06d}"
                        trips_data.append((trip_id, route_id, f"SERVICE_{route_id}", direction))
                        trip_id_counter += 1
        
        with conn.cursor() as cursor:
            extras.execute_values(
                cursor,
                "INSERT INTO gtfs_trips (trip_id, route_id, service_id, direction_id) VALUES %s ON CONFLICT (trip_id) DO NOTHING",
                trips_data
            )
            conn.commit()
            logger.info(f"Created {len(trips_data)} demo trips")
    
    def _create_demo_stop_times(self, conn):
        """Create demo stop times for trips"""
        # Get all trips and stops
        trips_df = pd.read_sql("SELECT trip_id, route_id FROM gtfs_trips LIMIT 100", conn)
        stops_df = pd.read_sql("SELECT stop_id FROM gtfs_stops", conn)
        
        stop_times_data = []
        
        for _, trip in trips_df.iterrows():
            # Assign 5-8 stops per trip
            num_stops = np.random.randint(5, 9)
            selected_stops = stops_df.sample(n=num_stops)['stop_id'].tolist()
            
            base_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
            
            for i, stop_id in enumerate(selected_stops):
                arrival_time = base_time + timedelta(minutes=i*10)
                departure_time = arrival_time + timedelta(minutes=2)
                
                stop_times_data.append((
                    trip['trip_id'],
                    stop_id,
                    i + 1,
                    arrival_time.time(),
                    departure_time.time()
                ))
        
        with conn.cursor() as cursor:
            extras.execute_values(
                cursor,
                "INSERT INTO gtfs_stop_times (trip_id, stop_id, stop_sequence, arrival_time, departure_time) VALUES %s",
                stop_times_data
            )
            conn.commit()
            logger.info(f"Created {len(stop_times_data)} demo stop times")
    
    def _create_demo_unified_data(self, conn):
        """Create demo unified data (simulated real-time + historical)"""
        # Generate 7 days of historical data
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        unified_data = []
        
        # Get sample trips and stops
        trips_df = pd.read_sql("SELECT trip_id, route_id FROM gtfs_trips LIMIT 50", conn)
        stops_df = pd.read_sql("SELECT stop_id, stop_lat, stop_lon FROM gtfs_stops", conn)
        
        current_time = start_date
        
        while current_time <= end_date:
            for _, trip in trips_df.iterrows():
                for _, stop in stops_df.iterrows():
                    # Simulate realistic demand patterns
                    hour = current_time.hour
                    day_of_week = current_time.strftime('%A')
                    is_weekend = current_time.weekday() >= 5
                    
                    # Base demand varies by time and day
                    base_demand = 20
                    if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hours
                        base_demand = 80
                    elif is_weekend:
                        base_demand = 40
                    
                    # Add randomness
                    dwell_time = np.random.poisson(base_demand * 0.5) + 30  # 30 seconds minimum
                    
                    # Simulate weather impact
                    weather_conditions = ['Clear', 'Cloudy', 'Rainy', 'Sunny']
                    weather = np.random.choice(weather_conditions, p=[0.4, 0.3, 0.2, 0.1])
                    
                    # Temperature varies by season
                    temperature = np.random.normal(20, 10)  # 20°C average, 10°C std
                    
                    # Event flag (5% chance of major event)
                    event_flag = np.random.random() < 0.05
                    
                    # Delay simulation
                    delay = np.random.normal(2, 5)  # 2 min average delay, 5 min std
                    
                    # Demand level classification
                    if dwell_time > 120:
                        demand_level = 'Overloaded'
                    elif dwell_time > 60:
                        demand_level = 'High'
                    elif dwell_time > 30:
                        demand_level = 'Normal'
                    else:
                        demand_level = 'Low'
                    
                    unified_data.append((
                        current_time,
                        trip['trip_id'],
                        stop['stop_id'],
                        trip['route_id'],
                        f"VEH_{np.random.randint(1000, 9999)}",
                        stop['stop_lat'] + np.random.normal(0, 0.001),  # Add GPS noise
                        stop['stop_lon'] + np.random.normal(0, 0.001),
                        current_time - timedelta(minutes=5),  # Scheduled arrival
                        current_time + timedelta(seconds=delay*60),  # Actual arrival
                        delay,
                        dwell_time,
                        demand_level,
                        weather,
                        temperature,
                        event_flag,
                        day_of_week,
                        hour,
                        is_weekend
                    ))
            
            current_time += timedelta(hours=1)
        
        # Insert in batches
        batch_size = 1000
        for i in range(0, len(unified_data), batch_size):
            batch = unified_data[i:i+batch_size]
            with conn.cursor() as cursor:
                extras.execute_values(
                    cursor,
                    """INSERT INTO unified_data 
                    (timestamp, trip_id, stop_id, route_id, vehicle_id, latitude, longitude,
                     scheduled_arrival, actual_arrival, delay_minutes, dwell_time_seconds,
                     inferred_demand_level, weather_condition, temperature_celsius, event_flag,
                     day_of_week, hour_of_day, is_weekend) VALUES %s""",
                    batch
                )
                conn.commit()
        
        logger.info(f"Created {len(unified_data)} demo unified data records")


if __name__ == "__main__":
    ingestor = SimpleGTFSIngestion()
    ingestor.create_demo_data() 