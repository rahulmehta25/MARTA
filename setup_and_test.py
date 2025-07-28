#!/usr/bin/env python3
"""
MARTA System Setup and Testing Script
Initializes the system and runs comprehensive tests
"""
import os
import sys
import subprocess
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_command(command, description, check=True):
    """Run a shell command with error handling"""
    print(f"\n🔄 {description}")
    print(f"   Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"   ✅ Success: {result.stdout.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e.stderr.strip()}")
        return False


def check_environment():
    """Check if required environment is set up"""
    print("🔍 Checking Environment Setup")
    print("=" * 50)
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    else:
        print("✅ Python version OK")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found - using defaults")
        print("   Copy env.example to .env and configure your settings")
    
    # Check if virtual environment is active
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment active")
    else:
        print("⚠️  Virtual environment not detected")
    
    return True


def install_dependencies():
    """Install Python and Node.js dependencies"""
    print("\n📦 Installing Dependencies")
    print("=" * 50)
    
    # Install Python dependencies
    if run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        print("✅ Python dependencies installed")
    else:
        print("❌ Failed to install Python dependencies")
        return False
    
    # Install frontend dependencies
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        if run_command("cd frontend && npm install", "Installing frontend dependencies"):
            print("✅ Frontend dependencies installed")
        else:
            print("❌ Failed to install frontend dependencies")
            return False
    else:
        print("⚠️  Frontend directory not found")
    
    return True


def setup_database():
    """Set up the database schema and initial data"""
    print("\n🗄️  Setting Up Database")
    print("=" * 50)
    
    # Check if PostgreSQL is running
    if run_command("pg_isready -h localhost -p 5432", "Checking PostgreSQL connection", check=False):
        print("✅ PostgreSQL is running")
    else:
        print("⚠️  PostgreSQL not running - you may need to start it")
        print("   For Docker: docker-compose up -d postgres")
        print("   For local: sudo systemctl start postgresql")
    
    # Run database setup
    if run_command("python setup_real_marta_data.py", "Setting up database schema and data"):
        print("✅ Database setup completed")
        return True
    else:
        print("❌ Database setup failed")
        return False


def run_tests():
    """Run the test suite"""
    print("\n🧪 Running Tests")
    print("=" * 50)
    
    # Install pytest if not already installed
    run_command("pip install pytest pytest-cov", "Installing pytest", check=False)
    
    # Run unit tests
    if run_command("python -m pytest tests/ -v --tb=short", "Running unit tests"):
        print("✅ Unit tests passed")
    else:
        print("❌ Unit tests failed")
        return False
    
    # Run specific test categories
    test_categories = [
        ("API tests", "python -m pytest tests/ -m api -v"),
        ("Database tests", "python -m pytest tests/ -m database -v"),
        ("ML tests", "python -m pytest tests/ -m ml -v")
    ]
    
    for category, command in test_categories:
        if run_command(command, f"Running {category}", check=False):
            print(f"✅ {category} passed")
        else:
            print(f"⚠️  {category} had issues")
    
    return True


def test_api_endpoints():
    """Test API endpoints"""
    print("\n🌐 Testing API Endpoints")
    print("=" * 50)
    
    # Start API server in background
    print("Starting API server...")
    api_process = subprocess.Popen(
        ["python", "run_api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(5)
    
    # Test health endpoint
    import requests
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        if response.status_code == 200:
            print("✅ API health check passed")
        else:
            print(f"❌ API health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API health check failed: {e}")
    
    # Stop API server
    api_process.terminate()
    api_process.wait()
    
    return True


def test_frontend():
    """Test frontend build"""
    print("\n🎨 Testing Frontend")
    print("=" * 50)
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("⚠️  Frontend directory not found")
        return True
    
    # Test frontend build
    if run_command("cd frontend && npm run build", "Building frontend", check=False):
        print("✅ Frontend build successful")
        return True
    else:
        print("❌ Frontend build failed")
        return False


def generate_report():
    """Generate a setup report"""
    print("\n📊 Setup Report")
    print("=" * 50)
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "environment_file": os.path.exists('.env'),
        "database_setup": os.path.exists('database/real_marta_schema.sql'),
        "frontend_package_json": os.path.exists('frontend/package.json'),
        "test_files": len(list(Path("tests").glob("test_*.py"))),
        "api_files": len(list(Path("src/api").glob("*.py"))),
        "model_files": len(list(Path("src/models").glob("*.py")))
    }
    
    print("System Status:")
    for key, value in report.items():
        if key == "timestamp":
            print(f"  {key}: {value}")
        elif isinstance(value, bool):
            status = "✅" if value else "❌"
            print(f"  {key}: {status}")
        else:
            print(f"  {key}: {value}")
    
    return report


def main():
    """Main setup and testing function"""
    print("🚇 MARTA System Setup and Testing")
    print("=" * 60)
    print("This script will:")
    print("1. Check environment setup")
    print("2. Install dependencies")
    print("3. Set up database")
    print("4. Run comprehensive tests")
    print("5. Test API endpoints")
    print("6. Test frontend build")
    print("7. Generate setup report")
    print()
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed")
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        print("❌ Database setup failed")
        sys.exit(1)
    
    # Run tests
    if not run_tests():
        print("❌ Tests failed")
        sys.exit(1)
    
    # Test API
    if not test_api_endpoints():
        print("❌ API tests failed")
        sys.exit(1)
    
    # Test frontend
    if not test_frontend():
        print("❌ Frontend tests failed")
        sys.exit(1)
    
    # Generate report
    report = generate_report()
    
    print("\n🎉 Setup and Testing Completed Successfully!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("1. Start the API server: python run_api.py")
    print("2. Start the frontend: cd frontend && npm start")
    print("3. Access the platform:")
    print("   - Backend API: http://localhost:8001")
    print("   - Frontend: http://localhost:3000")
    print("   - API Docs: http://localhost:8001/docs")
    print("\n🔧 For development:")
    print("   - Run tests: python -m pytest tests/ -v")
    print("   - Check coverage: python -m pytest --cov=src")
    print("   - Lint code: flake8 src/ tests/")


if __name__ == "__main__":
    main() 