"""
Stop-related API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import get_db
from src.database.models_sqlite import Stop, RealTimeArrival

router = APIRouter()


@router.get("/")
async def get_stops(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    lat: Optional[float] = Query(None, description="Latitude for proximity search"),
    lon: Optional[float] = Query(None, description="Longitude for proximity search"),
    radius: Optional[float] = Query(1.0, description="Radius in miles for proximity search"),
    db: Session = Depends(get_db)
):
    """Get all transit stops, optionally filtered by location."""
    query = db.query(Stop)
    
    # Add proximity filtering if coordinates provided
    if lat is not None and lon is not None:
        # Simple distance calculation (for demo - use PostGIS in production)
        # This is approximate and works for small distances
        lat_range = radius / 69.0  # Rough conversion miles to degrees
        lon_range = radius / (69.0 * 0.86)  # Adjust for latitude
        
        query = query.filter(
            Stop.stop_lat.between(lat - lat_range, lat + lat_range),
            Stop.stop_lon.between(lon - lon_range, lon + lon_range)
        )
    
    stops = query.offset(skip).limit(limit).all()
    return [stop.to_dict() for stop in stops]


@router.get("/{stop_id}")
async def get_stop(stop_id: str, db: Session = Depends(get_db)):
    """Get a specific stop by ID."""
    stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail=f"Stop {stop_id} not found")
    return stop.to_dict()


@router.get("/{stop_id}/arrivals")
async def get_stop_arrivals(stop_id: str, db: Session = Depends(get_db)):
    """Get real-time arrivals for a stop."""
    stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail=f"Stop {stop_id} not found")
    
    # Get real-time arrivals
    arrivals = db.query(RealTimeArrival).filter(
        RealTimeArrival.stop_id == stop_id
    ).order_by(RealTimeArrival.predicted_time).limit(10).all()
    
    return {
        "stop_id": stop_id,
        "stop_name": stop.stop_name,
        "arrivals": [arrival.to_dict() for arrival in arrivals] if arrivals else [],
        "last_updated": arrivals[0].last_updated.isoformat() if arrivals else None
    }