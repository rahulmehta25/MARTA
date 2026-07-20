#!/bin/bash
# MARTA Platform Environment Setup Script
# This script helps set up the correct environment for the MARTA platform

echo "🚇 MARTA Demand Forecasting Platform - Environment Setup"
echo "=================================================="

# Check if we're in the correct directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found. Please run this script from the MARTA project root."
    exit 1
fi

# Check if virtual environment exists
if [ -d "marta_env" ]; then
    echo "✅ Found marta_env virtual environment"
    echo "Activating marta_env..."
    source marta_env/bin/activate
    ENV_NAME="marta_env"
elif [ -d ".venv" ]; then
    echo "✅ Found .venv virtual environment"
    echo "Activating .venv..."
    source .venv/bin/activate
    ENV_NAME=".venv"
else
    echo "❌ No virtual environment found. Creating marta_env..."
    python3 -m venv marta_env
    source marta_env/bin/activate
    ENV_NAME="marta_env"
fi

echo "📦 Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🔧 Installing additional dashboard dependencies..."
pip install folium streamlit-folium plotly psycopg2-binary

echo "✅ Environment setup complete!"
echo ""
echo "To activate the environment in the future:"
echo "  source $ENV_NAME/bin/activate"
echo ""
echo "To run the demo platform:"
echo "  python demo_platform.py"
echo ""
echo "To run the dashboard:"
echo "  streamlit run src/visualization/demo_dashboard.py"
echo ""
echo "To run the test system:"
echo "  python test_system.py" 