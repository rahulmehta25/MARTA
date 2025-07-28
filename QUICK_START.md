# 🚇 MARTA Platform - Quick Start Guide

This guide will help you get the MARTA platform up and running quickly with the new Lovable UI integration.

## 🎯 What You'll Get

- **Modern React Frontend**: Beautiful, responsive UI with real-time transit data
- **Python Backend API**: FastAPI-based optimization and simulation services
- **PostgreSQL Database**: Geospatial data storage with PostGIS
- **Machine Learning Models**: Demand forecasting and route optimization
- **Real-time Features**: Live transit updates and interactive maps

## 📋 Prerequisites

- **Python 3.8+** (Python 3.11 recommended)
- **Node.js 18+** (for frontend development)
- **PostgreSQL 12+** with PostGIS extension
- **Git** (for version control)

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
# Install PostgreSQL and PostGIS (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib postgis

# Or on macOS
brew install postgresql postgis
```

### 2. Set Up Environment

```bash
# Run the environment setup script
./setup_environment.sh

# Set up the database
./setup_database.sh
```

### 3. Start the System

```bash
# Start the full development environment
./start_development.sh
```

This will start:
- **Backend API** on http://localhost:8001
- **Frontend** on http://localhost:5173
- **API Documentation** on http://localhost:8001/docs

## 🔧 Manual Setup (if scripts don't work)

### Backend Setup

```bash
# Create virtual environment
python3 -m venv marta_env
source marta_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DB_HOST=localhost
export DB_NAME=marta_db
export DB_USER=marta_user
export DB_PASSWORD=marta_password

# Start API server
python3 run_api.py
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 🗄️ Database Setup

If the database setup script doesn't work, manually create the database:

```sql
-- Connect as postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE marta_db;
CREATE USER marta_user WITH PASSWORD 'marta_password';
GRANT ALL PRIVILEGES ON DATABASE marta_db TO marta_user;

-- Connect to the database
\c marta_db

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Grant permissions
GRANT ALL ON SCHEMA public TO marta_user;

-- Load schema
\q

-- Load the schema file
psql -h localhost -U marta_user -d marta_db -f database/schema.sql
```

## 🧪 Testing the System

### 1. Check API Health

Visit http://localhost:8001/health to verify the API is running.

### 2. Test Frontend

Visit http://localhost:5173 to see the new UI.

### 3. Test API Endpoints

```bash
# Health check
curl http://localhost:8001/health

# Get routes
curl http://localhost:8001/routes

# Get stops
curl http://localhost:8001/stops
```

## 🐛 Troubleshooting

### Common Issues

1. **"No module named 'joblib'"**
   ```bash
   pip install joblib scipy networkx
   ```

2. **PostgreSQL connection failed**
   - Check if PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify database exists: `psql -h localhost -U marta_user -d marta_db`

3. **Frontend won't start**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run dev
   ```

4. **Port already in use**
   - Kill processes: `lsof -ti:8001 | xargs kill -9`
   - Or change ports in the configuration files

### Environment Variables

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_NAME=marta_db
DB_USER=marta_user
DB_PASSWORD=marta_password
API_HOST=0.0.0.0
API_PORT=8001
FRONTEND_PORT=5173
```

## 📊 What's Available

### Frontend Features
- **Interactive Transit Map**: Real-time bus locations and routes
- **Analytics Dashboard**: Demand forecasting and performance metrics
- **Optimization Tools**: Route optimization and simulation
- **Search & Filter**: Find routes, stops, and schedules
- **Mobile Responsive**: Works on all devices

### Backend API Endpoints
- `GET /health` - System health check
- `GET /routes` - Get all transit routes
- `GET /stops` - Get all transit stops
- `POST /optimize` - Run route optimization
- `POST /simulate` - Run route simulation
- `GET /optimization-history` - Get optimization history

### Database Tables
- `gtfs_routes` - Transit route definitions
- `gtfs_stops` - Transit stop locations
- `gtfs_trips` - Trip schedules
- `gtfs_stop_times` - Stop timing data
- `optimization_results` - Optimization history
- `demand_forecasts` - ML demand predictions

## 🎉 Next Steps

1. **Explore the UI**: Navigate through the different tabs and features
2. **Test Optimization**: Try running route optimizations
3. **Add Real Data**: Import actual MARTA GTFS data
4. **Customize**: Modify the UI or add new features
5. **Deploy**: Set up for production use

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the logs in the terminal
3. Check the API documentation at http://localhost:8001/docs
4. Verify all services are running properly

---

**Happy coding! 🚇✨** 