"""Pydantic v2 models for MARTA API."""
from .base import (
    BaseResponse,
    PaginatedResponse,
    PaginationParams,
    ErrorResponse,
    SuccessResponse,
)
from .stops import (
    StopBase,
    StopResponse,
    StopDetailResponse,
    StopListResponse,
    StopForecastRequest,
    StopForecastResponse,
    DemandLevel,
)
from .routes import (
    RouteBase,
    RouteResponse,
    RouteDetailResponse,
    RouteListResponse,
    RouteOptimizeRequest,
    RouteOptimizeResponse,
    OptimizationResult,
    HeadwayOptimization,
    ShortTurnProposal,
)
from .analytics import (
    RidershipTrendResponse,
    PerformanceKPIResponse,
    TimeSeriesDataPoint,
    RoutePerformance,
    SystemMetrics,
)
from .realtime import (
    VehiclePosition,
    VehiclePositionResponse,
    ArrivalPrediction,
    ArrivalPredictionResponse,
    ServiceAlert,
    WebSocketMessage,
    WebSocketMessageType,
)
from .health import (
    HealthStatus,
    HealthCheckResponse,
    ComponentHealth,
    DataFreshness,
)
from .auth import (
    TokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)

__all__ = [
    # Base
    "BaseResponse",
    "PaginatedResponse",
    "PaginationParams",
    "ErrorResponse",
    "SuccessResponse",
    # Stops
    "StopBase",
    "StopResponse",
    "StopDetailResponse",
    "StopListResponse",
    "StopForecastRequest",
    "StopForecastResponse",
    "DemandLevel",
    # Routes
    "RouteBase",
    "RouteResponse",
    "RouteDetailResponse",
    "RouteListResponse",
    "RouteOptimizeRequest",
    "RouteOptimizeResponse",
    "OptimizationResult",
    "HeadwayOptimization",
    "ShortTurnProposal",
    # Analytics
    "RidershipTrendResponse",
    "PerformanceKPIResponse",
    "TimeSeriesDataPoint",
    "RoutePerformance",
    "SystemMetrics",
    # Realtime
    "VehiclePosition",
    "VehiclePositionResponse",
    "ArrivalPrediction",
    "ArrivalPredictionResponse",
    "ServiceAlert",
    "WebSocketMessage",
    "WebSocketMessageType",
    # Health
    "HealthStatus",
    "HealthCheckResponse",
    "ComponentHealth",
    "DataFreshness",
    # Auth
    "TokenRequest",
    "TokenResponse",
    "UserCreate",
    "UserResponse",
]
