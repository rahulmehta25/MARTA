import os
import time
import logging
import psycopg2
import requests
from datetime import datetime
from google.transit import gtfs_realtime_pb2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MARTA GTFS-RT API Endpoints
VEHICLE_POSITIONS_URL = "https://api.marta.io/gtfs-rt/vehicle-positions/vehicle.pb"
TRIP_UPDATES_URL = "https://api.marta.io/gtfs-rt/trip-updates/tripupdate.pb"

# API Key (set as environment variable)
API_KEY = os.getenv("MARTA_API_KEY", "YOUR_MARTA_API_KEY")
HEADERS = {"x-api-key": API_KEY}

# Database connection details (set as environment variables)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Table names
VEHICLE_POSITIONS_TABLE = "gtfs_vehicle_positions"
TRIP_UPDATES_TABLE = "gtfs_trip_updates"

# Create tables if they don't exist
CREATE_VEHICLE_POSITIONS_TABLE = f'''
CREATE TABLE IF NOT EXISTS {VEHICLE_POSITIONS_TABLE} (
    id TEXT,
    trip_id TEXT,
    route_id TEXT,
    vehicle_id TEXT,
    latitude NUMERIC,
    longitude NUMERIC,
    bearing NUMERIC,
    speed NUMERIC,
    timestamp TIMESTAMP,
    current_status TEXT
);
'''

CREATE_TRIP_UPDATES_TABLE = f'''
CREATE TABLE IF NOT EXISTS {TRIP_UPDATES_TABLE} (
    id TEXT,
    trip_id TEXT,
    route_id TEXT,
    direction_id INTEGER,
    start_time TEXT,
    start_date TEXT,
    timestamp TIMESTAMP,
    stop_id TEXT,
    stop_sequence INTEGER,
    arrival_delay INTEGER,
    arrival_time TIMESTAMP,
    departure_delay INTEGER,
    departure_time TIMESTAMP
);
'''

def create_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

def setup_tables(conn):
    with conn.cursor() as cursor:
        cursor.execute(CREATE_VEHICLE_POSITIONS_TABLE)
        cursor.execute(CREATE_TRIP_UPDATES_TABLE)
        conn.commit()
        logging.info("Ensured GTFS-RT tables exist.")

def fetch_and_parse_feed(url, feed_type):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed
    except Exception as e:
        logging.error(f"Error fetching/parsing {feed_type} feed: {e}")
        return None

def store_vehicle_positions(conn, data):
    if not data:
        return
    with conn.cursor() as cursor:
        for row in data:
            cursor.execute(f'''
                INSERT INTO {VEHICLE_POSITIONS_TABLE} (id, trip_id, route_id, vehicle_id, latitude, longitude, bearing, speed, timestamp, current_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                row['id'], row['trip_id'], row['route_id'], row['vehicle_id'],
                row['latitude'], row['longitude'], row['bearing'], row['speed'],
                row['timestamp'], row['current_status']
            ))
        conn.commit()
        logging.info(f"Inserted {len(data)} vehicle positions.")

def store_trip_updates(conn, data):
    if not data:
        return
    with conn.cursor() as cursor:
        for row in data:
            for update in row['stop_time_updates']:
                cursor.execute(f'''
                    INSERT INTO {TRIP_UPDATES_TABLE} (id, trip_id, route_id, direction_id, start_time, start_date, timestamp, stop_id, stop_sequence, arrival_delay, arrival_time, departure_delay, departure_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    row['id'], row['trip_id'], row['route_id'], row['direction_id'],
                    row['start_time'], row['start_date'], row['timestamp'],
                    update['stop_id'], update['stop_sequence'],
                    update['arrival_delay'], update['arrival_time'],
                    update['departure_delay'], update['departure_time']
                ))
        conn.commit()
        logging.info(f"Inserted {len(data)} trip updates.")

def process_vehicle_positions(feed):
    if not feed:
        return []
    processed_data = []
    for entity in feed.entity:
        if entity.HasField('vehicle'):
            vehicle = entity.vehicle
            processed_data.append({
                "id": entity.id,
                "trip_id": vehicle.trip.trip_id,
                "route_id": vehicle.trip.route_id,
                "vehicle_id": vehicle.vehicle.id,
                "latitude": vehicle.position.latitude,
                "longitude": vehicle.position.longitude,
                "bearing": vehicle.position.bearing,
                "speed": vehicle.position.speed,
                "timestamp": datetime.fromtimestamp(vehicle.timestamp) if vehicle.HasField('timestamp') else None,
                "current_status": gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus.Name(vehicle.current_status) if vehicle.HasField('current_status') else None
            })
    return processed_data

def process_trip_updates(feed):
    if not feed:
        return []
    processed_data = []
    for entity in feed.entity:
        if entity.HasField('trip_update'):
            trip_update = entity.trip_update
            updates = []
            for stop_time_update in trip_update.stop_time_update:
                updates.append({
                    "stop_id": stop_time_update.stop_id,
                    "stop_sequence": stop_time_update.stop_sequence,
                    "arrival_delay": stop_time_update.arrival.delay if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('delay') else None,
                    "arrival_time": datetime.fromtimestamp(stop_time_update.arrival.time) if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('time') else None,
                    "departure_delay": stop_time_update.departure.delay if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('delay') else None,
                    "departure_time": datetime.fromtimestamp(stop_time_update.departure.time) if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('time') else None,
                })
            processed_data.append({
                "id": entity.id,
                "trip_id": trip_update.trip.trip_id,
                "route_id": trip_update.trip.route_id,
                "direction_id": trip_update.trip.direction_id if trip_update.trip.HasField('direction_id') else None,
                "start_time": trip_update.trip.start_time if trip_update.trip.HasField('start_time') else None,
                "start_date": trip_update.trip.start_date if trip_update.trip.HasField('start_date') else None,
                "timestamp": datetime.fromtimestamp(trip_update.timestamp) if trip_update.HasField('timestamp') else None,
                "stop_time_updates": updates
            })
    return processed_data

def ingest_gtfs_realtime_stream(interval_seconds=30):
    logging.info(f"Starting GTFS-RT ingestion stream, polling every {interval_seconds} seconds...")
    conn = create_db_connection()
    setup_tables(conn)
    try:
        while True:
            logging.info(f"Fetching GTFS-RT data at {datetime.now().isoformat()}")
            # Fetch and process Vehicle Positions
            vp_feed = fetch_and_parse_feed(VEHICLE_POSITIONS_URL, "Vehicle Positions")
            vehicle_positions_data = process_vehicle_positions(vp_feed)
            store_vehicle_positions(conn, vehicle_positions_data)
            # Fetch and process Trip Updates
            tu_feed = fetch_and_parse_feed(TRIP_UPDATES_URL, "Trip Updates")
            trip_updates_data = process_trip_updates(tu_feed)
            store_trip_updates(conn, trip_updates_data)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        logging.info("Ingestion stopped by user.")
    except Exception as e:
        logging.error(f"Fatal error in ingestion loop: {e}")
    finally:
        conn.close()
        logging.info("Database connection closed.")

if __name__ == "__main__":
    ingest_gtfs_realtime_stream() 