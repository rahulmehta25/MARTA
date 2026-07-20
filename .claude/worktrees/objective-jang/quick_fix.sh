#!/bin/bash

echo "🚇 MARTA Quick Fix & Run"
echo "========================"

# Kill any existing processes
pkill -f "python3 run_api.py" 2>/dev/null

# Activate virtual environment
source marta_venv/bin/activate

# Install essential missing dependencies
echo "📦 Installing missing dependencies..."
pip install -q simpy pulp ortools
pip install -q gevent streamlit streamlit-folium
pip install -q plotly matplotlib seaborn
pip install -q prometheus-client structlog

# Set basic environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=marta_db
export DB_USER=postgres
export DB_PASSWORD=postgres
export USE_SYNTHETIC_DATA=true

echo ""
echo "✅ Dependencies installed!"
echo ""
echo "Starting API server on http://localhost:8001"
echo "============================================="
python3 run_api.py