#!/usr/bin/env python3
"""
MARTA Optimization Orchestrator
Coordinates route optimization and simulation workflows
"""
import os
import sys
import logging
import subprocess
import time
from datetime import datetime
import psycopg2
import joblib

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/optimization.log'),
        logging.StreamHandler()
    ]
)

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Optimization workflow configuration
OPTIMIZATION_WORKFLOW = [
    {
        'name': 'Route Optimization',
        'script': 'src/optimization/route_optimizer.py',
        'description': 'Generate route optimization proposals using ML predictions',
        'required': True,
        'timeout': 600  # 10 minutes
    },
    {
        'name': 'Route Simulation',
        'script': 'src/optimization/route_simulator.py',
        'description': 'Simulate route performance with and without optimizations',
        'required': True,
        'timeout': 900  # 15 minutes
    }
]

# Results storage
RESULTS_DIR = 'optimization_results'

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
    """Check if required data is available for optimization"""
    conn = create_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check GTFS data
            cursor.execute("SELECT COUNT(*) FROM gtfs_routes")
            routes_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM gtfs_stops")
            stops_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM gtfs_trips")
            trips_count = cursor.fetchone()[0]
            
            # Check ML models (optional)
            try:
                cursor.execute("SELECT COUNT(*) FROM ml_features LIMIT 1")
                features_count = cursor.fetchone()[0]
            except:
                features_count = 0  # Table doesn't exist yet
            
            logging.info(f"Data availability check:")
            logging.info(f"  GTFS Routes: {routes_count}")
            logging.info(f"  GTFS Stops: {stops_count}")
            logging.info(f"  GTFS Trips: {trips_count}")
            logging.info(f"  ML Features: {features_count}")
            
            # Require basic GTFS data
            if routes_count == 0 or stops_count == 0 or trips_count == 0:
                logging.error("❌ Missing required GTFS data")
                return False
            
            return True
            
    except Exception as e:
        logging.error(f"Data availability check failed: {e}")
        return False
    finally:
        conn.close()

def check_ml_models():
    """Check if ML models are available"""
    model_files = [
        'models/ensemble/ensemble_demand_level_model.pkl',
        'models/ensemble/ensemble_dwell_time_model.pkl'
    ]
    
    available_models = []
    for model_file in model_files:
        if os.path.exists(model_file):
            available_models.append(model_file)
    
    if available_models:
        logging.info(f"Found {len(available_models)} ML models")
        return True
    else:
        logging.warning("⚠️ No ML models found - will use fallback methods")
        return False

def run_optimization_script(script_config):
    """Run a single optimization script"""
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

def collect_optimization_results():
    """Collect and organize optimization results"""
    logging.info("Collecting optimization results...")
    
    results = {
        'optimization_results': [],
        'simulation_results': [],
        'comparison_results': [],
        'generated_files': []
    }
    
    # Look for optimization result files
    for filename in os.listdir('.'):
        if filename.startswith('optimization_results_') and filename.endswith('.pkl'):
            try:
                data = joblib.load(filename)
                results['optimization_results'].append({
                    'filename': filename,
                    'data': data
                })
                results['generated_files'].append(filename)
            except Exception as e:
                logging.warning(f"Could not load {filename}: {e}")
    
    # Look for simulation result files
    for filename in os.listdir('.'):
        if filename.startswith('simulation_results_') and filename.endswith('.pkl'):
            try:
                data = joblib.load(filename)
                results['simulation_results'].append({
                    'filename': filename,
                    'data': data
                })
                results['generated_files'].append(filename)
            except Exception as e:
                logging.warning(f"Could not load {filename}: {e}")
    
    return results

def generate_optimization_summary(workflow_results, collected_results):
    """Generate summary of optimization workflow"""
    print("\n" + "="*80)
    print("🚇 MARTA OPTIMIZATION WORKFLOW SUMMARY REPORT")
    print("="*80)
    print(f"📅 Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Total Execution Time: {sum(r['execution_time'] for r in workflow_results):.1f}s")
    print()
    
    # Workflow results
    print("📊 WORKFLOW EXECUTION RESULTS:")
    print("-" * 50)
    success_count = 0
    for result in workflow_results:
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"{status_icon} {result['script_name']}: {result['status'].upper()}")
        if result['status'] == 'success':
            success_count += 1
        if result['status'] != 'success' and 'error' in result:
            print(f"   Error: {result['error'][:100]}...")
    
    print(f"\n📈 Success Rate: {success_count}/{len(workflow_results)} ({success_count/len(workflow_results)*100:.1f}%)")
    
    # Generated files
    print("\n🗂️  GENERATED FILES:")
    print("-" * 50)
    
    if collected_results['generated_files']:
        for filename in collected_results['generated_files']:
            print(f"  📄 {filename}")
    else:
        print("  No result files generated")
    
    # Optimization results summary
    if collected_results['optimization_results']:
        print("\n🔧 OPTIMIZATION RESULTS SUMMARY:")
        print("-" * 50)
        
        for result in collected_results['optimization_results']:
            data = result['data']
            if 'overall_impact' in data:
                impact = data['overall_impact']
                print(f"\nFile: {result['filename']}")
                print(f"  Routes Analyzed: {data.get('routes_analyzed', 'N/A')}")
                print(f"  Short-Turn Proposals: {len(data.get('short_turn_proposals', []))}")
                print(f"  Headway Optimizations: {len(data.get('headway_optimizations', []))}")
                print(f"  Estimated Cost Savings: ${impact.get('estimated_cost_savings', 0):.0f}")
                print(f"  Estimated Revenue Increase: ${impact.get('estimated_revenue_increase', 0):.0f}")
    
    # Simulation results summary
    if collected_results['simulation_results']:
        print("\n🎮 SIMULATION RESULTS SUMMARY:")
        print("-" * 50)
        
        for result in collected_results['simulation_results']:
            data = result['data']
            if 'metrics' in data:
                metrics = data['metrics']
                print(f"\nFile: {result['filename']}")
                print(f"  Passengers: {data.get('passengers', 'N/A')}")
                print(f"  Buses: {data.get('buses', 'N/A')}")
                print(f"  Average Wait Time: {metrics.get('average_wait_time', 0):.1f} minutes")
                print(f"  Passenger Satisfaction: {metrics.get('passenger_satisfaction', 0):.1%}")
                print(f"  Vehicle Utilization: {metrics.get('vehicle_utilization', 0):.1%}")
    
    print("\n" + "="*80)

def save_workflow_results(workflow_results, collected_results):
    """Save workflow results to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'optimization_workflow_results_{timestamp}.pkl'
    
    workflow_summary = {
        'timestamp': datetime.now().isoformat(),
        'workflow_results': workflow_results,
        'collected_results': collected_results,
        'total_execution_time': sum(r['execution_time'] for r in workflow_results),
        'success_count': sum(1 for r in workflow_results if r['status'] == 'success')
    }
    
    joblib.dump(workflow_summary, filename)
    logging.info(f"Workflow results saved to {filename}")
    
    return filename

def main():
    """Main optimization orchestration function"""
    logging.info("🚀 Starting MARTA Optimization Orchestrator")
    
    # Create logs and results directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Check data availability
    if not check_data_availability():
        logging.error("❌ Data availability check failed. Please ensure GTFS data is loaded.")
        return False
    
    # Check ML models (optional)
    ml_models_available = check_ml_models()
    
    # Run optimization workflow
    workflow_results = []
    for script_config in OPTIMIZATION_WORKFLOW:
        result = run_optimization_script(script_config)
        result['script_name'] = script_config['name']
        workflow_results.append(result)
        
        # Add delay between scripts
        time.sleep(2)
    
    # Collect results
    collected_results = collect_optimization_results()
    
    # Generate summary report
    generate_optimization_summary(workflow_results, collected_results)
    
    # Save workflow results
    results_file = save_workflow_results(workflow_results, collected_results)
    
    # Determine overall success
    success_count = sum(1 for r in workflow_results if r['status'] == 'success')
    required_scripts = [s for s in OPTIMIZATION_WORKFLOW if s['required']]
    required_success = sum(1 for r in workflow_results[:len(required_scripts)] if r['status'] == 'success')
    
    if required_success == len(required_scripts):
        logging.info("🎉 All required optimization scripts completed successfully!")
        
        # Print next steps
        print("\n📋 NEXT STEPS:")
        print("-" * 30)
        print("1. Review optimization proposals in generated files")
        print("2. Validate simulation results against business requirements")
        print("3. Implement approved optimizations in production")
        print("4. Monitor performance improvements")
        print("5. Schedule regular optimization runs")
        
        return True
    else:
        logging.error(f"⚠️ Only {required_success}/{len(required_scripts)} required scripts succeeded")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 