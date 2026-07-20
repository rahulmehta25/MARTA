"""
Real-time arrivals API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta

from src.database.connection import get_db
from src.database.models_sqlite import RealTimeArrival, Stop, Route
from src.api.schemas.realtime import RealTimeArrivalResponse

router = APIRouter()


@router.get("/arrivals", response_model=List[RealTimeArrivalResponse])
async def get_arrivals(
    stop_id: Optional[str] = Query(None, description="Filter by stop ID"),
    route_id: Optional[str] = Query(None, description="Filter by route ID"),
    limit: int = Query(50, ge=1, le=200, description="Number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Get real-time arrival predictions.
    
    Returns upcoming arrivals filtered by stop and/or route.
    Results are ordered by arrival time.
    """
    query = db.query(
        RealTimeArrival,
        Stop.stop_name,
        Stop.stop_lat,
        Stop.stop_lon
    ).join(
        Stop, RealTimeArrival.stop_id == Stop.stop_id
    )
    
    # Apply filters
    if stop_id:
        query = query.filter(RealTimeArrival.stop_id == stop_id)
    if route_id:
        query = query.filter(RealTimeArrival.route_id == route_id)
    
    # Only show future arrivals (within next 2 hours)
    now = datetime.now()
    two_hours_later = now + timedelta(hours=2)
    query = query.filter(
        and_(
            RealTimeArrival.arrival_time >= now,
            RealTimeArrival.arrival_time <= two_hours_later
        )
    )
    
    # Order by arrival time and limit results
    query = query.order_by(RealTimeArrival.arrival_time).limit(limit)
    
    results = []
    for arrival, stop_name, stop_lat, stop_lon in query.all():
        results.append({
            "id": arrival.id,
            "stop_id": arrival.stop_id,
            "stop_name": stop_name,
            "stop_lat": stop_lat,
            "stop_lon": stop_lon,
            "route_id": arrival.route_id,
            "trip_id": arrival.trip_id,
            "arrival_time": arrival.arrival_time,
            "predicted_time": arrival.predicted_time,
            "delay_seconds": arrival.delay_seconds,
            "vehicle_id": arrival.vehicle_id,
            "last_updated": arrival.last_updated
        })
    
    return results


@router.get("/arrivals/by-station/{station_name}")
async def get_arrivals_by_station(
    station_name: str,
    limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Get real-time arrivals for a specific station by name.
    
    Searches for stations containing the provided name (case-insensitive).
    """
    # Find matching stops
    stops = db.query(Stop).filter(
        Stop.stop_name.ilike(f"%{station_name}%")
    ).all()
    
    if not stops:
        raise HTTPException(status_code=404, detail=f"No station found matching '{station_name}'")
    
    stop_ids = [stop.stop_id for stop in stops]
    
    # Get arrivals for these stops
    query = db.query(
        RealTimeArrival,
        Stop.stop_name,
        Stop.stop_lat,
        Stop.stop_lon
    ).join(
        Stop, RealTimeArrival.stop_id == Stop.stop_id
    ).filter(
        RealTimeArrival.stop_id.in_(stop_ids)
    )
    
    # Only show future arrivals
    now = datetime.now()
    query = query.filter(RealTimeArrival.arrival_time >= now)
    
    # Order by arrival time and limit
    query = query.order_by(RealTimeArrival.arrival_time).limit(limit)
    
    results = []
    for arrival, stop_name, stop_lat, stop_lon in query.all():
        results.append({
            "stop_id": arrival.stop_id,
            "stop_name": stop_name,
            "stop_lat": stop_lat,
            "stop_lon": stop_lon,
            "route_id": arrival.route_id,
            "trip_id": arrival.trip_id,
            "arrival_time": arrival.arrival_time,
            "predicted_time": arrival.predicted_time,
            "delay_seconds": arrival.delay_seconds,
            "vehicle_id": arrival.vehicle_id,
            "last_updated": arrival.last_updated
        })
    
    return {
        "station_query": station_name,
        "stations_found": [{"id": s.stop_id, "name": s.stop_name} for s in stops],
        "arrivals": results
    }


@router.get("/arrivals/next/{stop_id}")
async def get_next_arrival(
    stop_id: str,
    route_id: Optional[str] = Query(None, description="Filter by specific route"),
    db: Session = Depends(get_db)
):
    """
    Get the next arrival at a specific stop.
    
    Optionally filter by route to get the next arrival for a specific line.
    """
    # Verify stop exists
    stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail=f"Stop {stop_id} not found")
    
    query = db.query(RealTimeArrival).filter(
        RealTimeArrival.stop_id == stop_id
    )
    
    if route_id:
        query = query.filter(RealTimeArrival.route_id == route_id)
    
    # Get next arrival
    now = datetime.now()
    next_arrival = query.filter(
        RealTimeArrival.arrival_time >= now
    ).order_by(RealTimeArrival.arrival_time).first()
    
    if not next_arrival:
        return {
            "stop_id": stop_id,
            "stop_name": stop.stop_name,
            "message": "No upcoming arrivals found"
        }
    
    # Calculate wait time in minutes
    wait_time = (next_arrival.arrival_time - now).total_seconds() / 60
    
    return {
        "stop_id": stop_id,
        "stop_name": stop.stop_name,
        "route_id": next_arrival.route_id,
        "arrival_time": next_arrival.arrival_time,
        "wait_minutes": round(wait_time, 1),
        "vehicle_id": next_arrival.vehicle_id,
        "last_updated": next_arrival.last_updated
    }


@router.get("/status")
async def get_realtime_status(db: Session = Depends(get_db)):
    """
    Get status of real-time data availability.
    
    Shows when data was last updated and how many arrivals are available.
    """
    # Get latest update time
    latest = db.query(RealTimeArrival.last_updated).order_by(
        RealTimeArrival.last_updated.desc()
    ).first()
    
    # Count current arrivals
    now = datetime.now()
    current_count = db.query(RealTimeArrival).filter(
        RealTimeArrival.arrival_time >= now
    ).count()
    
    # Count by route
    route_counts = {}
    routes = db.query(
        RealTimeArrival.route_id,
        func.count(RealTimeArrival.id).label('count')
    ).filter(
        RealTimeArrival.arrival_time >= now
    ).group_by(RealTimeArrival.route_id).all()
    
    for route_id, count in routes:
        if route_id:
            route_counts[route_id] = count
    
    return {
        "status": "active" if latest and (now - latest[0]).seconds < 120 else "stale",
        "last_updated": latest[0] if latest else None,
        "current_arrivals": current_count,
        "arrivals_by_route": route_counts,
        "data_age_seconds": (now - latest[0]).seconds if latest else None
    }


@router.post("/refresh")
async def refresh_realtime_data():
    """
    Trigger a refresh of real-time data.
    
    This endpoint initiates a fetch from the MARTA API.
    Note: In production, this should be rate-limited and/or require authentication.
    """
    import subprocess
    import sys
    from pathlib import Path
    
    # Get the project root
    project_root = Path(__file__).parent.parent.parent.parent
    script_path = project_root / "scripts" / "fetch_real_time_rail.py"
    
    try:
        # Run the fetch script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Real-time data refreshed successfully",
                "timestamp": datetime.now()
            }
        else:
            return {
                "status": "error",
                "message": "Failed to refresh data",
                "error": result.stderr,
                "timestamp": datetime.now()
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Refresh operation timed out",
            "timestamp": datetime.now()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error refreshing data: {str(e)}",
            "timestamp": datetime.now()
        }