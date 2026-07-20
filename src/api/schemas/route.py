"""
Pydantic schemas for Route models.
"""
from pydantic import BaseModel, Field
from typing import Optional


class RouteBase(BaseModel):
    """Base route schema."""
    route_short_name: str = Field(..., max_length=50)
    route_long_name: str = Field(..., max_length=255)
    route_desc: Optional[str] = None
    route_type: int = Field(..., ge=0, le=7)
    route_color: Optional[str] = Field(None, max_length=6)
    route_text_color: Optional[str] = Field(None, max_length=6)


class RouteCreate(RouteBase):
    """Schema for creating a route."""
    route_id: str = Field(..., max_length=50)


class RouteResponse(RouteBase):
    """Schema for route responses."""
    route_id: str
    avg_delay_minutes: Optional[float] = None
    on_time_performance: Optional[float] = None
    daily_ridership: Optional[int] = None
    
    class Config:
        from_attributes = True