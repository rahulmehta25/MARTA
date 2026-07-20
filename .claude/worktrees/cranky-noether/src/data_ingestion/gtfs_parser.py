"""
GTFS Data Parser for MARTA Transit Data
Parses GTFS data and loads it into the database
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from datetime import datetime

from src.database.connection import get_db, engine
from src.database.models_sqlite import Stop, Route, Trip, StopTime, Calendar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GTFSParser:
    """Parse and load GTFS data into database"""
    
    def __init__(self, gtfs_path: str):
        self.gtfs_path = Path(gtfs_path)
        self.engine = engine
        
    def parse_agency(self) -> pd.DataFrame:
        """Parse agency.txt file"""
        file_path = self.gtfs_path / "agency.txt"
        if not file_path.exists():
            logger.warning("agency.txt not found")
            return pd.DataFrame()
        
        df = pd.read_csv(file_path)
        logger.info(f"Parsed {len(df)} agencies")
        return df
    
    def parse_stops(self) -> pd.DataFrame:
        """Parse stops.txt file"""
        file_path = self.gtfs_path / "stops.txt"
        if not file_path.exists():
            logger.error("stops.txt not found")
            return pd.DataFrame()
        
        df = pd.read_csv(file_path)
        logger.info(f"Parsed {len(df)} stops")
        return df
    
    def parse_routes(self) -> pd.DataFrame:
        """Parse routes.txt file"""
        file_path = self.gtfs_path / "routes.txt"
        if not file_path.exists():
            logger.error("routes.txt not found")
            return pd.DataFrame()
        
        df = pd.read_csv(file_path)
        logger.info(f"Parsed {len(df)} routes")
        return df
    
    def parse_trips(self) -> pd.DataFrame:
        """Parse trips.txt file"""
        file_path = self.gtfs_path / "trips.txt"
        if not file_path.exists():
            logger.error("trips.txt not found")
            return pd.DataFrame()
        
        df = pd.read_csv(file_path)
        logger.info(f"Parsed {len(df)} trips")
        return df
    
    def parse_stop_times(self) -> pd.DataFrame:
        """Parse stop_times.txt file"""
        file_path = self.gtfs_path / "stop_times.txt"
        if not file_path.exists():
            logger.error("stop_times.txt not found")
            return pd.DataFrame()
        
        # This file can be large, read in chunks if needed
        df = pd.read_csv(file_path)
        logger.info(f"Parsed {len(df)} stop times")
        return df
    
    def parse_calendar(self) -> pd.DataFrame:
        """Parse calendar.txt file"""
        file_path = self.gtfs_path / "calendar.txt"
        if not file_path.exists():
            logger.warning("calendar.txt not found")
            return pd.DataFrame()
        
        df = pd.read_csv(file_path)
        logger.info(f"Parsed {len(df)} calendar entries")
        return df
    
    def load_to_database(self):
        """Load all GTFS data into database"""
        db = next(get_db())
        
        try:
            # Load stops
            stops_df = self.parse_stops()
            if not stops_df.empty:
                self.load_stops(db, stops_df)
            
            # Load routes
            routes_df = self.parse_routes()
            if not routes_df.empty:
                self.load_routes(db, routes_df)
            
            # Load trips
            trips_df = self.parse_trips()
            if not trips_df.empty:
                self.load_trips(db, trips_df)
            
            # Load stop times (this can be slow for large datasets)
            stop_times_df = self.parse_stop_times()
            if not stop_times_df.empty:
                self.load_stop_times(db, stop_times_df)
            
            # Load calendar
            calendar_df = self.parse_calendar()
            if not calendar_df.empty:
                self.load_calendar(db, calendar_df)
            
            db.commit()
            logger.info("Successfully loaded all GTFS data to database")
            
        except Exception as e:
            logger.error(f"Error loading data to database: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def load_stops(self, db: Session, df: pd.DataFrame):
        """Load stops into database"""
        logger.info("Loading stops to database...")
        
        # Clear existing stops
        db.query(Stop).delete()
        
        for _, row in df.iterrows():
            stop = Stop(
                stop_id=str(row['stop_id']),
                stop_code=str(row.get('stop_code', '')) if pd.notna(row.get('stop_code')) else None,
                stop_name=row['stop_name'],
                stop_desc=row.get('stop_desc', ''),
                stop_lat=float(row['stop_lat']),
                stop_lon=float(row['stop_lon']),
                zone_id=str(row.get('zone_id', '')) if pd.notna(row.get('zone_id')) else None,
                stop_url=row.get('stop_url', ''),
                location_type=int(row.get('location_type', 0)),
                parent_station=str(row.get('parent_station', '')) if pd.notna(row.get('parent_station')) else None
            )
            db.add(stop)
        
        db.flush()
        logger.info(f"Loaded {len(df)} stops")
    
    def load_routes(self, db: Session, df: pd.DataFrame):
        """Load routes into database"""
        logger.info("Loading routes to database...")
        
        # Clear existing routes
        db.query(Route).delete()
        
        for _, row in df.iterrows():
            route = Route(
                route_id=str(row['route_id']),
                agency_id=str(row.get('agency_id', '')),
                route_short_name=str(row.get('route_short_name', '')),
                route_long_name=row['route_long_name'],
                route_desc=row.get('route_desc', ''),
                route_type=int(row['route_type']),
                route_url=row.get('route_url', ''),
                route_color=row.get('route_color', 'FFFFFF'),
                route_text_color=row.get('route_text_color', '000000')
            )
            db.add(route)
        
        db.flush()
        logger.info(f"Loaded {len(df)} routes")
    
    def load_trips(self, db: Session, df: pd.DataFrame):
        """Load trips into database"""
        logger.info("Loading trips to database...")
        
        # Clear existing trips
        db.query(Trip).delete()
        
        # Load in batches for better performance
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                trip = Trip(
                    trip_id=str(row['trip_id']),
                    route_id=str(row['route_id']),
                    service_id=str(row['service_id']),
                    trip_headsign=row.get('trip_headsign', ''),
                    trip_short_name=str(row.get('trip_short_name', '')) if pd.notna(row.get('trip_short_name')) else None,
                    direction_id=int(row.get('direction_id', 0)) if pd.notna(row.get('direction_id')) else 0,
                    block_id=str(row.get('block_id', '')) if pd.notna(row.get('block_id')) else None,
                    shape_id=str(row.get('shape_id', '')) if pd.notna(row.get('shape_id')) else None
                )
                db.add(trip)
            
            db.flush()
            logger.info(f"Loaded batch {i//batch_size + 1}/{(len(df)-1)//batch_size + 1}")
        
        logger.info(f"Loaded {len(df)} trips")
    
    def load_stop_times(self, db: Session, df: pd.DataFrame):
        """Load stop times into database"""
        logger.info("Loading stop times to database...")
        
        # Clear existing stop times
        db.query(StopTime).delete()
        
        # This can be very large, process in chunks
        batch_size = 5000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                stop_time = StopTime(
                    trip_id=str(row['trip_id']),
                    arrival_time=row['arrival_time'],
                    departure_time=row['departure_time'],
                    stop_id=str(row['stop_id']),
                    stop_sequence=int(row['stop_sequence']),
                    stop_headsign=row.get('stop_headsign', ''),
                    pickup_type=int(row.get('pickup_type', 0)),
                    drop_off_type=int(row.get('drop_off_type', 0))
                )
                db.add(stop_time)
            
            db.flush()
            logger.info(f"Loaded stop times batch {i//batch_size + 1}/{(len(df)-1)//batch_size + 1}")
        
        logger.info(f"Loaded {len(df)} stop times")
    
    def load_calendar(self, db: Session, df: pd.DataFrame):
        """Load calendar into database"""
        logger.info("Loading calendar to database...")
        
        # Clear existing calendar
        db.query(Calendar).delete()
        
        for _, row in df.iterrows():
            calendar = Calendar(
                service_id=str(row['service_id']),
                monday=bool(row['monday']),
                tuesday=bool(row['tuesday']),
                wednesday=bool(row['wednesday']),
                thursday=bool(row['thursday']),
                friday=bool(row['friday']),
                saturday=bool(row['saturday']),
                sunday=bool(row['sunday']),
                start_date=str(row['start_date']),
                end_date=str(row['end_date'])
            )
            db.add(calendar)
        
        db.flush()
        logger.info(f"Loaded {len(df)} calendar entries")


if __name__ == "__main__":
    # Example usage
    from src.data_ingestion.gtfs_downloader import GTFSDownloader
    
    # Download GTFS data
    downloader = GTFSDownloader()
    if downloader.download_gtfs():
        # Parse and load to database
        parser = GTFSParser(downloader.get_latest_data_path())
        parser.load_to_database()
        logger.info("GTFS data ingestion complete")