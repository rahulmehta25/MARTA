"""
Pydantic v2 models for analytics endpoints.
"""
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .base import BaseResponse


class TimeGranularity(str, Enum):
    """Time granularity for analytics."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TimeSeriesDataPoint(BaseModel):
    """Single data point in a time series."""

    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Metric value")
    label: Optional[str] = Field(None, description="Optional label")


class RidershipMetrics(BaseModel):
    """Ridership metrics for a time period."""

    total_riders: int = Field(..., ge=0, description="Total number of riders")
    average_daily_riders: float = Field(
        ...,
        ge=0,
        description="Average daily ridership",
    )
    peak_ridership: int = Field(..., ge=0, description="Peak ridership observed")
    peak_timestamp: datetime = Field(..., description="When peak occurred")
    percent_change: Optional[float] = Field(
        None,
        description="Percent change from previous period",
    )


class RidershipByMode(BaseModel):
    """Ridership broken down by transit mode."""

    bus: int = Field(default=0, ge=0, description="Bus ridership")
    rail: int = Field(default=0, ge=0, description="Rail ridership")
    paratransit: int = Field(default=0, ge=0, description="Paratransit ridership")


class RidershipTrendResponse(BaseResponse):
    """Response model for ridership trends."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "period_start": "2026-03-01",
                "period_end": "2026-03-13",
                "granularity": "daily",
                "metrics": {
                    "total_riders": 1500000,
                    "average_daily_riders": 115384,
                    "peak_ridership": 145000,
                    "peak_timestamp": "2026-03-07T08:00:00Z",
                    "percent_change": 5.2,
                },
                "time_series": [],
                "by_mode": {"bus": 900000, "rail": 550000, "paratransit": 50000},
            }
        }
    )

    period_start: date = Field(..., description="Start of analysis period")
    period_end: date = Field(..., description="End of analysis period")
    granularity: TimeGranularity = Field(..., description="Data granularity")
    metrics: RidershipMetrics = Field(..., description="Summary metrics")
    time_series: List[TimeSeriesDataPoint] = Field(
        default_factory=list,
        description="Time series data",
    )
    by_mode: RidershipByMode = Field(
        default_factory=RidershipByMode,
        description="Breakdown by transit mode",
    )
    by_route: Optional[Dict[str, int]] = Field(
        None,
        description="Ridership by route",
    )


class RoutePerformance(BaseModel):
    """Performance metrics for a single route."""

    route_id: str = Field(..., description="Route identifier")
    route_name: Optional[str] = Field(None, description="Route name")
    on_time_performance: float = Field(
        ...,
        ge=0,
        le=100,
        description="On-time performance percentage",
    )
    average_delay_minutes: float = Field(..., description="Average delay in minutes")
    trips_completed: int = Field(..., ge=0, description="Number of trips completed")
    trips_cancelled: int = Field(default=0, ge=0, description="Number of cancelled trips")
    passenger_load_factor: float = Field(
        ...,
        ge=0,
        le=100,
        description="Average passenger load as percentage of capacity",
    )


class SystemMetrics(BaseModel):
    """System-wide performance metrics."""

    overall_on_time_performance: float = Field(
        ...,
        ge=0,
        le=100,
        description="System-wide OTP percentage",
    )
    fleet_availability: float = Field(
        ...,
        ge=0,
        le=100,
        description="Fleet availability percentage",
    )
    average_headway_adherence: float = Field(
        ...,
        ge=0,
        le=100,
        description="Headway adherence percentage",
    )
    mean_distance_between_failures: Optional[float] = Field(
        None,
        ge=0,
        description="Mean distance between failures (miles)",
    )
    customer_complaints_per_100k: Optional[float] = Field(
        None,
        ge=0,
        description="Customer complaints per 100k riders",
    )
    active_vehicles: int = Field(..., ge=0, description="Number of active vehicles")
    active_routes: int = Field(..., ge=0, description="Number of active routes")


class PerformanceKPIResponse(BaseResponse):
    """Response model for system performance KPIs."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "period_start": "2026-03-01",
                "period_end": "2026-03-13",
                "system_metrics": {
                    "overall_on_time_performance": 87.5,
                    "fleet_availability": 95.2,
                    "average_headway_adherence": 82.3,
                    "active_vehicles": 450,
                    "active_routes": 110,
                },
                "route_performance": [],
                "trend_comparison": {
                    "otp_change": 2.5,
                    "ridership_change": 5.0,
                },
            }
        }
    )

    period_start: date = Field(..., description="Start of analysis period")
    period_end: date = Field(..., description="End of analysis period")
    system_metrics: SystemMetrics = Field(..., description="System-wide metrics")
    route_performance: List[RoutePerformance] = Field(
        default_factory=list,
        description="Per-route performance metrics",
    )
    top_performing_routes: Optional[List[str]] = Field(
        None,
        description="IDs of top performing routes",
    )
    underperforming_routes: Optional[List[str]] = Field(
        None,
        description="IDs of underperforming routes",
    )
    trend_comparison: Optional[Dict[str, float]] = Field(
        None,
        description="Comparison with previous period",
    )
    alerts: Optional[List[str]] = Field(
        None,
        description="Active performance alerts",
    )
