#!/bin/bash

# MARTA Quick Start Script
# This script sets up the MARTA system for immediate use

set -e  # Exit on any error

echo "🚇 MARTA Quick Start"
echo "===================="
echo "This script will set up your MARTA system for development"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the MARTA project root directory"
    exit 1
fi

# Step 1: Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_version="3.8.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_success "Python $python_version is compatible"
else
    print_error "Python 3.8+ is required. Found: $python_version"
    exit 1
fi

# Step 2: Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    if [ -f "env.example" ]; then
        cp env.example .env
        print_success ".env file created from template"
        print_warning "Please edit .env file with your actual API keys"
    else
        print_warning "No env.example found, creating basic .env file"
        cat > .env << EOF
# MARTA Configuration
DB_HOST=localhost
DB_NAME=marta_db
DB_USER=marta_user
DB_PASSWORD=marta_password
DB_PORT=5432

# API Keys (replace with your actual keys)
MARTA_API_KEY=your_marta_api_key_here
OPENWEATHER_API_KEY=your_openweather_api_key_here

# Development settings
DEBUG=True
ENVIRONMENT=development
EOF
        print_success "Basic .env file created"
    fi
else
    print_success ".env file already exists"
fi

# Step 3: Install Python dependencies
print_status "Installing Python dependencies..."
# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_status "Using virtual environment: $VIRTUAL_ENV"
    if "$VIRTUAL_ENV/bin/pip" install -r requirements.txt; then
        print_success "Python dependencies installed"
    else
        print_error "Failed to install Python dependencies"
        exit 1
    fi
else
    print_warning "No virtual environment detected"
    print_warning "Please activate your virtual environment first:"
    print_warning "  source marta_env_tf/bin/activate"
    exit 1
fi

# Step 4: Install frontend dependencies
if [ -d "frontend" ]; then
    print_status "Installing frontend dependencies..."
    cd frontend
    if npm install; then
        print_success "Frontend dependencies installed"
    else
        print_warning "Failed to install frontend dependencies"
        print_warning "You may need to install Node.js and npm"
    fi
    cd ..
else
    print_warning "Frontend directory not found"
fi

# Step 5: Check if PostgreSQL is running
print_status "Checking PostgreSQL connection..."
if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        print_success "PostgreSQL is running"
    else
        print_warning "PostgreSQL is not running"
        print_warning "You may need to start PostgreSQL or use Docker"
        echo "To start with Docker: docker-compose up -d postgres"
        echo "To start locally: sudo systemctl start postgresql"
    fi
else
    print_warning "pg_isready not found - cannot check PostgreSQL"
fi

# Step 6: Run database setup (if PostgreSQL is available)
print_status "Setting up database..."
if "$VIRTUAL_ENV/bin/python" setup_real_marta_data.py; then
    print_success "Database setup completed"
else
    print_warning "Database setup failed - you may need to start PostgreSQL first"
fi

# Step 6.5: Run basic tests
print_status "Running basic tests..."
if "$VIRTUAL_ENV/bin/python" -m pytest tests/ -v --tb=short -q; then
    print_success "Basic tests passed"
else
    print_warning "Some tests failed - this is normal for initial setup"
fi

# Step 7: Create necessary directories
print_status "Creating necessary directories..."
mkdir -p data/raw data/processed data/external logs models
print_success "Directories created"

# Step 8: Generate setup report
print_status "Generating setup report..."
"$VIRTUAL_ENV/bin/python" setup_and_test.py --report-only 2>/dev/null || echo "Setup report generation skipped"

echo ""
echo "🎉 Quick Start Setup Complete!"
echo "=============================="
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file with your API keys:"
echo "   - MARTA_API_KEY: Get from https://itsmarta.com/app-developer-resources.aspx"
echo "   - OPENWEATHER_API_KEY: Get from https://openweathermap.org/api"
echo ""
echo "2. Start the services:"
echo "   - API Server: python run_api.py"
echo "   - Frontend: cd frontend && npm start"
echo "   - Streamlit Dashboard: streamlit run src/visualization/demo_dashboard.py"
echo ""
echo "3. Access the platform:"
echo "   - Backend API: http://localhost:8001"
echo "   - Frontend: http://localhost:3000"
echo "   - API Docs: http://localhost:8001/docs"
echo "   - Dashboard: http://localhost:8501"
echo ""
echo "🔧 Development Commands:"
echo "   - Run tests: python -m pytest tests/ -v"
echo "   - Check coverage: python -m pytest --cov=src"
echo "   - Lint code: flake8 src/ tests/"
echo ""
echo "📚 Documentation:"
echo "   - README.md: Main documentation"
echo "   - API Integration Requirements.md: API details"
echo "   - Technical Implementation Guide.md: Technical details"
echo ""
print_success "MARTA system is ready for development!" 