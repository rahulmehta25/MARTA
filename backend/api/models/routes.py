"""
Pydantic v2 models for routes and optimization endpoints.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .base import BaseResponse, PaginationMeta


class RouteType(int, Enum):
    """GTFS route types."""
    TRAM = 0
    SUBWAY = 1
    RAIL = 2
    BUS = 3
    FERRY = 4
    CABLE_TRAM = 5
    AERIAL_LIFT = 6
    FUNICULAR = 7
    TROLLEYBUS = 11
    MONORAIL = 12


class RouteBase(BaseModel):
    """Base route model."""

    model_config = ConfigDict(from_attributes=True)

    route_id: str = Field(..., description="Unique route identifier")
    route_short_name: Optional[str] = Field(None, description="Short route name (e.g., '110')")
    route_long_name: Optional[str] = Field(None, description="Full route name")


class RouteResponse(RouteBase):
    """Route response model."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "route_id": "BLUE",
                "route_short_name": "Blue",
                "route_long_name": "Blue Line - Indian Creek to Hamilton E Holmes",
                "route_type": 1,
                "route_color": "0039A6",
                "route_text_color": "FFFFFF",
                "agency_id": "MARTA",
            }
        },
    )

    route_type: RouteType = Field(..., description="GTFS route type")
    route_color: Optional[str] = Field(
        None,
        pattern="^[0-9A-Fa-f]{6}$",
        description="Route color (hex without #)",
    )
    route_text_color: Optional[str] = Field(
        None,
        pattern="^[0-9A-Fa-f]{6}$",
        description="Text color for route (hex without #)",
    )
    agency_id: Optional[str] = Field(None, description="Operating agency ID")
    route_description: Optional[str] = Field(None, description="Route description")


class RouteDetailResponse(RouteResponse):
    """Detailed route response with stops and statistics."""

    stops: Optional[List[str]] = Field(
        default=None,
        description="Ordered list of stop IDs on this route",
    )
    stop_count: int = Field(default=0, ge=0, description="Number of stops")
    average_headway_minutes: Optional[float] = Field(
        None,
        ge=0,
        description="Average headway in minutes",
    )
    average_trip_duration_minutes: Optional[float] = Field(
        None,
        ge=0,
        description="Average trip duration in minutes",
    )
    daily_trips: Optional[int] = Field(
        None,
        ge=0,
        description="Number of trips per day",
    )
    current_status: Optional[str] = Field(
        None,
        description="Current operational status",
    )


class RouteListResponse(BaseResponse):
    """Response model for list of routes."""

    data: List[RouteResponse] = Field(default_factory=list)
    pagination: PaginationMeta


class RouteOptimizeRequest(BaseModel):
    """Request model for route optimization."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "route_ids": ["BLUE", "RED"],
                "optimization_type": "headway",
                "target_timestamp": "2026-03-13T17:00:00Z",
                "constraints": {
                    "min_headway_minutes": 5,
                    "max_headway_minutes": 15,
                    "bus_capacity": 50,
                },
            }
        }
    )

    route_ids: Optional[List[str]] = Field(
        default=None,
        description="Route IDs to optimize (None = all routes)",
    )
    optimization_type: str = Field(
        default="full",
        pattern="^(full|headway|short_turn|capacity)$",
        description="Type of optimization to perform",
    )
    target_timestamp: Optional[datetime] = Field(
        default=None,
        description="Target time for optimization (default: now)",
    )
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optimization constraints",
    )
    include_simulation: bool = Field(
        default=False,
        description="Include simulation results",
    )


class HeadwayOptimization(BaseModel):
    """Headway optimization result for a route."""

    route_id: str = Field(..., description="Route identifier")
    current_headway_minutes: float = Field(
        ...,
        ge=0,
        description="Current headway in minutes",
    )
    optimal_headway_minutes: float = Field(
        ...,
        ge=0,
        description="Recommended optimal headway",
    )
    demand_level: str = Field(..., description="Current demand level")
    recommended_frequency: float = Field(
        ...,
        ge=0,
        description="Recommended buses per hour",
    )
    expected_wait_time_reduction_minutes: Optional[float] = Field(
        None,
        description="Expected reduction in passenger wait time",
    )


class ShortTurnProposal(BaseModel):
    """Proposal for a short-turn loop."""

    route_id: str = Field(..., description="Route identifier")
    start_stop_id: str = Field(..., description="Start of short-turn segment")
    end_stop_id: str = Field(..., description="End of short-turn segment")
    turnaround_stop_id: str = Field(..., description="Turnaround point")
    feasibility_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Feasibility score (0-1)",
    )
    estimated_impact: Dict[str, float] = Field(
        ...,
        description="Estimated impact metrics",
    )


class OptimizationResult(BaseModel):
    """Complete optimization result."""

    optimization_id: str = Field(..., description="Unique optimization run ID")
    optimization_type: str = Field(..., description="Type of optimization performed")
    timestamp: datetime = Field(..., description="When optimization was run")
    routes_analyzed: int = Field(..., ge=0, description="Number of routes analyzed")
    computation_time_seconds: float = Field(
        ...,
        ge=0,
        description="Time taken for optimization",
    )
    headway_optimizations: List[HeadwayOptimization] = Field(
        default_factory=list,
        description="Headway optimization results",
    )
    short_turn_proposals: List[ShortTurnProposal] = Field(
        default_factory=list,
        description="Short-turn loop proposals",
    )
    overall_impact: Dict[str, float] = Field(
        default_factory=dict,
        description="Overall impact metrics",
    )


class RouteOptimizeResponse(BaseResponse):
    """Response model for route optimization."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "result": {
                    "optimization_id": "opt_abc123",
                    "optimization_type": "full",
                    "routes_analyzed": 5,
                    "computation_time_seconds": 2.5,
                    "headway_optimizations": [],
                    "short_turn_proposals": [],
                    "overall_impact": {
                        "wait_time_reduction_minutes": 3.5,
                        "cost_savings_dollars": 1500.0,
                    },
                },
            }
        }
    )

    result: OptimizationResult = Field(..., description="Optimization results")
    warnings: Optional[List[str]] = Field(
        default=None,
        description="Any warnings from the optimization",
    )
