#!/usr/bin/env python3
"""
Real GTFS-Realtime Data Ingestion for MARTA
Fetches and processes actual real-time data from MARTA GTFS-RT API
"""
import os
import sys
import logging
import requests
import psycopg2
from psycopg2 import extras
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import time
import json
import threading
from queue import Queue
import signal
import atexit

# GTFS-Realtime bindings
try:
    from google.transit import gtfs_realtime_pb2
    from google.protobuf import text_format
except ImportError:
    print("Warning: gtfs-realtime-bindings not installed. Install with: pip install gtfs-realtime-bindings")
    gtfs_realtime_pb2 = None

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealGTFSRealtimeIngestor:
    """Real GTFS-Realtime data ingestion from MARTA GTFS-RT API"""
    
    def __init__(self):
        # MARTA GTFS-RT API endpoints
        self.vehicle_positions_url = "https://api.marta.io/gtfs-rt/vehicle-positions/vehicle.pb"
        self.trip_updates_url = "https://api.marta.io/gtfs-rt/trip-updates/tripupdate.pb"
        self.api_key = os.getenv("MARTA_API_KEY")
        
        # Database configuration
        self.db_config = {
            'host': settings.DB_HOST,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD
        }
        
        # Streaming configuration
        self.polling_interval = 90  # seconds (GTFS-RT best practice)
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # Data storage
        self.data_queue = Queue()
        self.is_running = False
        self.thread = None
        
        # Statistics
        self.stats = {
            'vehicle_positions_received': 0,
            'trip_updates_received': 0,
            'errors': 0,
            'last_successful_fetch': None,
            'start_time': None
        }
    
    def create_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_config)
    
    def create_realtime_tables(self, conn):
        """Create real-time data tables if they don't exist"""
        logger.info("Creating real-time data tables...")
        
        with conn.cursor() as cursor:
            # Create vehicle positions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gtfs_vehicle_positions (
                    id SERIAL PRIMARY KEY,
                    vehicle_id VARCHAR(255),
                    trip_id VARCHAR(255),
                    route_id VARCHAR(255),
                    latitude NUMERIC,
                    longitude NUMERIC,
                    bearing NUMERIC,
                    speed NUMERIC,
                    timestamp TIMESTAMP,
                    current_status VARCHAR(50),
                    congestion_level VARCHAR(50),
                    occupancy_status VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create trip updates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gtfs_trip_updates (
                    id SERIAL PRIMARY KEY,
                    trip_id VARCHAR(255),
                    route_id VARCHAR(255),
                    direction_id INTEGER,
                    start_time VARCHAR(10),
                    start_date VARCHAR(8),
                    stop_id VARCHAR(255),
                    stop_sequence INTEGER,
                    arrival_delay INTEGER,
                    arrival_time TIMESTAMP,
                    departure_delay INTEGER,
                    departure_time TIMESTAMP,
                    schedule_relationship VARCHAR(50),
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create unified real-time data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS unified_realtime_data (
                    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    timestamp TIMESTAMP,
                    trip_id VARCHAR(255),
                    route_id VARCHAR(255),
                    stop_id VARCHAR(255),
                    stop_sequence INTEGER,
                    vehicle_id VARCHAR(255),
                    latitude NUMERIC,
                    longitude NUMERIC,
                    scheduled_arrival_time TIMESTAMP,
                    actual_arrival_time TIMESTAMP,
                    scheduled_departure_time TIMESTAMP,
                    actual_departure_time TIMESTAMP,
                    delay_minutes NUMERIC,
                    inferred_dwell_time_seconds NUMERIC,
                    inferred_demand_level VARCHAR(50),
                    weather_condition VARCHAR(50),
                    temperature_celsius NUMERIC,
                    precipitation_mm NUMERIC,
                    event_flag BOOLEAN,
                    day_of_week VARCHAR(20),
                    hour_of_day INTEGER,
                    is_weekend BOOLEAN,
                    is_holiday BOOLEAN,
                    zone_id VARCHAR(255),
                    nearby_pois_count INTEGER,
                    historical_dwell_time_avg NUMERIC,
                    historical_headway_avg NUMERIC,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vehicle_positions_timestamp 
                ON gtfs_vehicle_positions(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trip_updates_timestamp 
                ON gtfs_trip_updates(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_unified_realtime_timestamp 
                ON unified_realtime_data(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_unified_realtime_stop_id 
                ON unified_realtime_data(stop_id)
            """)
            
            conn.commit()
            logger.info("Real-time data tables created successfully")
    
    def fetch_vehicle_positions(self) -> Optional[gtfs_realtime_pb2.FeedMessage]:
        """Fetch real-time vehicle positions from MARTA GTFS-RT API"""
        try:
            headers = {}
            if self.api_key:
                headers['x-api-key'] = self.api_key
            
            response = requests.get(
                self.vehicle_positions_url, 
                headers=headers, 
                timeout=30
            )
            response.raise_for_status()
            
            if not gtfs_realtime_pb2:
                logger.error("gtfs-realtime-bindings not available")
                return None
            
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            logger.info(f"Fetched {len(feed.entity)} vehicle positions")
            self.stats['vehicle_positions_received'] += len(feed.entity)
            self.stats['last_successful_fetch'] = datetime.now()
            
            return feed
            
        except Exception as e:
            logger.error(f"Error fetching vehicle positions: {e}")
            self.stats['errors'] += 1
            return None
    
    def fetch_trip_updates(self) -> Optional[gtfs_realtime_pb2.FeedMessage]:
        """Fetch real-time trip updates from MARTA GTFS-RT API"""
        try:
            headers = {}
            if self.api_key:
                headers['x-api-key'] = self.api_key
            
            response = requests.get(
                self.trip_updates_url, 
                headers=headers, 
                timeout=30
            )
            response.raise_for_status()
            
            if not gtfs_realtime_pb2:
                logger.error("gtfs-realtime-bindings not available")
                return None
            
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            logger.info(f"Fetched {len(feed.entity)} trip updates")
            self.stats['trip_updates_received'] += len(feed.entity)
            self.stats['last_successful_fetch'] = datetime.now()
            
            return feed
            
        except Exception as e:
            logger.error(f"Error fetching trip updates: {e}")
            self.stats['errors'] += 1
            return None
    
    def process_vehicle_positions(self, feed: gtfs_realtime_pb2.FeedMessage, conn) -> int:
        """Process and store vehicle positions"""
        if not feed:
            return 0
        
        processed_count = 0
        
        try:
            with conn.cursor() as cursor:
                for entity in feed.entity:
                    if entity.HasField('vehicle'):
                        vehicle = entity.vehicle
                        
                        # Extract vehicle position data
                        vehicle_data = {
                            'vehicle_id': vehicle.vehicle.id if vehicle.HasField('vehicle') else None,
                            'trip_id': vehicle.trip.trip_id if vehicle.HasField('trip') else None,
                            'route_id': vehicle.trip.route_id if vehicle.HasField('trip') else None,
                            'latitude': vehicle.position.latitude if vehicle.HasField('position') else None,
                            'longitude': vehicle.position.longitude if vehicle.HasField('position') else None,
                            'bearing': vehicle.position.bearing if vehicle.HasField('position') else None,
                            'speed': vehicle.position.speed if vehicle.HasField('position') else None,
                            'timestamp': datetime.fromtimestamp(vehicle.timestamp) if vehicle.HasField('timestamp') else None,
                            'current_status': gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus.Name(vehicle.current_status) if vehicle.HasField('current_status') else None,
                            'congestion_level': gtfs_realtime_pb2.VehiclePosition.CongestionLevel.Name(vehicle.congestion_level) if vehicle.HasField('congestion_level') else None,
                            'occupancy_status': gtfs_realtime_pb2.VehiclePosition.OccupancyStatus.Name(vehicle.occupancy_status) if vehicle.HasField('occupancy_status') else None
                        }
                        
                        # Insert into database
                        cursor.execute("""
                            INSERT INTO gtfs_vehicle_positions 
                            (vehicle_id, trip_id, route_id, latitude, longitude, bearing, speed, 
                             timestamp, current_status, congestion_level, occupancy_status)
                            VALUES (%(vehicle_id)s, %(trip_id)s, %(route_id)s, %(latitude)s, %(longitude)s,
                                    %(bearing)s, %(speed)s, %(timestamp)s, %(current_status)s,
                                    %(congestion_level)s, %(occupancy_status)s)
                        """, vehicle_data)
                        
                        processed_count += 1
                
                conn.commit()
                logger.info(f"Processed {processed_count} vehicle positions")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error processing vehicle positions: {e}")
            self.stats['errors'] += 1
        
        return processed_count
    
    def process_trip_updates(self, feed: gtfs_realtime_pb2.FeedMessage, conn) -> int:
        """Process and store trip updates"""
        if not feed:
            return 0
        
        processed_count = 0
        
        try:
            with conn.cursor() as cursor:
                for entity in feed.entity:
                    if entity.HasField('trip_update'):
                        trip_update = entity.trip_update
                        
                        # Process each stop time update
                        for stop_time_update in trip_update.stop_time_update:
                            trip_data = {
                                'trip_id': trip_update.trip.trip_id if trip_update.HasField('trip') else None,
                                'route_id': trip_update.trip.route_id if trip_update.HasField('trip') else None,
                                'direction_id': trip_update.trip.direction_id if trip_update.HasField('trip') else None,
                                'start_time': trip_update.trip.start_time if trip_update.HasField('trip') else None,
                                'start_date': trip_update.trip.start_date if trip_update.HasField('trip') else None,
                                'stop_id': stop_time_update.stop_id,
                                'stop_sequence': stop_time_update.stop_sequence,
                                'arrival_delay': stop_time_update.arrival.delay if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('delay') else None,
                                'arrival_time': datetime.fromtimestamp(stop_time_update.arrival.time) if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('time') else None,
                                'departure_delay': stop_time_update.departure.delay if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('delay') else None,
                                'departure_time': datetime.fromtimestamp(stop_time_update.departure.time) if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('time') else None,
                                'schedule_relationship': gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.ScheduleRelationship.Name(stop_time_update.schedule_relationship) if stop_time_update.HasField('schedule_relationship') else None,
                                'timestamp': datetime.fromtimestamp(trip_update.timestamp) if trip_update.HasField('timestamp') else None
                            }
                            
                            # Insert into database
                            cursor.execute("""
                                INSERT INTO gtfs_trip_updates 
                                (trip_id, route_id, direction_id, start_time, start_date, stop_id, stop_sequence,
                                 arrival_delay, arrival_time, departure_delay, departure_time, 
                                 schedule_relationship, timestamp)
                                VALUES (%(trip_id)s, %(route_id)s, %(direction_id)s, %(start_time)s, %(start_date)s,
                                        %(stop_id)s, %(stop_sequence)s, %(arrival_delay)s, %(arrival_time)s,
                                        %(departure_delay)s, %(departure_time)s, %(schedule_relationship)s, %(timestamp)s)
                            """, trip_data)
                            
                            processed_count += 1
                
                conn.commit()
                logger.info(f"Processed {processed_count} trip updates")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error processing trip updates: {e}")
            self.stats['errors'] += 1
        
        return processed_count
    
    def create_unified_data(self, conn):
        """Create unified real-time data by combining GTFS static and real-time data"""
        try:
            logger.info("Creating unified real-time data...")
            
            with conn.cursor() as cursor:
                # Join trip updates with static GTFS data
                cursor.execute("""
                    INSERT INTO unified_realtime_data 
                    (timestamp, trip_id, route_id, stop_id, stop_sequence, vehicle_id,
                     scheduled_arrival_time, actual_arrival_time, scheduled_departure_time, actual_departure_time,
                     delay_minutes, inferred_dwell_time_seconds, day_of_week, hour_of_day, is_weekend)
                    SELECT 
                        tu.timestamp,
                        tu.trip_id,
                        tu.route_id,
                        tu.stop_id,
                        tu.stop_sequence,
                        vp.vehicle_id,
                        st.arrival_time::timestamp + (CURRENT_DATE::date - '1970-01-01'::date) as scheduled_arrival_time,
                        tu.arrival_time as actual_arrival_time,
                        st.departure_time::timestamp + (CURRENT_DATE::date - '1970-01-01'::date) as scheduled_departure_time,
                        tu.departure_time as actual_departure_time,
                        COALESCE(tu.arrival_delay, 0) / 60.0 as delay_minutes,
                        EXTRACT(EPOCH FROM (tu.departure_time - tu.arrival_time)) as inferred_dwell_time_seconds,
                        TO_CHAR(tu.timestamp, 'Day') as day_of_week,
                        EXTRACT(HOUR FROM tu.timestamp) as hour_of_day,
                        EXTRACT(DOW FROM tu.timestamp) IN (0, 6) as is_weekend
                    FROM gtfs_trip_updates tu
                    LEFT JOIN gtfs_stop_times st ON tu.trip_id = st.trip_id AND tu.stop_id = st.stop_id
                    LEFT JOIN gtfs_vehicle_positions vp ON tu.trip_id = vp.trip_id
                    WHERE tu.timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                    ON CONFLICT DO NOTHING
                """)
                
                conn.commit()
                logger.info("Unified real-time data created successfully")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating unified data: {e}")
    
    def fetch_and_process_data(self):
        """Fetch and process real-time data"""
        try:
            conn = self.create_db_connection()
            
            # Fetch vehicle positions
            vehicle_feed = self.fetch_vehicle_positions()
            if vehicle_feed:
                self.process_vehicle_positions(vehicle_feed, conn)
            
            # Fetch trip updates
            trip_feed = self.fetch_trip_updates()
            if trip_feed:
                self.process_trip_updates(trip_feed, conn)
            
            # Create unified data (every 10 minutes)
            if datetime.now().minute % 10 == 0:
                self.create_unified_data(conn)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error in fetch_and_process_data: {e}")
            self.stats['errors'] += 1
    
    def stream_realtime_data(self):
        """Continuous streaming of real-time data"""
        logger.info("Starting real-time data streaming...")
        self.stats['start_time'] = datetime.now()
        
        while self.is_running:
            try:
                self.fetch_and_process_data()
                time.sleep(self.polling_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping...")
                break
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}")
                time.sleep(self.retry_delay)
        
        logger.info("Real-time data streaming stopped")
    
    def start_streaming(self):
        """Start real-time data streaming in a separate thread"""
        if self.is_running:
            logger.warning("Streaming is already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self.stream_realtime_data)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Real-time data streaming started")
    
    def stop_streaming(self):
        """Stop real-time data streaming"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=10)
        
        logger.info("Real-time data streaming stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        stats = self.stats.copy()
        if stats['start_time']:
            stats['uptime'] = datetime.now() - stats['start_time']
        return stats
    
    def run_single_fetch(self) -> bool:
        """Run a single fetch of real-time data (for testing)"""
        try:
            logger.info("Running single real-time data fetch...")
            
            conn = self.create_db_connection()
            self.create_realtime_tables(conn)
            
            self.fetch_and_process_data()
            
            conn.close()
            
            logger.info("Single real-time data fetch completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in single fetch: {e}")
            return False


def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal")
    if hasattr(signal_handler, 'ingestor'):
        signal_handler.ingestor.stop_streaming()


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real GTFS-Realtime Data Ingestion')
    parser.add_argument('--stream', action='store_true', help='Start continuous streaming')
    parser.add_argument('--single-fetch', action='store_true', help='Run single fetch')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    
    args = parser.parse_args()
    
    # Create ingestor
    ingestor = RealGTFSRealtimeIngestor()
    
    # Set up signal handling
    signal_handler.ingestor = ingestor
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(ingestor.stop_streaming)
    
    try:
        if args.stream:
            # Start continuous streaming
            ingestor.start_streaming()
            
            # Keep main thread alive
            try:
                while ingestor.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            
        elif args.single_fetch:
            # Run single fetch
            success = ingestor.run_single_fetch()
            sys.exit(0 if success else 1)
            
        elif args.stats:
            # Show statistics
            stats = ingestor.get_stats()
            print(json.dumps(stats, indent=2, default=str))
            
        else:
            # Default: run single fetch
            success = ingestor.run_single_fetch()
            sys.exit(0 if success else 1)
            
    finally:
        ingestor.stop_streaming()


if __name__ == "__main__":
    main() 