#!/usr/bin/env python3
"""
Run Route Optimization
This script runs the route optimization simulation.
"""
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.optimization.route_optimizer import RouteOptimizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RouteOptimizationPipeline:
    """Runs the route optimization pipeline"""

    def run(self):
        """Runs the route optimization pipeline"""
        try:
            # Run route optimization
            logger.info("Running route optimization...")
            optimizer = RouteOptimizer()
            optimizer.optimize()
            optimizer.simulate()
            optimizer.evaluate()

            logger.info("Route optimization pipeline completed successfully!")

        except Exception as e:
            logger.error(f"Route optimization pipeline failed: {e}")
            raise

if __name__ == "__main__":
    pipeline = RouteOptimizationPipeline()
    pipeline.run()
