"""
Performance metrics API endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import Optional
from datetime import datetime, timedelta

from src.database import get_db
from src.database.models_sqlite import Route, Stop, Trip, StopTime, RealTimeArrival
from src.services.cache import cached

router = APIRouter()


@router.get("/system")
@cached("metrics:system", ttl=60)
async def get_system_metrics(db: Session = Depends(get_db)):
    """Get overall system performance metrics."""
    
    # Count entities
    total_routes = db.query(func.count(Route.route_id)).scalar()
    total_stops = db.query(func.count(Stop.stop_id)).scalar()
    total_trips = db.query(func.count(Trip.trip_id)).scalar()
    
    # Calculate on-time performance
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    
    recent_arrivals = db.query(RealTimeArrival).filter(
        RealTimeArrival.updated_at >= one_hour_ago
    ).all()
    
    if recent_arrivals:
        on_time_count = sum(1 for a in recent_arrivals if abs(a.delay_seconds or 0) <= 300)
        on_time_percentage = (on_time_count / len(recent_arrivals)) * 100
    else:
        on_time_percentage = 95.0  # Default when no data
    
    # Active vehicles (arrivals in last 5 minutes)
    five_min_ago = now - timedelta(minutes=5)
    active_vehicles = db.query(func.count(func.distinct(RealTimeArrival.train_id))).filter(
        RealTimeArrival.updated_at >= five_min_ago
    ).scalar() or 0
    
    return {
        "timestamp": now.isoformat(),
        "system_status": "operational",
        "total_routes": total_routes,
        "total_stops": total_stops,
        "total_trips": total_trips,
        "active_vehicles": active_vehicles,
        "on_time_percentage": round(on_time_percentage, 1),
        "last_update": now.isoformat()
    }


@router.get("/routes/{route_id}")
@cached("metrics:route", ttl=120)
async def get_route_metrics(
    route_id: str,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get performance metrics for a specific route."""
    
    # Get route info
    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        return {"error": "Route not found"}
    
    # Time window
    now = datetime.now()
    start_time = now - timedelta(hours=hours)
    
    # Get trips for this route
    trips = db.query(Trip).filter(Trip.route_id == route_id).all()
    trip_ids = [t.trip_id for t in trips]
    
    # Calculate metrics from real-time data
    arrivals = db.query(RealTimeArrival).filter(
        RealTimeArrival.trip_id.in_(trip_ids),
        RealTimeArrival.updated_at >= start_time
    ).all()
    
    if arrivals:
        avg_delay = sum(a.delay_seconds or 0 for a in arrivals) / len(arrivals)
        on_time = sum(1 for a in arrivals if abs(a.delay_seconds or 0) <= 300)
        on_time_pct = (on_time / len(arrivals)) * 100
        
        # Group by hour for timeline
        hourly_stats = {}
        for arrival in arrivals:
            hour = arrival.updated_at.replace(minute=0, second=0, microsecond=0)
            if hour not in hourly_stats:
                hourly_stats[hour] = {"count": 0, "total_delay": 0}
            hourly_stats[hour]["count"] += 1
            hourly_stats[hour]["total_delay"] += arrival.delay_seconds or 0
        
        timeline = [
            {
                "hour": hour.isoformat(),
                "avg_delay_seconds": stats["total_delay"] / stats["count"],
                "trip_count": stats["count"]
            }
            for hour, stats in sorted(hourly_stats.items())
        ]
    else:
        avg_delay = 0
        on_time_pct = 95.0
        timeline = []
    
    return {
        "route_id": route_id,
        "route_name": route.route_short_name,
        "time_window_hours": hours,
        "metrics": {
            "average_delay_seconds": round(avg_delay, 1),
            "on_time_percentage": round(on_time_pct, 1),
            "total_trips": len(arrivals),
            "active_trains": len(set(a.train_id for a in arrivals if a.train_id))
        },
        "timeline": timeline,
        "last_updated": now.isoformat()
    }


@router.get("/stops/{stop_id}")
@cached("metrics:stop", ttl=120)
async def get_stop_metrics(
    stop_id: str,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get performance metrics for a specific stop."""
    
    # Get stop info
    stop = db.query(Stop).filter(Stop.stop_id == stop_id).first()
    if not stop:
        return {"error": "Stop not found"}
    
    # Time window
    now = datetime.now()
    start_time = now - timedelta(hours=hours)
    
    # Get arrivals at this stop
    arrivals = db.query(RealTimeArrival).filter(
        RealTimeArrival.stop_id == stop_id,
        RealTimeArrival.updated_at >= start_time
    ).all()
    
    if arrivals:
        # Calculate wait times (time between consecutive arrivals)
        arrivals_by_route = {}
        for arrival in arrivals:
            if arrival.route_id not in arrivals_by_route:
                arrivals_by_route[arrival.route_id] = []
            arrivals_by_route[arrival.route_id].append(arrival)
        
        # Average headway per route
        headways = {}
        for route_id, route_arrivals in arrivals_by_route.items():
            sorted_arrivals = sorted(route_arrivals, key=lambda x: x.predicted_time)
            if len(sorted_arrivals) > 1:
                gaps = []
                for i in range(1, len(sorted_arrivals)):
                    gap = (sorted_arrivals[i].predicted_time - sorted_arrivals[i-1].predicted_time).seconds
                    gaps.append(gap)
                headways[route_id] = sum(gaps) / len(gaps) if gaps else 0
        
        # Peak hours analysis
        hourly_counts = {}
        for arrival in arrivals:
            hour = arrival.updated_at.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        peak_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    else:
        headways = {}
        peak_hours = []
    
    return {
        "stop_id": stop_id,
        "stop_name": stop.stop_name,
        "time_window_hours": hours,
        "metrics": {
            "total_arrivals": len(arrivals),
            "unique_routes": len(set(a.route_id for a in arrivals)),
            "average_headways": {
                route_id: round(headway / 60, 1)  # Convert to minutes
                for route_id, headway in headways.items()
            },
            "peak_hours": [
                {"hour": hour, "arrivals": count}
                for hour, count in peak_hours
            ]
        },
        "accessibility": {
            "wheelchair_boarding": stop.wheelchair_boarding,
            "has_bike_parking": stop.has_bike_parking,
            "has_car_parking": stop.has_car_parking
        },
        "last_updated": now.isoformat()
    }


@router.get("/crowding")
async def get_crowding_metrics(
    time_of_day: Optional[str] = Query(None, pattern="^(morning|afternoon|evening|night)$"),
    db: Session = Depends(get_db)
):
    """Get crowding and demand metrics."""
    
    # Define time periods
    time_periods = {
        "morning": (6, 10),
        "afternoon": (11, 16),
        "evening": (17, 20),
        "night": (20, 6)
    }
    
    # Get stops with demand data
    query = db.query(Stop).filter(Stop.avg_daily_boardings > 0)
    
    if time_of_day:
        # Filter by peak demand during specific time
        query = query.filter(Stop.peak_hour_demand > 0)
    
    stops = query.all()
    
    # Group by demand level
    demand_levels = {
        "high": [],
        "medium": [],
        "low": []
    }
    
    for stop in stops:
        level = stop.demand_level or "low"
        demand_levels[level].append({
            "stop_id": stop.stop_id,
            "stop_name": stop.stop_name,
            "daily_boardings": stop.avg_daily_boardings,
            "peak_demand": stop.peak_hour_demand
        })
    
    # Sort each level by demand
    for level in demand_levels:
        demand_levels[level].sort(key=lambda x: x["daily_boardings"] or 0, reverse=True)
    
    return {
        "time_filter": time_of_day,
        "high_demand_stops": demand_levels["high"][:10],
        "medium_demand_stops": demand_levels["medium"][:10],
        "low_demand_stops": demand_levels["low"][:10],
        "total_stops_analyzed": len(stops),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/delays")
async def get_delay_metrics(
    threshold_minutes: int = Query(5, ge=1, le=60),
    db: Session = Depends(get_db)
):
    """Get current delay information across the system."""
    
    # Get recent arrivals
    now = datetime.now()
    fifteen_min_ago = now - timedelta(minutes=15)
    
    arrivals = db.query(RealTimeArrival).filter(
        RealTimeArrival.updated_at >= fifteen_min_ago,
        RealTimeArrival.is_active == True
    ).all()
    
    # Filter for delays above threshold
    threshold_seconds = threshold_minutes * 60
    delayed_arrivals = [
        a for a in arrivals 
        if (a.delay_seconds or 0) > threshold_seconds
    ]
    
    # Group by route
    delays_by_route = {}
    for arrival in delayed_arrivals:
        if arrival.route_id not in delays_by_route:
            delays_by_route[arrival.route_id] = []
        delays_by_route[arrival.route_id].append({
            "stop_id": arrival.stop_id,
            "trip_id": arrival.trip_id,
            "delay_minutes": round((arrival.delay_seconds or 0) / 60, 1),
            "predicted_time": arrival.predicted_time.isoformat()
        })
    
    return {
        "threshold_minutes": threshold_minutes,
        "total_delays": len(delayed_arrivals),
        "affected_routes": list(delays_by_route.keys()),
        "delays_by_route": delays_by_route,
        "system_impact": {
            "percentage_delayed": round(
                (len(delayed_arrivals) / len(arrivals) * 100) if arrivals else 0,
                1
            ),
            "average_delay_minutes": round(
                sum(a.delay_seconds or 0 for a in delayed_arrivals) / 60 / len(delayed_arrivals),
                1
            ) if delayed_arrivals else 0
        },
        "timestamp": now.isoformat()
    }