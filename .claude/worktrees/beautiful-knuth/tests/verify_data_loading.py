#!/usr/bin/env python3
"""
Verify Data Loading
This script verifies that the data has been loaded correctly into the database.
"""
import os
import sys
import logging
import pandas as pd
import psycopg2

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataLoadingVerifier:
    """Verifies the data loading process"""

    def __init__(self):
        self.db_config = {
            'host': settings.DB_HOST,
            'database': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD
        }

    def verify(self):
        """Verifies that the data has been loaded correctly"""
        try:
            conn = psycopg2.connect(**self.db_config)

            # Verify that the tables have been created
            self._verify_table_creation(conn)

            # Verify that the tables have data
            self._verify_table_data(conn)

            conn.close()
            logger.info("Data loading verification completed successfully!")

        except Exception as e:
            logger.error(f"Data loading verification failed: {e}")
            raise

    def _verify_table_creation(self, conn):
        """Verifies that the tables have been created"""
        logger.info("Verifying table creation...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [table[0] for table in cursor.fetchall()]

            required_tables = [
                "gtfs_stops",
                "gtfs_routes",
                "gtfs_trips",
                "gtfs_stop_times",
                "gtfs_calendar",
                "gtfs_shapes",
                "unified_realtime_historical_data"
            ]

            for table in required_tables:
                if table not in tables:
                    raise Exception(f"Table {table} not found in the database")

        logger.info("Table creation verification successful!")

    def _verify_table_data(self, conn):
        """Verifies that the tables have data"""
        logger.info("Verifying table data...")
        with conn.cursor() as cursor:
            for table in [
                "gtfs_stops",
                "gtfs_routes",
                "gtfs_trips",
                "gtfs_stop_times",
                "gtfs_calendar",
                "gtfs_shapes",
                "unified_realtime_historical_data"
            ]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count == 0:
                    logger.warning(f"Table {table} is empty")
                else:
                    logger.info(f"Table {table} has {count} rows")

        logger.info("Table data verification successful!")

if __name__ == "__main__":
    verifier = DataLoadingVerifier()
    verifier.verify()
