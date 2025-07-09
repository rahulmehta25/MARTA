-- MARTA Demand Forecasting Platform Database Schema
-- GTFS Static Data Tables

-- Stops table
CREATE TABLE IF NOT EXISTS gtfs_stops (
    stop_id VARCHAR(255) PRIMARY KEY,
    stop_code VARCHAR(255),
    stop_name VARCHAR(255),
    stop_desc TEXT,
    stop_lat NUMERIC,
    stop_lon NUMERIC,
    zone_id VARCHAR(255),
    stop_url TEXT,
    location_type INTEGER,
    parent_station VARCHAR(255),
    wheelchair_boarding INTEGER,
    platform_code VARCHAR(255)
);

-- Routes table
CREATE TABLE IF NOT EXISTS gtfs_routes (
    route_id VARCHAR(255) PRIMARY KEY,
    agency_id VARCHAR(255),
    route_short_name VARCHAR(255),
    route_long_name VARCHAR(255),
    route_desc TEXT,
    route_type INTEGER,
    route_url TEXT,
    route_color VARCHAR(6),
    route_text_color VARCHAR(6),
    route_sort_order INTEGER,
    continuous_pickup INTEGER,
    continuous_dropoff INTEGER
);

-- Trips table
CREATE TABLE IF NOT EXISTS gtfs_trips (
    route_id VARCHAR(255) REFERENCES gtfs_routes(route_id),
    service_id VARCHAR(255),
    trip_id VARCHAR(255) PRIMARY KEY,
    trip_short_name VARCHAR(255),
    trip_headsign VARCHAR(255),
    direction_id INTEGER,
    block_id VARCHAR(255),
    shape_id VARCHAR(255),
    wheelchair_accessible INTEGER,
    bikes_allowed INTEGER
);

-- Stop times table
CREATE TABLE IF NOT EXISTS gtfs_stop_times (
    trip_id VARCHAR(255) REFERENCES gtfs_trips(trip_id),
    arrival_time TIME,
    departure_time TIME,
    stop_id VARCHAR(255) REFERENCES gtfs_stops(stop_id),
    stop_sequence INTEGER,
    stop_headsign VARCHAR(255),
    pickup_type INTEGER,
    drop_off_type INTEGER,
    shape_dist_traveled NUMERIC,
    timepoint INTEGER,
    PRIMARY KEY (trip_id, stop_sequence)
);

-- Calendar table
CREATE TABLE IF NOT EXISTS gtfs_calendar (
    service_id VARCHAR(255) PRIMARY KEY,
    monday BOOLEAN,
    tuesday BOOLEAN,
    wednesday BOOLEAN,
    thursday BOOLEAN,
    friday BOOLEAN,
    saturday BOOLEAN,
    sunday BOOLEAN,
    start_date DATE,
    end_date DATE
);

-- Shapes table
CREATE TABLE IF NOT EXISTS gtfs_shapes (
    shape_id VARCHAR(255),
    shape_pt_lat NUMERIC,
    shape_pt_lon NUMERIC,
    shape_pt_sequence INTEGER,
    shape_dist_traveled NUMERIC,
    PRIMARY KEY (shape_id, shape_pt_sequence)
);

-- Unified Real-time & Historical Data Table
CREATE TABLE IF NOT EXISTS unified_realtime_historical_data (
    record_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP,
    trip_id VARCHAR(255) REFERENCES gtfs_trips(trip_id),
    route_id VARCHAR(255) REFERENCES gtfs_routes(route_id),
    stop_id VARCHAR(255) REFERENCES gtfs_stops(stop_id),
    stop_sequence INTEGER,
    vehicle_id VARCHAR(255),
    latitude NUMERIC,
    longitude NUMERIC,
    scheduled_arrival_time TIMESTAMP,
    actual_arrival_time TIMESTAMP,
    scheduled_departure_time TIMESTAMP,
    actual_departure_time TIMESTAMP,
    delay_minutes NUMERIC,
    inferred_dwell_time_seconds NUMERIC,
    inferred_demand_level VARCHAR(50),
    weather_condition VARCHAR(100),
    temperature_celsius NUMERIC,
    precipitation_mm NUMERIC,
    event_flag BOOLEAN DEFAULT FALSE,
    day_of_week VARCHAR(20),
    hour_of_day INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN DEFAULT FALSE,
    zone_id VARCHAR(255),
    nearby_pois_count INTEGER,
    historical_dwell_time_avg NUMERIC,
    historical_headway_avg NUMERIC
);

-- Feature Store Table (for ML features)
CREATE TABLE IF NOT EXISTS feature_store (
    feature_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP,
    stop_id VARCHAR(255) REFERENCES gtfs_stops(stop_id),
    route_id VARCHAR(255) REFERENCES gtfs_routes(route_id),
    lag_demand_1hr NUMERIC,
    lag_demand_24hr NUMERIC,
    rolling_avg_demand_3hr NUMERIC,
    sin_hour_of_day NUMERIC,
    cos_hour_of_day NUMERIC,
    sin_day_of_week NUMERIC,
    cos_day_of_week NUMERIC,
    temperature_celsius NUMERIC,
    precipitation_mm NUMERIC,
    event_flag BOOLEAN,
    historical_dwell_time_avg NUMERIC,
    historical_headway_avg NUMERIC
);

-- Model Predictions Table
CREATE TABLE IF NOT EXISTS model_predictions (
    prediction_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP,
    stop_id VARCHAR(255) REFERENCES gtfs_stops(stop_id),
    route_id VARCHAR(255) REFERENCES gtfs_routes(route_id),
    predicted_riders INTEGER,
    demand_level VARCHAR(50),
    model_name VARCHAR(100),
    confidence_score NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Route Optimization Results Table
CREATE TABLE IF NOT EXISTS route_optimization_results (
    optimization_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP,
    original_route_id VARCHAR(255) REFERENCES gtfs_routes(route_id),
    proposed_route_id VARCHAR(255),
    optimization_type VARCHAR(100),
    impact_metrics JSONB,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_unified_timestamp ON unified_realtime_historical_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_unified_stop_id ON unified_realtime_historical_data(stop_id);
CREATE INDEX IF NOT EXISTS idx_unified_trip_id ON unified_realtime_historical_data(trip_id);
CREATE INDEX IF NOT EXISTS idx_unified_route_id ON unified_realtime_historical_data(route_id);
CREATE INDEX IF NOT EXISTS idx_feature_store_timestamp ON feature_store(timestamp);
CREATE INDEX IF NOT EXISTS idx_feature_store_stop_id ON feature_store(stop_id);
CREATE INDEX IF NOT EXISTS idx_model_predictions_timestamp ON model_predictions(timestamp);
CREATE INDEX IF NOT EXISTS idx_model_predictions_stop_id ON model_predictions(stop_id);

-- Create spatial index for stops
CREATE INDEX IF NOT EXISTS idx_stops_spatial ON gtfs_stops USING GIST (ST_SetSRID(ST_MakePoint(stop_lon, stop_lat), 4326)); 