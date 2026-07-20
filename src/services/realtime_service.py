"""
Real-time data service for MARTA train arrivals.
Polls MARTA's real-time API and updates the database.
"""
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import json

from sqlalchemy.orm import Session
from src.config.settings import settings
from src.database.models_sqlite import RealTimeArrival, Stop

logger = logging.getLogger(__name__)


class RealTimeService:
    """Service for fetching and processing real-time train data."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.api_key = settings.marta_api_key
        self.api_url = settings.marta_rail_api_url
        self.polling_interval = settings.real_time_poll_interval
        self.is_polling = False
        self._polling_task = None
    
    async def fetch_real_time_data(self) -> List[Dict]:
        """
        Fetch real-time arrival data from MARTA API.
        
        Returns:
            List of arrival dictionaries
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"apikey": self.api_key} if self.api_key else {}
                response = await client.get(self.api_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return data if isinstance(data, list) else []
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching real-time data: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching real-time data: {e}")
            return []
    
    async def process_arrivals(self, arrivals_data: List[Dict]) -> int:
        """
        Process and store real-time arrival data.
        
        Args:
            arrivals_data: List of arrival data from API
            
        Returns:
            Number of arrivals processed
        """
        processed = 0
        
        # Mark all existing arrivals as inactive
        self.db.query(RealTimeArrival).update({"is_active": False})
        
        for arrival in arrivals_data:
            try:
                # Parse arrival data
                stop_id = arrival.get('STATION')
                if not stop_id:
                    continue
                
                # Create or update arrival record
                real_time_arrival = RealTimeArrival(
                    stop_id=stop_id,
                    route_id=arrival.get('LINE', ''),
                    destination=arrival.get('DESTINATION', ''),
                    direction=arrival.get('DIRECTION', ''),
                    arrival_time=arrival.get('WAITING_TIME', ''),
                    predicted_time=self._calculate_predicted_time(arrival.get('WAITING_TIME')),
                    train_id=arrival.get('TRAIN_ID'),
                    delay_seconds=arrival.get('DELAY', 0),
                    is_delayed=arrival.get('DELAY', 0) > 60,
                    is_active=True,
                    event_time=datetime.utcnow(),
                    last_updated=datetime.utcnow()
                )
                
                self.db.add(real_time_arrival)
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing arrival: {e}, data: {arrival}")
                continue
        
        try:
            self.db.commit()
            logger.info(f"Processed {processed} real-time arrivals")
        except Exception as e:
            logger.error(f"Error committing arrivals: {e}")
            self.db.rollback()
            processed = 0
        
        return processed
    
    def _calculate_predicted_time(self, waiting_time: str) -> datetime:
        """
        Calculate predicted arrival time from waiting time string.
        
        Args:
            waiting_time: String like "5 min" or "Arriving"
            
        Returns:
            Predicted datetime
        """
        now = datetime.utcnow()
        
        if not waiting_time:
            return now
        
        waiting_lower = waiting_time.lower()
        
        # Handle special cases
        if waiting_lower in ['arriving', 'boarding', '0 min']:
            return now
        
        # Try to extract minutes
        try:
            if 'min' in waiting_lower:
                minutes = int(waiting_lower.split()[0])
                return now + timedelta(minutes=minutes)
        except (ValueError, IndexError):
            pass
        
        return now
    
    async def start_polling(self):
        """Start polling for real-time data."""
        if self.is_polling:
            logger.warning("Real-time polling already running")
            return
        
        self.is_polling = True
        self._polling_task = asyncio.create_task(self._poll_loop())
        logger.info(f"Started real-time polling (interval: {self.polling_interval}s)")
    
    async def stop_polling(self):
        """Stop polling for real-time data."""
        self.is_polling = False
        
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
        
        logger.info("Stopped real-time polling")
    
    async def _poll_loop(self):
        """Main polling loop."""
        while self.is_polling:
            try:
                # Fetch and process data
                data = await self.fetch_real_time_data()
                if data:
                    await self.process_arrivals(data)
                
                # Wait for next poll
                await asyncio.sleep(self.polling_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(self.polling_interval)
    
    def get_arrivals_for_stop(self, stop_id: str, limit: int = 10) -> List[RealTimeArrival]:
        """
        Get real-time arrivals for a specific stop.
        
        Args:
            stop_id: Stop ID
            limit: Maximum number of arrivals to return
            
        Returns:
            List of RealTimeArrival objects
        """
        return self.db.query(RealTimeArrival).filter(
            RealTimeArrival.stop_id == stop_id,
            RealTimeArrival.is_active == True
        ).order_by(RealTimeArrival.predicted_time).limit(limit).all()
    
    def get_system_status(self) -> Dict:
        """Get overall system status based on real-time data."""
        total_arrivals = self.db.query(RealTimeArrival).filter(
            RealTimeArrival.is_active == True
        ).count()
        
        delayed_arrivals = self.db.query(RealTimeArrival).filter(
            RealTimeArrival.is_active == True,
            RealTimeArrival.is_delayed == True
        ).count()
        
        last_update = self.db.query(RealTimeArrival.last_updated).order_by(
            RealTimeArrival.last_updated.desc()
        ).first()
        
        return {
            "total_active_arrivals": total_arrivals,
            "delayed_arrivals": delayed_arrivals,
            "delay_percentage": (delayed_arrivals / total_arrivals * 100) if total_arrivals > 0 else 0,
            "last_update": last_update[0].isoformat() if last_update else None,
            "is_polling": self.is_polling,
            "polling_interval": self.polling_interval
        }