#!/usr/bin/env python3
"""
MARTA Optimization API Runner
Starts the REST API server for optimization services
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Main API runner function"""
    print("🚇 MARTA Optimization API Server")
    print("=" * 50)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('src/api/optimization_api.py'):
        print("❌ Error: Please run this script from the MARTA project root directory")
        sys.exit(1)
    
    # Check environment variables
    required_env_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️ Warning: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Using default values. Set environment variables for production use.")
        print()
    
    # Import and run the API
    try:
        from src.api.optimization_api import main as run_api
        print("✅ API components loaded successfully")
        print("🌐 Starting API server on http://localhost:8001")
        print("📚 API documentation available at http://localhost:8001/docs")
        print("🔍 Health check available at http://localhost:8001/health")
        print()
        print("Press Ctrl+C to stop the server")
        print("-" * 50)
        
        run_api()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed:")
        print("   pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 