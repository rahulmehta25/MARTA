#!/usr/bin/env python3
"""
MARTA Data Processing Orchestrator
Coordinates trip reconstruction and feature engineering processes
"""
import os
import sys
import logging
import subprocess
import time
from datetime import datetime
import psycopg2

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_processing.log'),
        logging.StreamHandler()
    ]
)

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Processing scripts to run
PROCESSING_SCRIPTS = [
    {
        'name': 'Trip Reconstruction',
        'script': 'src/data_processing/trip_reconstruction.py',
        'description': 'Reconstructs historical trips from GTFS-RT and static data',
        'required': True,
        'timeout': 600  # 10 minutes
    },
    {
        'name': 'Feature Engineering',
        'script': 'src/data_processing/feature_engineering.py',
        'description': 'Creates ML-ready features from unified data',
        'required': True,
        'timeout': 900  # 15 minutes
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

def check_data_availability():
    """Check if required data is available for processing"""
    conn = create_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check GTFS static data
            cursor.execute("SELECT COUNT(*) FROM gtfs_stops")
            stops_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM gtfs_trips")
            trips_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM gtfs_stop_times")
            stop_times_count = cursor.fetchone()[0]
            
            # Check GTFS-RT data
            cursor.execute("SELECT COUNT(*) FROM gtfs_vehicle_positions")
            vp_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM gtfs_trip_updates")
            tu_count = cursor.fetchone()[0]
            
            logging.info(f"Data availability check:")
            logging.info(f"  GTFS Stops: {stops_count}")
            logging.info(f"  GTFS Trips: {trips_count}")
            logging.info(f"  GTFS Stop Times: {stop_times_count}")
            logging.info(f"  Vehicle Positions: {vp_count}")
            logging.info(f"  Trip Updates: {tu_count}")
            
            # Require at least some static and real-time data
            if stops_count == 0 or trips_count == 0 or stop_times_count == 0:
                logging.error("❌ Insufficient GTFS static data")
                return False
            
            if vp_count == 0 and tu_count == 0:
                logging.warning("⚠️ No GTFS-RT data available - will use sample data")
            
            return True
            
    except Exception as e:
        logging.error(f"Data availability check failed: {e}")
        return False
    finally:
        conn.close()

def run_processing_script(script_config):
    """Run a single processing script"""
    script_name = script_config['name']
    script_path = script_config['script']
    timeout = script_config['timeout']
    
    logging.info(f"Starting {script_name}...")
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

def generate_processing_summary(results):
    """Generate a summary of processing results"""
    print("\n" + "="*80)
    print("🚇 MARTA DATA PROCESSING SUMMARY REPORT")
    print("="*80)
    print(f"📅 Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Total Execution Time: {sum(r['execution_time'] for r in results):.1f}s")
    print()
    
    # Script results
    print("📊 PROCESSING SCRIPT RESULTS:")
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
    print("\n🗄️  PROCESSED DATA SUMMARY:")
    print("-" * 50)
    
    conn = create_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                # Check unified data
                cursor.execute("SELECT COUNT(*) FROM unified_data")
                unified_count = cursor.fetchone()[0]
                print(f"📋 Unified Data Records: {unified_count:,}")
                
                # Check ML features
                cursor.execute("SELECT COUNT(*) FROM ml_features")
                features_count = cursor.fetchone()[0]
                print(f"🔧 ML Features Records: {features_count:,}")
                
                # Check feature distribution
                if features_count > 0:
                    cursor.execute("SELECT target_demand_level, COUNT(*) FROM ml_features GROUP BY target_demand_level")
                    demand_dist = cursor.fetchall()
                    print(f"📊 Demand Level Distribution:")
                    for level, count in demand_dist:
                        print(f"   {level}: {count:,}")
                
        except Exception as e:
            logging.error(f"Error generating data summary: {e}")
        finally:
            conn.close()
    
    print("\n" + "="*80)

def main():
    """Main processing orchestration function"""
    logging.info("🚀 Starting MARTA Data Processing Orchestrator")
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Check data availability
    if not check_data_availability():
        logging.error("❌ Data availability check failed. Please ensure data ingestion is complete.")
        return False
    
    # Run all processing scripts
    results = []
    for script_config in PROCESSING_SCRIPTS:
        result = run_processing_script(script_config)
        result['script_name'] = script_config['name']
        results.append(result)
        
        # Add delay between scripts
        time.sleep(2)
    
    # Generate summary report
    generate_processing_summary(results)
    
    # Determine overall success
    success_count = sum(1 for r in results if r['status'] == 'success')
    required_scripts = [s for s in PROCESSING_SCRIPTS if s['required']]
    required_success = sum(1 for r in results[:len(required_scripts)] if r['status'] == 'success')
    
    if required_success == len(required_scripts):
        logging.info("🎉 All required processing scripts completed successfully!")
        return True
    else:
        logging.error(f"⚠️ Only {required_success}/{len(required_scripts)} required scripts succeeded")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 