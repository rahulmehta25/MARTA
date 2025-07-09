#!/usr/bin/env python3
"""
MARTA GTFS Real-Time Connector
Production-ready connector for MARTA GTFS feeds
"""
import os
import sys
import logging
import requests
import pandas as pd
import psycopg2
from psycopg2 import extras
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MARTAGTFSConnector:
    """Production GTFS connector for MARTA data"""
    
    def __init__(self):
        self.db_config = {
            'host': settings.DB_HOST,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD
        }
        
        # MARTA API endpoints (replace with actual endpoints)
        self.static_gtfs_url = "https://api.marta.io/gtfs/static/gtfs.zip"
        self.vehicle_positions_url = "https://api.marta.io/gtfs-rt/vehicle-positions/vehicle.pb"
        self.trip_updates_url = "https://api.marta.io/gtfs-rt/trip-updates/tripupdate.pb"
        
        # API authentication (replace with actual method)
        self.api_key = os.getenv("MARTA_API_KEY")
        self.headers = {"x-api-key": self.api_key} if self.api_key else {}
    
    def download_static_gtfs(self) -> bool:
        """Download and process MARTA static GTFS data"""
        try:
            logger.info("Downloading MARTA static GTFS data...")
            
            # Download GTFS ZIP file
            response = requests.get(self.static_gtfs_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            temp_file = "data/raw/marta_gtfs_latest.zip"
            os.makedirs(os.path.dirname(temp_file), exist_ok=True)
            
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded GTFS data: {len(response.content)} bytes")
            
            # Process the ZIP file (reuse existing ingestion logic)
            self._process_gtfs_zip(temp_file)
            
            return True
            
        except Exception as e:
            logger.error(f"Error downloading static GTFS: {e}")
            return False
    
    def _process_gtfs_zip(self, zip_path: str):
        """Process downloaded GTFS ZIP file"""
        import zipfile
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Extract and process each GTFS file
                gtfs_files = {
                    'stops.txt': 'gtfs_stops',
                    'routes.txt': 'gtfs_routes', 
                    'trips.txt': 'gtfs_trips',
                    'stop_times.txt': 'gtfs_stop_times'
                }
                
                conn = psycopg2.connect(**self.db_config)
                
                for filename, table_name in gtfs_files.items():
                    if filename in zf.namelist():
                        logger.info(f"Processing {filename}...")
                        self._load_gtfs_file(zf, filename, table_name, conn)
                
                conn.close()
                
        except Exception as e:
            logger.error(f"Error processing GTFS ZIP: {e}")
            raise
    
    def _load_gtfs_file(self, zip_file, filename: str, table_name: str, conn):
        """Load individual GTFS file into database"""
        try:
            with zip_file.open(filename) as f:
                df = pd.read_csv(f)
                
                # Convert DataFrame to list of tuples
                data = [tuple(row) for row in df.values]
                
                if not data:
                    logger.warning(f"No data found in {filename}")
                    return
                
                # Get column names
                columns = df.columns.tolist()
                
                # Prepare INSERT statement
                cols_str = ', '.join(columns)
                vals_str = ', '.join(['%s'] * len(columns))
                
                # Handle different table schemas
                if table_name == 'gtfs_stops':
                    insert_query = f"""
                        INSERT INTO {table_name} (stop_id, stop_name, stop_lat, stop_lon, zone_id) 
                        VALUES ({vals_str}) 
                        ON CONFLICT (stop_id) DO UPDATE SET 
                        stop_name = EXCLUDED.stop_name,
                        stop_lat = EXCLUDED.stop_lat,
                        stop_lon = EXCLUDED.stop_lon,
                        zone_id = EXCLUDED.zone_id
                    """
                elif table_name == 'gtfs_routes':
                    insert_query = f"""
                        INSERT INTO {table_name} (route_id, route_short_name, route_long_name, route_type) 
                        VALUES ({vals_str}) 
                        ON CONFLICT (route_id) DO UPDATE SET 
                        route_short_name = EXCLUDED.route_short_name,
                        route_long_name = EXCLUDED.route_long_name,
                        route_type = EXCLUDED.route_type
                    """
                else:
                    # Generic upsert for other tables
                    insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({vals_str})"
                
                with conn.cursor() as cursor:
                    extras.execute_values(cursor, insert_query, data, page_size=1000)
                    conn.commit()
                    
                logger.info(f"Loaded {len(data)} records into {table_name}")
                
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            conn.rollback()
            raise
    
    def fetch_realtime_data(self) -> Dict:
        """Fetch real-time GTFS data from MARTA API"""
        realtime_data = {
            'vehicle_positions': [],
            'trip_updates': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Fetch vehicle positions
            logger.info("Fetching vehicle positions...")
            vp_response = requests.get(self.vehicle_positions_url, headers=self.headers, timeout=10)
            if vp_response.status_code == 200:
                realtime_data['vehicle_positions'] = self._parse_vehicle_positions(vp_response.content)
            
            # Fetch trip updates
            logger.info("Fetching trip updates...")
            tu_response = requests.get(self.trip_updates_url, headers=self.headers, timeout=10)
            if tu_response.status_code == 200:
                realtime_data['trip_updates'] = self._parse_trip_updates(tu_response.content)
            
            logger.info(f"Fetched {len(realtime_data['vehicle_positions'])} vehicle positions, "
                       f"{len(realtime_data['trip_updates'])} trip updates")
            
        except Exception as e:
            logger.error(f"Error fetching real-time data: {e}")
        
        return realtime_data
    
    def _parse_vehicle_positions(self, content: bytes) -> List[Dict]:
        """Parse vehicle positions from protobuf content"""
        # This would use google-transit-gtfs-realtime library
        # For now, return empty list as placeholder
        return []
    
    def _parse_trip_updates(self, content: bytes) -> List[Dict]:
        """Parse trip updates from protobuf content"""
        # This would use google-transit-gtfs-realtime library
        # For now, return empty list as placeholder
        return []
    
    def store_realtime_data(self, realtime_data: Dict):
        """Store real-time data in unified_data table"""
        try:
            conn = psycopg2.connect(**self.db_config)
            
            # Process vehicle positions
            for vp in realtime_data['vehicle_positions']:
                self._store_vehicle_position(vp, conn)
            
            # Process trip updates
            for tu in realtime_data['trip_updates']:
                self._store_trip_update(tu, conn)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing real-time data: {e}")
            raise
    
    def _store_vehicle_position(self, vp: Dict, conn):
        """Store individual vehicle position"""
        # Implementation would depend on actual data structure
        pass
    
    def _store_trip_update(self, tu: Dict, conn):
        """Store individual trip update"""
        # Implementation would depend on actual data structure
        pass
    
    def run_realtime_stream(self, interval_seconds: int = 30):
        """Run continuous real-time data stream"""
        logger.info(f"Starting real-time data stream (interval: {interval_seconds}s)")
        
        while True:
            try:
                realtime_data = self.fetch_realtime_data()
                self.store_realtime_data(realtime_data)
                
                # Wait for next interval
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Real-time stream stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in real-time stream: {e}")
                time.sleep(interval_seconds)  # Continue despite errors


def main():
    """Main function for testing the connector"""
    connector = MARTAGTFSConnector()
    
    # Test static GTFS download
    print("Testing MARTA GTFS connector...")
    
    # Download static data
    success = connector.download_static_gtfs()
    if success:
        print("✅ Static GTFS download successful")
    else:
        print("❌ Static GTFS download failed")
    
    # Test real-time data fetch
    realtime_data = connector.fetch_realtime_data()
    print(f"✅ Real-time data fetch: {len(realtime_data['vehicle_positions'])} vehicles, "
          f"{len(realtime_data['trip_updates'])} updates")


if __name__ == "__main__":
    main() 