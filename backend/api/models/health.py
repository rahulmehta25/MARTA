"""
Pydantic v2 models for health check endpoints.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status of a single component."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "database",
                "status": "healthy",
                "latency_ms": 5.2,
                "message": "Connection pool healthy",
            }
        }
    )

    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Component status")
    latency_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Response latency in milliseconds",
    )
    message: Optional[str] = Field(None, description="Status message or error")
    last_checked: datetime = Field(
        default_factory=datetime.utcnow,
        description="When component was last checked",
    )
    details: Optional[Dict] = Field(None, description="Additional details")


class DataFreshness(BaseModel):
    """Data freshness information."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data_type": "vehicle_positions",
                "last_updated": "2026-03-13T12:00:00Z",
                "age_seconds": 30,
                "is_stale": False,
                "staleness_threshold_seconds": 120,
            }
        }
    )

    data_type: str = Field(..., description="Type of data")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    age_seconds: Optional[int] = Field(
        None,
        ge=0,
        description="Age of data in seconds",
    )
    is_stale: bool = Field(default=False, description="Whether data is stale")
    staleness_threshold_seconds: int = Field(
        ...,
        ge=0,
        description="Threshold for staleness in seconds",
    )
    record_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of records",
    )


class ModelAvailability(BaseModel):
    """ML model availability status."""

    model_name: str = Field(..., description="Model name")
    version: Optional[str] = Field(None, description="Model version")
    status: HealthStatus = Field(..., description="Model status")
    last_prediction: Optional[datetime] = Field(
        None,
        description="Last successful prediction time",
    )
    predictions_count: int = Field(
        default=0,
        ge=0,
        description="Number of predictions made",
    )
    average_latency_ms: Optional[float] = Field(
        None,
        ge=0,
        description="Average prediction latency",
    )


class HealthCheckResponse(BaseModel):
    """Complete health check response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "environment": "production",
                "uptime_seconds": 86400,
                "timestamp": "2026-03-13T12:00:00Z",
                "components": [],
                "data_freshness": [],
                "models": [],
            }
        }
    )

    status: HealthStatus = Field(..., description="Overall system status")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Running environment")
    uptime_seconds: float = Field(..., ge=0, description="Uptime in seconds")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp",
    )
    components: List[ComponentHealth] = Field(
        default_factory=list,
        description="Component health statuses",
    )
    data_freshness: List[DataFreshness] = Field(
        default_factory=list,
        description="Data freshness information",
    )
    models: List[ModelAvailability] = Field(
        default_factory=list,
        description="ML model availability",
    )


class LivenessResponse(BaseModel):
    """Simple liveness probe response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "alive",
                "timestamp": "2026-03-13T12:00:00Z",
            }
        }
    )

    status: str = Field(default="alive", description="Liveness status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ready",
                "checks": {
                    "database": True,
                    "cache": True,
                    "models": True,
                },
                "timestamp": "2026-03-13T12:00:00Z",
            }
        }
    )

    status: str = Field(..., description="Readiness status (ready/not_ready)")
    checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Individual readiness checks",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
