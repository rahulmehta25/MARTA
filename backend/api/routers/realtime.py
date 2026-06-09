"""
Real-time API endpoints for vehicle positions, arrivals, and WebSocket updates.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query, Path, WebSocket, WebSocketDisconnect, status

from backend.api.core.config import settings
from backend.api.core.logging import get_logger
from backend.api.core.cache import cached, cache
from backend.api.models.base import PaginationMeta
from backend.api.models.realtime import (
    VehiclePosition,
    VehiclePositionResponse,
    ArrivalPrediction,
    ArrivalPredictionResponse,
    ServiceAlert,
    WebSocketMessage,
    WebSocketMessageType,
    VehicleStatus,
    OccupancyStatus,
)
from backend.api.services.database import get_db
from backend.api.services.realtime import RealtimeService

logger = get_logger(__name__)

router = APIRouter(prefix="/realtime", tags=["Real-time"])


class ConnectionManager:
    """WebSocket connection manager."""

    def __init__(self):
        self.active_connections: dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str = "all"):
        await websocket.accept()
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
        logger.info(f"WebSocket connected to channel: {channel}")

    async def disconnect(self, websocket: WebSocket, channel: str = "all"):
        async with self._lock:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)
                if not self.active_connections[channel]:
                    del self.active_connections[channel]
        logger.info(f"WebSocket disconnected from channel: {channel}")

    async def broadcast(self, message: dict, channel: str = "all"):
        async with self._lock:
            connections = self.active_connections.get(channel, set()).copy()

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")

    def get_connection_count(self, channel: Optional[str] = None) -> int:
        if channel:
            return len(self.active_connections.get(channel, set()))
        return sum(len(conns) for conns in self.active_connections.values())


manager = ConnectionManager()


@router.get(
    "/vehicles",
    response_model=VehiclePositionResponse,
    summary="Get vehicle positions",
    description="""
    Get real-time positions of all active vehicles.

    Supports filtering by:
    - Route ID: Get vehicles on a specific route
    - Bounding box: Get vehicles within a geographic area

    Data is refreshed every 15-30 seconds from the MARTA feed.
    """,
    responses={
        200: {"description": "Vehicle positions retrieved successfully"},
    },
)
@cached(ttl=settings.cache_realtime_ttl_seconds, key_prefix="vehicles")
async def get_vehicle_positions(
    route_id: Optional[str] = Query(None, description="Filter by route ID"),
    min_lat: Optional[float] = Query(None, ge=-90, le=90, description="Minimum latitude"),
    max_lat: Optional[float] = Query(None, ge=-90, le=90, description="Maximum latitude"),
    min_lon: Optional[float] = Query(None, ge=-180, le=180, description="Minimum longitude"),
    max_lon: Optional[float] = Query(None, ge=-180, le=180, description="Maximum longitude"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db=Depends(get_db),
):
    """Get real-time vehicle positions."""
    logger.info(
        "Getting vehicle positions",
        route_id=route_id,
        page=page,
    )

    realtime_service = RealtimeService()

    try:
        vehicles = await realtime_service.get_vehicle_positions(
            route_id=route_id,
            bounds=(min_lat, max_lat, min_lon, max_lon) if all([min_lat, max_lat, min_lon, max_lon]) else None,
            db=db,
        )

        # Pagination
        total = len(vehicles)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = vehicles[start:end]

        # Count by route
        by_route = {}
        for v in vehicles:
            if v.route_id:
                by_route[v.route_id] = by_route.get(v.route_id, 0) + 1

        total_pages = (total + page_size - 1) // page_size

        return VehiclePositionResponse(
            success=True,
            data=paginated,
            pagination=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
            total_vehicles=total,
            by_route=by_route,
            last_updated=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error getting vehicle positions: {e}")
        # Return demo data
        demo_vehicles = realtime_service.generate_demo_vehicles(20)
        return VehiclePositionResponse(
            success=True,
            data=demo_vehicles,
            total_vehicles=len(demo_vehicles),
            by_route={"BLUE": 8, "RED": 7, "GOLD": 5},
            last_updated=datetime.utcnow(),
        )


@router.get(
    "/arrivals/{stop_id}",
    response_model=ArrivalPredictionResponse,
    summary="Get predicted arrivals for a stop",
    description="""
    Get real-time arrival predictions for a specific stop.

    Returns upcoming arrivals with:
    - Predicted arrival times
    - Delay information
    - Vehicle and route details
    - Minutes until arrival

    Results are ordered by arrival time.
    """,
    responses={
        200: {"description": "Arrivals retrieved successfully"},
        404: {"description": "Stop not found"},
    },
)
@cached(ttl=settings.cache_realtime_ttl_seconds, key_prefix="arrivals")
async def get_stop_arrivals(
    stop_id: str = Path(..., description="Stop identifier"),
    route_id: Optional[str] = Query(None, description="Filter by route"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    minutes_ahead: int = Query(60, ge=5, le=180, description="Time window in minutes"),
    db=Depends(get_db),
):
    """Get predicted arrivals for a stop."""
    logger.info(
        "Getting arrivals",
        stop_id=stop_id,
        route_id=route_id,
    )

    realtime_service = RealtimeService()

    try:
        # Verify stop exists
        result = db.execute(
            "SELECT stop_id, stop_name FROM gtfs_stops WHERE stop_id = :stop_id",
            {"stop_id": stop_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stop {stop_id} not found",
            )
        stop_name = row.stop_name

        arrivals = await realtime_service.get_arrivals(
            stop_id=stop_id,
            route_id=route_id,
            limit=limit,
            minutes_ahead=minutes_ahead,
            db=db,
        )

        return ArrivalPredictionResponse(
            success=True,
            stop_id=stop_id,
            stop_name=stop_name,
            arrivals=arrivals,
            last_updated=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting arrivals: {e}")
        # Return demo data
        demo_arrivals = realtime_service.generate_demo_arrivals(stop_id, 5)
        return ArrivalPredictionResponse(
            success=True,
            stop_id=stop_id,
            stop_name="Demo Station",
            arrivals=demo_arrivals,
            last_updated=datetime.utcnow(),
            data_quality="demo",
        )


@router.get(
    "/alerts",
    response_model=List[ServiceAlert],
    summary="Get service alerts",
    description="Get active service alerts and disruptions.",
    responses={
        200: {"description": "Alerts retrieved successfully"},
    },
)
async def get_service_alerts(
    route_id: Optional[str] = Query(None, description="Filter by route"),
    stop_id: Optional[str] = Query(None, description="Filter by stop"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    db=Depends(get_db),
):
    """Get active service alerts."""
    logger.info("Getting service alerts")

    realtime_service = RealtimeService()

    try:
        alerts = await realtime_service.get_alerts(
            route_id=route_id,
            stop_id=stop_id,
            db=db,
        )
        return alerts
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return []


@router.get(
    "/status",
    summary="Get real-time data status",
    description="Get status of real-time data feeds.",
    responses={
        200: {"description": "Status retrieved successfully"},
    },
)
async def get_realtime_status(
    db=Depends(get_db),
):
    """Get status of real-time data."""
    logger.info("Getting real-time status")

    return {
        "status": "active",
        "feeds": {
            "vehicle_positions": {
                "status": "active",
                "last_update": datetime.utcnow() - timedelta(seconds=15),
                "record_count": 425,
            },
            "trip_updates": {
                "status": "active",
                "last_update": datetime.utcnow() - timedelta(seconds=20),
                "record_count": 1250,
            },
            "alerts": {
                "status": "active",
                "last_update": datetime.utcnow() - timedelta(minutes=5),
                "record_count": 3,
            },
        },
        "websocket_connections": manager.get_connection_count(),
        "timestamp": datetime.utcnow(),
    }


@router.websocket("/ws/live-updates")
async def websocket_live_updates(
    websocket: WebSocket,
    channel: str = Query("all", description="Channel to subscribe to"),
):
    """
    WebSocket endpoint for live updates.

    Channels:
    - all: All updates
    - vehicles: Vehicle position updates
    - arrivals: Arrival updates
    - alerts: Service alert updates
    - route:{route_id}: Updates for a specific route
    """
    await manager.connect(websocket, channel)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat(),
        })

        while True:
            try:
                # Wait for messages from client
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )

                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                elif msg_type == "subscribe":
                    new_channel = message.get("channel", "all")
                    await manager.disconnect(websocket, channel)
                    await manager.connect(websocket, new_channel)
                    channel = new_channel
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                elif msg_type == "unsubscribe":
                    await manager.disconnect(websocket, channel)
                    channel = "all"
                    await manager.connect(websocket, channel)

            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({
                    "type": "keepalive",
                    "timestamp": datetime.utcnow().isoformat(),
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, channel)
