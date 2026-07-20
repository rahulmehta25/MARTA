"""
Main FastAPI application for MARTA Transit Analytics Platform.
"""
from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import logging

from src.config.settings import settings
from src.api.middleware import setup_middleware
from src.api.routers import health, routes, stops, metrics, realtime
from src.api.websocket import websocket_endpoint, manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Initialize database connection
    from src.database.connection import check_db_connection, get_db
    if check_db_connection():
        logger.info("Database connection established")
    else:
        logger.warning("Database connection failed - running in limited mode")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-time transit analytics and optimization for MARTA",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Setup middleware
setup_middleware(app)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(routes.router, prefix=f"{settings.api_prefix}/routes", tags=["routes"])
app.include_router(stops.router, prefix=f"{settings.api_prefix}/stops", tags=["stops"])
app.include_router(metrics.router, prefix=f"{settings.api_prefix}/metrics", tags=["metrics"])
app.include_router(realtime.router, prefix=f"{settings.api_prefix}/realtime", tags=["realtime"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs"
    }


# WebSocket endpoints
@app.websocket("/ws/real-time")
async def websocket_realtime(websocket: WebSocket):
    """WebSocket endpoint for real-time arrival updates."""
    from src.database.connection import get_db
    db = next(get_db())
    try:
        await websocket_endpoint(websocket, "real-time", db)
    finally:
        db.close()


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for service alerts."""
    from src.database.connection import get_db
    db = next(get_db())
    try:
        await websocket_endpoint(websocket, "alerts", db)
    finally:
        db.close()


@app.websocket("/ws/analytics")
async def websocket_analytics(websocket: WebSocket):
    """WebSocket endpoint for analytics updates."""
    from src.database.connection import get_db
    db = next(get_db())
    try:
        await websocket_endpoint(websocket, "analytics", db)
    finally:
        db.close()