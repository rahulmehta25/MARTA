"""
GTFS Static Data Ingestion Module
Handles downloading and parsing of MARTA's GTFS static data
"""
import os
import sys
import zipfile
import io
import logging
from typing import Dict, List, Optional
import pandas as pd
import psycopg2
from psycopg2 import extras
import requests
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from config.settings import settings
except ImportError:
    # Fallback for direct execution
    import os
    settings = type('Settings', (), {
        'DB_HOST': os.getenv('DB_HOST', 'localhost'),
        'DB_NAME': os.getenv('DB_NAME', 'marta_db'),
        'DB_USER': os.getenv('DB_USER', 'marta_user'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD', 'marta_password'),
        'DB_PORT': os.getenv('DB_PORT', 5432),
        'RAW_DATA_DIR': os.getenv('RAW_DATA_DIR', 'data/raw')
    })()

logger = logging.getLogger(__name__)


class GTFSIngestor:
    """Handles GTFS static data ingestion from MARTA"""
    
    def __init__(self):
        self.db_connection = None
        self.gtfs_data_path = os.path.join(settings.RAW_DATA_DIR, "gtfs_static")
        os.makedirs(self.gtfs_data_path, exist_ok=True)
        
        # GTFS file configurations
        self.gtfs_files_config = {
            "stops.txt": {
                "table": "gtfs_stops",
                "columns": [
                    "stop_id", "stop_code", "stop_name", "stop_desc", "stop_lat", "stop_lon",
                    "zone_id", "stop_url", "location_type", "parent_station", "wheelchair_boarding",
                    "stop_timezone"
                ],
                "primary_key": ["stop_id"]
            },
            "routes.txt": {
                "table": "gtfs_routes", 
                "columns": [
                    "route_id", "agency_id", "route_short_name", "route_long_name", "route_desc",
                    "route_type", "route_url", "route_color", "route_text_color", "route_sort_order",
                    "continuous_pickup", "continuous_dropoff"
                ],
                "primary_key": ["route_id"]
            },
            "trips.txt": {
                "table": "gtfs_trips",
                "columns": [
                    "trip_id", "route_id", "service_id", "trip_short_name", "trip_headsign",
                    "direction_id", "block_id", "shape_id", "wheelchair_accessible", "bikes_allowed"
                ],
                "primary_key": ["trip_id"]
            },
            "stop_times.txt": {
                "table": "gtfs_stop_times",
                "columns": [
                    "trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence",
                    "stop_headsign", "pickup_type", "drop_off_type", "shape_dist_traveled",
                    "timepoint"
                ],
                "primary_key": ["trip_id", "stop_sequence"]
            },
            "calendar.txt": {
                "table": "gtfs_calendar",
                "columns": [
                    "service_id", "monday", "tuesday", "wednesday", "thursday", "friday",
                    "saturday", "sunday", "start_date", "end_date"
                ],
                "primary_key": ["service_id"]
            },
            "shapes.txt": {
                "table": "gtfs_shapes",
                "columns": [
                    "shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence", "shape_dist_traveled"
                ],
                "primary_key": ["shape_id", "shape_pt_sequence"]
            }
        }
    
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
    
    def create_tables(self):
        """Create GTFS tables if they don't exist"""
        if not self.db_connection:
            self.create_db_connection()
        
        create_tables_sql = {
            "gtfs_stops": """
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
                    stop_timezone VARCHAR(255)
                );
            """,
            "gtfs_routes": """
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
                );
            """,
            "gtfs_trips": """
                CREATE TABLE IF NOT EXISTS gtfs_trips (
                    trip_id VARCHAR(255) PRIMARY KEY,
                    route_id VARCHAR(255) REFERENCES gtfs_routes(route_id),
                    service_id VARCHAR(255),
                    trip_short_name VARCHAR(255),
                    trip_headsign VARCHAR(255),
                    direction_id INTEGER,
                    block_id VARCHAR(255),
                    shape_id VARCHAR(255),
                    wheelchair_accessible INTEGER,
                    bikes_allowed INTEGER
                );
            """,
            "gtfs_stop_times": """
                CREATE TABLE IF NOT EXISTS gtfs_stop_times (
                    trip_id VARCHAR(255) REFERENCES gtfs_trips(trip_id),
                    arrival_time VARCHAR(8),
                    departure_time VARCHAR(8),
                    stop_id VARCHAR(255) REFERENCES gtfs_stops(stop_id),
                    stop_sequence INTEGER,
                    stop_headsign VARCHAR(255),
                    pickup_type INTEGER,
                    drop_off_type INTEGER,
                    shape_dist_traveled NUMERIC,
                    timepoint INTEGER,
                    PRIMARY KEY (trip_id, stop_sequence)
                );
            """,
            "gtfs_calendar": """
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
                );
            """,
            "gtfs_shapes": """
                CREATE TABLE IF NOT EXISTS gtfs_shapes (
                    shape_id VARCHAR(255),
                    shape_pt_lat NUMERIC,
                    shape_pt_lon NUMERIC,
                    shape_pt_sequence INTEGER,
                    shape_dist_traveled NUMERIC,
                    PRIMARY KEY (shape_id, shape_pt_sequence)
                );
            """
        }
        
        with self.db_connection.cursor() as cursor:
            for table_name, sql in create_tables_sql.items():
                try:
                    cursor.execute(sql)
                    logger.info(f"Created table: {table_name}")
                except Exception as e:
                    logger.warning(f"Table {table_name} may already exist: {e}")
        
        self.db_connection.commit()
    
    def download_gtfs_data(self) -> Optional[str]:
        """Download GTFS static data from MARTA"""
        try:
            # For now, we'll assume the GTFS data is manually downloaded
            # In production, this would be automated via web scraping or API
            gtfs_zip_path = os.path.join(self.gtfs_data_path, "gtfs_static.zip")
            
            if os.path.exists(gtfs_zip_path):
                logger.info(f"GTFS data found at: {gtfs_zip_path}")
                return gtfs_zip_path
            else:
                logger.warning(f"GTFS data not found at: {gtfs_zip_path}")
                logger.info("Please manually download GTFS data from MARTA Developer Portal")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download GTFS data: {e}")
            return None
    
    def load_csv_to_db(self, zip_file_obj, csv_filename: str, config: Dict):
        """Load CSV data from zip file into database table"""
        table_name = config["table"]
        columns = config["columns"]
        logger.info(f"Loading {csv_filename} into {table_name}...")
        
        try:
            with zip_file_obj.open(csv_filename) as f:
                df = pd.read_csv(io.TextIOWrapper(f, encoding='utf-8'))
                
                # Ensure column names match database schema
                df = df.reindex(columns=columns, fill_value=None)

                # Handle specific data type conversions for stops.txt
                if csv_filename == "stops.txt":
                    # Convert to nullable integer type, then replace NaN with None
                    for col in ["location_type", "wheelchair_boarding"]:
                        if col in df.columns:
                            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)
                
                # Handle specific data type conversions for routes.txt
                if csv_filename == "routes.txt":
                    for col in ["route_type", "route_sort_order", "continuous_pickup", "continuous_dropoff"]:
                        if col in df.columns:
                            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)

                # Handle specific data type conversions for calendar.txt
                if csv_filename == "calendar.txt":
                    for col in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                        if col in df.columns:
                            df[col] = df[col].apply(lambda x: bool(int(x)) if x is not None else None)
                    for col in ["start_date", "end_date"]:
                        if col in df.columns:
                            df[col] = df[col].apply(lambda x: pd.to_datetime(str(int(x)), format='%Y%m%d').date() if x is not None else None)

                # General cleanup: replace NaN with None and ensure native Python types
                df = df.where(pd.notnull(df), None)
                df = df.astype(object)

                # Convert DataFrame to list of tuples
                data_to_insert = [tuple(row) for row in df.values]
                
                if not data_to_insert:
                    logger.warning(f"No data to insert for {csv_filename}")
                    return
                
                # Prepare INSERT statement with upsert capability
                cols_str = ', '.join(columns)
                vals_str = ', '.join(['%s' for _ in columns])
                
                # Use ON CONFLICT for upsert (PostgreSQL specific)
                table_name = config["table"]
                columns = config["columns"]
                conflict_cols = config["primary_key"]
                update_cols = [f"{col} = EXCLUDED.{col}" for col in columns[1:]]
                
                insert_query = f"""
                    INSERT INTO {table_name} ({cols_str}) 
                    VALUES %s 
                    ON CONFLICT ({', '.join(conflict_cols)}) 
                    DO UPDATE SET {', '.join(update_cols)}
                """
                
                with self.db_connection.cursor() as cursor:
                    extras.execute_values(cursor, insert_query, data_to_insert, page_size=1000)
                    self.db_connection.commit()
                    
                logger.info(f"Successfully loaded {len(data_to_insert)} rows into {table_name}")
                
        except Exception as e:
            self.db_connection.rollback()
            logger.error(f"Error loading {csv_filename}: {e}")
            raise
    
    def ingest_gtfs_static(self, gtfs_zip_path: str):
        """Main method to ingest GTFS static data"""
        try:
            # Create database connection and tables
            self.create_db_connection()
            self.create_tables()
            
            with zipfile.ZipFile(gtfs_zip_path, 'r') as zf:
                for gtfs_file, config in self.gtfs_files_config.items():
                    if gtfs_file in zf.namelist():
                        self.load_csv_to_db(zf, gtfs_file, config)
                    else:
                        logger.warning(f"File {gtfs_file} not found in GTFS zip")
            
            logger.info("GTFS static data ingestion completed successfully")
            
        except Exception as e:
            logger.error(f"GTFS ingestion failed: {e}")
            raise
        finally:
            if self.db_connection:
                self.db_connection.close()
    
    def validate_gtfs_data(self) -> Dict[str, bool]:
        """Validate GTFS data quality"""
        validation_results = {}
        
        try:
            self.create_db_connection()
            
            # Check for required files
            for table_name in self.gtfs_files_config.keys():
                table_name_clean = table_name.replace('.txt', '')
                with self.db_connection.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name_clean}")
                    count = cursor.fetchone()[0]
                    validation_results[f"{table_name}_has_data"] = count > 0
            
            # Check referential integrity
            with self.db_connection.cursor() as cursor:
                # Check if trips reference valid routes
                cursor.execute("""
                    SELECT COUNT(*) FROM gtfs_trips t 
                    LEFT JOIN gtfs_routes r ON t.route_id = r.route_id 
                    WHERE r.route_id IS NULL
                """)
                orphan_trips = cursor.fetchone()[0]
                validation_results["referential_integrity_trips_routes"] = orphan_trips == 0
                
                # Check if stop_times reference valid trips and stops
                cursor.execute("""
                    SELECT COUNT(*) FROM gtfs_stop_times st 
                    LEFT JOIN gtfs_trips t ON st.trip_id = t.trip_id 
                    LEFT JOIN gtfs_stops s ON st.stop_id = s.stop_id 
                    WHERE t.trip_id IS NULL OR s.stop_id IS NULL
                """)
                orphan_stop_times = cursor.fetchone()[0]
                validation_results["referential_integrity_stop_times"] = orphan_stop_times == 0
            
            logger.info("GTFS data validation completed")
            
        except Exception as e:
            logger.error(f"GTFS validation failed: {e}")
            validation_results["validation_error"] = False
        
        finally:
            if self.db_connection:
                self.db_connection.close()
        
        return validation_results


def main():
    """Main function for GTFS ingestion"""
    logging.basicConfig(level=logging.INFO)
    
    ingestor = GTFSIngestor()
    
    # Download GTFS data
    gtfs_zip_path = ingestor.download_gtfs_data()
    
    if gtfs_zip_path:
        # Ingest GTFS data
        ingestor.ingest_gtfs_static(gtfs_zip_path)
        
        # Validate ingested data
        validation_results = ingestor.validate_gtfs_data()
        logger.info(f"Validation results: {validation_results}")
    else:
        logger.error("GTFS data not available for ingestion")


if __name__ == "__main__":
    main() 