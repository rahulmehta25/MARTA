#!/usr/bin/env python3
"""
Run Demand Forecasting
This script runs the demand forecasting model.
"""
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.models.demand_forecaster import DemandForecaster

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DemandForecastingPipeline:
    """Runs the demand forecasting pipeline"""

    def run(self):
        """Runs the demand forecasting pipeline"""
        try:
            # Run demand forecasting
            logger.info("Running demand forecasting...")
            forecaster = DemandForecaster()
            forecaster.train()
            forecaster.predict()
            forecaster.evaluate()

            logger.info("Demand forecasting pipeline completed successfully!")

        except Exception as e:
            logger.error(f"Demand forecasting pipeline failed: {e}")
            raise

if __name__ == "__main__":
    pipeline = DemandForecastingPipeline()
    pipeline.run()
