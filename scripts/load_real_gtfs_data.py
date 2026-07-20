#!/usr/bin/env python3
"""
Load real MARTA GTFS data into SQLite database
This replaces the sample data with actual MARTA routes, stops, and schedules
"""

import os
import sys
import csv
from pathlib import Path
from datetime import datetime, time
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.database.models_sqlite import Base, Route, Stop, Trip, StopTime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GTFSLoader:
    """Load GTFS data from CSV files into database"""
    
    def __init__(self, gtfs_path: str, db_path: str = "marta_data.db"):
        """Initialize loader with GTFS directory path"""
        self.gtfs_path = Path(gtfs_path)
        self.db_path = Path(db_path)
        
        # Create database engine
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def clear_existing_data(self):
        """Clear existing data from database"""
        logger.info("Clearing existing data...")
        session = self.Session()
        try:
            # Delete in correct order due to foreign keys
            session.query(StopTime).delete()
            session.query(Trip).delete()
            session.query(Stop).delete()
            session.query(Route).delete()
            session.commit()
            logger.info("Existing data cleared")
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def load_routes(self):
        """Load routes from routes.txt"""
        logger.info("Loading routes...")
        session = self.Session()
        count = 0
        
        try:
            with open(self.gtfs_path / "routes.txt", 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Filter for rail routes (route_type 0 or 1) and major bus routes
                    route_type = int(row.get('route_type', 3))
                    
                    # MARTA rail routes typically have color codes
                    # Bus routes have route_type = 3
                    if route_type in [0, 1] or (route_type == 3 and row.get('route_short_name', '').isdigit() and int(row.get('route_short_name', '999')) < 200):
                        route = Route(
                            route_id=row['route_id'],
                            route_short_name=row.get('route_short_name', ''),
                            route_long_name=row.get('route_long_name', ''),
                            route_type=route_type,
                            route_color=row.get('route_color', 'FFFFFF'),
                            route_text_color=row.get('route_text_color', '000000')
                        )
                        session.add(route)
                        count += 1
                        
                        if count % 100 == 0:
                            session.commit()
                            logger.info(f"  Loaded {count} routes...")
            
            session.commit()
            logger.info(f"Loaded {count} routes")
            
        except Exception as e:
            logger.error(f"Error loading routes: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def load_stops(self):
        """Load stops from stops.txt"""
        logger.info("Loading stops...")
        session = self.Session()
        count = 0
        
        try:
            with open(self.gtfs_path / "stops.txt", 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Only load stops (not zones or other location types)
                    location_type_str = row.get('location_type', '').strip()
                    location_type = int(location_type_str) if location_type_str else 0
                    if location_type in [0, 1]:  # 0 = stop, 1 = station
                        stop = Stop(
                            stop_id=row['stop_id'],
                            stop_code=row.get('stop_code', row['stop_id']),
                            stop_name=row['stop_name'],
                            stop_desc=row.get('stop_desc', ''),
                            stop_lat=float(row['stop_lat']),
                            stop_lon=float(row['stop_lon']),
                            zone_id=row.get('zone_id', ''),
                            location_type=location_type
                        )
                        session.add(stop)
                        count += 1
                        
                        if count % 500 == 0:
                            session.commit()
                            logger.info(f"  Loaded {count} stops...")
            
            session.commit()
            logger.info(f"Loaded {count} stops")
            
        except Exception as e:
            logger.error(f"Error loading stops: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def load_trips(self):
        """Load trips from trips.txt"""
        logger.info("Loading trips...")
        session = self.Session()
        count = 0
        
        # Get valid route IDs
        valid_routes = set(r.route_id for r in session.query(Route.route_id).all())
        
        try:
            with open(self.gtfs_path / "trips.txt", 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Only load trips for routes we imported
                    if row['route_id'] in valid_routes:
                        trip = Trip(
                            trip_id=row['trip_id'],
                            route_id=row['route_id'],
                            service_id=row['service_id'],
                            trip_headsign=row.get('trip_headsign', ''),
                            direction_id=int(row.get('direction_id', 0)),
                            block_id=row.get('block_id', ''),
                            shape_id=row.get('shape_id', '')
                        )
                        session.add(trip)
                        count += 1
                        
                        if count % 1000 == 0:
                            session.commit()
                            logger.info(f"  Loaded {count} trips...")
            
            session.commit()
            logger.info(f"Loaded {count} trips")
            
        except Exception as e:
            logger.error(f"Error loading trips: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def load_stop_times(self, limit=50000):
        """Load stop times from stop_times.txt (limited for performance)"""
        logger.info(f"Loading stop times (limit: {limit})...")
        session = self.Session()
        count = 0
        
        # Get valid trip and stop IDs
        valid_trips = set(t.trip_id for t in session.query(Trip.trip_id).all())
        valid_stops = set(s.stop_id for s in session.query(Stop.stop_id).all())
        
        try:
            with open(self.gtfs_path / "stop_times.txt", 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Only load stop times for valid trips and stops
                    if row['trip_id'] in valid_trips and row['stop_id'] in valid_stops:
                        stop_time = StopTime(
                            trip_id=row['trip_id'],
                            arrival_time=row.get('arrival_time', ''),
                            departure_time=row.get('departure_time', ''),
                            stop_id=row['stop_id'],
                            stop_sequence=int(row['stop_sequence']),
                            stop_headsign=row.get('stop_headsign', ''),
                            pickup_type=int(row.get('pickup_type', 0)),
                            drop_off_type=int(row.get('drop_off_type', 0))
                        )
                        session.add(stop_time)
                        count += 1
                        
                        if count % 5000 == 0:
                            session.commit()
                            logger.info(f"  Loaded {count} stop times...")
                        
                        if count >= limit:
                            break
            
            session.commit()
            logger.info(f"Loaded {count} stop times")
            
        except Exception as e:
            logger.error(f"Error loading stop times: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_statistics(self):
        """Get statistics about loaded data"""
        session = self.Session()
        try:
            stats = {
                'routes': session.query(Route).count(),
                'stops': session.query(Stop).count(),
                'trips': session.query(Trip).count(),
                'stop_times': session.query(StopTime).count(),
                'rail_routes': session.query(Route).filter(Route.route_type.in_([0, 1])).count(),
                'bus_routes': session.query(Route).filter(Route.route_type == 3).count(),
                'stations': session.query(Stop).filter(Stop.location_type == 1).count(),
                'stops': session.query(Stop).filter(Stop.location_type == 0).count()
            }
            return stats
        finally:
            session.close()
    
    def load_all(self):
        """Load all GTFS data"""
        logger.info("=" * 60)
        logger.info("MARTA GTFS Data Loader")
        logger.info("=" * 60)
        
        # Clear existing data
        self.clear_existing_data()
        
        # Load data in order
        self.load_routes()
        self.load_stops()
        self.load_trips()
        self.load_stop_times()
        
        # Print statistics
        stats = self.get_statistics()
        
        logger.info("=" * 60)
        logger.info("Data loading complete!")
        logger.info("=" * 60)
        logger.info("Database statistics:")
        logger.info(f"  Total routes: {stats['routes']}")
        logger.info(f"    - Rail routes: {stats['rail_routes']}")
        logger.info(f"    - Bus routes: {stats['bus_routes']}")
        logger.info(f"  Total stops: {stats['stops']}")
        logger.info(f"    - Stations: {stats['stations']}")
        logger.info(f"    - Stops: {stats['stops']}")
        logger.info(f"  Total trips: {stats['trips']}")
        logger.info(f"  Total stop times: {stats['stop_times']}")
        logger.info("=" * 60)


def main():
    """Main function"""
    # Paths
    project_root = Path(__file__).parent.parent
    gtfs_path = project_root / "data"
    db_path = project_root / "marta_data.db"
    
    # Check if GTFS data exists
    if not gtfs_path.exists():
        logger.error(f"GTFS data directory not found: {gtfs_path}")
        logger.info("Please download GTFS data first:")
        logger.info("  curl -L -o data/marta_gtfs.zip https://itsmarta.com/google_transit.zip")
        logger.info("  cd data && unzip marta_gtfs.zip")
        sys.exit(1)
    
    # Load data
    loader = GTFSLoader(gtfs_path, db_path)
    loader.load_all()


if __name__ == "__main__":
    main()