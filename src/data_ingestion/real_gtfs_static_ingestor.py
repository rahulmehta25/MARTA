#!/usr/bin/env python3
"""
Real GTFS Static Data Ingestion for MARTA
Downloads and ingests actual GTFS static data from MARTA Developer Portal
"""
import os
import sys
import logging
import requests
import zipfile
import io
import pandas as pd
import psycopg2
from psycopg2 import extras
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import hashlib

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealGTFSStaticIngestor:
    """Real GTFS static data ingestion from MARTA Developer Portal"""
    
    def __init__(self):
        self.marta_portal_url = "https://itsmarta.com/app-developer-resources.aspx"
        self.gtfs_download_url = "https://itsmarta.com/gtfs/gtfs.zip"  # Example URL - may need to be updated
        self.api_key = os.getenv("MARTA_API_KEY")
        
        # Database configuration
        self.db_config = {
            'host': settings.DB_HOST,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD
        }
        
        # GTFS file mappings
        self.gtfs_files = {
            'stops.txt': {
                'table': 'gtfs_stops',
                'columns': [
                    'stop_id', 'stop_code', 'stop_name', 'stop_desc', 'stop_lat', 'stop_lon',
                    'zone_id', 'stop_url', 'location_type', 'parent_station', 'wheelchair_boarding',
                    'platform_code'
                ]
            },
            'routes.txt': {
                'table': 'gtfs_routes',
                'columns': [
                    'route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_desc',
                    'route_type', 'route_url', 'route_color', 'route_text_color', 'route_sort_order',
                    'continuous_pickup', 'continuous_dropoff'
                ]
            },
            'trips.txt': {
                'table': 'gtfs_trips',
                'columns': [
                    'route_id', 'service_id', 'trip_id', 'trip_short_name', 'trip_headsign',
                    'direction_id', 'block_id', 'shape_id', 'wheelchair_accessible', 'bikes_allowed'
                ]
            },
            'stop_times.txt': {
                'table': 'gtfs_stop_times',
                'columns': [
                    'trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence',
                    'stop_headsign', 'pickup_type', 'drop_off_type', 'shape_dist_traveled',
                    'timepoint'
                ]
            },
            'calendar.txt': {
                'table': 'gtfs_calendar',
                'columns': [
                    'service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                    'saturday', 'sunday', 'start_date', 'end_date'
                ]
            },
            'shapes.txt': {
                'table': 'gtfs_shapes',
                'columns': [
                    'shape_id', 'shape_pt_lat', 'shape_pt_lon', 'shape_pt_sequence', 'shape_dist_traveled'
                ]
            }
        }
    
    def discover_gtfs_url(self) -> Optional[str]:
        """Discover the actual GTFS download URL from MARTA Developer Portal"""
        try:
            logger.info("Discovering GTFS download URL from MARTA Developer Portal...")
            
            # Try to find the GTFS download link on the developer portal
            response = requests.get(self.marta_portal_url, timeout=30)
            response.raise_for_status()
            
            # Look for GTFS download links in the HTML
            # This is a simplified approach - may need to be updated based on actual portal structure
            if 'gtfs' in response.text.lower():
                # Try common GTFS URL patterns
                possible_urls = [
                    "https://itsmarta.com/gtfs/gtfs.zip",
                    "https://itsmarta.com/developer/gtfs.zip",
                    "https://itsmarta.com/app-developer-resources/gtfs.zip",
                    "https://api.marta.io/gtfs/gtfs.zip"
                ]
                
                for url in possible_urls:
                    try:
                        test_response = requests.head(url, timeout=10)
                        if test_response.status_code == 200:
                            logger.info(f"Found GTFS download URL: {url}")
                            return url
                    except:
                        continue
            
            # If no URL found, return the default
            logger.warning("Could not discover GTFS URL, using default")
            return self.gtfs_download_url
            
        except Exception as e:
            logger.error(f"Error discovering GTFS URL: {e}")
            return None
    
    def download_gtfs_static(self, output_path: str = "data/raw/gtfs_static.zip") -> Optional[str]:
        """Download latest GTFS static data from MARTA Developer Portal"""
        try:
            # Discover the actual download URL
            download_url = self.discover_gtfs_url()
            if not download_url:
                raise Exception("Could not discover GTFS download URL")
            
            logger.info(f"Downloading GTFS static data from: {download_url}")
            
            # Set up headers for the request
            headers = {}
            if self.api_key:
                headers['x-api-key'] = self.api_key
            
            # Download the GTFS ZIP file
            response = requests.get(download_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the ZIP file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify the ZIP file
            with zipfile.ZipFile(output_path, 'r') as zf:
                file_list = zf.namelist()
                logger.info(f"GTFS ZIP contains {len(file_list)} files: {file_list}")
                
                # Check for required GTFS files
                required_files = ['stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt']
                missing_files = [f for f in required_files if f not in file_list]
                
                if missing_files:
                    raise Exception(f"Missing required GTFS files: {missing_files}")
            
            # Calculate file hash for verification
            with open(output_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            logger.info(f"GTFS static data downloaded successfully to {output_path}")
            logger.info(f"File size: {os.path.getsize(output_path)} bytes")
            logger.info(f"File hash: {file_hash}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading GTFS static data: {e}")
            return None
    
    def validate_gtfs_data(self, gtfs_zip_path: str) -> bool:
        """Validate GTFS data against GTFS specification"""
        try:
            logger.info("Validating GTFS data...")
            
            with zipfile.ZipFile(gtfs_zip_path, 'r') as zf:
                # Check required files
                required_files = ['stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt']
                for file_name in required_files:
                    if file_name not in zf.namelist():
                        logger.error(f"Missing required file: {file_name}")
                        return False
                
                # Validate stops.txt
                with zf.open('stops.txt') as f:
                    stops_df = pd.read_csv(f)
                    required_stop_columns = ['stop_id', 'stop_lat', 'stop_lon']
                    for col in required_stop_columns:
                        if col not in stops_df.columns:
                            logger.error(f"Missing required column in stops.txt: {col}")
                            return False
                    
                    # Validate coordinates
                    if not all((-90 <= stops_df['stop_lat']) & (stops_df['stop_lat'] <= 90)):
                        logger.error("Invalid latitude values in stops.txt")
                        return False
                    if not all((-180 <= stops_df['stop_lon']) & (stops_df['stop_lon'] <= 180)):
                        logger.error("Invalid longitude values in stops.txt")
                        return False
                
                # Validate routes.txt
                with zf.open('routes.txt') as f:
                    routes_df = pd.read_csv(f)
                    required_route_columns = ['route_id', 'route_short_name', 'route_long_name']
                    for col in required_route_columns:
                        if col not in routes_df.columns:
                            logger.error(f"Missing required column in routes.txt: {col}")
                            return False
                
                # Validate trips.txt
                with zf.open('trips.txt') as f:
                    trips_df = pd.read_csv(f)
                    required_trip_columns = ['route_id', 'service_id', 'trip_id']
                    for col in required_trip_columns:
                        if col not in trips_df.columns:
                            logger.error(f"Missing required column in trips.txt: {col}")
                            return False
                
                # Validate stop_times.txt
                with zf.open('stop_times.txt') as f:
                    stop_times_df = pd.read_csv(f)
                    required_stop_time_columns = ['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence']
                    for col in required_stop_time_columns:
                        if col not in stop_times_df.columns:
                            logger.error(f"Missing required column in stop_times.txt: {col}")
                            return False
                
                logger.info("GTFS data validation passed")
                return True
                
        except Exception as e:
            logger.error(f"Error validating GTFS data: {e}")
            return False
    
    def create_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_config)
    
    def create_gtfs_tables(self, conn):
        """Create GTFS tables if they don't exist"""
        logger.info("Creating GTFS tables...")
        
        with conn.cursor() as cursor:
            # Create stops table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gtfs_stops (
                    stop_id VARCHAR(255) PRIMARY KEY,
                    stop_code VARCHAR(255),
                    stop_name VARCHAR(255),
                    stop_desc TEXT,
                    stop_lat NUMERIC,
                    stop_lon NUMERIC,
                    zone_id VARCHAR(255),
                    stop_url TEXT,
                    location_type INTEGER,
                    parent_station VARCHAR(255),
                    wheelchair_boarding INTEGER,
                    platform_code VARCHAR(255)
                )
            """)
            
            # Create routes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gtfs_routes (
                    route_id VARCHAR(255) PRIMARY KEY,
                    agency_id VARCHAR(255),
                    route_short_name VARCHAR(255),
                    route_long_name VARCHAR(255),
                    route_desc TEXT,
                    route_type INTEGER,
                    route_url TEXT,
                    route_color VARCHAR(6),
                    route_text_color VARCHAR(6),
                    route_sort_order INTEGER,
                    continuous_pickup INTEGER,
                    continuous_dropoff INTEGER
                )
            """)
            
            # Create trips table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gtfs_trips (
                    route_id VARCHAR(255),
                    service_id VARCHAR(255),
                    trip_id VARCHAR(255) PRIMARY KEY,
                    trip_short_name VARCHAR(255),
                    trip_headsign VARCHAR(255),
                    direction_id INTEGER,
                    block_id VARCHAR(255),
                    shape_id VARCHAR(255),
                    wheelchair_accessible INTEGER,
                    bikes_allowed INTEGER,
                    FOREIGN KEY (route_id) REFERENCES gtfs_routes(route_id)
                )
            """)
            
            # Create stop_times table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gtfs_stop_times (
                    trip_id VARCHAR(255),
                    arrival_time TIME,
                    departure_time TIME,
                    stop_id VARCHAR(255),
                    stop_sequence INTEGER,
                    stop_headsign VARCHAR(255),
                    pickup_type INTEGER,
                    drop_off_type INTEGER,
                    shape_dist_traveled NUMERIC,
                    timepoint INTEGER,
                    PRIMARY KEY (trip_id, stop_sequence),
                    FOREIGN KEY (trip_id) REFERENCES gtfs_trips(trip_id),
                    FOREIGN KEY (stop_id) REFERENCES gtfs_stops(stop_id)
                )
            """)
            
            # Create calendar table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gtfs_calendar (
                    service_id VARCHAR(255) PRIMARY KEY,
                    monday BOOLEAN,
                    tuesday BOOLEAN,
                    wednesday BOOLEAN,
                    thursday BOOLEAN,
                    friday BOOLEAN,
                    saturday BOOLEAN,
                    sunday BOOLEAN,
                    start_date DATE,
                    end_date DATE
                )
            """)
            
            # Create shapes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gtfs_shapes (
                    shape_id VARCHAR(255),
                    shape_pt_lat NUMERIC,
                    shape_pt_lon NUMERIC,
                    shape_pt_sequence INTEGER,
                    shape_dist_traveled NUMERIC,
                    PRIMARY KEY (shape_id, shape_pt_sequence)
                )
            """)
            
            conn.commit()
            logger.info("GTFS tables created successfully")
    
    def load_csv_to_db(self, conn, zip_file_obj, csv_filename, table_name, columns):
        """Load CSV data from ZIP file into database table"""
        logger.info(f"Loading {csv_filename} into {table_name}...")
        
        try:
            with zip_file_obj.open(csv_filename) as f:
                df = pd.read_csv(io.TextIOWrapper(f, encoding='utf-8'))
                
                # Ensure column names match database schema
                df = df.reindex(columns=columns, fill_value=None)
                
                # Convert DataFrame to list of tuples for psycopg2.extras.execute_values
                data_to_insert = [tuple(row) for row in df.values]
                
                if not data_to_insert:
                    logger.warning(f"No data to insert for {csv_filename}")
                    return 0
                
                # Prepare the INSERT statement with ON CONFLICT handling
                cols_str = ', '.join(columns)
                vals_str = ', '.join([f'%s' for _ in columns])
                
                # Use UPSERT for primary key conflicts
                conflict_columns = [columns[0]]  # Assume first column is primary key
                update_columns = [col for col in columns[1:] if col is not None]
                
                if update_columns:
                    update_str = ', '.join([f'{col} = EXCLUDED.{col}' for col in update_columns])
                    insert_query = f"""
                        INSERT INTO {table_name} ({cols_str}) 
                        VALUES ({vals_str}) 
                        ON CONFLICT ({', '.join(conflict_columns)}) 
                        DO UPDATE SET {update_str}
                    """
                else:
                    insert_query = f"""
                        INSERT INTO {table_name} ({cols_str}) 
                        VALUES ({vals_str}) 
                        ON CONFLICT ({', '.join(conflict_columns)}) 
                        DO NOTHING
                    """
                
                with conn.cursor() as cursor:
                    extras.execute_values(cursor, insert_query, data_to_insert, page_size=1000)
                    conn.commit()
                    
                    logger.info(f"Successfully loaded {len(data_to_insert)} rows into {table_name}")
                    return len(data_to_insert)
                    
        except Exception as e:
            conn.rollback()
            logger.error(f"Error loading {csv_filename}: {e}")
            raise
    
    def ingest_gtfs_static(self, gtfs_zip_path: str) -> bool:
        """Ingest real GTFS static data into database"""
        try:
            logger.info(f"Ingesting GTFS static data from {gtfs_zip_path}")
            
            # Validate GTFS data first
            if not self.validate_gtfs_data(gtfs_zip_path):
                raise Exception("GTFS data validation failed")
            
            # Create database connection
            conn = self.create_db_connection()
            
            # Create tables if they don't exist
            self.create_gtfs_tables(conn)
            
            # Load data from ZIP file
            with zipfile.ZipFile(gtfs_zip_path, 'r') as zf:
                total_rows = 0
                
                for gtfs_file, config in self.gtfs_files.items():
                    if gtfs_file in zf.namelist():
                        rows_loaded = self.load_csv_to_db(
                            conn, zf, gtfs_file, config["table"], config["columns"]
                        )
                        total_rows += rows_loaded
                    else:
                        logger.warning(f"File {gtfs_file} not found in GTFS ZIP")
                
                logger.info(f"Total rows loaded: {total_rows}")
            
            conn.close()
            logger.info("GTFS static data ingestion completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting GTFS static data: {e}")
            return False
    
    def run_ingestion(self, download_new: bool = True, gtfs_zip_path: Optional[str] = None) -> bool:
        """Run complete GTFS static data ingestion"""
        try:
            logger.info("Starting real GTFS static data ingestion...")
            
            # Download new data if requested
            if download_new:
                downloaded_path = self.download_gtfs_static()
                if not downloaded_path:
                    raise Exception("Failed to download GTFS static data")
                gtfs_zip_path = downloaded_path
            
            # Use provided path or downloaded path
            if not gtfs_zip_path:
                raise Exception("No GTFS ZIP file provided")
            
            # Ingest the data
            success = self.ingest_gtfs_static(gtfs_zip_path)
            
            if success:
                logger.info("✅ Real GTFS static data ingestion completed successfully")
            else:
                logger.error("❌ Real GTFS static data ingestion failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in GTFS static data ingestion: {e}")
            return False


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real GTFS Static Data Ingestion')
    parser.add_argument('--gtfs-zip', type=str, help='Path to GTFS ZIP file (optional)')
    parser.add_argument('--download', action='store_true', default=True, help='Download new GTFS data')
    parser.add_argument('--no-download', action='store_true', help='Use existing GTFS ZIP file')
    
    args = parser.parse_args()
    
    # Override download flag if --no-download is specified
    download_new = args.download and not args.no_download
    
    # Run ingestion
    ingestor = RealGTFSStaticIngestor()
    success = ingestor.run_ingestion(download_new=download_new, gtfs_zip_path=args.gtfs_zip)
    
    if success:
        print("✅ Real GTFS static data ingestion completed successfully")
        sys.exit(0)
    else:
        print("❌ Real GTFS static data ingestion failed")
        sys.exit(1)


if __name__ == "__main__":
    main() 