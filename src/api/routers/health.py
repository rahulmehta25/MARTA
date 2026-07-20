"""
Health check endpoints for monitoring.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import psutil
import os

from src.database import get_db, check_db_connection
from src.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with system information."""
    
    # Check database
    db_status = "connected" if check_db_connection() else "disconnected"
    
    # Get system metrics
    process = psutil.Process(os.getpid())
    memory = process.memory_info()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "database": {
            "status": db_status,
            "url": settings.db_host
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": memory.rss / 1024 / 1024,
            "disk_usage_percent": psutil.disk_usage('/').percent
        },
        "features": {
            "real_time_updates": settings.enable_real_time_updates,
            "ml_predictions": settings.enable_ml_predictions,
            "caching": settings.enable_caching
        }
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes/container deployments."""
    if not check_db_connection():
        return {
            "status": "not_ready",
            "reason": "database_unavailable"
        }
    
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes/container deployments."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }