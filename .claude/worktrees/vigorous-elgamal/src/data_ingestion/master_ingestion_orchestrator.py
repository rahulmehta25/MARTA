#!/usr/bin/env python3
"""
MARTA Data Ingestion Master Orchestrator
Coordinates all data ingestion processes for the MARTA Demand Forecasting Platform
"""
import os
import sys
import logging
import subprocess
import time
from datetime import datetime
import psycopg2
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_ingestion.log'),
        logging.StreamHandler()
    ]
)

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Ingestion scripts to run
INGESTION_SCRIPTS = [
    {
        'name': 'GTFS-Realtime Data',
        'script': 'src/data_ingestion/gtfs_realtime_ingestion.py',
        'description': 'Real-time vehicle positions and trip updates',
        'required': True,
        'timeout': 300  # 5 minutes
    },
    {
        'name': 'Ridership KPI Data',
        'script': 'src/data_ingestion/ridership_kpi_scraper.py',
        'description': 'Monthly ridership metrics from MARTA KPI reports',
        'required': True,
        'timeout': 120  # 2 minutes
    },
    {
        'name': 'GIS Layers',
        'script': 'src/data_ingestion/gis_layers_ingestion.py',
        'description': 'MARTA station and route geographic data',
        'required': True,
        'timeout': 180  # 3 minutes
    },
    {
        'name': 'Weather Data',
        'script': 'src/data_ingestion/weather_data_fetcher.py',
        'description': 'Current and historical weather data for Atlanta',
        'required': False,
        'timeout': 300  # 5 minutes
    },
    {
        'name': 'Event Data',
        'script': 'src/data_ingestion/event_data_scraper.py',
        'description': 'Major venue events and schedules',
        'required': False,
        'timeout': 180  # 3 minutes
    }
]

def create_db_connection():
    """Create database connection"""
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return None

def check_database_status():
    """Check if database is accessible and has required tables"""
    conn = create_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check if GTFS static tables exist
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE 'gtfs_%'
            """)
            gtfs_tables = cursor.fetchall()
            
            if len(gtfs_tables) < 5:  # Should have at least 5 GTFS tables
                logging.warning("GTFS static tables may not be fully loaded")
                return False
            
            logging.info(f"Database check passed. Found {len(gtfs_tables)} GTFS tables")
            return True
            
    except Exception as e:
        logging.error(f"Database status check failed: {e}")
        return False
    finally:
        conn.close()

def run_ingestion_script(script_config):
    """Run a single ingestion script"""
    script_name = script_config['name']
    script_path = script_config['script']
    timeout = script_config['timeout']
    
    logging.info(f"Starting {script_name} ingestion...")
    start_time = time.time()
    
    try:
        # Run the script as a subprocess
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            logging.info(f"✅ {script_name} completed successfully in {execution_time:.1f}s")
            return {
                'status': 'success',
                'execution_time': execution_time,
                'output': result.stdout
            }
        else:
            logging.error(f"❌ {script_name} failed with return code {result.returncode}")
            logging.error(f"Error output: {result.stderr}")
            return {
                'status': 'failed',
                'execution_time': execution_time,
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        logging.error(f"⏰ {script_name} timed out after {timeout}s")
        return {
            'status': 'timeout',
            'execution_time': timeout,
            'error': f'Script timed out after {timeout} seconds'
        }
    except Exception as e:
        logging.error(f"💥 {script_name} failed with exception: {e}")
        return {
            'status': 'exception',
            'execution_time': time.time() - start_time,
            'error': str(e)
        }

def generate_data_summary():
    """Generate a summary of all ingested data"""
    conn = create_db_connection()
    if not conn:
        return {}
    
    summary = {}
    
    try:
        with conn.cursor() as cursor:
            # Count records in each table
            tables_to_check = [
                'gtfs_stops', 'gtfs_routes', 'gtfs_trips', 'gtfs_stop_times',
                'gtfs_vehicle_positions', 'gtfs_trip_updates',
                'marta_ridership_kpi', 'marta_gis_layers',
                'atlanta_weather_data', 'atlanta_events_data'
            ]
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    summary[table] = count
                except Exception:
                    summary[table] = 0
            
            # Get latest timestamps for real-time data
            try:
                cursor.execute("SELECT MAX(timestamp) FROM gtfs_vehicle_positions")
                latest_vp = cursor.fetchone()[0]
                summary['latest_vehicle_position'] = latest_vp
            except:
                summary['latest_vehicle_position'] = None
                
            try:
                cursor.execute("SELECT MAX(timestamp) FROM gtfs_trip_updates")
                latest_tu = cursor.fetchone()[0]
                summary['latest_trip_update'] = latest_tu
            except:
                summary['latest_trip_update'] = None
                
    except Exception as e:
        logging.error(f"Error generating data summary: {e}")
    finally:
        conn.close()
    
    return summary

def print_summary_report(results, data_summary):
    """Print a comprehensive summary report"""
    print("\n" + "="*80)
    print("🚇 MARTA DATA INGESTION SUMMARY REPORT")
    print("="*80)
    print(f"📅 Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Total Execution Time: {sum(r['execution_time'] for r in results):.1f}s")
    print()
    
    # Script results
    print("📊 INGESTION SCRIPT RESULTS:")
    print("-" * 50)
    success_count = 0
    for result in results:
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"{status_icon} {result['script_name']}: {result['status'].upper()}")
        if result['status'] == 'success':
            success_count += 1
        if result['status'] != 'success' and 'error' in result:
            print(f"   Error: {result['error'][:100]}...")
    
    print(f"\n📈 Success Rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    
    # Data summary
    print("\n🗄️  DATABASE SUMMARY:")
    print("-" * 50)
    for table, count in data_summary.items():
        if 'latest' not in table:
            print(f"📋 {table}: {count:,} records")
    
    # Real-time data status
    print("\n🔄 REAL-TIME DATA STATUS:")
    print("-" * 50)
    if data_summary.get('latest_vehicle_position'):
        print(f"🚌 Latest Vehicle Position: {data_summary['latest_vehicle_position']}")
    else:
        print("🚌 Vehicle Positions: No data")
        
    if data_summary.get('latest_trip_update'):
        print(f"🚇 Latest Trip Update: {data_summary['latest_trip_update']}")
    else:
        print("🚇 Trip Updates: No data")
    
    print("\n" + "="*80)

def main():
    """Main orchestration function"""
    logging.info("🚀 Starting MARTA Data Ingestion Orchestrator")
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Check database status
    if not check_database_status():
        logging.error("❌ Database check failed. Please ensure database is running and accessible.")
        return False
    
    # Run all ingestion scripts
    results = []
    for script_config in INGESTION_SCRIPTS:
        result = run_ingestion_script(script_config)
        result['script_name'] = script_config['name']
        results.append(result)
        
        # Add delay between scripts to avoid overwhelming external APIs
        time.sleep(2)
    
    # Generate data summary
    data_summary = generate_data_summary()
    
    # Print summary report
    print_summary_report(results, data_summary)
    
    # Determine overall success
    success_count = sum(1 for r in results if r['status'] == 'success')
    required_scripts = [s for s in INGESTION_SCRIPTS if s['required']]
    required_success = sum(1 for r in results[:len(required_scripts)] if r['status'] == 'success')
    
    if required_success == len(required_scripts):
        logging.info("🎉 All required ingestion scripts completed successfully!")
        return True
    else:
        logging.error(f"⚠️  Only {required_success}/{len(required_scripts)} required scripts succeeded")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 