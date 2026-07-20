import logging
from src.data_ingestion.gtfs_realtime_processor import GTFSRealtimeProcessor

def main():
    """Main function for historical GTFS-RT data ingestion"""
    logging.basicConfig(level=logging.INFO)
    
    processor = GTFSRealtimeProcessor()
    
    # Ingest historical data for model training
    processor.ingest_historical_realtime_data(num_iterations=10, interval_seconds=30)

if __name__ == "__main__":
    main()
