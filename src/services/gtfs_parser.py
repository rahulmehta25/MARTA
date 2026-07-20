"""
GTFS data parser for MARTA transit data.
Handles parsing of GTFS static feed data.
"""
import csv
import zipfile
import io
from typing import Dict, List, Any, Optional
from datetime import datetime, time
import logging

from sqlalchemy.orm import Session
from src.database.models import Route, Stop, Trip, StopTime

logger = logging.getLogger(__name__)


class GTFSParser:
    """Parse GTFS static feed data."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.stats = {
            "routes": 0,
            "stops": 0,
            "trips": 0,
            "stop_times": 0,
            "errors": 0
        }
    
    def parse_zip(self, zip_data: bytes) -> Dict[str, int]:
        """
        Parse GTFS ZIP file and load data into database.
        
        Args:
            zip_data: GTFS ZIP file content as bytes
            
        Returns:
            Dictionary with import statistics
        """
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                # Parse in correct order (dependencies first)
                self._parse_routes(zf)
                self._parse_stops(zf)
                self._parse_trips(zf)
                self._parse_stop_times(zf)
                
                # Commit all changes
                self.db.commit()
                logger.info(f"GTFS import completed: {self.stats}")
                
        except Exception as e:
            logger.error(f"Error parsing GTFS data: {e}")
            self.db.rollback()
            raise
            
        return self.stats
    
    def _parse_routes(self, zf: zipfile.ZipFile):
        """Parse routes.txt file."""
        try:
            with zf.open('routes.txt') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                
                for row in reader:
                    route = self.db.query(Route).filter_by(
                        route_id=row['route_id']
                    ).first()
                    
                    if not route:
                        route = Route()
                    
                    # Update fields
                    route.route_id = row['route_id']
                    route.route_short_name = row.get('route_short_name', '')
                    route.route_long_name = row.get('route_long_name', '')
                    route.route_desc = row.get('route_desc', None)
                    route.route_type = int(row.get('route_type', 0))
                    route.route_url = row.get('route_url', None)
                    route.route_color = row.get('route_color', None)
                    route.route_text_color = row.get('route_text_color', None)
                    
                    self.db.add(route)
                    self.stats["routes"] += 1
                    
                self.db.flush()
                logger.info(f"Imported {self.stats['routes']} routes")
                
        except KeyError as e:
            logger.error(f"Missing routes.txt in GTFS feed: {e}")
        except Exception as e:
            logger.error(f"Error parsing routes: {e}")
            self.stats["errors"] += 1
    
    def _parse_stops(self, zf: zipfile.ZipFile):
        """Parse stops.txt file."""
        try:
            with zf.open('stops.txt') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                
                for row in reader:
                    stop = self.db.query(Stop).filter_by(
                        stop_id=row['stop_id']
                    ).first()
                    
                    if not stop:
                        stop = Stop()
                    
                    # Update fields
                    stop.stop_id = row['stop_id']
                    stop.stop_code = row.get('stop_code', None)
                    stop.stop_name = row.get('stop_name', '')
                    stop.stop_desc = row.get('stop_desc', None)
                    stop.stop_lat = float(row.get('stop_lat', 0))
                    stop.stop_lon = float(row.get('stop_lon', 0))
                    stop.zone_id = row.get('zone_id', None)
                    stop.stop_url = row.get('stop_url', None)
                    stop.location_type = int(row.get('location_type', 0))
                    stop.parent_station = row.get('parent_station', None)
                    stop.stop_timezone = row.get('stop_timezone', None)
                    stop.wheelchair_boarding = int(row.get('wheelchair_boarding', 0))
                    stop.platform_code = row.get('platform_code', None)
                    
                    self.db.add(stop)
                    self.stats["stops"] += 1
                    
                self.db.flush()
                logger.info(f"Imported {self.stats['stops']} stops")
                
        except KeyError as e:
            logger.error(f"Missing stops.txt in GTFS feed: {e}")
        except Exception as e:
            logger.error(f"Error parsing stops: {e}")
            self.stats["errors"] += 1
    
    def _parse_trips(self, zf: zipfile.ZipFile):
        """Parse trips.txt file."""
        try:
            with zf.open('trips.txt') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                
                for row in reader:
                    trip = self.db.query(Trip).filter_by(
                        trip_id=row['trip_id']
                    ).first()
                    
                    if not trip:
                        trip = Trip()
                    
                    # Update fields
                    trip.trip_id = row['trip_id']
                    trip.route_id = row['route_id']
                    trip.service_id = row['service_id']
                    trip.trip_headsign = row.get('trip_headsign', None)
                    trip.trip_short_name = row.get('trip_short_name', None)
                    trip.direction_id = int(row.get('direction_id', 0))
                    trip.block_id = row.get('block_id', None)
                    trip.shape_id = row.get('shape_id', None)
                    trip.wheelchair_accessible = int(row.get('wheelchair_accessible', 0))
                    trip.bikes_allowed = int(row.get('bikes_allowed', 0))
                    
                    self.db.add(trip)
                    self.stats["trips"] += 1
                    
                self.db.flush()
                logger.info(f"Imported {self.stats['trips']} trips")
                
        except KeyError as e:
            logger.error(f"Missing trips.txt in GTFS feed: {e}")
        except Exception as e:
            logger.error(f"Error parsing trips: {e}")
            self.stats["errors"] += 1
    
    def _parse_stop_times(self, zf: zipfile.ZipFile):
        """Parse stop_times.txt file."""
        try:
            with zf.open('stop_times.txt') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                
                # Batch process for better performance
                batch_size = 1000
                batch = []
                
                for row in reader:
                    stop_time = StopTime(
                        trip_id=row['trip_id'],
                        stop_id=row['stop_id'],
                        arrival_time=self._parse_time(row.get('arrival_time')),
                        departure_time=self._parse_time(row.get('departure_time')),
                        stop_sequence=int(row.get('stop_sequence', 0)),
                        stop_headsign=row.get('stop_headsign', None),
                        pickup_type=int(row.get('pickup_type', 0)),
                        drop_off_type=int(row.get('drop_off_type', 0)),
                        shape_dist_traveled=float(row.get('shape_dist_traveled', 0)) if row.get('shape_dist_traveled') else None,
                        timepoint=int(row.get('timepoint', 1)) if row.get('timepoint') else None
                    )
                    
                    batch.append(stop_time)
                    self.stats["stop_times"] += 1
                    
                    if len(batch) >= batch_size:
                        self.db.bulk_save_objects(batch)
                        self.db.flush()
                        batch = []
                
                # Save remaining batch
                if batch:
                    self.db.bulk_save_objects(batch)
                    self.db.flush()
                
                logger.info(f"Imported {self.stats['stop_times']} stop times")
                
        except KeyError as e:
            logger.error(f"Missing stop_times.txt in GTFS feed: {e}")
        except Exception as e:
            logger.error(f"Error parsing stop times: {e}")
            self.stats["errors"] += 1
    
    def _parse_time(self, time_str: Optional[str]) -> Optional[time]:
        """
        Parse GTFS time string (can be > 24:00:00 for next day).
        
        Args:
            time_str: Time string in HH:MM:SS format
            
        Returns:
            Python time object or None
        """
        if not time_str:
            return None
            
        try:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2]) if len(parts) > 2 else 0
            
            # Handle times > 24:00:00 (next day)
            if hours >= 24:
                hours = hours % 24
            
            return time(hours, minutes, seconds)
        except (ValueError, IndexError):
            logger.warning(f"Invalid time format: {time_str}")
            return None