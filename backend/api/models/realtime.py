"""
Pydantic v2 models for real-time endpoints.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .base import BaseResponse, PaginationMeta


class VehicleStatus(str, Enum):
    """Vehicle status codes."""
    INCOMING_AT = "incoming_at"
    STOPPED_AT = "stopped_at"
    IN_TRANSIT_TO = "in_transit_to"


class OccupancyStatus(str, Enum):
    """Vehicle occupancy status."""
    EMPTY = "empty"
    MANY_SEATS_AVAILABLE = "many_seats_available"
    FEW_SEATS_AVAILABLE = "few_seats_available"
    STANDING_ROOM_ONLY = "standing_room_only"
    CRUSHED_STANDING_ROOM_ONLY = "crushed"
    FULL = "full"
    NOT_ACCEPTING_PASSENGERS = "not_accepting"


class CongestionLevel(str, Enum):
    """Traffic congestion level."""
    UNKNOWN = "unknown"
    RUNNING_SMOOTHLY = "smooth"
    STOP_AND_GO = "stop_and_go"
    CONGESTION = "congestion"
    SEVERE_CONGESTION = "severe"


class VehiclePosition(BaseModel):
    """Vehicle position model."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "vehicle_id": "V1234",
                "route_id": "BLUE",
                "trip_id": "trip_001",
                "latitude": 33.7541,
                "longitude": -84.3916,
                "bearing": 180.0,
                "speed_mph": 25.5,
                "current_status": "in_transit_to",
                "current_stop_sequence": 5,
                "occupancy_status": "few_seats_available",
                "timestamp": "2026-03-13T12:00:00Z",
            }
        },
    )

    vehicle_id: str = Field(..., description="Unique vehicle identifier")
    route_id: Optional[str] = Field(None, description="Route this vehicle is serving")
    trip_id: Optional[str] = Field(None, description="Current trip ID")
    latitude: float = Field(..., ge=-90, le=90, description="Current latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Current longitude")
    bearing: Optional[float] = Field(
        None,
        ge=0,
        le=360,
        description="Direction of travel in degrees",
    )
    speed_mph: Optional[float] = Field(
        None,
        ge=0,
        description="Current speed in mph",
    )
    current_status: Optional[VehicleStatus] = Field(
        None,
        description="Current vehicle status",
    )
    current_stop_id: Optional[str] = Field(None, description="Current or next stop ID")
    current_stop_sequence: Optional[int] = Field(
        None,
        ge=0,
        description="Stop sequence number",
    )
    occupancy_status: Optional[OccupancyStatus] = Field(
        None,
        description="Current occupancy level",
    )
    congestion_level: Optional[CongestionLevel] = Field(
        None,
        description="Traffic congestion level",
    )
    timestamp: datetime = Field(..., description="Position timestamp")


class VehiclePositionResponse(BaseResponse):
    """Response model for vehicle positions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": [],
                "total_vehicles": 150,
                "by_route": {"BLUE": 25, "RED": 28},
                "last_updated": "2026-03-13T12:00:00Z",
            }
        }
    )

    data: List[VehiclePosition] = Field(
        default_factory=list,
        description="List of vehicle positions",
    )
    pagination: Optional[PaginationMeta] = Field(None, description="Pagination info")
    total_vehicles: int = Field(..., ge=0, description="Total active vehicles")
    by_route: Optional[dict] = Field(None, description="Vehicle count by route")
    last_updated: datetime = Field(..., description="When data was last updated")


class ArrivalPrediction(BaseModel):
    """Arrival prediction for a stop."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "stop_id": "FIVE_POINTS",
                "stop_name": "Five Points Station",
                "route_id": "BLUE",
                "trip_id": "trip_001",
                "vehicle_id": "V1234",
                "scheduled_arrival": "2026-03-13T12:00:00Z",
                "predicted_arrival": "2026-03-13T12:02:30Z",
                "delay_seconds": 150,
                "headsign": "Hamilton E Holmes",
                "arrival_in_minutes": 5,
            }
        },
    )

    stop_id: str = Field(..., description="Stop identifier")
    stop_name: Optional[str] = Field(None, description="Stop name")
    route_id: str = Field(..., description="Route identifier")
    route_name: Optional[str] = Field(None, description="Route name")
    trip_id: Optional[str] = Field(None, description="Trip identifier")
    vehicle_id: Optional[str] = Field(None, description="Vehicle identifier")
    scheduled_arrival: Optional[datetime] = Field(
        None,
        description="Scheduled arrival time",
    )
    predicted_arrival: datetime = Field(..., description="Predicted arrival time")
    delay_seconds: int = Field(default=0, description="Delay in seconds (+ = late)")
    headsign: Optional[str] = Field(None, description="Trip headsign/destination")
    arrival_in_minutes: float = Field(
        ...,
        description="Minutes until arrival",
    )
    is_realtime: bool = Field(
        default=True,
        description="Whether this is a real-time prediction",
    )


class ArrivalPredictionResponse(BaseResponse):
    """Response model for arrival predictions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "stop_id": "FIVE_POINTS",
                "stop_name": "Five Points Station",
                "arrivals": [],
                "last_updated": "2026-03-13T12:00:00Z",
            }
        }
    )

    stop_id: str = Field(..., description="Stop identifier")
    stop_name: Optional[str] = Field(None, description="Stop name")
    arrivals: List[ArrivalPrediction] = Field(
        default_factory=list,
        description="List of predicted arrivals",
    )
    last_updated: datetime = Field(..., description="When predictions were updated")
    data_quality: Optional[str] = Field(
        None,
        description="Data quality indicator",
    )


class AlertSeverity(str, Enum):
    """Service alert severity."""
    INFO = "info"
    WARNING = "warning"
    SEVERE = "severe"


class AlertEffect(str, Enum):
    """Effect of service alert."""
    NO_SERVICE = "no_service"
    REDUCED_SERVICE = "reduced_service"
    SIGNIFICANT_DELAYS = "significant_delays"
    DETOUR = "detour"
    ADDITIONAL_SERVICE = "additional_service"
    MODIFIED_SERVICE = "modified_service"
    OTHER = "other"
    UNKNOWN = "unknown"


class ServiceAlert(BaseModel):
    """Service alert model."""

    alert_id: str = Field(..., description="Unique alert identifier")
    severity: AlertSeverity = Field(..., description="Alert severity")
    effect: AlertEffect = Field(..., description="Effect of the alert")
    header: str = Field(..., description="Alert headline")
    description: str = Field(..., description="Full alert description")
    affected_routes: List[str] = Field(
        default_factory=list,
        description="Affected route IDs",
    )
    affected_stops: List[str] = Field(
        default_factory=list,
        description="Affected stop IDs",
    )
    start_time: Optional[datetime] = Field(None, description="Alert start time")
    end_time: Optional[datetime] = Field(None, description="Alert end time")
    url: Optional[str] = Field(None, description="More information URL")


class WebSocketMessageType(str, Enum):
    """WebSocket message types."""
    VEHICLE_UPDATE = "vehicle_update"
    ARRIVAL_UPDATE = "arrival_update"
    ALERT = "alert"
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """WebSocket message model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "vehicle_update",
                "data": {},
                "timestamp": "2026-03-13T12:00:00Z",
            }
        }
    )

    type: WebSocketMessageType = Field(..., description="Message type")
    data: Optional[dict] = Field(None, description="Message payload")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp",
    )
    channel: Optional[str] = Field(None, description="Subscription channel")
    error: Optional[str] = Field(None, description="Error message if type is error")
