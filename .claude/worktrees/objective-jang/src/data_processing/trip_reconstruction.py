#!/usr/bin/env python3
"""
MARTA Historical Trip Reconstruction Module
Reconstructs historical trips by aligning GTFS-RT data with static GTFS data
"""
import os
import logging
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Unified data table
UNIFIED_TABLE = "unified_data"

CREATE_UNIFIED_TABLE = f'''
CREATE TABLE IF NOT EXISTS {UNIFIED_TABLE} (
    record_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP,
    trip_id TEXT,
    route_id TEXT,
    stop_id TEXT,
    stop_sequence INTEGER,
    vehicle_id TEXT,
    latitude NUMERIC,
    longitude NUMERIC,
    scheduled_arrival_time TIMESTAMP,
    actual_arrival_time TIMESTAMP,
    scheduled_departure_time TIMESTAMP,
    actual_departure_time TIMESTAMP,
    delay_minutes NUMERIC,
    inferred_dwell_time_seconds NUMERIC,
    inferred_demand_level TEXT,
    weather_condition TEXT,
    temperature_celsius NUMERIC,
    precipitation_mm NUMERIC,
    event_flag BOOLEAN,
    day_of_week TEXT,
    hour_of_day INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    zone_id TEXT,
    nearby_pois_count INTEGER,
    historical_dwell_time_avg NUMERIC,
    historical_headway_avg NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

def create_db_connection():
    """Create database connection"""
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

def setup_unified_table(conn):
    """Create unified data table if it doesn't exist"""
    with conn.cursor() as cursor:
        cursor.execute(CREATE_UNIFIED_TABLE)
        conn.commit()
        logging.info(f"Ensured unified table {UNIFIED_TABLE} exists.")

def load_static_gtfs_data(conn) -> Dict[str, pd.DataFrame]:
    """Load static GTFS data from database"""
    logging.info("Loading static GTFS data...")
    
    static_data = {}
    
    # Load stops
    stops_df = pd.read_sql("SELECT * FROM gtfs_stops", conn)
    static_data['stops'] = stops_df
    logging.info(f"Loaded {len(stops_df)} stops")
    
    # Load routes
    routes_df = pd.read_sql("SELECT * FROM gtfs_routes", conn)
    static_data['routes'] = routes_df
    logging.info(f"Loaded {len(routes_df)} routes")
    
    # Load trips
    trips_df = pd.read_sql("SELECT * FROM gtfs_trips", conn)
    static_data['trips'] = trips_df
    logging.info(f"Loaded {len(trips_df)} trips")
    
    # Load stop times
    stop_times_df = pd.read_sql("SELECT * FROM gtfs_stop_times", conn)
    static_data['stop_times'] = stop_times_df
    logging.info(f"Loaded {len(stop_times_df)} stop times")
    
    # Load calendar
    calendar_df = pd.read_sql("SELECT * FROM gtfs_calendar", conn)
    static_data['calendar'] = calendar_df
    logging.info(f"Loaded {len(calendar_df)} calendar entries")
    
    return static_data

def load_realtime_data(conn, hours_back: int = 24) -> Dict[str, pd.DataFrame]:
    """Load recent GTFS-RT data from database"""
    logging.info(f"Loading GTFS-RT data from last {hours_back} hours...")
    
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    
    # Load vehicle positions
    vp_query = f"""
    SELECT * FROM gtfs_vehicle_positions 
    WHERE timestamp >= %s
    ORDER BY timestamp
    """
    vehicle_positions_df = pd.read_sql(vp_query, conn, params=[cutoff_time])
    logging.info(f"Loaded {len(vehicle_positions_df)} vehicle positions")
    
    # Load trip updates
    tu_query = f"""
    SELECT * FROM gtfs_trip_updates 
    WHERE timestamp >= %s
    ORDER BY timestamp
    """
    trip_updates_df = pd.read_sql(tu_query, conn, params=[cutoff_time])
    logging.info(f"Loaded {len(trip_updates_df)} trip updates")
    
    return {
        'vehicle_positions': vehicle_positions_df,
        'trip_updates': trip_updates_df
    }

def load_external_data(conn) -> Dict[str, pd.DataFrame]:
    """Load external data (weather, events)"""
    logging.info("Loading external data...")
    
    external_data = {}
    
    # Load weather data
    try:
        weather_df = pd.read_sql("SELECT * FROM atlanta_weather_data", conn)
        external_data['weather'] = weather_df
        logging.info(f"Loaded {len(weather_df)} weather records")
    except Exception as e:
        logging.warning(f"Could not load weather data: {e}")
        external_data['weather'] = pd.DataFrame()
    
    # Load event data
    try:
        events_df = pd.read_sql("SELECT * FROM atlanta_events_data", conn)
        external_data['events'] = events_df
        logging.info(f"Loaded {len(events_df)} events")
    except Exception as e:
        logging.warning(f"Could not load event data: {e}")
        external_data['events'] = pd.DataFrame()
    
    return external_data

def calculate_dwell_time(actual_arrival: datetime, actual_departure: datetime) -> float:
    """Calculate dwell time in seconds"""
    if pd.isna(actual_arrival) or pd.isna(actual_departure):
        return 0.0
    
    dwell_seconds = (actual_departure - actual_arrival).total_seconds()
    return max(0.0, dwell_seconds)

def infer_demand_level(dwell_time_seconds: float) -> str:
    """Infer demand level based on dwell time"""
    if dwell_time_seconds > 180:  # > 3 minutes
        return "Overloaded"
    elif dwell_time_seconds > 120:  # > 2 minutes
        return "High"
    elif dwell_time_seconds > 60:   # > 1 minute
        return "Normal"
    else:
        return "Low"

def calculate_delay(scheduled_time: datetime, actual_time: datetime) -> float:
    """Calculate delay in minutes"""
    if pd.isna(scheduled_time) or pd.isna(actual_time):
        return 0.0
    
    delay_seconds = (actual_time - scheduled_time).total_seconds()
    return delay_seconds / 60.0

def get_weather_context(timestamp: datetime, weather_df: pd.DataFrame) -> Dict:
    """Get weather context for a specific timestamp"""
    if weather_df.empty:
        return {
            'weather_condition': 'Unknown',
            'temperature_celsius': 20.0,
            'precipitation_mm': 0.0
        }
    
    # Find closest weather record
    weather_df['time_diff'] = abs(weather_df['timestamp'] - timestamp)
    closest_weather = weather_df.loc[weather_df['time_diff'].idxmin()]
    
    return {
        'weather_condition': closest_weather.get('weather_condition', 'Unknown'),
        'temperature_celsius': closest_weather.get('temperature_celsius', 20.0),
        'precipitation_mm': closest_weather.get('precipitation_mm', 0.0)
    }

def get_event_context(timestamp: datetime, events_df: pd.DataFrame) -> bool:
    """Check if there's an event happening around the timestamp"""
    if events_df.empty:
        return False
    
    # Check if there's an event within 3 hours of the timestamp
    event_window = timedelta(hours=3)
    
    for _, event in events_df.iterrows():
        event_time = pd.to_datetime(event['event_date'])
        if abs(event_time - timestamp) <= event_window:
            return True
    
    return False

def reconstruct_trips(static_data: Dict, realtime_data: Dict, external_data: Dict) -> pd.DataFrame:
    """Reconstruct historical trips by aligning static and real-time data"""
    logging.info("Reconstructing historical trips...")
    
    unified_records = []
    
    # Process trip updates (more reliable for timing)
    trip_updates_df = realtime_data['trip_updates']
    
    for _, tu in trip_updates_df.iterrows():
        try:
            # Find corresponding static trip data
            trip_id = tu['trip_id']
            stop_id = tu['stop_id']
            
            # Get static stop time data
            static_stop_time = static_data['stop_times'][
                (static_data['stop_times']['trip_id'] == trip_id) & 
                (static_data['stop_times']['stop_id'] == stop_id)
            ]
            
            if static_stop_time.empty:
                continue
            
            static_stop_time = static_stop_time.iloc[0]
            
            # Get trip and route info
            trip_info = static_data['trips'][static_data['trips']['trip_id'] == trip_id]
            if trip_info.empty:
                continue
            
            trip_info = trip_info.iloc[0]
            route_id = trip_info['route_id']
            
            # Get stop info
            stop_info = static_data['stops'][static_data['stops']['stop_id'] == stop_id]
            if stop_info.empty:
                continue
            
            stop_info = stop_info.iloc[0]
            
            # Calculate times
            actual_arrival = tu.get('arrival_time')
            actual_departure = tu.get('departure_time')
            
            # Parse scheduled times (GTFS format: HH:MM:SS)
            scheduled_arrival_str = static_stop_time['arrival_time']
            scheduled_departure_str = static_stop_time['departure_time']
            
            # Convert to datetime (simplified - would need proper date handling)
            timestamp = tu['timestamp']
            scheduled_arrival = timestamp.replace(
                hour=int(scheduled_arrival_str.split(':')[0]),
                minute=int(scheduled_arrival_str.split(':')[1]),
                second=int(scheduled_arrival_str.split(':')[2])
            )
            scheduled_departure = timestamp.replace(
                hour=int(scheduled_departure_str.split(':')[0]),
                minute=int(scheduled_departure_str.split(':')[1]),
                second=int(scheduled_departure_str.split(':')[2])
            )
            
            # Calculate metrics
            dwell_time = calculate_dwell_time(actual_arrival, actual_departure)
            demand_level = infer_demand_level(dwell_time)
            delay_minutes = calculate_delay(scheduled_arrival, actual_arrival)
            
            # Get external context
            weather_context = get_weather_context(timestamp, external_data['weather'])
            event_flag = get_event_context(timestamp, external_data['events'])
            
            # Create unified record
            record = {
                'timestamp': timestamp,
                'trip_id': trip_id,
                'route_id': route_id,
                'stop_id': stop_id,
                'stop_sequence': static_stop_time['stop_sequence'],
                'vehicle_id': tu.get('vehicle_id'),
                'latitude': stop_info['stop_lat'],
                'longitude': stop_info['stop_lon'],
                'scheduled_arrival_time': scheduled_arrival,
                'actual_arrival_time': actual_arrival,
                'scheduled_departure_time': scheduled_departure,
                'actual_departure_time': actual_departure,
                'delay_minutes': delay_minutes,
                'inferred_dwell_time_seconds': dwell_time,
                'inferred_demand_level': demand_level,
                'weather_condition': weather_context['weather_condition'],
                'temperature_celsius': weather_context['temperature_celsius'],
                'precipitation_mm': weather_context['precipitation_mm'],
                'event_flag': event_flag,
                'day_of_week': timestamp.strftime('%A'),
                'hour_of_day': timestamp.hour,
                'is_weekend': timestamp.weekday() >= 5,
                'is_holiday': False,  # Would need holiday calendar
                'zone_id': stop_info.get('zone_id'),
                'nearby_pois_count': 0,  # Would need POI data
                'historical_dwell_time_avg': 0.0,  # Would need historical aggregation
                'historical_headway_avg': 0.0  # Would need historical aggregation
            }
            
            unified_records.append(record)
            
        except Exception as e:
            logging.warning(f"Error processing trip update: {e}")
            continue
    
    logging.info(f"Reconstructed {len(unified_records)} trip records")
    return pd.DataFrame(unified_records)

def store_unified_data(conn, unified_df: pd.DataFrame):
    """Store unified data in database"""
    if unified_df.empty:
        logging.warning("No unified data to store")
        return
    
    logging.info(f"Storing {len(unified_df)} unified records...")
    
    with conn.cursor() as cursor:
        for _, record in unified_df.iterrows():
            cursor.execute(f'''
                INSERT INTO {UNIFIED_TABLE} (
                    timestamp, trip_id, route_id, stop_id, stop_sequence, vehicle_id,
                    latitude, longitude, scheduled_arrival_time, actual_arrival_time,
                    scheduled_departure_time, actual_departure_time, delay_minutes,
                    inferred_dwell_time_seconds, inferred_demand_level, weather_condition,
                    temperature_celsius, precipitation_mm, event_flag, day_of_week,
                    hour_of_day, is_weekend, is_holiday, zone_id, nearby_pois_count,
                    historical_dwell_time_avg, historical_headway_avg
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trip_id, stop_id, timestamp) DO UPDATE SET
                    actual_arrival_time = EXCLUDED.actual_arrival_time,
                    actual_departure_time = EXCLUDED.actual_departure_time,
                    delay_minutes = EXCLUDED.delay_minutes,
                    inferred_dwell_time_seconds = EXCLUDED.inferred_dwell_time_seconds,
                    inferred_demand_level = EXCLUDED.inferred_demand_level,
                    weather_condition = EXCLUDED.weather_condition,
                    temperature_celsius = EXCLUDED.temperature_celsius,
                    precipitation_mm = EXCLUDED.precipitation_mm,
                    event_flag = EXCLUDED.event_flag
            ''', (
                record['timestamp'], record['trip_id'], record['route_id'], record['stop_id'],
                record['stop_sequence'], record['vehicle_id'], record['latitude'], record['longitude'],
                record['scheduled_arrival_time'], record['actual_arrival_time'],
                record['scheduled_departure_time'], record['actual_departure_time'],
                record['delay_minutes'], record['inferred_dwell_time_seconds'],
                record['inferred_demand_level'], record['weather_condition'],
                record['temperature_celsius'], record['precipitation_mm'], record['event_flag'],
                record['day_of_week'], record['hour_of_day'], record['is_weekend'],
                record['is_holiday'], record['zone_id'], record['nearby_pois_count'],
                record['historical_dwell_time_avg'], record['historical_headway_avg']
            ))
        
        conn.commit()
        logging.info("Unified data stored successfully")

def main():
    """Main reconstruction process"""
    logging.info("🚀 Starting MARTA Trip Reconstruction")
    
    conn = create_db_connection()
    setup_unified_table(conn)
    
    try:
        # Load all data
        static_data = load_static_gtfs_data(conn)
        realtime_data = load_realtime_data(conn, hours_back=24)
        external_data = load_external_data(conn)
        
        # Reconstruct trips
        unified_df = reconstruct_trips(static_data, realtime_data, external_data)
        
        # Store results
        if not unified_df.empty:
            store_unified_data(conn, unified_df)
            logging.info("✅ Trip reconstruction completed successfully")
        else:
            logging.warning("⚠️ No trip data to reconstruct")
            
    except Exception as e:
        logging.error(f"❌ Trip reconstruction failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main() 