#!/usr/bin/env python3
"""
Setup Real MARTA Data
This script downloads and ingests the real MARTA GTFS data into the database.
"""
import os
import sys
import logging
import requests
import zipfile
import io

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings
from src.data_ingestion.gtfs_ingestor import GTFSIngestor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealMARTADataSetup:
    """Handles the setup of real MARTA data"""

    def __init__(self):
        self.gtfs_zip_url = "https://www.itsmarta.com/google_transit_feed/google_transit.zip"
        self.gtfs_zip_path = os.path.join(settings.RAW_DATA_DIR, "gtfs_static", "google_transit.zip")

    def download_real_gtfs_data(self):
        """Downloads the real MARTA GTFS data"""
        logger.info(f"Downloading real MARTA GTFS data from {self.gtfs_zip_url}...")
        try:
            response = requests.get(self.gtfs_zip_url)
            response.raise_for_status()

            os.makedirs(os.path.dirname(self.gtfs_zip_path), exist_ok=True)
            with open(self.gtfs_zip_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Successfully downloaded real MARTA GTFS data to {self.gtfs_zip_path}")
            return self.gtfs_zip_path
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download real MARTA GTFS data: {e}")
            raise

    def setup(self):
        """Downloads and ingests the real MARTA GTFS data"""
        try:
            gtfs_zip_path = self.download_real_gtfs_data()
            ingestor = GTFSIngestor()
            ingestor.ingest_gtfs_static(gtfs_zip_path)
            logger.info("Successfully ingested real MARTA GTFS data into the database")
        except Exception as e:
            logger.error(f"Failed to setup real MARTA data: {e}")
            raise

if __name__ == "__main__":
    setup = RealMARTADataSetup()
    setup.setup()
