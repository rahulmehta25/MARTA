"""
Schemas for real-time arrival data.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RealTimeArrivalResponse(BaseModel):
    """Schema for real-time arrival response."""
    
    id: int
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    route_id: Optional[str] = None
    trip_id: Optional[str] = None
    arrival_time: datetime
    predicted_time: Optional[datetime] = None
    delay_seconds: int = 0
    vehicle_id: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NextArrivalResponse(BaseModel):
    """Schema for next arrival response."""
    
    stop_id: str
    stop_name: str
    route_id: Optional[str] = None
    arrival_time: Optional[datetime] = None
    wait_minutes: Optional[float] = None
    vehicle_id: Optional[str] = None
    last_updated: Optional[datetime] = None
    message: Optional[str] = None


class StationArrivalsResponse(BaseModel):
    """Schema for station arrivals response."""
    
    station_query: str
    stations_found: list
    arrivals: list


class RealtimeStatusResponse(BaseModel):
    """Schema for real-time status response."""
    
    status: str = Field(..., description="Status of real-time data (active/stale)")
    last_updated: Optional[datetime] = None
    current_arrivals: int = 0
    arrivals_by_route: dict = {}
    data_age_seconds: Optional[int] = None