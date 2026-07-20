#!/usr/bin/env python3
"""
Setup Real MARTA Data Pipeline
Creates database schema and runs comprehensive data ingestion
"""
import os
import sys
import logging
import psycopg2
from psycopg2 import sql

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_database_schema():
    """Create database schema for real MARTA data"""
    try:
        logger.info("Setting up database schema...")
        
        # Connect to database
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        
        # Read and execute schema file
        schema_file = "database/real_marta_schema.sql"
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
                conn.commit()
            
            logger.info("✅ Database schema created successfully")
        else:
            logger.error(f"Schema file not found: {schema_file}")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error setting up database schema: {e}")
        return False


def check_environment_variables():
    """Check if required environment variables are set"""
    required_vars = {
        'MARTA_API_KEY': 'MARTA API key for GTFS realtime data',
        'OPENWEATHER_API_KEY': 'OpenWeatherMap API key for weather data'
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var}: {description}")
    
    if missing_vars:
        logger.warning("⚠️  Missing environment variables:")
        for var in missing_vars:
            logger.warning(f"   - {var}")
        logger.warning("Some data sources may not be available without these keys")
    
    return len(missing_vars) == 0


def run_data_ingestion():
    """Run the comprehensive data ingestion pipeline"""
    try:
        logger.info("Starting real MARTA data ingestion...")
        
        # Import and run the ingestion pipeline
        from src.data_ingestion.real_marta_data_ingestion import RealMARTADataIngestion
        
        ingestion = RealMARTADataIngestion()
        ingestion.ingest_all_data()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error running data ingestion: {e}")
        return False


def verify_data_ingestion():
    """Verify that data was ingested successfully"""
    try:
        logger.info("Verifying data ingestion...")
        
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        
        # Check table counts
        tables_to_check = [
            'gtfs_stops',
            'gtfs_routes', 
            'gtfs_trips',
            'gtfs_stop_times',
            'ridership_metrics',
            'weather_data',
            'event_data',
            'gis_stations',
            'unified_data_enhanced'
        ]
        
        print("\n📊 Data Ingestion Verification:")
        print("=" * 50)
        
        for table in tables_to_check:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"✅ {table}: {count:,} records")
            except Exception as e:
                print(f"❌ {table}: Error - {e}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error verifying data ingestion: {e}")


def main():
    """Main setup function"""
    print("🚇 MARTA Real Data Pipeline Setup")
    print("=" * 50)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    env_ok = check_environment_variables()
    
    # Setup database schema
    print("\n2. Setting up database schema...")
    schema_ok = setup_database_schema()
    
    if not schema_ok:
        print("❌ Database schema setup failed. Exiting.")
        sys.exit(1)
    
    # Run data ingestion
    print("\n3. Running data ingestion...")
    ingestion_ok = run_data_ingestion()
    
    if not ingestion_ok:
        print("❌ Data ingestion failed. Exiting.")
        sys.exit(1)
    
    # Verify data ingestion
    print("\n4. Verifying data ingestion...")
    verify_data_ingestion()
    
    print("\n✅ Real MARTA data pipeline setup completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Run the Streamlit dashboard: streamlit run src/visualization/demo_dashboard.py")
    print("   2. Start the React frontend: cd frontend && npm start")
    print("   3. Access the platform at:")
    print("      - Backend: http://localhost:8501")
    print("      - Frontend: http://localhost:3003")


if __name__ == "__main__":
    main() 