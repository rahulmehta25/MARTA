#!/usr/bin/env python3
"""
MARTA Data Ingestion Runner
Simple script to run all data ingestion processes
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

def main():
    print("🚇 MARTA Data Ingestion Runner")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("✅ Environment check passed")
    print("🚀 Starting data ingestion...")
    print()
    
    # Run the master orchestrator
    try:
        result = subprocess.run([
            sys.executable, 'src/data_ingestion/master_ingestion_orchestrator.py'
        ], check=True)
        
        print("\n🎉 Data ingestion completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Data ingestion failed with exit code {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Data ingestion interrupted by user")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 