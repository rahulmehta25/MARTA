"""
Real-time data service for vehicle positions and arrivals.
"""
import random
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from backend.api.core.logging import get_logger
from backend.api.models.realtime import (
    VehiclePosition,
    ArrivalPrediction,
    ServiceAlert,
    VehicleStatus,
    OccupancyStatus,
    AlertSeverity,
    AlertEffect,
)

logger = get_logger(__name__)

# Atlanta area bounding box
ATLANTA_BOUNDS = {
    "min_lat": 33.6,
    "max_lat": 33.9,
    "min_lon": -84.6,
    "max_lon": -84.2,
}


class RealtimeService:
    """Service for real-time transit data."""

    async def get_vehicle_positions(
        self,
        route_id: Optional[str] = None,
        bounds: Optional[Tuple[float, float, float, float]] = None,
        db=None,
    ) -> List[VehiclePosition]:
        """Get current vehicle positions."""
        logger.info("Getting vehicle positions", route_id=route_id)

        # Try to get from database
        if db is not None:
            try:
                query = """
                    SELECT
                        vehicle_id, route_id, trip_id, latitude, longitude,
                        bearing, speed, current_stop_sequence, current_status,
                        occupancy_status, timestamp
                    FROM gtfs_vehicle_positions
                    WHERE timestamp > NOW() - INTERVAL '5 minutes'
                """
                params = {}

                if route_id:
                    query += " AND route_id = :route_id"
                    params["route_id"] = route_id

                if bounds:
                    min_lat, max_lat, min_lon, max_lon = bounds
                    query += " AND latitude BETWEEN :min_lat AND :max_lat"
                    query += " AND longitude BETWEEN :min_lon AND :max_lon"
                    params.update({
                        "min_lat": min_lat,
                        "max_lat": max_lat,
                        "min_lon": min_lon,
                        "max_lon": max_lon,
                    })

                query += " ORDER BY timestamp DESC"

                result = db.execute(query, params)
                rows = result.fetchall()

                vehicles = []
                for row in rows:
                    vehicles.append(VehiclePosition(
                        vehicle_id=row.vehicle_id,
                        route_id=row.route_id,
                        trip_id=row.trip_id,
                        latitude=float(row.latitude),
                        longitude=float(row.longitude),
                        bearing=float(row.bearing) if row.bearing else None,
                        speed_mph=float(row.speed) if row.speed else None,
                        current_status=VehicleStatus(row.current_status) if row.current_status else None,
                        current_stop_sequence=row.current_stop_sequence,
                        occupancy_status=OccupancyStatus(row.occupancy_status) if row.occupancy_status else None,
                        timestamp=row.timestamp,
                    ))

                if vehicles:
                    return vehicles

            except Exception as e:
                logger.warning(f"Could not get vehicles from DB: {e}")

        # Return demo data
        return self.generate_demo_vehicles(20, route_id)

    async def get_arrivals(
        self,
        stop_id: str,
        route_id: Optional[str] = None,
        limit: int = 10,
        minutes_ahead: int = 60,
        db=None,
    ) -> List[ArrivalPrediction]:
        """Get arrival predictions for a stop."""
        logger.info("Getting arrivals", stop_id=stop_id, route_id=route_id)

        # Try to get from database
        if db is not None:
            try:
                query = """
                    SELECT
                        tu.stop_id, tu.route_id, tu.trip_id, tu.vehicle_id,
                        tu.arrival_delay, st.arrival_time as scheduled_time,
                        t.trip_headsign, r.route_short_name
                    FROM gtfs_trip_updates tu
                    JOIN gtfs_stop_times st ON tu.trip_id = st.trip_id AND tu.stop_id = st.stop_id
                    JOIN gtfs_trips t ON tu.trip_id = t.trip_id
                    JOIN gtfs_routes r ON t.route_id = r.route_id
                    WHERE tu.stop_id = :stop_id
                    AND tu.timestamp > NOW() - INTERVAL '5 minutes'
                    ORDER BY st.arrival_time
                    LIMIT :limit
                """
                params = {"stop_id": stop_id, "limit": limit}

                if route_id:
                    query = query.replace("WHERE", f"WHERE tu.route_id = '{route_id}' AND")

                result = db.execute(query, params)
                rows = result.fetchall()

                arrivals = []
                now = datetime.utcnow()
                for row in rows:
                    scheduled = row.scheduled_time
                    delay = row.arrival_delay or 0
                    predicted = scheduled + timedelta(seconds=delay) if scheduled else now

                    arrivals.append(ArrivalPrediction(
                        stop_id=stop_id,
                        route_id=row.route_id,
                        route_name=row.route_short_name,
                        trip_id=row.trip_id,
                        vehicle_id=row.vehicle_id,
                        scheduled_arrival=scheduled,
                        predicted_arrival=predicted,
                        delay_seconds=delay,
                        headsign=row.trip_headsign,
                        arrival_in_minutes=max(0, (predicted - now).total_seconds() / 60),
                    ))

                if arrivals:
                    return arrivals

            except Exception as e:
                logger.warning(f"Could not get arrivals from DB: {e}")

        # Return demo data
        return self.generate_demo_arrivals(stop_id, limit, route_id)

    async def get_alerts(
        self,
        route_id: Optional[str] = None,
        stop_id: Optional[str] = None,
        db=None,
    ) -> List[ServiceAlert]:
        """Get active service alerts."""
        logger.info("Getting service alerts")

        # Return demo alerts
        alerts = [
            ServiceAlert(
                alert_id="alert_001",
                severity=AlertSeverity.WARNING,
                effect=AlertEffect.SIGNIFICANT_DELAYS,
                header="Blue Line Delays",
                description="Expect 10-15 minute delays on the Blue Line due to signal issues.",
                affected_routes=["BLUE"],
                start_time=datetime.utcnow() - timedelta(hours=1),
            ),
            ServiceAlert(
                alert_id="alert_002",
                severity=AlertSeverity.INFO,
                effect=AlertEffect.MODIFIED_SERVICE,
                header="Route 12 Detour",
                description="Route 12 is on detour due to road construction on Peachtree St.",
                affected_routes=["12"],
                start_time=datetime.utcnow() - timedelta(days=1),
                end_time=datetime.utcnow() + timedelta(days=7),
            ),
        ]

        # Filter if requested
        if route_id:
            alerts = [a for a in alerts if route_id in a.affected_routes]
        if stop_id:
            alerts = [a for a in alerts if stop_id in a.affected_stops]

        return alerts

    def generate_demo_vehicles(
        self,
        count: int = 20,
        route_id: Optional[str] = None,
    ) -> List[VehiclePosition]:
        """Generate demo vehicle positions."""
        routes = [route_id] if route_id else ["BLUE", "RED", "GOLD", "GREEN", "12", "21"]
        statuses = list(VehicleStatus)
        occupancies = list(OccupancyStatus)

        vehicles = []
        for i in range(count):
            lat = random.uniform(ATLANTA_BOUNDS["min_lat"], ATLANTA_BOUNDS["max_lat"])
            lon = random.uniform(ATLANTA_BOUNDS["min_lon"], ATLANTA_BOUNDS["max_lon"])

            vehicles.append(VehiclePosition(
                vehicle_id=f"V{1000 + i}",
                route_id=random.choice(routes),
                trip_id=f"trip_{i:03d}",
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                bearing=random.uniform(0, 360),
                speed_mph=random.uniform(0, 35),
                current_status=random.choice(statuses),
                current_stop_sequence=random.randint(1, 30),
                occupancy_status=random.choice(occupancies),
                timestamp=datetime.utcnow() - timedelta(seconds=random.randint(0, 30)),
            ))

        return vehicles

    def generate_demo_arrivals(
        self,
        stop_id: str,
        count: int = 5,
        route_id: Optional[str] = None,
    ) -> List[ArrivalPrediction]:
        """Generate demo arrival predictions."""
        routes = [route_id] if route_id else ["BLUE", "RED", "GOLD", "GREEN"]
        headsigns = {
            "BLUE": ["Indian Creek", "Hamilton E Holmes"],
            "RED": ["North Springs", "Airport"],
            "GOLD": ["Doraville", "Airport"],
            "GREEN": ["Bankhead", "Edgewood/Candler Park"],
        }

        arrivals = []
        now = datetime.utcnow()

        for i in range(count):
            route = random.choice(routes)
            minutes = 2 + i * random.randint(5, 12)
            delay = random.randint(-60, 180)

            scheduled = now + timedelta(minutes=minutes)
            predicted = scheduled + timedelta(seconds=delay)

            arrivals.append(ArrivalPrediction(
                stop_id=stop_id,
                route_id=route,
                route_name=route,
                trip_id=f"trip_{i:03d}",
                vehicle_id=f"V{1000 + i}",
                scheduled_arrival=scheduled,
                predicted_arrival=predicted,
                delay_seconds=delay,
                headsign=random.choice(headsigns.get(route, ["Destination"])),
                arrival_in_minutes=round((predicted - now).total_seconds() / 60, 1),
            ))

        return sorted(arrivals, key=lambda a: a.predicted_arrival)
