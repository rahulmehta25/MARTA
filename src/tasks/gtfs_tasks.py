"""
GTFS-related background tasks.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
import requests

from src.database import SessionLocal
from src.services.gtfs_parser import GTFSParser
from src.services.gtfs_downloader import GTFSDownloader
from src.services.realtime_poller import RealTimePoller
from src.services.cache import cache

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def update_gtfs_data(self):
    """Download and update GTFS static data."""
    try:
        logger.info("Starting GTFS data update")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Download latest GTFS data
            downloader = GTFSDownloader()
            zip_data = downloader.download_gtfs()
            
            if not zip_data:
                logger.error("Failed to download GTFS data")
                return {"status": "failed", "error": "Download failed"}
            
            # Parse and load data
            parser = GTFSParser(db)
            result = parser.parse_zip(zip_data)
            
            # Clear related caches
            cache.clear_pattern("routes:*")
            cache.clear_pattern("stops:*")
            cache.clear_pattern("trips:*")
            
            logger.info(f"GTFS update completed: {result}")
            return {"status": "success", "result": result}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"GTFS update failed: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=5)
def poll_realtime_data(self):
    """Poll real-time arrival data."""
    try:
        logger.debug("Polling real-time data")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Poll real-time data
            poller = RealTimePoller(db)
            result = poller.poll()
            
            # Clear arrival caches
            cache.clear_pattern("arrivals:*")
            
            return {"status": "success", "arrivals_updated": result}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Real-time polling failed: {e}")
        raise self.retry(exc=e, countdown=10)


@shared_task
def fetch_service_alerts():
    """Fetch and process service alerts."""
    try:
        logger.info("Fetching service alerts")
        
        # MARTA alerts endpoint (example)
        url = "https://developerservices.itsmarta.com/alerts"
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Failed to fetch alerts: {response.status_code}")
            return {"status": "failed", "error": "API error"}
        
        alerts = response.json()
        
        # Process and store alerts
        db = SessionLocal()
        try:
            from src.database.models import ServiceAlert
            
            # Clear old alerts
            db.query(ServiceAlert).filter(
                ServiceAlert.is_active == False
            ).delete()
            
            # Add new alerts
            for alert_data in alerts:
                alert = ServiceAlert(
                    alert_id=alert_data.get('id'),
                    header_text=alert_data.get('header'),
                    description_text=alert_data.get('description'),
                    severity_level=alert_data.get('severity', 'info'),
                    effect=alert_data.get('effect'),
                    start_time=datetime.fromisoformat(alert_data.get('start', datetime.now().isoformat())),
                    end_time=datetime.fromisoformat(alert_data.get('end', '2099-12-31T23:59:59')),
                    is_active=True
                )
                db.merge(alert)
            
            db.commit()
            
            # Clear alert caches
            cache.clear_pattern("alerts:*")
            
            logger.info(f"Processed {len(alerts)} alerts")
            return {"status": "success", "alerts_processed": len(alerts)}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Alert fetch failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def validate_gtfs_data():
    """Validate GTFS data integrity."""
    try:
        logger.info("Starting GTFS validation")
        
        db = SessionLocal()
        try:
            from src.database.models import Route, Stop, Trip, StopTime
            
            issues = []
            
            # Check for routes without trips
            orphan_routes = db.query(Route).filter(
                ~Route.trips.any()
            ).count()
            if orphan_routes > 0:
                issues.append(f"{orphan_routes} routes without trips")
            
            # Check for stops without stop times
            orphan_stops = db.query(Stop).filter(
                ~Stop.stop_times.any()
            ).count()
            if orphan_stops > 0:
                issues.append(f"{orphan_stops} stops without stop times")
            
            # Check for trips without stop times
            incomplete_trips = db.query(Trip).filter(
                ~Trip.stop_times.any()
            ).count()
            if incomplete_trips > 0:
                issues.append(f"{incomplete_trips} trips without stop times")
            
            if issues:
                logger.warning(f"GTFS validation issues: {', '.join(issues)}")
                return {"status": "warning", "issues": issues}
            else:
                logger.info("GTFS validation passed")
                return {"status": "success", "message": "No issues found"}
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"GTFS validation failed: {e}")
        return {"status": "failed", "error": str(e)}