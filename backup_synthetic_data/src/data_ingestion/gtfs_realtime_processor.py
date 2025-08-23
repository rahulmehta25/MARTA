"""
GTFS-Realtime Data Processor
Handles continuous polling and processing of MARTA's GTFS-RT feeds
"""
import os
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
import psycopg2
from psycopg2 import extras
import pandas as pd
import numpy as np

from google.transit import gtfs_realtime_pb2

from config.settings import settings

logger = logging.getLogger(__name__)


class GTFSRealtimeProcessor:
    """Handles GTFS-Realtime data processing from MARTA"""
    
    def __init__(self):
        self.db_connection = None
        self.headers = {}
        
        # Set up API headers if API key is available
        if settings.MARTA_API_KEY:
            self.headers = {"x-api-key": settings.MARTA_API_KEY}
        
        # Create unified data table for real-time data
        self.create_unified_table()
    
    def create_db_connection(self):
        """Create database connection"""
        try:
            self.db_connection = psycopg2.connect(
                host=settings.DB_HOST,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                port=settings.DB_PORT
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def create_unified_table(self):
        """Create unified table for real-time and historical data"""
        if not self.db_connection:
            self.create_db_connection()
        
        create_unified_table_sql = """
            CREATE TABLE IF NOT EXISTS unified_realtime_historical_data (
                record_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
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
                weather_condition VARCHAR(100),
                temperature_celsius NUMERIC,
                precipitation_mm NUMERIC,
                event_flag BOOLEAN DEFAULT FALSE,
                day_of_week VARCHAR(20),
                hour_of_day INTEGER,
                is_weekend BOOLEAN,
                is_holiday BOOLEAN DEFAULT FALSE,
                zone_id VARCHAR(255),
                nearby_pois_count INTEGER,
                historical_dwell_time_avg NUMERIC,
                historical_headway_avg NUMERIC,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Create indexes for better query performance
            CREATE INDEX IF NOT EXISTS idx_unified_timestamp ON unified_realtime_historical_data(timestamp);
            CREATE INDEX IF NOT EXISTS idx_unified_trip_id ON unified_realtime_historical_data(trip_id);
            CREATE INDEX IF NOT EXISTS idx_unified_stop_id ON unified_realtime_historical_data(stop_id);
            CREATE INDEX IF NOT EXISTS idx_unified_route_id ON unified_realtime_historical_data(route_id);
        """
        
        with self.db_connection.cursor() as cursor:
            cursor.execute(create_unified_table_sql)
            self.db_connection.commit()
            logger.info("Unified real-time historical data table created")
    
    def fetch_and_parse_feed(self, url: str, feed_type: str) -> Optional[gtfs_realtime_pb2.FeedMessage]:
        """Fetch and parse GTFS-RT feed"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            response.raise_for_status()
            
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            logger.debug(f"Successfully fetched {feed_type} feed with {len(feed.entity)} entities")
            return feed
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {feed_type} feed from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing {feed_type} feed: {e}")
            return None
    
    def process_vehicle_positions(self, feed: gtfs_realtime_pb2.FeedMessage) -> List[Dict[str, Any]]:
        """Process vehicle positions from GTFS-RT feed"""
        if not feed:
            return []
        
        processed_data = []
        for entity in feed.entity:
            if entity.HasField('vehicle'):
                vehicle = entity.vehicle
                
                # Extract vehicle position data
                vehicle_data = {
                    "id": entity.id,
                    "trip_id": vehicle.trip.trip_id if vehicle.HasField('trip') else None,
                    "route_id": vehicle.trip.route_id if vehicle.HasField('trip') else None,
                    "vehicle_id": vehicle.vehicle.id if vehicle.HasField('vehicle') else None,
                    "latitude": vehicle.position.latitude if vehicle.HasField('position') else None,
                    "longitude": vehicle.position.longitude if vehicle.HasField('position') else None,
                    "bearing": vehicle.position.bearing if vehicle.HasField('position') else None,
                    "speed": vehicle.position.speed if vehicle.HasField('position') else None,
                    "timestamp": datetime.fromtimestamp(vehicle.timestamp) if vehicle.HasField('timestamp') else None,
                    "current_status": gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus.Name(vehicle.current_status) if vehicle.HasField('current_status') else None
                }
                processed_data.append(vehicle_data)
        
        return processed_data
    
    def process_trip_updates(self, feed: gtfs_realtime_pb2.FeedMessage) -> List[Dict[str, Any]]:
        """Process trip updates from GTFS-RT feed"""
        if not feed:
            return []
        
        processed_data = []
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                trip_update = entity.trip_update
                
                # Process stop time updates
                for stop_time_update in trip_update.stop_time_update:
                    update_data = {
                        "id": entity.id,
                        "trip_id": trip_update.trip.trip_id if trip_update.HasField('trip') else None,
                        "route_id": trip_update.trip.route_id if trip_update.HasField('trip') else None,
                        "direction_id": trip_update.trip.direction_id if trip_update.trip.HasField('direction_id') else None,
                        "start_time": trip_update.trip.start_time if trip_update.trip.HasField('start_time') else None,
                        "start_date": trip_update.trip.start_date if trip_update.trip.HasField('start_date') else None,
                        "timestamp": datetime.fromtimestamp(trip_update.timestamp) if trip_update.HasField('timestamp') else None,
                        "stop_id": stop_time_update.stop_id,
                        "stop_sequence": stop_time_update.stop_sequence if stop_time_update.HasField('stop_sequence') else None,
                        "arrival_delay": stop_time_update.arrival.delay if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('delay') else None,
                        "arrival_time": datetime.fromtimestamp(stop_time_update.arrival.time) if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('time') else None,
                        "departure_delay": stop_time_update.departure.delay if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('delay') else None,
                        "departure_time": datetime.fromtimestamp(stop_time_update.departure.time) if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('time') else None,
                    }
                    processed_data.append(update_data)
        
        return processed_data
    
    def enrich_with_static_data(self, realtime_data: List[Dict[str, Any]], data_type: str) -> List[Dict[str, Any]]:
        """Enrich real-time data with static GTFS information"""
        if not realtime_data:
            return []
        
        enriched_data = []
        
        for record in realtime_data:
            enriched_record = record.copy()
            
            # Add temporal features
            if record.get('timestamp'):
                timestamp = record['timestamp']
                enriched_record.update({
                    "day_of_week": timestamp.strftime("%A"),
                    "hour_of_day": timestamp.hour,
                    "is_weekend": timestamp.weekday() >= 5,
                    "is_holiday": self.is_holiday(timestamp.date())
                })
            
            # Add static GTFS data if trip_id is available
            if record.get('trip_id'):
                static_data = self.get_static_trip_data(record['trip_id'])
                if static_data:
                    enriched_record.update(static_data)
            
            # Calculate delay if both scheduled and actual times are available
            if data_type == "trip_updates":
                enriched_record = self.calculate_delays(enriched_record)
            
            enriched_data.append(enriched_record)
        
        return enriched_data
    
    def get_static_trip_data(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Get static GTFS data for a trip"""
        if not self.db_connection:
            return None
        
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute("""
                    SELECT t.route_id, r.route_short_name, r.route_long_name
                    FROM gtfs_trips t
                    JOIN gtfs_routes r ON t.route_id = r.route_id
                    WHERE t.trip_id = %s
                """, (trip_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "route_id": result[0],
                        "route_short_name": result[1],
                        "route_long_name": result[2]
                    }
        except Exception as e:
            logger.error(f"Error fetching static trip data: {e}")
        
        return None
    
    def calculate_delays(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate delays between scheduled and actual times"""
        if record.get('arrival_time') and record.get('scheduled_arrival_time'):
            arrival_delay = (record['arrival_time'] - record['scheduled_arrival_time']).total_seconds() / 60
            record['delay_minutes'] = arrival_delay
        
        if record.get('departure_time') and record.get('scheduled_departure_time'):
            departure_delay = (record['departure_time'] - record['scheduled_departure_time']).total_seconds() / 60
            record['departure_delay_minutes'] = departure_delay
        
        return record
    
    def is_holiday(self, date) -> bool:
        """Check if date is a holiday (simplified implementation)"""
        # This is a simplified implementation
        # In production, you'd use a proper holiday calendar
        holidays_2024 = [
            "2024-01-01",  # New Year's Day
            "2024-01-15",  # Martin Luther King Jr. Day
            "2024-02-19",  # Presidents' Day
            "2024-05-27",  # Memorial Day
            "2024-07-04",  # Independence Day
            "2024-09-02",  # Labor Day
            "2024-10-14",  # Columbus Day
            "2024-11-11",  # Veterans Day
            "2024-11-28",  # Thanksgiving Day
            "2024-12-25",  # Christmas Day
        ]
        
        return date.strftime("%Y-%m-%d") in holidays_2024
    
    def store_realtime_data(self, data: List[Dict[str, Any]]):
        """Store processed real-time data in database"""
        if not data:
            return
        
        if not self.db_connection:
            self.create_db_connection()
        
        # Prepare data for insertion
        columns = [
            "timestamp", "trip_id", "route_id", "stop_id", "stop_sequence",
            "vehicle_id", "latitude", "longitude", "scheduled_arrival_time",
            "actual_arrival_time", "scheduled_departure_time", "actual_departure_time",
            "delay_minutes", "day_of_week", "hour_of_day", "is_weekend", "is_holiday"
        ]
        
        data_to_insert = []
        for record in data:
            row = []
            for col in columns:
                row.append(record.get(col))
            data_to_insert.append(tuple(row))
        
        # Insert data
        cols_str = ', '.join(columns)
        vals_str = ', '.join([f'%s' for _ in columns])
        
        insert_query = f"""
            INSERT INTO unified_realtime_historical_data ({cols_str})
            VALUES %s
        """
        
        try:
            with self.db_connection.cursor() as cursor:
                extras.execute_values(cursor, insert_query, data_to_insert, page_size=1000)
                self.db_connection.commit()
                logger.info(f"Stored {len(data_to_insert)} real-time records")
        except Exception as e:
            self.db_connection.rollback()
            logger.error(f"Error storing real-time data: {e}")
            raise
    
    def ingest_historical_realtime_data(self, num_iterations: int = 10, interval_seconds: int = 30):
        """Fetches and processes GTFS-RT feeds for a specified number of iterations.
        This is for historical data ingestion for model training.
        """
        logger.info(f"Starting historical GTFS-RT data ingestion for {num_iterations} iterations...")
        
        for i in range(num_iterations):
            logger.debug(f"Fetching GTFS-RT data (iteration {i+1}/{num_iterations}) at {datetime.now().isoformat()}")
            
            # Fetch and process Vehicle Positions
            vp_feed = self.fetch_and_parse_feed(
                settings.MARTA_GTFS_RT_VEHICLE_URL, 
                "Vehicle Positions"
            )
            vehicle_positions_data = self.process_vehicle_positions(vp_feed)
            
            if vehicle_positions_data:
                logger.info(f"Processed {len(vehicle_positions_data)} vehicle positions")
                # Store vehicle position data
                self.store_realtime_data(vehicle_positions_data)
            
            # Fetch and process Trip Updates
            tu_feed = self.fetch_and_parse_feed(
                settings.MARTA_GTFS_RT_TRIP_URL, 
                "Trip Updates"
            )
            trip_updates_data = self.process_trip_updates(tu_feed)
            
            if trip_updates_data:
                # Enrich trip updates with static data
                enriched_trip_data = self.enrich_with_static_data(trip_updates_data, "trip_updates")
                logger.info(f"Processed {len(enriched_trip_data)} trip updates")
                # Store trip update data
                self.store_realtime_data(enriched_trip_data)
            
            if i < num_iterations - 1:
                time.sleep(interval_seconds)
        
        logger.info("Historical GTFS-RT data ingestion completed.")

    def ingest_historical_realtime_data(self, num_iterations: int = 10, interval_seconds: int = 30):
        """Fetches and processes GTFS-RT feeds for a specified number of iterations.
        This is for historical data ingestion for model training.
        """
        logger.info(f"Starting historical GTFS-RT data ingestion for {num_iterations} iterations...")
        
        for i in range(num_iterations):
            logger.debug(f"Fetching GTFS-RT data (iteration {i+1}/{num_iterations}) at {datetime.now().isoformat()}")
            
            # Fetch and process Vehicle Positions
            vp_feed = self.fetch_and_parse_feed(
                settings.MARTA_GTFS_RT_VEHICLE_URL, 
                "Vehicle Positions"
            )
            vehicle_positions_data = self.process_vehicle_positions(vp_feed)
            
            if vehicle_positions_data:
                logger.info(f"Processed {len(vehicle_positions_data)} vehicle positions")
                # Store vehicle position data
                self.store_realtime_data(vehicle_positions_data)
            
            # Fetch and process Trip Updates
            tu_feed = self.fetch_and_parse_feed(
                settings.MARTA_GTFS_RT_TRIP_URL, 
                "Trip Updates"
            )
            trip_updates_data = self.process_trip_updates(tu_feed)
            
            if trip_updates_data:
                # Enrich trip updates with static data
                enriched_trip_data = self.enrich_with_static_data(trip_updates_data, "trip_updates")
                logger.info(f"Processed {len(enriched_trip_data)} trip updates")
                # Store trip update data
                self.store_realtime_data(enriched_trip_data)
            
            if i < num_iterations - 1:
                time.sleep(interval_seconds)
        
        logger.info("Historical GTFS-RT data ingestion completed.")

    def generate_synthetic_realtime_data(self, num_days: int = 7):
        """Generates and ingests synthetic real-time data based on static GTFS.
        This is used when real-time API is unavailable or for demo purposes.
        """
        logger.info(f"Generating {num_days} days of synthetic real-time data...")

        if not self.db_connection:
            self.create_db_connection()

        try:
            # Fetch static GTFS data
            trips_df = pd.read_sql("SELECT trip_id, route_id, service_id FROM gtfs_trips", self.db_connection)
            stop_times_df = pd.read_sql("SELECT trip_id, stop_id, stop_sequence, arrival_time, departure_time FROM gtfs_stop_times", self.db_connection)
            stops_df = pd.read_sql("SELECT stop_id, stop_lat, stop_lon FROM gtfs_stops", self.db_connection)

            # Merge dataframes
            merged_df = pd.merge(stop_times_df, trips_df, on='trip_id')
            merged_df = pd.merge(merged_df, stops_df, on='stop_id')

            synthetic_data = []
            current_date = datetime.now().date() - timedelta(days=num_days)

            for day_offset in range(num_days):
                date_to_simulate = current_date + timedelta(days=day_offset)
                logger.info(f"Simulating data for {date_to_simulate}...")

                for _, row in merged_df.iterrows():
                    # Simulate timestamp
                    scheduled_arrival_str = row['arrival_time']
                    scheduled_departure_str = row['departure_time']

                    # Convert time strings to timedelta for calculation
                    try:
                        # Handle potential 'days' in timedelta if time crosses midnight
                        h, m, s = map(int, scheduled_arrival_str.split(':'))
                        scheduled_arrival_td = timedelta(hours=h, minutes=m, seconds=s)
                        h, m, s = map(int, scheduled_departure_str.split(':'))
                        scheduled_departure_td = timedelta(hours=h, minutes=m, seconds=s)
                    except ValueError:
                        # Handle cases where time might be > 24:00:00 (GTFS extended times)
                        # For simplicity, cap at 23:59:59 for now or handle more robustly
                        logger.warning(f"Invalid time format or extended time: {scheduled_arrival_str} or {scheduled_departure_str}. Skipping row.")
                        continue

                    # Combine date and time
                    scheduled_arrival_time = datetime.combine(date_to_simulate, (datetime.min + scheduled_arrival_td).time())
                    scheduled_departure_time = datetime.combine(date_to_simulate, (datetime.min + scheduled_departure_td).time())

                    # Simulate delay (normal distribution around 2 minutes, std dev 5 minutes)
                    delay_minutes = np.random.normal(2, 5)
                    actual_arrival_time = scheduled_arrival_time + timedelta(minutes=delay_minutes)
                    actual_departure_time = scheduled_departure_time + timedelta(minutes=delay_minutes + np.random.normal(0, 1)) # Add small noise to departure

                    # Ensure actual times are not before scheduled times (simple correction)
                    if actual_arrival_time < scheduled_arrival_time:
                        actual_arrival_time = scheduled_arrival_time
                    if actual_departure_time < scheduled_departure_time:
                        actual_departure_time = scheduled_departure_time

                    inferred_dwell_time_seconds = (actual_departure_time - actual_arrival_time).total_seconds()
                    if inferred_dwell_time_seconds < 0: inferred_dwell_time_seconds = 0 # Ensure non-negative

                    # Simulate demand level based on dwell time
                    if inferred_dwell_time_seconds > 120:
                        inferred_demand_level = 'Overloaded'
                    elif inferred_dwell_time_seconds > 60:
                        inferred_demand_level = 'High'
                    elif inferred_dwell_time_seconds > 30:
                        inferred_demand_level = 'Normal'
                    else:
                        inferred_demand_level = 'Low'

                    # Simulate weather (simplified)
                    weather_conditions = ['Clear', 'Cloudy', 'Rainy', 'Sunny']
                    weather_condition = np.random.choice(weather_conditions, p=[0.4, 0.3, 0.2, 0.1])
                    temperature_celsius = np.random.normal(20, 5) # Avg 20C, std 5C
                    precipitation_mm = np.random.uniform(0, 10) if weather_condition == 'Rainy' else 0

                    # Simulate event flag (low probability)
                    event_flag = np.random.rand() < 0.01

                    # Temporal features
                    day_of_week = date_to_simulate.strftime("%A")
                    hour_of_day = scheduled_arrival_time.hour
                    is_weekend = date_to_simulate.weekday() >= 5
                    is_holiday = self.is_holiday(date_to_simulate) # Re-use existing holiday check

                    synthetic_data.append({
                        "timestamp": actual_arrival_time,
                        "trip_id": row['trip_id'],
                        "route_id": row['route_id'],
                        "stop_id": row['stop_id'],
                        "stop_sequence": row['stop_sequence'],
                        "vehicle_id": f"VEH_{np.random.randint(1000, 9999)}",
                        "latitude": row['stop_lat'] + np.random.normal(0, 0.0001), # Add small noise
                        "longitude": row['stop_lon'] + np.random.normal(0, 0.0001), # Add small noise
                        "scheduled_arrival_time": scheduled_arrival_time,
                        "actual_arrival_time": actual_arrival_time,
                        "scheduled_departure_time": scheduled_departure_time,
                        "actual_departure_time": actual_departure_time,
                        "delay_minutes": delay_minutes,
                        "inferred_dwell_time_seconds": inferred_dwell_time_seconds,
                        "inferred_demand_level": inferred_demand_level,
                        "weather_condition": weather_condition,
                        "temperature_celsius": temperature_celsius,
                        "precipitation_mm": precipitation_mm,
                        "event_flag": event_flag,
                        "day_of_week": day_of_week,
                        "hour_of_day": hour_of_day,
                        "is_weekend": is_weekend,
                        "is_holiday": is_holiday,
                        "zone_id": None, # Not available from static GTFS, can be added later
                        "nearby_pois_count": None, # Not available from static GTFS, can be added later
                        "historical_dwell_time_avg": None, # Calculated later
                        "historical_headway_avg": None # Calculated later
                    })
            
            # Store generated data in batches
            if synthetic_data:
                self.store_realtime_data(synthetic_data)
                synthetic_data = [] # Clear for next batch/day

        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
            raise

        logger.info("Synthetic real-time data generation completed.")

    def process_gtfs_realtime_stream(self, interval_seconds: int = None):
        """Main method to process GTFS-RT streams continuously"""
        if interval_seconds is None:
            interval_seconds = settings.GTFS_RT_POLL_INTERVAL
        
        logger.info(f"Starting GTFS-RT processing stream, polling every {interval_seconds} seconds...")
        
        while True:
            try:
                logger.debug(f"Fetching GTFS-RT data at {datetime.now().isoformat()}")
                
                # Fetch and process Vehicle Positions
                vp_feed = self.fetch_and_parse_feed(
                    settings.MARTA_GTFS_RT_VEHICLE_URL, 
                    "Vehicle Positions"
                )
                vehicle_positions_data = self.process_vehicle_positions(vp_feed)
                
                if vehicle_positions_data:
                    logger.info(f"Processed {len(vehicle_positions_data)} vehicle positions")
                    # Store vehicle position data
                    self.store_realtime_data(vehicle_positions_data)
                
                # Fetch and process Trip Updates
                tu_feed = self.fetch_and_parse_feed(
                    settings.MARTA_GTFS_RT_TRIP_URL, 
                    "Trip Updates"
                )
                trip_updates_data = self.process_trip_updates(tu_feed)
                
                if trip_updates_data:
                    # Enrich trip updates with static data
                    enriched_trip_data = self.enrich_with_static_data(trip_updates_data, "trip_updates")
                    logger.info(f"Processed {len(enriched_trip_data)} trip updates")
                    # Store trip update data
                    self.store_realtime_data(enriched_trip_data)
                
                # Wait before next poll
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("GTFS-RT processing stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in GTFS-RT processing: {e}")
                time.sleep(interval_seconds)  # Continue polling even after errors
    
    def get_recent_data(self, hours: int = 24) -> pd.DataFrame:
        """Get recent real-time data for analysis"""
        if not self.db_connection:
            self.create_db_connection()
        
        query = """
            SELECT * FROM unified_realtime_historical_data
            WHERE timestamp >= NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC
        """
        
        try:
            df = pd.read_sql_query(query, self.db_connection, params=(hours,))
            return df
        except Exception as e:
            logger.error(f"Error fetching recent data: {e}")
            return pd.DataFrame()


def main():
    """Main function for GTFS-RT processing"""
    logging.basicConfig(level=logging.INFO)
    
    processor = GTFSRealtimeProcessor()
    
    # Start continuous processing
    processor.process_gtfs_realtime_stream()


if __name__ == "__main__":
    main() 