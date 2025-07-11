#!/usr/bin/env python3
"""
Real MARTA Data Ingestion
This script ingests the real MARTA GTFS data into the database.
"""
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings
from src.data_ingestion.gtfs_ingestor import GTFSIngestor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealMARTADataIngestion:
    """Handles the ingestion of real MARTA data"""

    def __init__(self):
        self.gtfs_zip_path = os.path.join(settings.RAW_DATA_DIR, "gtfs_static", "google_transit.zip")

    def ingest(self):
        """Ingests the real MARTA GTFS data"""
        try:
            if not os.path.exists(self.gtfs_zip_path):
                raise FileNotFoundError(f"Real MARTA GTFS data not found at {self.gtfs_zip_path}. Please run the setup script first.")

            ingestor = GTFSIngestor()
            ingestor.ingest_gtfs_static(self.gtfs_zip_path)
            logger.info("Successfully ingested real MARTA GTFS data into the database")
        except Exception as e:
            logger.error(f"Failed to ingest real MARTA data: {e}")
            raise

if __name__ == "__main__":
    ingestion = RealMARTADataIngestion()
    ingestion.ingest()