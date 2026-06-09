"""
Base Pydantic v2 models for pagination and common responses.
"""
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model with common fields."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "success": True,
                "timestamp": "2026-03-13T12:00:00Z",
            }
        },
    )

    success: bool = Field(default=True, description="Whether the request was successful")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp (UTC)",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracing",
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid stop_id format",
                    "details": {"field": "stop_id", "value": "invalid"},
                },
                "timestamp": "2026-03-13T12:00:00Z",
                "request_id": "abc123",
            }
        }
    )

    success: bool = Field(default=False)
    error: dict = Field(
        ...,
        description="Error details",
        json_schema_extra={
            "example": {
                "code": "NOT_FOUND",
                "message": "Resource not found",
            }
        },
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class SuccessResponse(BaseResponse):
    """Generic success response with optional message."""

    message: Optional[str] = Field(default=None, description="Optional success message")
    data: Optional[Any] = Field(default=None, description="Response data")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 20,
                "sort_by": "name",
                "sort_order": "asc",
            }
        }
    )

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page",
    )
    sort_by: Optional[str] = Field(
        default=None,
        description="Field to sort by",
    )
    sort_order: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    )


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseResponse, Generic[T]):
    """Generic paginated response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": [],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False,
                },
                "timestamp": "2026-03-13T12:00:00Z",
            }
        }
    )

    data: List[T] = Field(default_factory=list, description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


class GeoLocation(BaseModel):
    """Geographic location model."""

    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude in decimal degrees",
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude in decimal degrees",
    )


class TimeRange(BaseModel):
    """Time range for filtering."""

    start: datetime = Field(..., description="Start of time range")
    end: datetime = Field(..., description="End of time range")
