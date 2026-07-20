#!/usr/bin/env python3
"""
Real Data Ingestion Runner for MARTA Platform
Replaces synthetic data generation with real data from MARTA sources
"""
import os
import sys
import logging
import argparse
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.data_ingestion.real_gtfs_static_ingestor import RealGTFSStaticIngestor
from src.data_ingestion.real_gtfs_realtime_ingestor import RealGTFSRealtimeIngestor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealDataIngestionRunner:
    """Runner for real data ingestion components"""
    
    def __init__(self):
        self.gtfs_static_ingestor = RealGTFSStaticIngestor()
        self.gtfs_realtime_ingestor = RealGTFSRealtimeIngestor()
    
    def run_gtfs_static_ingestion(self, download_new: bool = True, gtfs_zip_path: str = None) -> bool:
        """Run GTFS static data ingestion"""
        logger.info("🚇 Starting real GTFS static data ingestion...")
        
        try:
            success = self.gtfs_static_ingestor.run_ingestion(
                download_new=download_new,
                gtfs_zip_path=gtfs_zip_path
            )
            
            if success:
                logger.info("✅ GTFS static data ingestion completed successfully")
            else:
                logger.error("❌ GTFS static data ingestion failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in GTFS static ingestion: {e}")
            return False
    
    def run_gtfs_realtime_ingestion(self, stream: bool = False) -> bool:
        """Run GTFS real-time data ingestion"""
        logger.info("🔄 Starting real GTFS real-time data ingestion...")
        
        try:
            if stream:
                # Start continuous streaming
                logger.info("Starting continuous real-time data streaming...")
                self.gtfs_realtime_ingestor.start_streaming()
                
                # Keep running until interrupted
                try:
                    while self.gtfs_realtime_ingestor.is_running:
                        import time
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received interrupt, stopping streaming...")
                    self.gtfs_realtime_ingestor.stop_streaming()
                
                return True
            else:
                # Run single fetch
                success = self.gtfs_realtime_ingestor.run_single_fetch()
                
                if success:
                    logger.info("✅ GTFS real-time data ingestion completed successfully")
                else:
                    logger.error("❌ GTFS real-time data ingestion failed")
                
                return success
                
        except Exception as e:
            logger.error(f"Error in GTFS real-time ingestion: {e}")
            return False
    
    def run_complete_ingestion(self, stream_realtime: bool = False) -> bool:
        """Run complete real data ingestion pipeline"""
        logger.info("🚀 Starting complete real data ingestion pipeline...")
        
        try:
            # Step 1: GTFS Static Data
            logger.info("Step 1/2: GTFS Static Data Ingestion")
            static_success = self.run_gtfs_static_ingestion()
            
            if not static_success:
                logger.error("GTFS static ingestion failed, stopping pipeline")
                return False
            
            # Step 2: GTFS Real-time Data
            logger.info("Step 2/2: GTFS Real-time Data Ingestion")
            realtime_success = self.run_gtfs_realtime_ingestion(stream=stream_realtime)
            
            if not realtime_success:
                logger.error("GTFS real-time ingestion failed")
                return False
            
            logger.info("🎉 Complete real data ingestion pipeline completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error in complete ingestion pipeline: {e}")
            return False
    
    def show_status(self):
        """Show ingestion status and statistics"""
        logger.info("📊 Real Data Ingestion Status")
        logger.info("=" * 50)
        
        # Show GTFS real-time statistics
        stats = self.gtfs_realtime_ingestor.get_stats()
        logger.info(f"Real-time Statistics:")
        logger.info(f"  - Vehicle positions received: {stats.get('vehicle_positions_received', 0)}")
        logger.info(f"  - Trip updates received: {stats.get('trip_updates_received', 0)}")
        logger.info(f"  - Errors: {stats.get('errors', 0)}")
        logger.info(f"  - Last successful fetch: {stats.get('last_successful_fetch', 'Never')}")
        
        if stats.get('start_time'):
            uptime = stats.get('uptime', 'Unknown')
            logger.info(f"  - Uptime: {uptime}")
        
        # Check database connectivity
        try:
            conn = self.gtfs_static_ingestor.create_db_connection()
            with conn.cursor() as cursor:
                # Check GTFS static data
                cursor.execute("SELECT COUNT(*) FROM gtfs_stops")
                stops_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM gtfs_routes")
                routes_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM gtfs_trips")
                trips_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM gtfs_stop_times")
                stop_times_count = cursor.fetchone()[0]
                
                # Check real-time data
                cursor.execute("SELECT COUNT(*) FROM gtfs_vehicle_positions")
                vehicle_positions_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM gtfs_trip_updates")
                trip_updates_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM unified_realtime_data")
                unified_data_count = cursor.fetchone()[0]
            
            conn.close()
            
            logger.info(f"Database Status:")
            logger.info(f"  - GTFS Stops: {stops_count}")
            logger.info(f"  - GTFS Routes: {routes_count}")
            logger.info(f"  - GTFS Trips: {trips_count}")
            logger.info(f"  - GTFS Stop Times: {stop_times_count}")
            logger.info(f"  - Vehicle Positions: {vehicle_positions_count}")
            logger.info(f"  - Trip Updates: {trip_updates_count}")
            logger.info(f"  - Unified Data: {unified_data_count}")
            
        except Exception as e:
            logger.error(f"Error checking database status: {e}")


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Real Data Ingestion Runner for MARTA Platform')
    
    # Command options
    parser.add_argument('--gtfs-static', action='store_true', help='Run GTFS static data ingestion')
    parser.add_argument('--gtfs-realtime', action='store_true', help='Run GTFS real-time data ingestion')
    parser.add_argument('--stream', action='store_true', help='Start continuous real-time streaming')
    parser.add_argument('--complete', action='store_true', help='Run complete ingestion pipeline')
    parser.add_argument('--status', action='store_true', help='Show ingestion status and statistics')
    
    # GTFS static options
    parser.add_argument('--gtfs-zip', type=str, help='Path to GTFS ZIP file (for static ingestion)')
    parser.add_argument('--no-download', action='store_true', help='Use existing GTFS ZIP file (don\'t download)')
    
    args = parser.parse_args()
    
    # Create runner
    runner = RealDataIngestionRunner()
    
    try:
        if args.status:
            # Show status
            runner.show_status()
            
        elif args.complete:
            # Run complete pipeline
            success = runner.run_complete_ingestion(stream_realtime=args.stream)
            sys.exit(0 if success else 1)
            
        elif args.gtfs_static:
            # Run GTFS static ingestion
            download_new = not args.no_download
            success = runner.run_gtfs_static_ingestion(
                download_new=download_new,
                gtfs_zip_path=args.gtfs_zip
            )
            sys.exit(0 if success else 1)
            
        elif args.gtfs_realtime:
            # Run GTFS real-time ingestion
            success = runner.run_gtfs_realtime_ingestion(stream=args.stream)
            sys.exit(0 if success else 1)
            
        else:
            # Default: show help
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping...")
        runner.gtfs_realtime_ingestor.stop_streaming()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error in real data ingestion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 