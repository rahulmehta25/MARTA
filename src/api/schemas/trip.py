"""
Pydantic schemas for Trip models.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import time


class TripBase(BaseModel):
    """Base trip schema."""
    route_id: str = Field(..., min_length=1, max_length=50)
    service_id: str = Field(..., min_length=1, max_length=50)
    trip_headsign: Optional[str] = Field(None, max_length=255)
    direction_id: Optional[int] = Field(None, ge=0, le=1)
    wheelchair_accessible: Optional[int] = Field(None, ge=0, le=2)
    bikes_allowed: Optional[int] = Field(None, ge=0, le=2)
    
    @validator('direction_id')
    def validate_direction(cls, v):
        if v is not None and v not in [0, 1]:
            raise ValueError('Direction must be 0 (outbound) or 1 (inbound)')
        return v


class TripCreate(TripBase):
    """Schema for creating a trip."""
    trip_id: str = Field(..., min_length=1, max_length=100)
    trip_short_name: Optional[str] = Field(None, max_length=50)
    block_id: Optional[str] = Field(None, max_length=50)
    shape_id: Optional[str] = Field(None, max_length=50)


class TripResponse(TripBase):
    """Schema for trip responses."""
    trip_id: str
    trip_short_name: Optional[str] = None
    block_id: Optional[str] = None
    shape_id: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    avg_delay_minutes: Optional[int] = None
    completion_rate: Optional[int] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            time: lambda v: v.strftime("%H:%M:%S") if v else None
        }


class TripOptimizationRequest(BaseModel):
    """Request for trip optimization."""
    route_ids: List[str] = Field(..., min_items=1)
    time_window: str = Field("peak", pattern="^(peak|off-peak|all)$")
    optimization_goal: str = Field("efficiency", pattern="^(efficiency|coverage|speed)$")
    constraints: Optional[dict] = None
    
    @validator('route_ids')
    def validate_route_ids(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 routes can be optimized at once')
        return v


class TripOptimizationResponse(BaseModel):
    """Response for trip optimization."""
    success: bool
    optimized_trips: List[dict]
    improvement_metrics: dict
    recommendations: List[str]
    processing_time_ms: int