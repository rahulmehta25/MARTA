"""
Pydantic schemas for Stop models.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class StopBase(BaseModel):
    """Base stop schema."""
    stop_name: str = Field(..., min_length=1, max_length=255)
    stop_desc: Optional[str] = None
    stop_lat: float = Field(..., ge=-90, le=90)
    stop_lon: float = Field(..., ge=-180, le=180)
    wheelchair_boarding: Optional[int] = Field(None, ge=0, le=2)
    
    @validator('stop_lat')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('stop_lon')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class StopCreate(StopBase):
    """Schema for creating a stop."""
    stop_id: str = Field(..., min_length=1, max_length=50)
    stop_code: Optional[str] = Field(None, max_length=50)


class StopUpdate(BaseModel):
    """Schema for updating a stop."""
    stop_name: Optional[str] = Field(None, min_length=1, max_length=255)
    stop_desc: Optional[str] = None
    wheelchair_boarding: Optional[int] = Field(None, ge=0, le=2)
    has_bike_parking: Optional[bool] = None
    has_car_parking: Optional[bool] = None
    parking_capacity: Optional[int] = Field(None, ge=0)


class StopResponse(StopBase):
    """Schema for stop responses."""
    stop_id: str
    stop_code: Optional[str] = None
    location_type: Optional[int] = None
    parent_station: Optional[str] = None
    has_bike_parking: bool = False
    has_car_parking: bool = False
    parking_capacity: Optional[int] = None
    avg_daily_boardings: Optional[int] = None
    peak_hour_demand: Optional[int] = None
    demand_level: Optional[str] = None
    
    class Config:
        from_attributes = True


class StopWithArrivals(StopResponse):
    """Stop with real-time arrivals."""
    arrivals: List['ArrivalResponse'] = []
    last_updated: Optional[datetime] = None


class ArrivalResponse(BaseModel):
    """Real-time arrival response."""
    stop_id: str
    route_id: str
    destination: str
    direction: str
    arrival_time: str
    predicted_time: datetime
    delay_seconds: int = 0
    is_delayed: bool = False
    train_id: Optional[str] = None
    
    class Config:
        from_attributes = True


# Avoid circular import
StopWithArrivals.model_rebuild()