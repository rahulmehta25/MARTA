#!/bin/bash

# MARTA Development Startup Script
# This script sets up and starts the MARTA development environment

set -e  # Exit on any error

echo "🚇 MARTA Development Environment"
echo "================================"
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
if [ ! -f "requirements.txt" ] || [ ! -f "frontend/package.json" ]; then
    print_error "Please run this script from the MARTA project root directory"
    exit 1
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "No virtual environment detected"
    print_warning "Please activate your virtual environment first:"
    print_warning "  source marta_env_new/bin/activate"
    exit 1
fi

print_status "Setting up frontend dependencies..."

# Install frontend dependencies
cd frontend
if [ ! -d "node_modules" ]; then
    print_status "Installing frontend dependencies (this may take a few minutes)..."
    npm install
    print_success "Frontend dependencies installed"
else
    print_success "Frontend dependencies already installed"
fi

cd ..

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p data/raw data/processed data/external logs models
print_success "Directories created"

# Function to start backend API
start_backend() {
    print_status "Starting backend API server..."
    python run_api.py &
    BACKEND_PID=$!
    print_success "Backend API started (PID: $BACKEND_PID)"
    
    # Wait for backend to start
    sleep 5
    
    # Test backend health
    if curl -s http://localhost:8001/health > /dev/null; then
        print_success "Backend API is healthy"
    else
        print_warning "Backend API may not be fully ready yet"
    fi
}

# Function to start frontend
start_frontend() {
    print_status "Starting frontend development server..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    print_success "Frontend started (PID: $FRONTEND_PID)"
}

# Function to cleanup on exit
cleanup() {
    print_status "Shutting down development servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        print_status "Backend API stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_status "Frontend stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start services
start_backend
start_frontend

echo ""
print_success "🎉 MARTA Development Environment is ready!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8001"
echo "📚 API Docs: http://localhost:8001/docs"
echo "🔍 Health Check: http://localhost:8001/health"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user to stop
wait 