# 🚇 MARTA Data Ingestion System

## Overview

This system provides comprehensive data ingestion capabilities for the MARTA Demand Forecasting & Route Optimization Platform. It automatically collects, processes, and stores data from multiple external sources to provide a rich dataset for machine learning model training.

## 📊 Data Sources

### 1. **GTFS-Realtime Data** (Real-time)
- **Source**: MARTA GTFS-RT API
- **Data**: Vehicle positions, trip updates, delays
- **Frequency**: Every 30 seconds
- **Tables**: `gtfs_vehicle_positions`, `gtfs_trip_updates`

### 2. **Ridership KPI Data** (Monthly)
- **Source**: MARTA KPI Reports (https://itsmarta.com/KPIRidership.aspx)
- **Data**: Monthly ridership metrics by mode
- **Frequency**: Monthly updates
- **Tables**: `marta_ridership_kpi`

### 3. **GIS Layers** (Static)
- **Source**: Atlanta Regional Commission Open Data
- **Data**: Station locations, route geometries
- **Frequency**: As needed
- **Tables**: `marta_gis_layers`

### 4. **Weather Data** (Real-time + Historical)
- **Source**: OpenWeatherMap API
- **Data**: Temperature, precipitation, conditions
- **Frequency**: Current + 5 days historical
- **Tables**: `atlanta_weather_data`

### 5. **Event Data** (Scheduled)
- **Source**: Major venue websites
- **Data**: Sports events, concerts, conferences
- **Frequency**: Daily updates
- **Tables**: `atlanta_events_data`

## 🛠️ Installation & Setup

### 1. Install Dependencies

```bash
# Core dependencies
pip install pandas psycopg2-binary requests beautifulsoup4

# GTFS-Realtime support
pip install gtfs-realtime-bindings

# GIS support
pip install fiona shapely

# Weather API support
pip install requests

# Already installed: folium streamlit-folium plotly
```

### 2. Set Environment Variables

```bash
# Database Configuration
export DB_HOST=localhost
export DB_NAME=marta_db
export DB_USER=marta_user
export DB_PASSWORD=marta_password

# API Keys (Optional - scripts will use sample data if not provided)
export MARTA_API_KEY=your_marta_api_key
export OPENWEATHER_API_KEY=your_openweather_api_key
```

### 3. Database Setup

Ensure your PostgreSQL database is running and accessible with the credentials above. The scripts will automatically create required tables.

## 🚀 Running the System

### Option 1: Run All Ingestion Scripts (Recommended)

```bash
python3 run_data_ingestion.py
```

This will:
- Check environment variables
- Run all ingestion scripts in sequence
- Generate a comprehensive summary report
- Handle errors gracefully

### Option 2: Run Individual Scripts

```bash
# GTFS-Realtime (continuous stream)
python3 src/data_ingestion/gtfs_realtime_ingestion.py

# Ridership KPI Data
python3 src/data_ingestion/ridership_kpi_scraper.py

# GIS Layers
python3 src/data_ingestion/gis_layers_ingestion.py

# Weather Data
python3 src/data_ingestion/weather_data_fetcher.py

# Event Data
python3 src/data_ingestion/event_data_scraper.py
```

### Option 3: Master Orchestrator

```bash
python3 src/data_ingestion/master_ingestion_orchestrator.py
```

## 📁 File Structure

```
src/data_ingestion/
├── gtfs_realtime_ingestion.py      # Real-time vehicle & trip data
├── ridership_kpi_scraper.py        # Monthly ridership metrics
├── gis_layers_ingestion.py         # Geographic data
├── weather_data_fetcher.py         # Weather data
├── event_data_scraper.py           # Event schedules
└── master_ingestion_orchestrator.py # Orchestrates all scripts

data/external/                      # Output CSV files
├── marta_ridership_kpi.csv
├── atlanta_weather_data.csv
└── atlanta_events_data.csv

data/gis/                          # GIS data files
├── marta_rail_stations.geojson
└── marta_bus_stops.geojson

logs/                              # Log files
└── data_ingestion.log
```

## 📊 Database Schema

### GTFS-Realtime Tables

```sql
-- Vehicle positions
CREATE TABLE gtfs_vehicle_positions (
    id TEXT,
    trip_id TEXT,
    route_id TEXT,
    vehicle_id TEXT,
    latitude NUMERIC,
    longitude NUMERIC,
    bearing NUMERIC,
    speed NUMERIC,
    timestamp TIMESTAMP,
    current_status TEXT
);

-- Trip updates
CREATE TABLE gtfs_trip_updates (
    id TEXT,
    trip_id TEXT,
    route_id TEXT,
    direction_id INTEGER,
    start_time TEXT,
    start_date TEXT,
    timestamp TIMESTAMP,
    stop_id TEXT,
    stop_sequence INTEGER,
    arrival_delay INTEGER,
    arrival_time TIMESTAMP,
    departure_delay INTEGER,
    departure_time TIMESTAMP
);
```

### External Data Tables

```sql
-- Ridership KPI
CREATE TABLE marta_ridership_kpi (
    report_month TEXT,
    bus_ridership BIGINT,
    rail_ridership BIGINT,
    mobility_ridership BIGINT,
    total_ridership BIGINT
);

-- GIS Layers
CREATE TABLE marta_gis_layers (
    id SERIAL PRIMARY KEY,
    layer_name TEXT,
    feature_id TEXT,
    feature_name TEXT,
    feature_type TEXT,
    properties JSONB,
    geom GEOMETRY(GEOMETRY, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Weather Data
CREATE TABLE atlanta_weather_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    temperature_celsius NUMERIC,
    feels_like_celsius NUMERIC,
    humidity INTEGER,
    pressure_hpa NUMERIC,
    wind_speed_mps NUMERIC,
    wind_direction_degrees INTEGER,
    weather_condition TEXT,
    weather_description TEXT,
    precipitation_mm NUMERIC,
    visibility_meters INTEGER,
    cloudiness_percent INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event Data
CREATE TABLE atlanta_events_data (
    id SERIAL PRIMARY KEY,
    venue_name TEXT,
    event_name TEXT,
    event_date DATE,
    event_time TIME,
    event_type TEXT,
    event_description TEXT,
    venue_lat NUMERIC,
    venue_lon NUMERIC,
    estimated_attendance INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Configuration

### API Keys

- **MARTA API Key**: Required for GTFS-Realtime data
  - Get from: https://itsmarta.com/app-developer-resources.aspx
- **OpenWeatherMap API Key**: Optional for weather data
  - Get from: https://openweathermap.org/api

### Database Configuration

All scripts use environment variables for database connection:
- `DB_HOST`: Database host (default: localhost)
- `DB_NAME`: Database name (default: marta_db)
- `DB_USER`: Database user (default: marta_user)
- `DB_PASSWORD`: Database password

### Logging

All scripts log to both console and file:
- Console: Real-time progress
- File: `logs/data_ingestion.log`

## 🚨 Error Handling

### Graceful Degradation

- **Missing API Keys**: Scripts generate sample data
- **Network Issues**: Retry logic with exponential backoff
- **Database Errors**: Detailed error logging
- **Missing Tables**: Auto-creation of required tables

### Sample Data Generation

When external sources are unavailable, scripts generate realistic sample data:
- Weather: Historical patterns for Atlanta
- Events: Scheduled events for major venues
- Ridership: Monthly patterns based on typical MARTA data

## 📈 Monitoring & Maintenance

### Data Quality Checks

- Timestamp validation
- Geographic coordinate validation
- Data type consistency
- Missing value handling

### Performance Optimization

- Batch database inserts
- Connection pooling
- Rate limiting for APIs
- Efficient data structures

### Log Analysis

Monitor `logs/data_ingestion.log` for:
- Success/failure rates
- Data volume trends
- Error patterns
- Performance metrics

## 🔄 Scheduling

### Automated Execution

For production use, schedule the orchestrator:

```bash
# Cron job for daily execution
0 2 * * * cd /path/to/marta && python3 run_data_ingestion.py

# Or use systemd timer for more control
```

### Real-time GTFS-RT

For continuous real-time data:

```bash
# Run in background
nohup python3 src/data_ingestion/gtfs_realtime_ingestion.py &

# Or use systemd service
```

## 🎯 Next Steps

1. **Set up API keys** for real data collection
2. **Configure database** with proper credentials
3. **Run initial ingestion** to populate all tables
4. **Monitor logs** for any issues
5. **Schedule regular execution** for ongoing data collection
6. **Integrate with ML pipeline** for model training

## 📞 Support

For issues or questions:
1. Check the logs in `logs/data_ingestion.log`
2. Verify environment variables are set correctly
3. Ensure database is accessible
4. Check API key validity (if using real data sources)

---

**Status**: ✅ Complete and Ready for Production Use 