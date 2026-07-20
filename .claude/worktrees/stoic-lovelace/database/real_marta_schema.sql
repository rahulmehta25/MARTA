-- Real MARTA Data Schema
-- Additional tables for comprehensive MARTA data ingestion

-- Ridership Metrics Table
CREATE TABLE IF NOT EXISTS ridership_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_boardings INTEGER,
    rail_boardings INTEGER,
    bus_boardings INTEGER,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GIS Stations Table (with PostGIS geometry)
CREATE TABLE IF NOT EXISTS gis_stations (
    station_id VARCHAR(255) PRIMARY KEY,
    station_name VARCHAR(255),
    geom GEOMETRY(Point, 4326),
    zone_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Weather Data Table
CREATE TABLE IF NOT EXISTS weather_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    temperature NUMERIC(5,2),
    humidity INTEGER,
    weather_condition VARCHAR(100),
    precipitation NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event Data Table
CREATE TABLE IF NOT EXISTS event_data (
    event_id VARCHAR(255) PRIMARY KEY,
    event_name VARCHAR(255),
    venue VARCHAR(255),
    date DATE,
    latitude NUMERIC(10,8),
    longitude NUMERIC(11,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhanced Unified Data Table (if not exists)
CREATE TABLE IF NOT EXISTS unified_data_enhanced (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    trip_id VARCHAR(255),
    route_id VARCHAR(255),
    stop_id VARCHAR(255),
    vehicle_id VARCHAR(255),
    latitude NUMERIC(10,8),
    longitude NUMERIC(11,8),
    bearing NUMERIC(5,2),
    speed NUMERIC(5,2),
    arrival_delay INTEGER,
    departure_delay INTEGER,
    dwell_time_seconds INTEGER,
    inferred_demand_level VARCHAR(50),
    weather_condition VARCHAR(100),
    temperature NUMERIC(5,2),
    precipitation NUMERIC(5,2),
    event_flag BOOLEAN DEFAULT FALSE,
    day_of_week VARCHAR(20),
    hour_of_day INTEGER,
    is_weekend BOOLEAN,
    zone_id VARCHAR(100),
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ridership_metrics_date ON ridership_metrics(date);
CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_event_data_date ON event_data(date);
CREATE INDEX IF NOT EXISTS idx_unified_data_enhanced_timestamp ON unified_data_enhanced(timestamp);
CREATE INDEX IF NOT EXISTS idx_unified_data_enhanced_stop_id ON unified_data_enhanced(stop_id);
CREATE INDEX IF NOT EXISTS idx_unified_data_enhanced_route_id ON unified_data_enhanced(route_id);

-- Spatial index for GIS stations
CREATE INDEX IF NOT EXISTS idx_gis_stations_geom ON gis_stations USING GIST(geom);

-- Comments for documentation
COMMENT ON TABLE ridership_metrics IS 'Monthly ridership metrics from MARTA KPI reports';
COMMENT ON TABLE gis_stations IS 'MARTA station locations with GIS geometry from Atlanta Regional Commission';
COMMENT ON TABLE weather_data IS 'Weather data from OpenWeatherMap API for Atlanta';
COMMENT ON TABLE event_data IS 'Event data from major venues in Atlanta';
COMMENT ON TABLE unified_data_enhanced IS 'Enhanced unified dataset combining all data sources'; 