"""API Routers for MARTA Transit API."""
from .stops import router as stops_router
from .routes import router as routes_router
from .analytics import router as analytics_router
from .realtime import router as realtime_router
from .health import router as health_router
from .auth import router as auth_router

__all__ = [
    "stops_router",
    "routes_router",
    "analytics_router",
    "realtime_router",
    "health_router",
    "auth_router",
]
