#!/usr/bin/env python3
"""
Run Data Pipeline
This script runs the complete data pipeline, from data ingestion to data verification.
"""
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_ingestion.setup_real_marta_data import RealMARTADataSetup
from src.data_ingestion.real_marta_data_ingestion import RealMARTADataIngestion
from src.data_ingestion.gtfs_realtime_processor import GTFSRealtimeProcessor
from tests.verify_data_loading import DataLoadingVerifier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataPipeline:
    """Runs the complete data pipeline"""

    def run(self):
        """Runs the complete data pipeline"""
        try:
            # Setup real MARTA data
            logger.info("Setting up real MARTA data...")
            setup = RealMARTADataSetup()
            setup.setup()

            # Ingest real MARTA data
            logger.info("Ingesting real MARTA data...")
            ingestion = RealMARTADataIngestion()
            ingestion.ingest()

            # Create unified table
            logger.info("Creating unified table...")
            gtfs_rt_processor = GTFSRealtimeProcessor()
            gtfs_rt_processor.create_unified_table()

            # Ingest historical real-time data
            logger.info("Generating and ingesting synthetic real-time data...")
            gtfs_rt_processor.generate_synthetic_realtime_data(num_days=7) # Generate 7 days of synthetic data

            # Verify data loading
            logger.info("Verifying data loading...")
            verifier = DataLoadingVerifier()
            verifier.verify()

            logger.info("Data pipeline completed successfully!")

        except Exception as e:
            logger.error(f"Data pipeline failed: {e}")
            raise

if __name__ == "__main__":
    pipeline = DataPipeline()
    pipeline.run()
