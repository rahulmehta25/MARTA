"""
Analytics service for ridership and performance metrics.
"""
import random
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from backend.api.core.logging import get_logger
from backend.api.models.analytics import (
    TimeGranularity,
    RidershipMetrics,
    RidershipByMode,
    SystemMetrics,
    RoutePerformance,
    TimeSeriesDataPoint,
)

logger = get_logger(__name__)


class AnalyticsService:
    """Service for analytics and reporting."""

    async def get_ridership_data(
        self,
        start_date: date,
        end_date: date,
        granularity: TimeGranularity,
        route_ids: Optional[List[str]] = None,
        db=None,
    ) -> Tuple[RidershipMetrics, List[TimeSeriesDataPoint], RidershipByMode, Optional[Dict]]:
        """Get ridership data for a time period."""
        logger.info(
            "Getting ridership data",
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )

        # Try to get from database
        if db is not None:
            try:
                # Query ridership data
                # This would query unified_transit_data or similar table
                pass
            except Exception as e:
                logger.warning(f"Could not get ridership from DB: {e}")

        # Generate demo data
        time_series = self.generate_demo_time_series(start_date, end_date, granularity)

        # Calculate metrics from time series
        values = [p.value for p in time_series]
        total = sum(values)
        days = (end_date - start_date).days + 1

        peak_idx = values.index(max(values))
        peak_point = time_series[peak_idx]

        metrics = RidershipMetrics(
            total_riders=int(total),
            average_daily_riders=round(total / days),
            peak_ridership=int(peak_point.value),
            peak_timestamp=peak_point.timestamp,
            percent_change=random.uniform(-5, 10),
        )

        by_mode = RidershipByMode(
            bus=int(total * 0.60),
            rail=int(total * 0.37),
            paratransit=int(total * 0.03),
        )

        by_route = None
        if route_ids:
            by_route = {}
            for route_id in route_ids:
                by_route[route_id] = int(total * random.uniform(0.05, 0.15))

        return metrics, time_series, by_mode, by_route

    async def get_performance_data(
        self,
        start_date: date,
        end_date: date,
        db=None,
    ) -> Tuple[SystemMetrics, List[RoutePerformance]]:
        """Get system performance data."""
        logger.info(
            "Getting performance data",
            start_date=start_date,
            end_date=end_date,
        )

        # Generate system metrics
        system_metrics = SystemMetrics(
            overall_on_time_performance=random.uniform(82, 92),
            fleet_availability=random.uniform(90, 98),
            average_headway_adherence=random.uniform(78, 88),
            mean_distance_between_failures=random.uniform(8000, 15000),
            customer_complaints_per_100k=random.uniform(2, 8),
            active_vehicles=random.randint(400, 450),
            active_routes=random.randint(100, 120),
        )

        # Generate route performance
        route_performance = self.generate_demo_route_performance(15)

        return system_metrics, route_performance

    def generate_demo_time_series(
        self,
        start_date: date,
        end_date: date,
        granularity: TimeGranularity,
    ) -> List[TimeSeriesDataPoint]:
        """Generate demo time series data."""
        series = []

        if granularity == TimeGranularity.HOURLY:
            delta = timedelta(hours=1)
            base_value = 2000
        elif granularity == TimeGranularity.DAILY:
            delta = timedelta(days=1)
            base_value = 48000
        elif granularity == TimeGranularity.WEEKLY:
            delta = timedelta(weeks=1)
            base_value = 320000
        else:  # MONTHLY
            delta = timedelta(days=30)
            base_value = 1400000

        current = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date, datetime.min.time())

        while current <= end:
            # Add time-based variation
            hour = current.hour if granularity == TimeGranularity.HOURLY else 12
            day = current.weekday()

            # Peak hours and weekday multipliers
            if granularity == TimeGranularity.HOURLY:
                if 7 <= hour <= 9 or 16 <= hour <= 18:
                    multiplier = 1.5
                elif 10 <= hour <= 15:
                    multiplier = 1.0
                elif 6 <= hour <= 22:
                    multiplier = 0.6
                else:
                    multiplier = 0.2
            else:
                multiplier = 1.0 if day < 5 else 0.6

            value = base_value * multiplier * random.uniform(0.85, 1.15)

            series.append(TimeSeriesDataPoint(
                timestamp=current,
                value=round(value),
            ))

            current += delta

        return series

    def generate_demo_route_performance(self, count: int = 10) -> List[RoutePerformance]:
        """Generate demo route performance data."""
        routes = []
        route_names = [
            "BLUE", "RED", "GOLD", "GREEN",
            "110", "12", "21", "36", "39", "40",
            "51", "55", "60", "73", "78",
        ]

        for i, route_id in enumerate(route_names[:count]):
            otp = random.uniform(75, 95)
            routes.append(RoutePerformance(
                route_id=route_id,
                route_name=f"Route {route_id}",
                on_time_performance=round(otp, 1),
                average_delay_minutes=round((100 - otp) / 20, 1),
                trips_completed=random.randint(40, 100),
                trips_cancelled=random.randint(0, 3),
                passenger_load_factor=round(random.uniform(50, 90), 1),
            ))

        return sorted(routes, key=lambda r: r.on_time_performance, reverse=True)
