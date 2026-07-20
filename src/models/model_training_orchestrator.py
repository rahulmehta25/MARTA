#!/usr/bin/env python3
"""
MARTA Model Training Orchestrator
Coordinates training of all ML models for demand forecasting
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
        logging.FileHandler('logs/model_training.log'),
        logging.StreamHandler()
    ]
)

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Training scripts to run
TRAINING_SCRIPTS = [
    {
        'name': 'LSTM Demand Forecaster',
        'script': 'src/models/lstm_demand_forecaster.py',
        'description': 'LSTM-based time-series demand forecasting',
        'required': True,
        'timeout': 1800  # 30 minutes
    },
    {
        'name': 'XGBoost Demand Forecaster',
        'script': 'src/models/xgboost_demand_forecaster.py',
        'description': 'XGBoost-based demand forecasting',
        'required': True,
        'timeout': 900  # 15 minutes
    },
    {
        'name': 'Model Ensemble',
        'script': 'src/models/model_ensemble.py',
        'description': 'Ensemble combining LSTM and XGBoost',
        'required': False,
        'timeout': 600  # 10 minutes
    }
]

# Model storage
MODELS_DIR = 'models'

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
    """Check if required ML features are available for training"""
    conn = create_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Check ML features
            cursor.execute("SELECT COUNT(*) FROM ml_features")
            features_count = cursor.fetchone()[0]
            
            # Check target variables
            cursor.execute("SELECT COUNT(*) FROM ml_features WHERE target_dwell_time_seconds IS NOT NULL")
            dwell_time_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ml_features WHERE target_demand_level IS NOT NULL")
            demand_level_count = cursor.fetchone()[0]
            
            logging.info(f"Data availability check:")
            logging.info(f"  Total ML Features: {features_count}")
            logging.info(f"  Dwell Time Targets: {dwell_time_count}")
            logging.info(f"  Demand Level Targets: {demand_level_count}")
            
            # Require at least some features and targets
            if features_count == 0:
                logging.error("❌ No ML features available")
                return False
            
            if dwell_time_count == 0 and demand_level_count == 0:
                logging.error("❌ No target variables available")
                return False
            
            return True
            
    except Exception as e:
        logging.error(f"Data availability check failed: {e}")
        return False
    finally:
        conn.close()

def run_training_script(script_config):
    """Run a single training script"""
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

def check_model_files():
    """Check which model files were created"""
    logging.info("Checking created model files...")
    
    model_files = {
        'lstm': [],
        'xgboost': [],
        'ensemble': []
    }
    
    # Check LSTM models
    lstm_dir = f'{MODELS_DIR}/lstm'
    if os.path.exists(lstm_dir):
        for file in os.listdir(lstm_dir):
            if file.endswith('.h5') or file.endswith('.pkl'):
                model_files['lstm'].append(file)
    
    # Check XGBoost models
    xgb_dir = f'{MODELS_DIR}/xgboost'
    if os.path.exists(xgb_dir):
        for file in os.listdir(xgb_dir):
            if file.endswith('.pkl'):
                model_files['xgboost'].append(file)
    
    # Check Ensemble models
    ensemble_dir = f'{MODELS_DIR}/ensemble'
    if os.path.exists(ensemble_dir):
        for file in os.listdir(ensemble_dir):
            if file.endswith('.pkl'):
                model_files['ensemble'].append(file)
    
    # Check scalers
    scalers_dir = f'{MODELS_DIR}/scalers'
    scaler_files = []
    if os.path.exists(scalers_dir):
        for file in os.listdir(scalers_dir):
            if file.endswith('.pkl'):
                scaler_files.append(file)
    
    return model_files, scaler_files

def generate_training_summary(results):
    """Generate a summary of training results"""
    print("\n" + "="*80)
    print("🚇 MARTA MODEL TRAINING SUMMARY REPORT")
    print("="*80)
    print(f"📅 Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Total Execution Time: {sum(r['execution_time'] for r in results):.1f}s")
    print()
    
    # Script results
    print("📊 TRAINING SCRIPT RESULTS:")
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
    
    # Model files created
    print("\n🗂️  CREATED MODEL FILES:")
    print("-" * 50)
    
    model_files, scaler_files = check_model_files()
    
    for model_type, files in model_files.items():
        if files:
            print(f"\n{model_type.upper()} Models:")
            for file in files:
                print(f"  📄 {file}")
    
    if scaler_files:
        print(f"\nScalers:")
        for file in scaler_files:
            print(f"  📄 {file}")
    
    # Model performance summary (if available)
    print("\n📊 MODEL PERFORMANCE SUMMARY:")
    print("-" * 50)
    
    # Try to load and display model info
    for model_type in ['lstm', 'xgboost', 'ensemble']:
        for target_type in ['dwell_time', 'demand_level']:
            info_path = f'{MODELS_DIR}/{model_type}/{model_type}_{target_type}_info.pkl'
            if os.path.exists(info_path):
                try:
                    model_info = joblib.load(info_path)
                    metrics = model_info.get('evaluation_metrics', {})
                    
                    if target_type == 'dwell_time':
                        rmse = metrics.get('rmse', 'N/A')
                        r2 = metrics.get('r2_score', 'N/A')
                        print(f"{model_type.upper()} {target_type}: RMSE={rmse}, R²={r2}")
                    else:
                        accuracy = metrics.get('accuracy', 'N/A')
                        print(f"{model_type.upper()} {target_type}: Accuracy={accuracy}")
                except Exception as e:
                    logging.warning(f"Could not load model info from {info_path}: {e}")
    
    print("\n" + "="*80)

def main():
    """Main training orchestration function"""
    logging.info("🚀 Starting MARTA Model Training Orchestrator")
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Check data availability
    if not check_data_availability():
        logging.error("❌ Data availability check failed. Please ensure data processing is complete.")
        return False
    
    # Run all training scripts
    results = []
    for script_config in TRAINING_SCRIPTS:
        result = run_training_script(script_config)
        result['script_name'] = script_config['name']
        results.append(result)
        
        # Add delay between scripts
        time.sleep(2)
    
    # Generate summary report
    generate_training_summary(results)
    
    # Determine overall success
    success_count = sum(1 for r in results if r['status'] == 'success')
    required_scripts = [s for s in TRAINING_SCRIPTS if s['required']]
    required_success = sum(1 for r in results[:len(required_scripts)] if r['status'] == 'success')
    
    if required_success == len(required_scripts):
        logging.info("🎉 All required model training scripts completed successfully!")
        return True
    else:
        logging.error(f"⚠️ Only {required_success}/{len(required_scripts)} required scripts succeeded")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 