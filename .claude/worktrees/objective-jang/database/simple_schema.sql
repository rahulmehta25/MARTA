-- Simplified MARTA Demo Schema - Focus on Core GTFS Tables
-- This schema prioritizes demo functionality over complete GTFS compliance

-- Stops table
CREATE TABLE IF NOT EXISTS gtfs_stops (
    stop_id VARCHAR(255) PRIMARY KEY,
    stop_name VARCHAR(255),
    stop_lat NUMERIC,
    stop_lon NUMERIC,
    zone_id VARCHAR(255)
);

-- Routes table  
CREATE TABLE IF NOT EXISTS gtfs_routes (
    route_id VARCHAR(255) PRIMARY KEY,
    route_short_name VARCHAR(255),
    route_long_name VARCHAR(255),
    route_type INTEGER
);

-- Trips table
CREATE TABLE IF NOT EXISTS gtfs_trips (
    trip_id VARCHAR(255) PRIMARY KEY,
    route_id VARCHAR(255) REFERENCES gtfs_routes(route_id),
    service_id VARCHAR(255),
    direction_id INTEGER
);

-- Stop times table
CREATE TABLE IF NOT EXISTS gtfs_stop_times (
    id SERIAL PRIMARY KEY,
    trip_id VARCHAR(255) REFERENCES gtfs_trips(trip_id),
    stop_id VARCHAR(255) REFERENCES gtfs_stops(stop_id),
    stop_sequence INTEGER,
    arrival_time TIME,
    departure_time TIME
);

-- Unified real-time data table (for demo)
CREATE TABLE IF NOT EXISTS unified_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    trip_id VARCHAR(255),
    stop_id VARCHAR(255),
    route_id VARCHAR(255),
    vehicle_id VARCHAR(255),
    latitude NUMERIC,
    longitude NUMERIC,
    scheduled_arrival TIMESTAMP,
    actual_arrival TIMESTAMP,
    delay_minutes NUMERIC,
    dwell_time_seconds NUMERIC,
    inferred_demand_level VARCHAR(50),
    weather_condition VARCHAR(100),
    temperature_celsius NUMERIC,
    event_flag BOOLEAN,
    day_of_week VARCHAR(20),
    hour_of_day INTEGER,
    is_weekend BOOLEAN
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_stop_times_trip_id ON gtfs_stop_times(trip_id);
CREATE INDEX IF NOT EXISTS idx_stop_times_stop_id ON gtfs_stop_times(stop_id);
CREATE INDEX IF NOT EXISTS idx_unified_timestamp ON unified_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_unified_stop_id ON unified_data(stop_id); 