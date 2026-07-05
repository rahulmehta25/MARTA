"""
Health check endpoints for liveness and readiness probes.
"""
import time
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, Response, status

from backend.api.core.config import settings
from backend.api.core.logging import get_logger
from backend.api.core.cache import cache
from backend.api.models.health import (
    HealthStatus,
    HealthCheckResponse,
    ComponentHealth,
    DataFreshness,
    ModelAvailability,
    LivenessResponse,
    ReadinessResponse,
)
from backend.api.services.database import get_db, check_db_health

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])

# Track server start time for uptime calculation
_start_time = time.time()


async def check_database_health(db) -> ComponentHealth:
    """Check database health."""
    start = time.time()
    try:
        is_healthy = await check_db_health(db)
        latency = (time.time() - start) * 1000
        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            message="Connection pool healthy" if is_healthy else "Connection failed",
        )
    except Exception as e:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=str(e),
        )


async def check_cache_health() -> ComponentHealth:
    """Check cache health."""
    try:
        stats = cache.stats()
        return ComponentHealth(
            name="cache",
            status=HealthStatus.HEALTHY,
            message=f"Size: {stats['size']}/{stats['maxsize']}, Hit rate: {stats['hit_rate']:.1%}",
            details=stats,
        )
    except Exception as e:
        return ComponentHealth(
            name="cache",
            status=HealthStatus.DEGRADED,
            message=str(e),
        )


async def check_model_availability() -> List[ModelAvailability]:
    """Check ML model availability."""
    models = []

    # Check for demand forecasting model
    try:
        import os
        model_path = os.path.join(settings.models_dir, "xgboost_model.pkl")
        if os.path.exists(model_path):
            models.append(ModelAvailability(
                model_name="demand_forecast",
                version="2.0.0",
                status=HealthStatus.HEALTHY,
            ))
        else:
            models.append(ModelAvailability(
                model_name="demand_forecast",
                status=HealthStatus.DEGRADED,
            ))
    except Exception:
        models.append(ModelAvailability(
            model_name="demand_forecast",
            status=HealthStatus.UNHEALTHY,
        ))

    return models


async def check_data_freshness(db) -> List[DataFreshness]:
    """Check freshness of various data types."""
    freshness = []

    # Check vehicle positions freshness
    try:
        result = db.execute(
            "SELECT MAX(timestamp) FROM gtfs_vehicle_positions"
        )
        last_update = result.scalar()
        if last_update:
            age = (datetime.utcnow() - last_update).total_seconds()
            freshness.append(DataFreshness(
                data_type="vehicle_positions",
                last_updated=last_update,
                age_seconds=int(age),
                is_stale=age > 120,
                staleness_threshold_seconds=120,
            ))
    except Exception:
        freshness.append(DataFreshness(
            data_type="vehicle_positions",
            is_stale=True,
            staleness_threshold_seconds=120,
        ))

    # Check GTFS static data freshness
    try:
        result = db.execute(
            "SELECT MAX(created_at) FROM gtfs_stops"
        )
        last_update = result.scalar()
        if last_update:
            age = (datetime.utcnow() - last_update).total_seconds()
            freshness.append(DataFreshness(
                data_type="gtfs_static",
                last_updated=last_update,
                age_seconds=int(age),
                is_stale=age > 86400,  # 24 hours
                staleness_threshold_seconds=86400,
            ))
    except Exception:
        freshness.append(DataFreshness(
            data_type="gtfs_static",
            is_stale=True,
            staleness_threshold_seconds=86400,
        ))

    return freshness


def determine_overall_status(components: List[ComponentHealth]) -> HealthStatus:
    """Determine overall health status from component statuses.
    DB/cache being down = degraded (not unhealthy) so Cloud Run doesn't kill the container.
    """
    statuses = [c.status for c in components]

    if all(s == HealthStatus.HEALTHY for s in statuses):
        return HealthStatus.HEALTHY
    else:
        return HealthStatus.DEGRADED


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Full health check",
    description="""
    Comprehensive health check including all system components.

    Checks:
    - Database connectivity and pool health
    - Cache status and hit rates
    - ML model availability
    - Data freshness (real-time and static)

    Returns overall status: healthy, degraded, or unhealthy.
    """,
    responses={
        200: {"description": "System is healthy or degraded"},
        503: {"description": "System is unhealthy"},
    },
)
async def health_check(
    response: Response,
    db=Depends(get_db),
):
    """Comprehensive health check."""
    logger.debug("Running health check")

    components = []

    # Check database
    db_health = await check_database_health(db)
    components.append(db_health)

    # Check cache
    cache_health = await check_cache_health()
    components.append(cache_health)

    # Check models
    models = await check_model_availability()

    # Check data freshness
    try:
        data_freshness = await check_data_freshness(db)
    except Exception:
        data_freshness = []

    # Determine overall status
    overall_status = determine_overall_status(components)

    # Set response status code
    if overall_status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    uptime = time.time() - _start_time

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(uptime, 2),
        components=components,
        data_freshness=data_freshness,
        models=models,
    )


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="""
    Simple liveness check for Kubernetes health probes.

    Returns 200 if the application is running.
    Does not check external dependencies.
    """,
    responses={
        200: {"description": "Application is alive"},
    },
)
async def liveness():
    """Simple liveness probe."""
    return LivenessResponse(
        status="alive",
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="""
    Readiness check for Kubernetes health probes.

    Checks if the application is ready to serve traffic:
    - Database is connected
    - Cache is available
    - Models are loaded (if required)

    Returns 503 if not ready.
    """,
    responses={
        200: {"description": "Application is ready"},
        503: {"description": "Application is not ready"},
    },
)
async def readiness(
    response: Response,
    db=Depends(get_db),
):
    """Readiness probe."""
    checks = {}

    # Check database
    try:
        is_healthy = await check_db_health(db)
        checks["database"] = is_healthy
    except Exception:
        checks["database"] = False

    # Check cache
    try:
        cache.stats()
        checks["cache"] = True
    except Exception:
        checks["cache"] = False

    # Check models (optional)
    if settings.enable_ml_predictions:
        import os
        model_path = os.path.join(settings.models_dir, "xgboost_model.pkl")
        checks["models"] = os.path.exists(model_path)
    else:
        checks["models"] = True

    # Determine readiness
    is_ready = all(checks.values())

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        checks=checks,
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/system/health",
    response_model=HealthCheckResponse,
    summary="System health (alias)",
    description="Alias for /health endpoint.",
)
async def system_health(
    response: Response,
    db=Depends(get_db),
):
    """System health check (alias for /health)."""
    return await health_check(response, db)
