"""
Pydantic v2 models for stops endpoints.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .base import BaseResponse, PaginatedResponse, PaginationMeta


class DemandLevel(str, Enum):
    """Predicted demand level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StopBase(BaseModel):
    """Base stop model."""

    model_config = ConfigDict(from_attributes=True)

    stop_id: str = Field(..., description="Unique stop identifier")
    stop_name: str = Field(..., description="Human-readable stop name")
    stop_code: Optional[str] = Field(None, description="Stop code for passengers")


class StopResponse(StopBase):
    """Stop response model."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "stop_id": "FIVE_POINTS",
                "stop_name": "Five Points Station",
                "stop_code": "5PT",
                "latitude": 33.7541,
                "longitude": -84.3916,
                "zone_id": "zone_1",
                "location_type": 1,
                "wheelchair_boarding": 1,
            }
        },
    )

    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    zone_id: Optional[str] = Field(None, description="Fare zone identifier")
    location_type: int = Field(
        default=0,
        ge=0,
        le=4,
        description="0=stop, 1=station, 2=entrance, 3=generic node, 4=boarding area",
    )
    wheelchair_boarding: int = Field(
        default=0,
        ge=0,
        le=2,
        description="0=unknown, 1=accessible, 2=not accessible",
    )
    routes_served: Optional[List[str]] = Field(
        default=None,
        description="List of route IDs serving this stop",
    )


class StopDetailResponse(StopResponse):
    """Detailed stop response with additional metadata."""

    parent_station: Optional[str] = Field(None, description="Parent station ID")
    platform_code: Optional[str] = Field(None, description="Platform code")
    stop_description: Optional[str] = Field(None, description="Stop description")
    stop_url: Optional[str] = Field(None, description="URL with stop information")
    average_daily_boardings: Optional[int] = Field(
        None,
        ge=0,
        description="Average daily passenger boardings",
    )
    current_demand_level: Optional[DemandLevel] = Field(
        None,
        description="Current demand level",
    )
    nearby_stops: Optional[List["StopResponse"]] = Field(
        default=None,
        description="Nearby stops within walking distance",
    )


class StopListResponse(BaseResponse):
    """Response model for list of stops."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": [
                    {
                        "stop_id": "FIVE_POINTS",
                        "stop_name": "Five Points Station",
                        "latitude": 33.7541,
                        "longitude": -84.3916,
                    }
                ],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False,
                },
            }
        }
    )

    data: List[StopResponse] = Field(default_factory=list)
    pagination: PaginationMeta


class StopForecastRequest(BaseModel):
    """Request model for stop demand forecast."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "forecast_horizon_hours": 24,
                "include_confidence": True,
                "granularity_minutes": 60,
            }
        }
    )

    forecast_horizon_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Forecast horizon in hours (1-168)",
    )
    include_confidence: bool = Field(
        default=True,
        description="Include confidence intervals",
    )
    granularity_minutes: int = Field(
        default=60,
        ge=15,
        le=360,
        description="Forecast granularity in minutes",
    )


class ForecastDataPoint(BaseModel):
    """Single forecast data point."""

    timestamp: datetime = Field(..., description="Forecast timestamp")
    predicted_demand: float = Field(
        ...,
        ge=0,
        description="Predicted passenger demand",
    )
    demand_level: DemandLevel = Field(..., description="Categorical demand level")
    confidence_lower: Optional[float] = Field(
        None,
        ge=0,
        description="Lower bound of 95% confidence interval",
    )
    confidence_upper: Optional[float] = Field(
        None,
        ge=0,
        description="Upper bound of 95% confidence interval",
    )


class StopForecastResponse(BaseResponse):
    """Response model for stop demand forecast."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "stop_id": "FIVE_POINTS",
                "stop_name": "Five Points Station",
                "model_name": "ensemble_v2",
                "model_version": "2.1.0",
                "generated_at": "2026-03-13T12:00:00Z",
                "forecast_horizon_hours": 24,
                "forecasts": [
                    {
                        "timestamp": "2026-03-13T13:00:00Z",
                        "predicted_demand": 450.5,
                        "demand_level": "high",
                        "confidence_lower": 380.0,
                        "confidence_upper": 520.0,
                    }
                ],
            }
        }
    )

    stop_id: str = Field(..., description="Stop identifier")
    stop_name: str = Field(..., description="Stop name")
    model_name: str = Field(..., description="ML model used for prediction")
    model_version: str = Field(..., description="Model version")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When forecast was generated",
    )
    forecast_horizon_hours: int = Field(..., description="Forecast horizon in hours")
    forecasts: List[ForecastDataPoint] = Field(
        default_factory=list,
        description="Forecast data points",
    )
    feature_importance: Optional[dict] = Field(
        None,
        description="Feature importance from the model",
    )


# Update forward references
StopDetailResponse.model_rebuild()
