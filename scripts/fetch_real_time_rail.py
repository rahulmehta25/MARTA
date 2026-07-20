#!/usr/bin/env python3
"""
Fetch real-time MARTA rail arrival data and store in database
This integrates with MARTA's Rail Realtime RESTful API
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models_sqlite import Base, RealTimeArrival, Stop
from src.config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealTimeRailFetcher:
    """Fetch and store real-time MARTA rail arrival data"""
    
    def __init__(self, db_path: str = "marta_data.db"):
        """Initialize fetcher with database connection"""
        self.db_path = Path(db_path)
        self.api_key = settings.marta_rail_api_key
        self.api_url = settings.marta_rail_api_url
        
        if not self.api_key:
            raise ValueError("MARTA_RAIL_API_KEY not found in environment variables")
        
        # Create database engine
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def fetch_rail_arrivals(self) -> Optional[List[Dict]]:
        """Fetch real-time rail arrival data from MARTA API"""
        try:
            # Build API URL with key
            url = f"{self.api_url}?apiKey={self.api_key}"
            
            logger.info(f"Fetching real-time rail data from MARTA API...")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} arrival records")
                return data
            else:
                logger.error(f"API returned status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching data from API: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing API response: {e}")
            return None
    
    def parse_arrival_time(self, time_str: str) -> Optional[datetime]:
        """Parse arrival time string from API"""
        try:
            # MARTA API returns times like "12:30:00 PM" or "1:45:00 AM"
            # Convert to datetime
            time_str = time_str.strip()
            
            # Handle different time formats
            if 'T' in time_str:  # ISO format
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:  # 12-hour format with AM/PM
                now = datetime.now()
                # Parse time and combine with today's date
                time_parts = time_str.replace(' AM', '').replace(' PM', '').split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                # Adjust for PM
                if 'PM' in time_str and hour != 12:
                    hour += 12
                elif 'AM' in time_str and hour == 12:
                    hour = 0
                
                arrival = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time is in the past, assume it's tomorrow
                if arrival < now:
                    arrival += timedelta(days=1)
                
                return arrival
                
        except Exception as e:
            logger.warning(f"Could not parse time '{time_str}': {e}")
            return None
    
    def store_arrivals(self, arrivals: List[Dict]):
        """Store arrival data in database"""
        session = self.Session()
        stored_count = 0
        
        try:
            # Clear existing real-time arrivals (they're ephemeral)
            session.query(RealTimeArrival).delete()
            
            # Get valid stop IDs
            valid_stops = set(s.stop_id for s in session.query(Stop.stop_id).all())
            
            for arrival in arrivals:
                try:
                    # Extract fields from API response
                    # MARTA API fields may vary, so we handle multiple formats
                    station = arrival.get('STATION', arrival.get('station', ''))
                    destination = arrival.get('DESTINATION', arrival.get('destination', ''))
                    line = arrival.get('LINE', arrival.get('line', ''))
                    arrival_time = arrival.get('NEXT_ARR', arrival.get('next_arr', ''))
                    waiting_time = arrival.get('WAITING_TIME', arrival.get('waiting_time', ''))
                    direction = arrival.get('DIRECTION', arrival.get('direction', ''))
                    train_id = arrival.get('TRAIN_ID', arrival.get('train_id', ''))
                    
                    # Skip if essential fields are missing
                    if not station or not arrival_time:
                        continue
                    
                    # Try to match station name to stop_id
                    # MARTA stations often end with "STATION"
                    station_name = station.upper().replace(' STATION', '')
                    
                    # Find matching stop in database
                    stop = session.query(Stop).filter(
                        Stop.stop_name.like(f'%{station_name}%')
                    ).first()
                    
                    if not stop:
                        logger.debug(f"Could not find stop for station: {station}")
                        continue
                    
                    # Parse arrival time
                    arrival_datetime = self.parse_arrival_time(arrival_time)
                    if not arrival_datetime:
                        continue
                    
                    # Create real-time arrival record
                    rt_arrival = RealTimeArrival(
                        stop_id=stop.stop_id,
                        route_id=line,  # Line color (RED, GOLD, etc.)
                        arrival_time=arrival_datetime,
                        predicted_time=arrival_datetime,  # Use predicted_time for real-time
                        trip_id=train_id or f"{line}_{station}_{arrival_time}",
                        vehicle_id=train_id,
                        delay_seconds=0,  # Calculate if we have scheduled time
                        last_updated=datetime.now()
                    )
                    
                    session.add(rt_arrival)
                    stored_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing arrival record: {e}")
                    logger.debug(f"Problematic record: {arrival}")
                    continue
            
            session.commit()
            logger.info(f"Stored {stored_count} real-time arrival records")
            
        except Exception as e:
            logger.error(f"Error storing arrivals: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_current_arrivals(self, station_name: Optional[str] = None) -> List[Dict]:
        """Get current arrivals from database"""
        session = self.Session()
        try:
            query = session.query(RealTimeArrival, Stop).join(
                Stop, RealTimeArrival.stop_id == Stop.stop_id
            )
            
            if station_name:
                query = query.filter(Stop.stop_name.like(f'%{station_name}%'))
            
            # Order by arrival time
            query = query.order_by(RealTimeArrival.arrival_time)
            
            results = []
            for arrival, stop in query.all():
                results.append({
                    'station': stop.stop_name,
                    'stop_id': stop.stop_id,
                    'route': arrival.route_id,
                    'trip_id': arrival.trip_id,
                    'arrival_time': arrival.arrival_time.isoformat(),
                    'predicted_time': arrival.predicted_time.isoformat() if arrival.predicted_time else None,
                    'vehicle_id': arrival.vehicle_id,
                    'delay_seconds': arrival.delay_seconds
                })
            
            return results
            
        finally:
            session.close()
    
    def fetch_and_store(self):
        """Main method to fetch and store real-time data"""
        logger.info("=" * 60)
        logger.info("MARTA Real-Time Rail Data Fetcher")
        logger.info("=" * 60)
        
        # Fetch data from API
        arrivals = self.fetch_rail_arrivals()
        
        if arrivals:
            # Store in database
            self.store_arrivals(arrivals)
            
            # Display sample of current arrivals
            current = self.get_current_arrivals()
            if current:
                logger.info("\nSample of current arrivals:")
                for i, arrival in enumerate(current[:5]):
                    logger.info(f"  {arrival['station']} ({arrival['stop_id']})")
                    logger.info(f"    Line: {arrival['route']}, Time: {arrival['arrival_time']}")
            
            return True
        else:
            logger.error("Failed to fetch real-time data")
            return False
    
    def continuous_fetch(self, interval_seconds: int = 30):
        """Continuously fetch data at specified interval"""
        import time
        
        logger.info(f"Starting continuous fetch with {interval_seconds}s interval")
        logger.info("Press Ctrl+C to stop")
        
        while True:
            try:
                success = self.fetch_and_store()
                if success:
                    logger.info(f"Next update in {interval_seconds} seconds...")
                else:
                    logger.warning("Fetch failed, retrying in next interval...")
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("\nStopping continuous fetch...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                logger.info(f"Retrying in {interval_seconds} seconds...")
                time.sleep(interval_seconds)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch MARTA real-time rail data')
    parser.add_argument('--continuous', action='store_true', 
                       help='Run continuously at specified interval')
    parser.add_argument('--interval', type=int, default=30,
                       help='Polling interval in seconds (default: 30)')
    parser.add_argument('--station', type=str,
                       help='Filter results by station name')
    
    args = parser.parse_args()
    
    # Paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / "marta_data.db"
    
    # Initialize fetcher
    fetcher = RealTimeRailFetcher(db_path)
    
    if args.continuous:
        # Run continuously
        fetcher.continuous_fetch(args.interval)
    else:
        # Run once
        fetcher.fetch_and_store()
        
        # Show filtered results if requested
        if args.station:
            arrivals = fetcher.get_current_arrivals(args.station)
            if arrivals:
                print(f"\nArrivals for '{args.station}':")
                for arrival in arrivals:
                    print(f"  Line {arrival['route']} at {arrival['arrival_time']} (Vehicle: {arrival['vehicle_id']})")
            else:
                print(f"No arrivals found for '{args.station}'")


if __name__ == "__main__":
    main()