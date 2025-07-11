#!/usr/bin/env python3
"""
GTFS Data Ingestion Module
Handles ingestion of GTFS static data into PostgreSQL database
"""
import os
import sys
import zipfile
import io
import logging
import pandas as pd
import psycopg2
from psycopg2 import extras
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GTFSIngestion:
    """Handles GTFS static data ingestion"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or {
            'host': settings.DB_HOST,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'port': settings.DB_PORT
        }
        
        # GTFS file configurations
        self.gtfs_files_config = {
            "stops.txt": {
                "table": "gtfs_stops",
                "columns": [
                    "stop_id", "stop_code", "stop_name", "stop_desc", "stop_lat", "stop_lon",
                    "zone_id", "stop_url", "location_type", "parent_station", "wheelchair_boarding",
                    "platform_code"
                ]
            },
            "routes.txt": {
                "table": "gtfs_routes",
                "columns": [
                    "route_id", "agency_id", "route_short_name", "route_long_name", "route_desc",
                    "route_type", "route_url", "route_color", "route_text_color", "route_sort_order",
                    "continuous_pickup", "continuous_dropoff"
                ]
            },
            "trips.txt": {
                "table": "gtfs_trips",
                "columns": [
                    "route_id", "service_id", "trip_id", "trip_short_name", "trip_headsign",
                    "direction_id", "block_id", "shape_id", "wheelchair_accessible", "bikes_allowed"
                ]
            },
            "stop_times.txt": {
                "table": "gtfs_stop_times",
                "columns": [
                    "trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence",
                    "stop_headsign", "pickup_type", "drop_off_type", "shape_dist_traveled",
                    "timepoint"
                ]
            },
            "calendar.txt": {
                "table": "gtfs_calendar",
                "columns": [
                    "service_id", "monday", "tuesday", "wednesday", "thursday", "friday",
                    "saturday", "sunday", "start_date", "end_date"
                ]
            },
            "shapes.txt": {
                "table": "gtfs_shapes",
                "columns": [
                    "shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence", "shape_dist_traveled"
                ]
            }
        }
    
    def create_db_connection(self):
        """Create database connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def load_csv_to_db(self, conn, zip_file_obj, csv_filename, table_name, columns):
        """Load CSV data from ZIP file into database table"""
        logger.info(f"Loading {csv_filename} into {table_name}...")
        
        try:
            with zip_file_obj.open(csv_filename) as f:
                df = pd.read_csv(io.TextIOWrapper(f, encoding='utf-8'))
                
                # Ensure column names match database schema and handle missing columns
                df = df.reindex(columns=columns, fill_value=None)
                
                # Convert DataFrame to list of tuples for psycopg2.extras.execute_values
                data_to_insert = [tuple(row) for row in df.values]
                
                if not data_to_insert:
                    logger.warning(f"No data to insert for {csv_filename}.")
                    return
                
                # Prepare the INSERT statement for execute_values
                cols_str = ', '.join(columns)
                # Find PK for ON CONFLICT (first column is always PK in our schema)
                pk_col = columns[0]
                update_str = ', '.join([f'{col} = EXCLUDED.{col}' for col in columns[1:]])
                insert_query = f"""
                    INSERT INTO {table_name} ({cols_str}) 
                    VALUES %s 
                    ON CONFLICT ({pk_col}) DO UPDATE SET {update_str};
                """
                
                with conn.cursor() as cursor:
                    extras.execute_values(cursor, insert_query, data_to_insert, page_size=1000)
                    conn.commit()
                    logger.info(f"Successfully loaded {len(data_to_insert)} rows into {table_name}.")
                    
        except Exception as e:
            conn.rollback()
            logger.error(f"Error loading {csv_filename}: {e}")
            raise
    
    def ingest_gtfs_static(self, gtfs_zip_path: str):
        """Ingest GTFS static data from ZIP file"""
        conn = None
        try:
            conn = self.create_db_connection()
            
            with zipfile.ZipFile(gtfs_zip_path, 'r') as zf:
                for gtfs_file, config in self.gtfs_files_config.items():
                    if gtfs_file in zf.namelist():
                        self.load_csv_to_db(conn, zf, gtfs_file, config["table"], config["columns"])
                    else:
                        logger.warning(f"Warning: {gtfs_file} not found in zip file.")
                        
        except Exception as e:
            logger.error(f"An error occurred during GTFS static ingestion: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_demo_gtfs_data(self, output_path: str = "data/static/demo_gtfs.zip"):
        """Create demo GTFS data for testing"""
        logger.info("Creating demo GTFS data...")
        
        # Create demo stops
        stops_data = pd.DataFrame({
            'stop_id': [f'stop_{i:03d}' for i in range(1, 21)],
            'stop_code': [f'SC{i:03d}' for i in range(1, 21)],
            'stop_name': [f'Stop {i}' for i in range(1, 21)],
            'stop_desc': [f'Demo stop {i} for MARTA demand forecasting' for i in range(1, 21)],
            'stop_lat': np.random.uniform(33.7, 33.8, 20),
            'stop_lon': np.random.uniform(-84.4, -84.3, 20),
            'zone_id': [f'zone_{i//5 + 1}' for i in range(20)],
            'stop_url': [''] * 20,
            'location_type': [0] * 20,
            'parent_station': [''] * 20,
            'wheelchair_boarding': [1] * 20,
            'platform_code': [''] * 20
        })
        
        # Create demo routes
        routes_data = pd.DataFrame({
            'route_id': [f'route_{i:03d}' for i in range(1, 6)],
            'agency_id': ['MARTA'] * 5,
            'route_short_name': [f'R{i}' for i in range(1, 6)],
            'route_long_name': [f'Demo Route {i}' for i in range(1, 6)],
            'route_desc': [f'Demo route {i} for testing' for i in range(1, 6)],
            'route_type': [3] * 5,  # Bus
            'route_url': [''] * 5,
            'route_color': ['FF0000', '00FF00', '0000FF', 'FFFF00', 'FF00FF'],
            'route_text_color': ['FFFFFF'] * 5,
            'route_sort_order': list(range(1, 6)),
            'continuous_pickup': [0] * 5,
            'continuous_dropoff': [0] * 5
        })
        
        # Create demo trips
        trips_data = []
        for route_idx, route_id in enumerate(routes_data['route_id']):
            for direction in [0, 1]:  # Two directions
                for hour in range(6, 22, 2):  # Every 2 hours from 6 AM to 10 PM
                    trip_id = f'trip_{route_idx}_{direction}_{hour:02d}'
                    trips_data.append({
                        'route_id': route_id,
                        'service_id': 'weekday',
                        'trip_id': trip_id,
                        'trip_short_name': f'{route_id}_{hour:02d}',
                        'trip_headsign': f'Demo {route_id} {"North" if direction == 0 else "South"}',
                        'direction_id': direction,
                        'block_id': f'block_{route_idx}',
                        'shape_id': f'shape_{route_idx}',
                        'wheelchair_accessible': 1,
                        'bikes_allowed': 1
                    })
        
        trips_df = pd.DataFrame(trips_data)
        
        # Create demo stop times
        stop_times_data = []
        for _, trip in trips_df.iterrows():
            route_stops = stops_data.sample(n=8, random_state=42).reset_index(drop=True)
            base_time = datetime.strptime('06:00:00', '%H:%M:%S')
            
            for seq, (_, stop) in enumerate(route_stops.iterrows()):
                arrival_time = base_time + timedelta(minutes=seq * 5)
                departure_time = arrival_time + timedelta(minutes=1)
                
                stop_times_data.append({
                    'trip_id': trip['trip_id'],
                    'arrival_time': arrival_time.time(),
                    'departure_time': departure_time.time(),
                    'stop_id': stop['stop_id'],
                    'stop_sequence': seq + 1,
                    'stop_headsign': '',
                    'pickup_type': 0,
                    'drop_off_type': 0,
                    'shape_dist_traveled': seq * 0.5,
                    'timepoint': 1
                })
        
        stop_times_df = pd.DataFrame(stop_times_data)
        
        # Create demo calendar
        calendar_data = pd.DataFrame({
            'service_id': ['weekday', 'weekend'],
            'monday': [True, False],
            'tuesday': [True, False],
            'wednesday': [True, False],
            'thursday': [True, False],
            'friday': [True, False],
            'saturday': [False, True],
            'sunday': [False, True],
            'start_date': ['20240101', '20240101'],
            'end_date': ['20241231', '20241231']
        })
        
        # Create demo shapes
        shapes_data = []
        for route_idx in range(5):
            for seq in range(10):
                shapes_data.append({
                    'shape_id': f'shape_{route_idx}',
                    'shape_pt_lat': 33.75 + np.random.normal(0, 0.01),
                    'shape_pt_lon': -84.35 + np.random.normal(0, 0.01),
                    'shape_pt_sequence': seq,
                    'shape_dist_traveled': seq * 0.5
                })
        
        shapes_df = pd.DataFrame(shapes_data)
        
        # Save to ZIP file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write each DataFrame to CSV in the ZIP using an in-memory buffer
            zf.writestr('stops.txt', stops_data.to_csv(index=False))
            zf.writestr('routes.txt', routes_data.to_csv(index=False))
            zf.writestr('trips.txt', trips_df.to_csv(index=False))
            zf.writestr('stop_times.txt', stop_times_df.to_csv(index=False))
            zf.writestr('calendar.txt', calendar_data.to_csv(index=False))
            zf.writestr('shapes.txt', shapes_df.to_csv(index=False))
        
        logger.info(f"Demo GTFS data created at {output_path}")
        return output_path
    
    def run_ingestion(self, gtfs_zip_path: Optional[str] = None, create_demo: bool = True):
        """Run the complete GTFS ingestion process"""
        try:
            if gtfs_zip_path and os.path.exists(gtfs_zip_path):
                logger.info(f"Ingesting GTFS data from {gtfs_zip_path}")
                self.ingest_gtfs_static(gtfs_zip_path)
            elif create_demo:
                logger.info("Creating and ingesting demo GTFS data")
                demo_path = self.create_demo_gtfs_data()
                self.ingest_gtfs_static(demo_path)
            else:
                raise FileNotFoundError("No GTFS ZIP file provided and demo creation disabled")
                
            logger.info("GTFS ingestion completed successfully!")
            
        except Exception as e:
            logger.error(f"GTFS ingestion failed: {e}")
            raise


def main():
    """Main function for running GTFS ingestion"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GTFS Data Ingestion')
    parser.add_argument('--gtfs-zip', type=str, help='Path to GTFS ZIP file')
    parser.add_argument('--create-demo', action='store_true', default=True, 
                       help='Create demo data if no GTFS file provided')
    parser.add_argument('--no-demo', action='store_true', help='Disable demo data creation')
    
    args = parser.parse_args()
    
    # Override create_demo if --no-demo is specified
    create_demo = args.create_demo and not args.no_demo
    
    ingestor = GTFSIngestion()
    ingestor.run_ingestion(gtfs_zip_path=args.gtfs_zip, create_demo=create_demo)


if __name__ == "__main__":
    main() 