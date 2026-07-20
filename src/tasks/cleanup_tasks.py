"""
Data cleanup and maintenance background tasks.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from sqlalchemy import func

from src.database import SessionLocal
from src.database.models import RealTimeArrival, ServiceAlert
from src.services.cache import cache

logger = get_task_logger(__name__)


@shared_task
def cleanup_old_arrivals():
    """Remove old real-time arrival data."""
    try:
        logger.info("Starting cleanup of old arrivals")
        
        db = SessionLocal()
        try:
            # Define retention period
            retention_days = 7
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Count records to delete
            old_count = db.query(func.count(RealTimeArrival.id)).filter(
                RealTimeArrival.updated_at < cutoff_date
            ).scalar()
            
            if old_count > 0:
                # Delete old records
                db.query(RealTimeArrival).filter(
                    RealTimeArrival.updated_at < cutoff_date
                ).delete()
                
                db.commit()
                logger.info(f"Deleted {old_count} old arrival records")
            else:
                logger.info("No old arrival records to delete")
            
            # Also mark very old arrivals as inactive
            inactive_cutoff = datetime.now() - timedelta(hours=1)
            db.query(RealTimeArrival).filter(
                RealTimeArrival.updated_at < inactive_cutoff,
                RealTimeArrival.is_active == True
            ).update({"is_active": False})
            
            db.commit()
            
            return {"status": "success", "deleted": old_count}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def cleanup_expired_alerts():
    """Remove expired service alerts."""
    try:
        logger.info("Cleaning up expired alerts")
        
        db = SessionLocal()
        try:
            now = datetime.now()
            
            # Find expired alerts
            expired_count = db.query(func.count(ServiceAlert.id)).filter(
                ServiceAlert.end_time < now,
                ServiceAlert.is_active == True
            ).scalar()
            
            if expired_count > 0:
                # Mark as inactive
                db.query(ServiceAlert).filter(
                    ServiceAlert.end_time < now,
                    ServiceAlert.is_active == True
                ).update({"is_active": False})
                
                db.commit()
                logger.info(f"Deactivated {expired_count} expired alerts")
            
            # Delete very old alerts (30+ days)
            old_cutoff = now - timedelta(days=30)
            old_count = db.query(func.count(ServiceAlert.id)).filter(
                ServiceAlert.end_time < old_cutoff
            ).scalar()
            
            if old_count > 0:
                db.query(ServiceAlert).filter(
                    ServiceAlert.end_time < old_cutoff
                ).delete()
                
                db.commit()
                logger.info(f"Deleted {old_count} old alerts")
            
            return {"status": "success", "expired": expired_count, "deleted": old_count}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Alert cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def clear_stale_cache():
    """Clear stale cache entries."""
    try:
        logger.info("Clearing stale cache entries")
        
        patterns_to_clear = [
            "metrics:*",  # Clear old metrics
            "arrivals:*",  # Clear arrival predictions
            "optimizations:*"  # Clear old optimizations
        ]
        
        total_cleared = 0
        for pattern in patterns_to_clear:
            cleared = cache.clear_pattern(pattern)
            total_cleared += cleared
            logger.debug(f"Cleared {cleared} keys matching {pattern}")
        
        logger.info(f"Cache cleanup completed: {total_cleared} keys cleared")
        return {"status": "success", "cleared": total_cleared}
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def optimize_database():
    """Run database optimization tasks."""
    try:
        logger.info("Starting database optimization")
        
        db = SessionLocal()
        try:
            # Analyze tables for query optimization
            tables = ['routes', 'stops', 'trips', 'stop_times', 'real_time_arrivals']
            
            for table in tables:
                try:
                    db.execute(f"ANALYZE {table}")
                    logger.debug(f"Analyzed table {table}")
                except Exception as e:
                    logger.warning(f"Could not analyze {table}: {e}")
            
            db.commit()
            
            # Get database statistics
            stats = {}
            for table in tables:
                count = db.execute(f"SELECT COUNT(*) FROM {table}").scalar()
                stats[table] = count
            
            logger.info(f"Database optimization completed. Table counts: {stats}")
            return {"status": "success", "stats": stats}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def generate_daily_report():
    """Generate daily system report."""
    try:
        logger.info("Generating daily report")
        
        db = SessionLocal()
        try:
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            
            # Collect statistics
            from src.database.models import Route, Stop, Trip
            
            # System counts
            total_routes = db.query(func.count(Route.route_id)).scalar()
            total_stops = db.query(func.count(Stop.stop_id)).scalar()
            total_trips = db.query(func.count(Trip.trip_id)).scalar()
            
            # Yesterday's performance
            yesterdays_arrivals = db.query(RealTimeArrival).filter(
                RealTimeArrival.updated_at >= yesterday,
                RealTimeArrival.updated_at < now
            ).all()
            
            if yesterdays_arrivals:
                on_time = sum(1 for a in yesterdays_arrivals if abs(a.delay_seconds or 0) <= 300)
                on_time_pct = (on_time / len(yesterdays_arrivals)) * 100
                avg_delay = sum(a.delay_seconds or 0 for a in yesterdays_arrivals) / len(yesterdays_arrivals)
            else:
                on_time_pct = 0
                avg_delay = 0
            
            # Active alerts
            active_alerts = db.query(func.count(ServiceAlert.id)).filter(
                ServiceAlert.is_active == True
            ).scalar()
            
            report = {
                "date": yesterday.date().isoformat(),
                "generated_at": now.isoformat(),
                "system": {
                    "total_routes": total_routes,
                    "total_stops": total_stops,
                    "total_trips": total_trips
                },
                "performance": {
                    "total_arrivals": len(yesterdays_arrivals),
                    "on_time_percentage": round(on_time_pct, 1),
                    "average_delay_minutes": round(avg_delay / 60, 1)
                },
                "alerts": {
                    "active_count": active_alerts
                }
            }
            
            # Store report
            cache.set(f"report:daily:{yesterday.date()}", report, ttl=86400 * 30)  # Keep for 30 days
            
            logger.info(f"Daily report generated for {yesterday.date()}")
            return {"status": "success", "report": report}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return {"status": "failed", "error": str(e)}