#!/usr/bin/env python3
"""
MARTA Model Training Runner
Simple script to run all ML model training workflows
"""
import os
import sys
import subprocess

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables before running:")
        print("export DB_HOST=localhost")
        print("export DB_NAME=marta_db")
        print("export DB_USER=marta_user")
        print("export DB_PASSWORD=marta_password")
        return False
    
    return True

def check_dependencies():
    """Check if required ML libraries are installed"""
    required_packages = [
        'tensorflow',
        'xgboost',
        'scikit-learn',
        'joblib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required Python packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nPlease install missing packages:")
        print("pip install tensorflow xgboost scikit-learn joblib")
        return False
    
    return True

def main():
    print("🚇 MARTA Model Training Runner")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("✅ Environment and dependencies check passed")
    print("🚀 Starting model training...")
    print()
    
    # Run the training orchestrator
    try:
        result = subprocess.run([
            sys.executable, 'src/models/model_training_orchestrator.py'
        ], check=True)
        
        print("\n🎉 Model training completed successfully!")
        print("\n📁 Trained models are available in the 'models/' directory:")
        print("   - models/lstm/     (LSTM models)")
        print("   - models/xgboost/  (XGBoost models)")
        print("   - models/ensemble/ (Ensemble models)")
        print("   - models/scalers/  (Data scalers)")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Model training failed with exit code {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Model training interrupted by user")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 