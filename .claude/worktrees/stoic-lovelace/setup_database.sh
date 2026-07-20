#!/bin/bash
# MARTA Database Setup Script
# This script helps set up PostgreSQL database for the MARTA platform

echo "🚇 MARTA Database Setup"
echo "======================"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install PostgreSQL first:"
    echo "   Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib postgis"
    echo "   macOS: brew install postgresql postgis"
    echo "   Windows: Download from https://www.postgresql.org/download/"
    exit 1
fi

# Check if we're in the correct directory
if [ ! -f "database/schema.sql" ]; then
    echo "❌ Error: database/schema.sql not found. Please run this script from the MARTA project root."
    exit 1
fi

echo "📋 Setting up MARTA database..."

# Create database and user
echo "Creating database and user..."
sudo -u postgres psql << EOF
CREATE DATABASE marta_db;
CREATE USER marta_user WITH PASSWORD 'marta_password';
GRANT ALL PRIVILEGES ON DATABASE marta_db TO marta_user;
\c marta_db
CREATE EXTENSION IF NOT EXISTS postgis;
GRANT ALL ON SCHEMA public TO marta_user;
EOF

echo "📊 Loading schema..."
psql -h localhost -U marta_user -d marta_db -f database/schema.sql

echo "✅ Database setup complete!"
echo ""
echo "Database connection details:"
echo "  Host: localhost"
echo "  Database: marta_db"
echo "  User: marta_user"
echo "  Password: marta_password"
echo ""
echo "To test the connection:"
echo "  psql -h localhost -U marta_user -d marta_db"
echo ""
echo "To run the API server:"
echo "  python3 run_api.py" 