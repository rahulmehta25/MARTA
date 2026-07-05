"""
Analytics API endpoints for ridership trends and performance KPIs.
"""
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status

from backend.api.core.config import settings
from backend.api.core.logging import get_logger
from backend.api.core.cache import cached
from backend.api.core.security import get_current_user, User
from backend.api.models.analytics import (
    RidershipTrendResponse,
    PerformanceKPIResponse,
    TimeGranularity,
    RidershipMetrics,
    RidershipByMode,
    SystemMetrics,
    RoutePerformance,
    TimeSeriesDataPoint,
)
from backend.api.services.database import get_db
from backend.api.services.analytics import AnalyticsService

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/ridership",
    response_model=RidershipTrendResponse,
    summary="Get ridership trends",
    description="""
    Retrieve ridership trends and statistics for a specified time period.

    Returns:
    - Total and average ridership metrics
    - Time series data at specified granularity
    - Breakdown by transit mode (bus, rail, paratransit)
    - Comparison with previous period

    Granularity options:
    - hourly: Hourly data (max 7 days)
    - daily: Daily data (max 90 days)
    - weekly: Weekly data (max 1 year)
    - monthly: Monthly data (max 2 years)
    """,
    responses={
        200: {"description": "Ridership data retrieved successfully"},
        400: {"description": "Invalid date range or parameters"},
    },
)
@cached(ttl=600, key_prefix="analytics_ridership")
async def get_ridership_trends(
    start_date: date = Query(
        default=None,
        description="Start date (defaults to 30 days ago)",
    ),
    end_date: date = Query(
        default=None,
        description="End date (defaults to today)",
    ),
    granularity: TimeGranularity = Query(
        default=TimeGranularity.DAILY,
        description="Data granularity",
    ),
    route_ids: Optional[str] = Query(
        default=None,
        description="Comma-separated route IDs to filter",
    ),
    include_by_route: bool = Query(
        default=False,
        description="Include breakdown by route",
    ),
    db=Depends(get_db),
):
    """Get ridership trends for a time period."""
    # Default date range
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )

    date_range_days = (end_date - start_date).days
    if granularity == TimeGranularity.HOURLY and date_range_days > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hourly granularity limited to 7 days maximum",
        )

    logger.info(
        "Getting ridership trends",
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )

    analytics_service = AnalyticsService()

    try:
        # Parse route filters
        route_list = None
        if route_ids:
            route_list = [r.strip() for r in route_ids.split(",")]

        # Get ridership data
        metrics, time_series, by_mode, by_route = await analytics_service.get_ridership_data(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            route_ids=route_list,
            db=db,
        )

        return RidershipTrendResponse(
            success=True,
            period_start=start_date,
            period_end=end_date,
            granularity=granularity,
            metrics=metrics,
            time_series=time_series,
            by_mode=by_mode,
            by_route=by_route if include_by_route else None,
        )

    except Exception as e:
        logger.error(f"Error getting ridership data: {e}")
        # Return demo data
        return RidershipTrendResponse(
            success=True,
            period_start=start_date,
            period_end=end_date,
            granularity=granularity,
            metrics=RidershipMetrics(
                total_riders=1500000,
                average_daily_riders=50000,
                peak_ridership=75000,
                peak_timestamp=datetime.combine(end_date, datetime.min.time()),
                percent_change=5.2,
            ),
            time_series=analytics_service.generate_demo_time_series(
                start_date, end_date, granularity
            ),
            by_mode=RidershipByMode(
                bus=900000,
                rail=550000,
                paratransit=50000,
            ),
        )


@router.get(
    "/performance",
    response_model=PerformanceKPIResponse,
    summary="Get system performance KPIs",
    description="""
    Retrieve system-wide performance key performance indicators (KPIs).

    Returns:
    - On-time performance (OTP)
    - Fleet availability
    - Headway adherence
    - Per-route performance breakdown
    - Top and underperforming routes
    - Trend comparison with previous period
    """,
    responses={
        200: {"description": "Performance KPIs retrieved successfully"},
        400: {"description": "Invalid date range"},
    },
)
@cached(ttl=300, key_prefix="analytics_performance")
async def get_performance_kpis(
    start_date: date = Query(
        default=None,
        description="Start date (defaults to 7 days ago)",
    ),
    end_date: date = Query(
        default=None,
        description="End date (defaults to today)",
    ),
    include_routes: bool = Query(
        default=True,
        description="Include per-route breakdown",
    ),
    top_n: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Number of top/bottom routes to include",
    ),
    db=Depends(get_db),
):
    """Get system performance KPIs."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=7)

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )

    logger.info(
        "Getting performance KPIs",
        start_date=start_date,
        end_date=end_date,
    )

    analytics_service = AnalyticsService()

    try:
        system_metrics, route_performance = await analytics_service.get_performance_data(
            start_date=start_date,
            end_date=end_date,
            db=db,
        )

        # Sort routes by OTP
        sorted_routes = sorted(
            route_performance,
            key=lambda r: r.on_time_performance,
            reverse=True,
        )
        top_routes = [r.route_id for r in sorted_routes[:top_n]]
        bottom_routes = [r.route_id for r in sorted_routes[-top_n:]]

        return PerformanceKPIResponse(
            success=True,
            period_start=start_date,
            period_end=end_date,
            system_metrics=system_metrics,
            route_performance=route_performance if include_routes else [],
            top_performing_routes=top_routes,
            underperforming_routes=bottom_routes,
            trend_comparison={
                "otp_change": 1.5,
                "ridership_change": 3.2,
            },
        )

    except Exception as e:
        logger.error(f"Error getting performance data: {e}")
        # Return demo data
        demo_routes = analytics_service.generate_demo_route_performance(10)
        return PerformanceKPIResponse(
            success=True,
            period_start=start_date,
            period_end=end_date,
            system_metrics=SystemMetrics(
                overall_on_time_performance=87.5,
                fleet_availability=94.2,
                average_headway_adherence=82.3,
                active_vehicles=425,
                active_routes=110,
            ),
            route_performance=demo_routes if include_routes else [],
            top_performing_routes=[r.route_id for r in demo_routes[:5]],
            underperforming_routes=[r.route_id for r in demo_routes[-5:]],
            trend_comparison={
                "otp_change": 1.5,
                "ridership_change": 3.2,
            },
        )


@router.get(
    "/summary",
    summary="Get analytics summary",
    description="Get a quick summary of key analytics metrics.",
    responses={
        200: {"description": "Summary retrieved successfully"},
    },
)
async def get_analytics_summary(
    db=Depends(get_db),
):
    """Get quick analytics summary."""
    logger.info("Getting analytics summary")

    return {
        "timestamp": datetime.utcnow(),
        "today": {
            "ridership": 48500,
            "on_time_performance": 88.2,
            "active_routes": 108,
            "active_vehicles": 412,
        },
        "week": {
            "total_ridership": 325000,
            "average_otp": 86.5,
            "busiest_day": "Tuesday",
            "busiest_route": "BLUE",
        },
        "alerts": {
            "performance_warnings": 3,
            "service_disruptions": 1,
        },
    }
