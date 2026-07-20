# src/services/data_ingestion_scheduler.py

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import schedule
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.data_ingestion.apc_client import APCAPIClient
from src.data_ingestion.weather_client import WeatherAPIClient
from src.data_ingestion.traffic_client import TomTomTrafficAPIClient
from src.database.connection import get_db_connection
from src.services.data_validator import DataValidator
from src.services.feature_engineer import FeatureEngineer

logger = logging.getLogger(__name__)

class DataIngestionScheduler:
    """
    Manages scheduled data ingestion from external APIs.
    Coordinates APC, Weather, and Traffic data collection.
    """

    def __init__(self):
        # Initialize API clients
        self.apc_client = None
        self.weather_client = None
        self.traffic_client = None

        # Initialize supporting services
        self.validator = DataValidator()
        self.feature_engineer = FeatureEngineer()

        # Thread pool for parallel ingestion
        self.executor = ThreadPoolExecutor(max_workers=5)

        # MARTA service area coordinates
        self.marta_coordinates = {
            "center": (33.7490, -84.3880),  # Atlanta center
            "bbox": (33.6400, -84.5500, 33.8800, -84.2800),  # Service area
            "key_stations": [
                {"name": "Five Points", "lat": 33.7540, "lon": -84.3916},
                {"name": "Airport", "lat": 33.6407, "lon": -84.4467},
                {"name": "Lindbergh", "lat": 33.8229, "lon": -84.3677},
                {"name": "Midtown", "lat": 33.7808, "lon": -84.3865},
                {"name": "North Springs", "lat": 33.9458, "lon": -84.3569}
            ]
        }

    def initialize_clients(self):
        """Initialize API clients with credentials."""
        try:
            # APC Client
            apc_key = os.getenv("APC_API_KEY")
            if apc_key:
                self.apc_client = APCAPIClient(api_key=apc_key)
                logger.info("APC client initialized")
            else:
                logger.warning("APC_API_KEY not found")

            # Weather Client
            weather_key = os.getenv("WEATHER_API_KEY")
            if weather_key:
                self.weather_client = WeatherAPIClient(api_key=weather_key)
                logger.info("Weather client initialized")
            else:
                logger.warning("WEATHER_API_KEY not found")

            # Traffic Client
            traffic_key = os.getenv("TOMTOM_API_KEY")
            if traffic_key:
                self.traffic_client = TomTomTrafficAPIClient(api_key=traffic_key)
                logger.info("Traffic client initialized")
            else:
                logger.warning("TOMTOM_API_KEY not found")

        except Exception as e:
            logger.error(f"Error initializing API clients: {e}")

    # ========== APC Data Ingestion ==========

    def ingest_apc_realtime(self):
        """Ingest real-time APC occupancy data."""
        if not self.apc_client:
            logger.warning("APC client not available")
            return

        try:
            start_time = datetime.now()
            records_processed = 0
            records_failed = 0

            # Fetch real-time occupancy for all vehicles
            occupancy_data = self.apc_client.get_realtime_occupancy()

            for record in occupancy_data:
                try:
                    # Validate data
                    if self.validator.validate_apc_data(record):
                        # Process and store
                        self._store_apc_data(record)
                        records_processed += 1
                    else:
                        records_failed += 1
                except Exception as e:
                    logger.error(f"Error processing APC record: {e}")
                    records_failed += 1

            # Log ingestion results
            self._log_ingestion(
                source_type="apc_realtime",
                records_processed=records_processed,
                records_failed=records_failed,
                start_time=start_time
            )

            logger.info(f"APC real-time ingestion complete: {records_processed} processed, {records_failed} failed")

        except Exception as e:
            logger.error(f"APC real-time ingestion failed: {e}")

    def ingest_apc_historical(self, hours: int = 24):
        """Ingest historical APC data for the specified period."""
        if not self.apc_client:
            logger.warning("APC client not available")
            return

        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            historical_data = self.apc_client.get_historical_ridership(
                start_time.isoformat(),
                end_time.isoformat()
            )

            # Process and store historical data
            for record in historical_data:
                self._store_apc_historical(record)

            logger.info(f"APC historical ingestion complete: {len(historical_data)} records")

        except Exception as e:
            logger.error(f"APC historical ingestion failed: {e}")

    # ========== Weather Data Ingestion ==========

    def ingest_weather_current(self):
        """Ingest current weather conditions."""
        if not self.weather_client:
            logger.warning("Weather client not available")
            return

        try:
            start_time = datetime.now()
            records_processed = 0

            # Fetch weather for key stations
            for station in self.marta_coordinates["key_stations"]:
                try:
                    weather_data = self.weather_client.get_current_weather(
                        station["lat"], station["lon"]
                    )

                    # Add location info
                    weather_data["location_name"] = station["name"]

                    # Extract features
                    features = self.feature_engineer.extract_weather_features(weather_data)

                    # Store in database
                    self._store_weather_data(weather_data, features)
                    records_processed += 1

                except Exception as e:
                    logger.error(f"Error fetching weather for {station['name']}: {e}")

            # Log ingestion
            self._log_ingestion(
                source_type="weather_current",
                records_processed=records_processed,
                records_failed=0,
                start_time=start_time
            )

            logger.info(f"Weather ingestion complete: {records_processed} locations")

        except Exception as e:
            logger.error(f"Weather ingestion failed: {e}")

    def ingest_weather_forecast(self):
        """Ingest weather forecast data."""
        if not self.weather_client:
            logger.warning("Weather client not available")
            return

        try:
            # Get 48-hour forecast for center point
            lat, lon = self.marta_coordinates["center"]
            forecast_data = self.weather_client.get_hourly_forecast(lat, lon)

            # Process and store forecast
            self._store_weather_forecast(forecast_data)

            logger.info("Weather forecast ingestion complete")

        except Exception as e:
            logger.error(f"Weather forecast ingestion failed: {e}")

    # ========== Traffic Data Ingestion ==========

    def ingest_traffic_flow(self):
        """Ingest real-time traffic flow data."""
        if not self.traffic_client:
            logger.warning("Traffic client not available")
            return

        try:
            start_time = datetime.now()
            records_processed = 0

            # Get traffic flow for major corridors
            major_corridors = [
                {"name": "I-75/I-85", "point": "33.7550,-84.3880"},
                {"name": "I-20", "point": "33.7537,-84.3863"},
                {"name": "GA-400", "point": "33.8688,-84.3620"},
                {"name": "I-285", "point": "33.8547,-84.3588"}
            ]

            for corridor in major_corridors:
                try:
                    traffic_data = self.traffic_client.get_traffic_flow(corridor["point"])

                    # Extract features
                    features = self.feature_engineer.extract_traffic_features(traffic_data)

                    # Store in database
                    self._store_traffic_data(traffic_data, features)
                    records_processed += 1

                except Exception as e:
                    logger.error(f"Error fetching traffic for {corridor['name']}: {e}")

            # Log ingestion
            self._log_ingestion(
                source_type="traffic_flow",
                records_processed=records_processed,
                records_failed=0,
                start_time=start_time
            )

            logger.info(f"Traffic ingestion complete: {records_processed} corridors")

        except Exception as e:
            logger.error(f"Traffic ingestion failed: {e}")

    def ingest_traffic_incidents(self):
        """Ingest traffic incident data."""
        if not self.traffic_client:
            logger.warning("Traffic client not available")
            return

        try:
            # Get incidents for service area
            bbox = self.marta_coordinates["bbox"]

            # Note: This would need to be implemented in traffic_client
            # For now, log as not implemented
            logger.info("Traffic incidents ingestion not yet implemented")

        except Exception as e:
            logger.error(f"Traffic incidents ingestion failed: {e}")

    # ========== Parallel Ingestion ==========

    def run_parallel_ingestion(self):
        """Run all ingestion tasks in parallel."""
        logger.info("Starting parallel data ingestion")

        futures = []

        # Submit all ingestion tasks
        if self.apc_client:
            futures.append(self.executor.submit(self.ingest_apc_realtime))

        if self.weather_client:
            futures.append(self.executor.submit(self.ingest_weather_current))

        if self.traffic_client:
            futures.append(self.executor.submit(self.ingest_traffic_flow))

        # Wait for completion
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Ingestion task failed: {e}")

        logger.info("Parallel ingestion complete")

    # ========== Database Storage Methods ==========

    def _store_apc_data(self, data: Dict[str, Any]):
        """Store APC data in database."""
        # This would connect to Supabase and insert data
        # For now, just log
        logger.debug(f"Storing APC data: {data.get('vehicle_id', 'unknown')}")

    def _store_apc_historical(self, data: Dict[str, Any]):
        """Store historical APC data."""
        logger.debug("Storing historical APC data")

    def _store_weather_data(self, data: Dict[str, Any], features: Dict[str, Any]):
        """Store weather data in database."""
        logger.debug(f"Storing weather data for {data.get('location_name', 'unknown')}")

    def _store_weather_forecast(self, data: Dict[str, Any]):
        """Store weather forecast data."""
        logger.debug("Storing weather forecast data")

    def _store_traffic_data(self, data: Dict[str, Any], features: Dict[str, Any]):
        """Store traffic data in database."""
        logger.debug("Storing traffic flow data")

    def _log_ingestion(self, source_type: str, records_processed: int,
                      records_failed: int, start_time: datetime):
        """Log ingestion metrics."""
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        status = "success" if records_failed == 0 else "partial"
        if records_processed == 0:
            status = "failed"

        logger.info(
            f"Ingestion complete - Type: {source_type}, "
            f"Processed: {records_processed}, Failed: {records_failed}, "
            f"Time: {execution_time:.2f}s, Status: {status}"
        )

    # ========== Scheduling Methods ==========

    def schedule_jobs(self):
        """Schedule all data ingestion jobs."""
        logger.info("Scheduling data ingestion jobs")

        # Real-time data (high frequency)
        schedule.every(30).seconds.do(self.ingest_apc_realtime)  # Every 30 seconds
        schedule.every(5).minutes.do(self.ingest_traffic_flow)    # Every 5 minutes

        # Near real-time data (medium frequency)
        schedule.every(15).minutes.do(self.ingest_weather_current)  # Every 15 minutes

        # Forecast/historical data (low frequency)
        schedule.every(1).hours.do(self.ingest_weather_forecast)    # Every hour
        schedule.every(6).hours.do(self.ingest_apc_historical)      # Every 6 hours
        schedule.every(1).hours.do(self.ingest_traffic_incidents)   # Every hour

        # Parallel ingestion batch
        schedule.every(10).minutes.do(self.run_parallel_ingestion)  # Every 10 minutes

        logger.info("Jobs scheduled successfully")

    def run(self):
        """Run the scheduler."""
        self.initialize_clients()
        self.schedule_jobs()

        logger.info("Data ingestion scheduler started")

        # Run initial ingestion
        self.run_parallel_ingestion()

        # Keep running scheduled jobs
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait before retrying


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run scheduler
    scheduler = DataIngestionScheduler()
    scheduler.run()