#!/usr/bin/env python3
"""
Main script to run the entire MARTA Demand Forecasting and Route Optimization pipeline.
"""
import logging
from scripts.run_pipeline import DataPipeline
from scripts.run_demand_forecasting import DemandForecastingPipeline
from scripts.run_route_optimization import RouteOptimizationPipeline

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to run the entire pipeline."""
    logger.info("Starting the MARTA Demand Forecasting and Route Optimization pipeline...")

    try:
        # Run the data pipeline
        data_pipeline = DataPipeline()
        data_pipeline.run()

        # Run the demand forecasting pipeline
        demand_forecasting_pipeline = DemandForecastingPipeline()
        demand_forecasting_pipeline.run()

        # Run the route optimization pipeline
        route_optimization_pipeline = RouteOptimizationPipeline()
        route_optimization_pipeline.run()

        logger.info("MARTA Demand Forecasting and Route Optimization pipeline completed successfully!")

    except Exception as e:
        logger.error(f"An error occurred during the pipeline execution: {e}")

if __name__ == "__main__":
    main()
