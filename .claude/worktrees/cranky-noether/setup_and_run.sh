#!/bin/bash

echo "🚇 MARTA Platform Setup & Run Script"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "marta_venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv marta_venv
fi

# Activate virtual environment
source marta_venv/bin/activate

# Install core dependencies
echo "📚 Installing core dependencies..."
pip install -q joblib scipy networkx scikit-learn
pip install -q fastapi uvicorn pandas numpy sqlalchemy psycopg2-binary
pip install -q python-dotenv requests gtfs-kit haversine folium
pip install -q asyncpg redis aioredis

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=marta_db
DB_USER=postgres
DB_PASSWORD=postgres

# API Configuration
API_PORT=8001
API_HOST=0.0.0.0

# Frontend Configuration
FRONTEND_URL=http://localhost:5173

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Feature Flags
USE_SYNTHETIC_DATA=false
ENABLE_CACHING=true
EOF
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Available commands:"
echo "  1. Run API Server:        python3 run_api.py"
echo "  2. Run Data Ingestion:    python3 run_data_ingestion.py"
echo "  3. Run Tests:             python3 run_tests.py"
echo "  4. Run Demo Platform:     python3 demo_platform.py"
echo ""
echo "Starting API server..."
echo "======================================"
python3 run_api.py