#!/bin/bash
# Quick fix for Streamlit environment issues
# This script ensures all required packages are installed in the current environment

echo "🔧 Fixing Streamlit Environment Dependencies"
echo "=========================================="

# Install core dashboard dependencies
echo "📦 Installing dashboard dependencies..."
pip install folium streamlit-folium plotly psycopg2-binary

# Install additional dependencies that might be missing
echo "📦 Installing additional dependencies..."
pip install pandas numpy requests

echo "✅ Environment fix complete!"
echo ""
echo "You can now run:"
echo "  streamlit run src/visualization/demo_dashboard.py"
echo ""
echo "The dashboard should be available at:"
echo "  http://localhost:8501" 