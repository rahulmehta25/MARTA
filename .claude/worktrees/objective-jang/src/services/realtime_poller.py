#!/usr/bin/env python3
"""
Background service for polling MARTA real-time data.
This service runs continuously and updates the database with fresh arrival data.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealTimePoller:
    """Service for continuously polling real-time MARTA data."""
    
    def __init__(self, interval_seconds: int = 30):
        """
        Initialize the poller.
        
        Args:
            interval_seconds: Polling interval in seconds (default: 30)
        """
        self.interval = interval_seconds
        self.running = False
        self.fetch_script = Path(__file__).parent.parent.parent / "scripts" / "fetch_real_time_rail.py"
        
    async def fetch_data(self):
        """Fetch real-time data using the existing script."""
        try:
            logger.info("Fetching real-time rail data...")
            
            # Run the fetch script asynchronously
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(self.fetch_script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Parse output to check how many records were stored
                output = stdout.decode()
                if "Stored" in output:
                    for line in output.split('\n'):
                        if "Stored" in line:
                            logger.info(line.strip())
                            break
                else:
                    logger.info("Data fetch completed successfully")
                return True
            else:
                logger.error(f"Error fetching data: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Exception during data fetch: {e}")
            return False
    
    async def run_forever(self):
        """Run the polling service continuously."""
        logger.info(f"Starting real-time polling service (interval: {self.interval}s)")
        logger.info("Press Ctrl+C to stop")
        
        self.running = True
        consecutive_failures = 0
        max_failures = 5
        
        while self.running:
            try:
                # Fetch data
                success = await self.fetch_data()
                
                if success:
                    consecutive_failures = 0
                    logger.info(f"Next update in {self.interval} seconds...")
                else:
                    consecutive_failures += 1
                    logger.warning(f"Fetch failed ({consecutive_failures}/{max_failures})")
                    
                    # If too many failures, increase wait time
                    if consecutive_failures >= max_failures:
                        wait_time = self.interval * 3
                        logger.error(f"Too many consecutive failures. Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        consecutive_failures = 0
                        continue
                
                # Wait for next interval
                await asyncio.sleep(self.interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}")
                await asyncio.sleep(self.interval)
    
    def stop(self):
        """Stop the polling service."""
        logger.info("Stopping polling service...")
        self.running = False


class PollingManager:
    """Manager for coordinating multiple polling services."""
    
    def __init__(self):
        """Initialize the polling manager."""
        self.pollers = []
        
    def add_poller(self, poller: RealTimePoller):
        """Add a poller to be managed."""
        self.pollers.append(poller)
        
    async def run_all(self):
        """Run all registered pollers concurrently."""
        if not self.pollers:
            logger.warning("No pollers registered")
            return
            
        logger.info(f"Starting {len(self.pollers)} polling service(s)")
        
        # Create tasks for all pollers
        tasks = [poller.run_forever() for poller in self.pollers]
        
        try:
            # Run all pollers concurrently
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down all pollers...")
            for poller in self.pollers:
                poller.stop()
        except Exception as e:
            logger.error(f"Error in polling manager: {e}")
            for poller in self.pollers:
                poller.stop()


async def main():
    """Main entry point for the polling service."""
    # Get polling interval from settings or use default
    interval = getattr(settings, 'real_time_poll_interval', 30)
    
    # Create and configure pollers
    rail_poller = RealTimePoller(interval_seconds=interval)
    
    # Create manager and add pollers
    manager = PollingManager()
    manager.add_poller(rail_poller)
    
    # Run all pollers
    await manager.run_all()


if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)