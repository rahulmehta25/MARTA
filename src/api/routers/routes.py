"""
Route-related API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import get_db
from src.database.models_sqlite import Route
from src.api.schemas.route import RouteResponse, RouteCreate
from src.services.cache import cache, cached

router = APIRouter()


@router.get("/", response_model=List[RouteResponse])
async def get_routes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all transit routes."""
    routes = db.query(Route).offset(skip).limit(limit).all()
    return routes


@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(route_id: str, db: Session = Depends(get_db)):
    """Get a specific route by ID."""
    # Check cache first
    cache_key = f"route:{route_id}"
    cached_route = cache.get(cache_key)
    if cached_route:
        return cached_route
    
    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
    
    # Cache the result
    route_dict = route.to_dict()
    cache.set(cache_key, route_dict, ttl=300)  # 5 minutes
    return route


@router.get("/{route_id}/performance")
async def get_route_performance(route_id: str, db: Session = Depends(get_db)):
    """Get performance metrics for a route."""
    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
    
    return {
        "route_id": route.route_id,
        "route_name": route.route_short_name,
        "avg_delay_minutes": 2.5,  # Simulated data
        "on_time_performance": 92.5,  # Simulated data
        "daily_ridership": 35000,  # Simulated data
        "status": "operational"
    }