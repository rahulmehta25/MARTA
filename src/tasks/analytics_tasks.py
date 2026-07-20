"""
Analytics and optimization background tasks.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from sqlalchemy import func
import numpy as np

from src.database import SessionLocal
from src.database.models import Route, Stop, Trip, StopTime, RealTimeArrival
from src.services.cache import cache

logger = get_task_logger(__name__)


@shared_task
def calculate_system_metrics():
    """Calculate and cache system-wide performance metrics."""
    try:
        logger.info("Calculating system metrics")
        
        db = SessionLocal()
        try:
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            
            # Calculate on-time performance
            recent_arrivals = db.query(RealTimeArrival).filter(
                RealTimeArrival.updated_at >= one_hour_ago
            ).all()
            
            if recent_arrivals:
                on_time = sum(1 for a in recent_arrivals if abs(a.delay_seconds or 0) <= 300)
                on_time_pct = (on_time / len(recent_arrivals)) * 100
                avg_delay = sum(a.delay_seconds or 0 for a in recent_arrivals) / len(recent_arrivals)
            else:
                on_time_pct = 95.0
                avg_delay = 0
            
            # Count active vehicles
            five_min_ago = now - timedelta(minutes=5)
            active_vehicles = db.query(
                func.count(func.distinct(RealTimeArrival.train_id))
            ).filter(
                RealTimeArrival.updated_at >= five_min_ago
            ).scalar() or 0
            
            # Store metrics
            metrics = {
                "timestamp": now.isoformat(),
                "on_time_percentage": round(on_time_pct, 1),
                "average_delay_seconds": round(avg_delay, 1),
                "active_vehicles": active_vehicles,
                "total_arrivals_hour": len(recent_arrivals)
            }
            
            # Cache metrics
            cache.set("metrics:system:latest", metrics, ttl=300)
            
            logger.info(f"System metrics calculated: {metrics}")
            return {"status": "success", "metrics": metrics}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Metrics calculation failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def calculate_route_metrics(route_id: str):
    """Calculate performance metrics for a specific route."""
    try:
        logger.info(f"Calculating metrics for route {route_id}")
        
        db = SessionLocal()
        try:
            # Get route
            route = db.query(Route).filter(Route.route_id == route_id).first()
            if not route:
                return {"status": "failed", "error": "Route not found"}
            
            # Time windows
            now = datetime.now()
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)
            
            # Get trips for route
            trips = db.query(Trip).filter(Trip.route_id == route_id).all()
            trip_ids = [t.trip_id for t in trips]
            
            # Calculate daily metrics
            daily_arrivals = db.query(RealTimeArrival).filter(
                RealTimeArrival.trip_id.in_(trip_ids),
                RealTimeArrival.updated_at >= day_ago
            ).all()
            
            if daily_arrivals:
                daily_on_time = sum(1 for a in daily_arrivals if abs(a.delay_seconds or 0) <= 300)
                daily_on_time_pct = (daily_on_time / len(daily_arrivals)) * 100
                daily_avg_delay = sum(a.delay_seconds or 0 for a in daily_arrivals) / len(daily_arrivals)
            else:
                daily_on_time_pct = 95.0
                daily_avg_delay = 0
            
            # Calculate weekly trends
            weekly_arrivals = db.query(RealTimeArrival).filter(
                RealTimeArrival.trip_id.in_(trip_ids),
                RealTimeArrival.updated_at >= week_ago
            ).all()
            
            # Group by day
            daily_stats = {}
            for arrival in weekly_arrivals:
                day = arrival.updated_at.date()
                if day not in daily_stats:
                    daily_stats[day] = {"count": 0, "delays": []}
                daily_stats[day]["count"] += 1
                daily_stats[day]["delays"].append(arrival.delay_seconds or 0)
            
            # Calculate trends
            trend_data = []
            for day, stats in sorted(daily_stats.items()):
                avg_delay = sum(stats["delays"]) / len(stats["delays"]) if stats["delays"] else 0
                on_time = sum(1 for d in stats["delays"] if abs(d) <= 300)
                on_time_pct = (on_time / len(stats["delays"]) * 100) if stats["delays"] else 95.0
                
                trend_data.append({
                    "date": day.isoformat(),
                    "trips": stats["count"],
                    "avg_delay_seconds": round(avg_delay, 1),
                    "on_time_percentage": round(on_time_pct, 1)
                })
            
            metrics = {
                "route_id": route_id,
                "route_name": route.route_short_name,
                "daily": {
                    "on_time_percentage": round(daily_on_time_pct, 1),
                    "average_delay_seconds": round(daily_avg_delay, 1),
                    "total_trips": len(daily_arrivals)
                },
                "weekly_trend": trend_data,
                "calculated_at": now.isoformat()
            }
            
            # Cache metrics
            cache.set(f"metrics:route:{route_id}", metrics, ttl=600)
            
            logger.info(f"Route {route_id} metrics calculated")
            return {"status": "success", "metrics": metrics}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Route metrics calculation failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def optimize_routes():
    """Optimize route schedules based on demand patterns."""
    try:
        logger.info("Starting route optimization")
        
        db = SessionLocal()
        try:
            # Get all active routes
            routes = db.query(Route).all()
            
            optimizations = []
            
            for route in routes:
                # Get stop times for route
                stop_times = db.query(StopTime).join(Trip).filter(
                    Trip.route_id == route.route_id
                ).all()
                
                if not stop_times:
                    continue
                
                # Analyze arrival patterns
                arrivals = db.query(RealTimeArrival).join(Trip).filter(
                    Trip.route_id == route.route_id,
                    RealTimeArrival.updated_at >= datetime.now() - timedelta(days=7)
                ).all()
                
                if len(arrivals) < 100:
                    continue  # Not enough data
                
                # Calculate average delays by hour
                hourly_delays = {}
                for arrival in arrivals:
                    hour = arrival.updated_at.hour
                    if hour not in hourly_delays:
                        hourly_delays[hour] = []
                    hourly_delays[hour].append(arrival.delay_seconds or 0)
                
                # Find problematic hours
                problem_hours = []
                for hour, delays in hourly_delays.items():
                    avg_delay = sum(delays) / len(delays)
                    if avg_delay > 300:  # More than 5 minutes average delay
                        problem_hours.append({
                            "hour": hour,
                            "avg_delay_minutes": round(avg_delay / 60, 1),
                            "trip_count": len(delays)
                        })
                
                if problem_hours:
                    # Generate optimization suggestions
                    optimization = {
                        "route_id": route.route_id,
                        "route_name": route.route_short_name,
                        "problem_hours": problem_hours,
                        "suggestions": []
                    }
                    
                    # Add suggestions based on patterns
                    peak_delay_hour = max(problem_hours, key=lambda x: x["avg_delay_minutes"])
                    if peak_delay_hour["avg_delay_minutes"] > 10:
                        optimization["suggestions"].append(
                            f"Add extra service during hour {peak_delay_hour['hour']} to reduce {peak_delay_hour['avg_delay_minutes']} min delays"
                        )
                    
                    if len(problem_hours) >= 3:
                        optimization["suggestions"].append(
                            "Consider adjusting base schedule - multiple hours show delays"
                        )
                    
                    optimizations.append(optimization)
            
            # Cache optimization results
            result = {
                "timestamp": datetime.now().isoformat(),
                "routes_analyzed": len(routes),
                "optimizations": optimizations
            }
            
            cache.set("optimizations:latest", result, ttl=3600)
            
            logger.info(f"Route optimization completed: {len(optimizations)} routes need attention")
            return {"status": "success", "result": result}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Route optimization failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def analyze_stop_demand():
    """Analyze demand patterns at stops."""
    try:
        logger.info("Analyzing stop demand patterns")
        
        db = SessionLocal()
        try:
            # Get all stops
            stops = db.query(Stop).all()
            
            demand_analysis = []
            
            for stop in stops:
                # Get arrivals at this stop
                week_ago = datetime.now() - timedelta(days=7)
                arrivals = db.query(RealTimeArrival).filter(
                    RealTimeArrival.stop_id == stop.stop_id,
                    RealTimeArrival.updated_at >= week_ago
                ).all()
                
                if not arrivals:
                    continue
                
                # Calculate hourly distribution
                hourly_counts = {}
                for arrival in arrivals:
                    hour = arrival.updated_at.hour
                    hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                
                # Find peak hours
                if hourly_counts:
                    peak_hour = max(hourly_counts, key=hourly_counts.get)
                    avg_hourly = sum(hourly_counts.values()) / 24
                    
                    # Calculate demand level
                    peak_ratio = hourly_counts[peak_hour] / avg_hourly if avg_hourly > 0 else 1
                    
                    if peak_ratio > 3:
                        demand_level = "high"
                    elif peak_ratio > 1.5:
                        demand_level = "medium"
                    else:
                        demand_level = "low"
                    
                    # Update stop with demand info
                    stop.peak_hour_demand = hourly_counts[peak_hour]
                    stop.avg_daily_boardings = sum(hourly_counts.values()) // 7
                    stop.demand_level = demand_level
                    
                    demand_analysis.append({
                        "stop_id": stop.stop_id,
                        "stop_name": stop.stop_name,
                        "peak_hour": peak_hour,
                        "peak_arrivals": hourly_counts[peak_hour],
                        "daily_average": stop.avg_daily_boardings,
                        "demand_level": demand_level
                    })
            
            db.commit()
            
            # Sort by demand
            demand_analysis.sort(key=lambda x: x["daily_average"], reverse=True)
            
            # Cache results
            result = {
                "timestamp": datetime.now().isoformat(),
                "stops_analyzed": len(demand_analysis),
                "high_demand_stops": [s for s in demand_analysis if s["demand_level"] == "high"][:10],
                "analysis": demand_analysis[:50]  # Top 50 stops
            }
            
            cache.set("demand:analysis:latest", result, ttl=3600)
            
            logger.info(f"Stop demand analysis completed: {len(demand_analysis)} stops analyzed")
            return {"status": "success", "result": result}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Demand analysis failed: {e}")
        return {"status": "failed", "error": str(e)}