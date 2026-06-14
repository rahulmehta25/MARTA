"""
MARTA Transit Analytics API - Production FastAPI Application

A production-grade API for transit demand forecasting, route optimization,
real-time tracking, and analytics.

Features:
- JWT and API key authentication
- Rate limiting with token bucket algorithm
- Response caching with TTL
- Structured JSON logging with request ID tracking
- Health checks (liveness + readiness)
- OpenAPI documentation with examples
- WebSocket support for real-time updates
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from backend.api.core.config import settings
from backend.api.core.logging import setup_logging, get_logger
from backend.api.core.cache import cache, cache_cleanup_task
from backend.api.middleware import setup_middleware
from backend.api.routers import (
    stops_router,
    routes_router,
    analytics_router,
    realtime_router,
    health_router,
    auth_router,
)
from backend.api.services.database import init_database

# Setup logging
setup_logging(
    level=settings.log_level,
    log_format=settings.log_format,
    log_file=settings.log_file,
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(
        "Starting MARTA Transit API",
        version=settings.app_version,
        environment=settings.environment,
    )

    # Initialize database
    db_ok = init_database()
    if db_ok:
        logger.info("Database connection established")
    else:
        logger.warning("Database connection failed - running in demo mode")

    # Start cache cleanup task
    cleanup_task = asyncio.create_task(cache_cleanup_task(interval=60))

    yield

    # Shutdown
    logger.info("Shutting down MARTA Transit API")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


def custom_openapi():
    """Generate custom OpenAPI schema with additional metadata."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.api_title,
        version=settings.app_version,
        description="""
# MARTA Transit Analytics API

Production-grade API for transit demand forecasting, route optimization,
real-time vehicle tracking, and system analytics.

## Features

- **Demand Forecasting**: ML-powered predictions at stop level
- **Route Optimization**: Headway and short-turn optimization
- **Real-time Tracking**: Vehicle positions and arrival predictions
- **Analytics**: Ridership trends and performance KPIs
- **WebSocket**: Live updates for real-time data

## Authentication

The API supports two authentication methods:

1. **JWT Token**: Obtain via `/api/v1/auth/token` endpoint
2. **API Key**: Pass in `X-API-Key` header

Some endpoints (forecasting, optimization) require authentication.
Read-only endpoints are publicly accessible.

## Rate Limiting

- 100 requests per minute per IP
- Burst limit of 20 requests
- Rate limit headers included in responses

## Response Format

All responses follow a consistent format:
```json
{
  "success": true,
  "data": {...},
  "timestamp": "2026-03-13T12:00:00Z",
  "request_id": "abc123"
}
```
        """,
        routes=app.routes,
        tags=[
            {
                "name": "Stops",
                "description": "Transit stops with demand forecasting",
            },
            {
                "name": "Routes",
                "description": "Transit routes with optimization",
            },
            {
                "name": "Analytics",
                "description": "Ridership and performance analytics",
            },
            {
                "name": "Real-time",
                "description": "Live vehicle positions and arrivals",
            },
            {
                "name": "Health",
                "description": "Health checks and system status",
            },
            {
                "name": "Authentication",
                "description": "JWT token and API key management",
            },
        ],
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT access token",
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": settings.api_key_header,
            "description": "API key for server-to-server authentication",
        },
    }

    # Add contact and license info
    openapi_schema["info"]["contact"] = {
        "name": "MARTA Analytics Team",
        "email": "analytics@itsmarta.com",
    }
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }

    # Add servers
    openapi_schema["servers"] = [
        {
            "url": f"http://localhost:{settings.api_port}",
            "description": "Development server",
        },
    ]
    if settings.is_production:
        openapi_schema["servers"].insert(0, {
            "url": "https://api.marta-analytics.com",
            "description": "Production server",
        })

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.app_version,
    description=settings.api_description,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Setup custom OpenAPI
app.openapi = custom_openapi

# Setup middleware
setup_middleware(app)

# Include routers
app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(stops_router, prefix=settings.api_prefix)
app.include_router(routes_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
app.include_router(realtime_router, prefix=settings.api_prefix)


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
        "endpoints": {
            "stops": f"{settings.api_prefix}/stops",
            "routes": f"{settings.api_prefix}/routes",
            "analytics": f"{settings.api_prefix}/analytics",
            "realtime": f"{settings.api_prefix}/realtime",
            "health": "/health",
            "auth": f"{settings.api_prefix}/auth",
        },
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
