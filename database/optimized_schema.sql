-- MARTA Demand Forecasting Platform - Optimized Database Schema
-- Includes advanced indexing, partitioning, and performance optimizations
-- PostgreSQL 14+ with PostGIS extension required

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================
-- GTFS STATIC DATA TABLES (Optimized)
-- =============================================

-- Agencies table (GTFS reference)
CREATE TABLE IF NOT EXISTS gtfs_agencies (
    agency_id VARCHAR(255) PRIMARY KEY,
    agency_name VARCHAR(255) NOT NULL,
    agency_url TEXT NOT NULL,
    agency_timezone VARCHAR(100) NOT NULL,
    agency_lang VARCHAR(10),
    agency_phone VARCHAR(50),
    agency_fare_url TEXT,
    agency_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optimized Stops table with spatial indexing
CREATE TABLE IF NOT EXISTS gtfs_stops (
    stop_id VARCHAR(255) PRIMARY KEY,
    stop_code VARCHAR(255),
    stop_name VARCHAR(255) NOT NULL,
    stop_desc TEXT,
    stop_lat NUMERIC(10,7) NOT NULL,
    stop_lon NUMERIC(10,7) NOT NULL,
    zone_id VARCHAR(255),
    stop_url TEXT,
    location_type INTEGER DEFAULT 0,
    parent_station VARCHAR(255),
    wheelchair_boarding INTEGER DEFAULT 0,
    platform_code VARCHAR(255),
    -- Spatial geometry column for efficient spatial queries
    geom GEOMETRY(POINT, 4326),
    -- Search optimization
    stop_name_search tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_stop_lat CHECK (stop_lat >= -90 AND stop_lat <= 90),
    CONSTRAINT chk_stop_lon CHECK (stop_lon >= -180 AND stop_lon <= 180),
    CONSTRAINT chk_location_type CHECK (location_type IN (0,1,2,3,4))
);

-- Auto-generate geometry from lat/lon
CREATE OR REPLACE FUNCTION update_stop_geom() RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.stop_lon, NEW.stop_lat), 4326);
    NEW.stop_name_search = to_tsvector('english', COALESCE(NEW.stop_name, '') || ' ' || COALESCE(NEW.stop_desc, ''));
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_stop_geom
    BEFORE INSERT OR UPDATE ON gtfs_stops
    FOR EACH ROW EXECUTE FUNCTION update_stop_geom();

-- Optimized Routes table
CREATE TABLE IF NOT EXISTS gtfs_routes (
    route_id VARCHAR(255) PRIMARY KEY,
    agency_id VARCHAR(255) REFERENCES gtfs_agencies(agency_id) ON DELETE CASCADE,
    route_short_name VARCHAR(255),
    route_long_name VARCHAR(255),
    route_desc TEXT,
    route_type INTEGER NOT NULL,
    route_url TEXT,
    route_color VARCHAR(6) DEFAULT 'FFFFFF',
    route_text_color VARCHAR(6) DEFAULT '000000',
    route_sort_order INTEGER,
    continuous_pickup INTEGER DEFAULT 1,
    continuous_dropoff INTEGER DEFAULT 1,
    -- Search optimization
    route_search tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_route_type CHECK (route_type IN (0,1,2,3,4,5,6,7,11,12)),
    CONSTRAINT chk_route_has_name CHECK (route_short_name IS NOT NULL OR route_long_name IS NOT NULL)
);

CREATE OR REPLACE FUNCTION update_route_search() RETURNS TRIGGER AS $$
BEGIN
    NEW.route_search = to_tsvector('english', 
        COALESCE(NEW.route_short_name, '') || ' ' || 
        COALESCE(NEW.route_long_name, '') || ' ' || 
        COALESCE(NEW.route_desc, '')
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_route_search
    BEFORE INSERT OR UPDATE ON gtfs_routes
    FOR EACH ROW EXECUTE FUNCTION update_route_search();

-- Calendar table with optimized date handling
CREATE TABLE IF NOT EXISTS gtfs_calendar (
    service_id VARCHAR(255) PRIMARY KEY,
    monday BOOLEAN NOT NULL DEFAULT FALSE,
    tuesday BOOLEAN NOT NULL DEFAULT FALSE,
    wednesday BOOLEAN NOT NULL DEFAULT FALSE,
    thursday BOOLEAN NOT NULL DEFAULT FALSE,
    friday BOOLEAN NOT NULL DEFAULT FALSE,
    saturday BOOLEAN NOT NULL DEFAULT FALSE,
    sunday BOOLEAN NOT NULL DEFAULT FALSE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    -- Computed columns for efficiency
    weekdays_only BOOLEAN GENERATED ALWAYS AS (
        monday AND tuesday AND wednesday AND thursday AND friday AND 
        NOT saturday AND NOT sunday
    ) STORED,
    weekends_only BOOLEAN GENERATED ALWAYS AS (
        NOT monday AND NOT tuesday AND NOT wednesday AND NOT thursday AND NOT friday AND 
        saturday AND sunday
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_date_range CHECK (start_date <= end_date)
);

-- Calendar exceptions
CREATE TABLE IF NOT EXISTS gtfs_calendar_dates (
    service_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    exception_type INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (service_id, date),
    CONSTRAINT chk_exception_type CHECK (exception_type IN (1,2))
);

-- Optimized Trips table
CREATE TABLE IF NOT EXISTS gtfs_trips (
    trip_id VARCHAR(255) PRIMARY KEY,
    route_id VARCHAR(255) NOT NULL REFERENCES gtfs_routes(route_id) ON DELETE CASCADE,
    service_id VARCHAR(255) NOT NULL,
    trip_headsign VARCHAR(255),
    trip_short_name VARCHAR(255),
    direction_id INTEGER DEFAULT 0,
    block_id VARCHAR(255),
    shape_id VARCHAR(255),
    wheelchair_accessible INTEGER DEFAULT 0,
    bikes_allowed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_direction_id CHECK (direction_id IN (0,1)),
    CONSTRAINT chk_wheelchair CHECK (wheelchair_accessible IN (0,1,2)),
    CONSTRAINT chk_bikes CHECK (bikes_allowed IN (0,1,2))
);

-- Stop times table with optimized time handling
CREATE TABLE IF NOT EXISTS gtfs_stop_times (
    trip_id VARCHAR(255) NOT NULL REFERENCES gtfs_trips(trip_id) ON DELETE CASCADE,
    stop_sequence INTEGER NOT NULL,
    stop_id VARCHAR(255) NOT NULL REFERENCES gtfs_stops(stop_id) ON DELETE CASCADE,
    arrival_time INTERVAL,
    departure_time INTERVAL,
    stop_headsign VARCHAR(255),
    pickup_type INTEGER DEFAULT 0,
    drop_off_type INTEGER DEFAULT 0,
    continuous_pickup INTEGER DEFAULT 1,
    continuous_drop_off INTEGER DEFAULT 1,
    shape_dist_traveled NUMERIC,
    timepoint INTEGER DEFAULT 1,
    -- Computed columns for faster queries
    arrival_seconds INTEGER GENERATED ALWAYS AS (
        EXTRACT(epoch FROM arrival_time)::INTEGER
    ) STORED,
    departure_seconds INTEGER GENERATED ALWAYS AS (
        EXTRACT(epoch FROM departure_time)::INTEGER
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (trip_id, stop_sequence),
    CONSTRAINT chk_pickup_type CHECK (pickup_type IN (0,1,2,3)),
    CONSTRAINT chk_drop_off_type CHECK (drop_off_type IN (0,1,2,3)),
    CONSTRAINT chk_timepoint CHECK (timepoint IN (0,1))
);

-- Optimized Shapes table
CREATE TABLE IF NOT EXISTS gtfs_shapes (
    shape_id VARCHAR(255) NOT NULL,
    shape_pt_sequence INTEGER NOT NULL,
    shape_pt_lat NUMERIC(10,7) NOT NULL,
    shape_pt_lon NUMERIC(10,7) NOT NULL,
    shape_dist_traveled NUMERIC,
    -- Spatial geometry
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (shape_id, shape_pt_sequence),
    CONSTRAINT chk_shape_lat CHECK (shape_pt_lat >= -90 AND shape_pt_lat <= 90),
    CONSTRAINT chk_shape_lon CHECK (shape_pt_lon >= -180 AND shape_pt_lon <= 180)
);

CREATE OR REPLACE FUNCTION update_shape_geom() RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.shape_pt_lon, NEW.shape_pt_lat), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_shape_geom
    BEFORE INSERT OR UPDATE ON gtfs_shapes
    FOR EACH ROW EXECUTE FUNCTION update_shape_geom();

-- =============================================
-- REAL-TIME DATA TABLES (Partitioned)
-- =============================================

-- Partitioned real-time vehicle positions
CREATE TABLE gtfs_vehicle_positions (
    id UUID DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL,
    trip_id VARCHAR(255),
    route_id VARCHAR(255),
    vehicle_id VARCHAR(255) NOT NULL,
    latitude NUMERIC(10,7) NOT NULL,
    longitude NUMERIC(10,7) NOT NULL,
    bearing REAL,
    speed REAL,
    current_stop_sequence INTEGER,
    current_status INTEGER,
    occupancy_status INTEGER,
    congestion_level INTEGER,
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id, timestamp),
    CONSTRAINT chk_vp_lat CHECK (latitude >= -90 AND latitude <= 90),
    CONSTRAINT chk_vp_lon CHECK (longitude >= -180 AND longitude <= 180)
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions for vehicle positions (last 12 months + next 3 months)
DO $$
DECLARE
    start_date DATE := date_trunc('month', CURRENT_DATE - INTERVAL '12 months');
    end_date DATE := date_trunc('month', CURRENT_DATE + INTERVAL '4 months');
    current_month DATE := start_date;
BEGIN
    WHILE current_month < end_date LOOP
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS gtfs_vehicle_positions_%s PARTITION OF gtfs_vehicle_positions
            FOR VALUES FROM (%L) TO (%L)',
            to_char(current_month, 'YYYY_MM'),
            current_month,
            current_month + INTERVAL '1 month'
        );
        current_month := current_month + INTERVAL '1 month';
    END LOOP;
END $$;

-- Partitioned real-time trip updates
CREATE TABLE gtfs_trip_updates (
    id UUID DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL,
    trip_id VARCHAR(255) NOT NULL,
    route_id VARCHAR(255),
    vehicle_id VARCHAR(255),
    stop_id VARCHAR(255),
    stop_sequence INTEGER,
    arrival_delay INTEGER,
    departure_delay INTEGER,
    schedule_relationship INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions for trip updates
DO $$
DECLARE
    start_date DATE := date_trunc('month', CURRENT_DATE - INTERVAL '12 months');
    end_date DATE := date_trunc('month', CURRENT_DATE + INTERVAL '4 months');
    current_month DATE := start_date;
BEGIN
    WHILE current_month < end_date LOOP
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS gtfs_trip_updates_%s PARTITION OF gtfs_trip_updates
            FOR VALUES FROM (%L) TO (%L)',
            to_char(current_month, 'YYYY_MM'),
            current_month,
            current_month + INTERVAL '1 month'
        );
        current_month := current_month + INTERVAL '1 month';
    END LOOP;
END $$;

-- =============================================
-- ENHANCED UNIFIED DATA TABLE (Partitioned)
-- =============================================

CREATE TABLE unified_transit_data (
    record_id UUID DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL,
    date_partition DATE GENERATED ALWAYS AS (timestamp::DATE) STORED,
    trip_id VARCHAR(255),
    route_id VARCHAR(255),
    stop_id VARCHAR(255),
    vehicle_id VARCHAR(255),
    stop_sequence INTEGER,
    
    -- Location data
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    geom GEOMETRY(POINT, 4326),
    
    -- Timing data
    scheduled_arrival_time TIMESTAMP,
    actual_arrival_time TIMESTAMP,
    scheduled_departure_time TIMESTAMP,
    actual_departure_time TIMESTAMP,
    arrival_delay_seconds INTEGER,
    departure_delay_seconds INTEGER,
    dwell_time_seconds INTEGER,
    
    -- Operational metrics
    passenger_load INTEGER,
    passenger_count INTEGER,
    occupancy_status INTEGER,
    door_state INTEGER,
    
    -- External factors
    weather_condition VARCHAR(100),
    temperature_celsius NUMERIC(4,1),
    precipitation_mm NUMERIC(6,2),
    wind_speed_kmh NUMERIC(5,1),
    visibility_km NUMERIC(4,1),
    
    -- Event flags
    event_flag BOOLEAN DEFAULT FALSE,
    holiday_flag BOOLEAN DEFAULT FALSE,
    special_service_flag BOOLEAN DEFAULT FALSE,
    
    -- Temporal features
    day_of_week INTEGER,
    hour_of_day INTEGER,
    minute_of_hour INTEGER,
    is_weekend BOOLEAN,
    is_rush_hour BOOLEAN,
    
    -- Derived metrics
    headway_adherence NUMERIC(5,2),
    schedule_adherence NUMERIC(5,2),
    service_reliability NUMERIC(5,2),
    
    -- Metadata
    data_source VARCHAR(50),
    quality_score NUMERIC(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (record_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create daily partitions for the last 30 days + next 7 days
DO $$
DECLARE
    start_date DATE := CURRENT_DATE - INTERVAL '30 days';
    end_date DATE := CURRENT_DATE + INTERVAL '8 days';
    current_date DATE := start_date;
BEGIN
    WHILE current_date < end_date LOOP
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS unified_transit_data_%s PARTITION OF unified_transit_data
            FOR VALUES FROM (%L) TO (%L)',
            to_char(current_date, 'YYYY_MM_DD'),
            current_date,
            current_date + INTERVAL '1 day'
        );
        current_date := current_date + INTERVAL '1 day';
    END LOOP;
END $$;

-- =============================================
-- FEATURE STORE (Optimized)
-- =============================================

CREATE TABLE feature_store (
    feature_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- 'stop', 'route', 'trip'
    entity_id VARCHAR(255) NOT NULL,
    
    -- Time-based features
    hour_sin NUMERIC(8,6),
    hour_cos NUMERIC(8,6),
    day_sin NUMERIC(8,6),
    day_cos NUMERIC(8,6),
    month_sin NUMERIC(8,6),
    month_cos NUMERIC(8,6),
    
    -- Lag features
    demand_lag_1h NUMERIC,
    demand_lag_24h NUMERIC,
    demand_lag_168h NUMERIC, -- 1 week
    
    -- Rolling statistics
    demand_rolling_mean_3h NUMERIC,
    demand_rolling_mean_24h NUMERIC,
    demand_rolling_std_24h NUMERIC,
    demand_rolling_max_24h NUMERIC,
    demand_rolling_min_24h NUMERIC,
    
    -- External features
    temperature NUMERIC(4,1),
    precipitation NUMERIC(6,2),
    wind_speed NUMERIC(5,1),
    visibility NUMERIC(4,1),
    weather_category VARCHAR(50),
    
    -- Operational features
    service_frequency_1h INTEGER,
    avg_headway_1h NUMERIC,
    schedule_adherence_1h NUMERIC,
    
    -- Event features
    is_event_day BOOLEAN,
    event_type VARCHAR(100),
    event_distance_km NUMERIC(6,2),
    
    -- Computed features
    demand_anomaly_score NUMERIC(8,4),
    service_disruption_flag BOOLEAN,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Composite index for fast lookups
    UNIQUE (entity_type, entity_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create weekly partitions for feature store
DO $$
DECLARE
    start_date DATE := date_trunc('week', CURRENT_DATE - INTERVAL '8 weeks');
    end_date DATE := date_trunc('week', CURRENT_DATE + INTERVAL '4 weeks');
    current_week DATE := start_date;
BEGIN
    WHILE current_week < end_date LOOP
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS feature_store_%s PARTITION OF feature_store
            FOR VALUES FROM (%L) TO (%L)',
            to_char(current_week, 'YYYY_WW'),
            current_week,
            current_week + INTERVAL '1 week'
        );
        current_week := current_week + INTERVAL '1 week';
    END LOOP;
END $$;

-- =============================================
-- PERFORMANCE OPTIMIZATION INDEXES
-- =============================================

-- GTFS Static Data Indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_stops_geom 
    ON gtfs_stops USING GIST (geom);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_stops_name_search 
    ON gtfs_stops USING GIN (stop_name_search);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_stops_zone 
    ON gtfs_stops (zone_id) WHERE zone_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_routes_type 
    ON gtfs_routes (route_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_routes_search 
    ON gtfs_routes USING GIN (route_search);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_routes_agency 
    ON gtfs_routes (agency_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_trips_route 
    ON gtfs_trips (route_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_trips_service 
    ON gtfs_trips (service_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_trips_direction 
    ON gtfs_trips (route_id, direction_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_stop_times_trip 
    ON gtfs_stop_times (trip_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_stop_times_stop 
    ON gtfs_stop_times (stop_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_stop_times_arrival 
    ON gtfs_stop_times (arrival_seconds) WHERE arrival_seconds IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_stop_times_departure 
    ON gtfs_stop_times (departure_seconds) WHERE departure_seconds IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_shapes_geom 
    ON gtfs_shapes USING GIST (geom);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_shapes_sequence 
    ON gtfs_shapes (shape_id, shape_pt_sequence);

-- Calendar Indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_calendar_dates 
    ON gtfs_calendar_dates (date, service_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gtfs_calendar_service_dates 
    ON gtfs_calendar (service_id, start_date, end_date);

-- Real-time Data Indexes (created on partition parent for inheritance)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vp_timestamp_vehicle 
    ON ONLY gtfs_vehicle_positions (timestamp, vehicle_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vp_geom 
    ON ONLY gtfs_vehicle_positions USING GIST (geom);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vp_route_time 
    ON ONLY gtfs_vehicle_positions (route_id, timestamp) WHERE route_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tu_timestamp_trip 
    ON ONLY gtfs_trip_updates (timestamp, trip_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tu_stop_time 
    ON ONLY gtfs_trip_updates (stop_id, timestamp) WHERE stop_id IS NOT NULL;

-- Unified Transit Data Indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_utd_timestamp_route 
    ON ONLY unified_transit_data (timestamp, route_id) WHERE route_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_utd_timestamp_stop 
    ON ONLY unified_transit_data (timestamp, stop_id) WHERE stop_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_utd_geom 
    ON ONLY unified_transit_data USING GIST (geom) WHERE geom IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_utd_delay_analysis 
    ON ONLY unified_transit_data (timestamp, route_id, arrival_delay_seconds) 
    WHERE arrival_delay_seconds IS NOT NULL;

-- Feature Store Indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fs_entity_time 
    ON ONLY feature_store (entity_type, entity_id, timestamp);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fs_timestamp 
    ON ONLY feature_store (timestamp);

-- =============================================
-- AUTOMATIC INDEX CREATION FOR PARTITIONS
-- =============================================

-- Function to create indexes on new partitions
CREATE OR REPLACE FUNCTION create_partition_indexes()
RETURNS event_trigger
LANGUAGE plpgsql
AS $$
DECLARE
    obj record;
BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands() WHERE command_tag = 'CREATE TABLE'
    LOOP
        -- Check if this is a partition of one of our tables
        IF obj.object_identity LIKE '%gtfs_vehicle_positions_%' THEN
            EXECUTE format('CREATE INDEX CONCURRENTLY IF NOT EXISTS %I ON %s (timestamp, vehicle_id)',
                'idx_' || replace(split_part(obj.object_identity, '.', -1), 'gtfs_vehicle_positions_', 'vp_') || '_time_vehicle',
                obj.object_identity);
            EXECUTE format('CREATE INDEX CONCURRENTLY IF NOT EXISTS %I ON %s USING GIST (geom)',
                'idx_' || replace(split_part(obj.object_identity, '.', -1), 'gtfs_vehicle_positions_', 'vp_') || '_geom',
                obj.object_identity);
                
        ELSIF obj.object_identity LIKE '%gtfs_trip_updates_%' THEN
            EXECUTE format('CREATE INDEX CONCURRENTLY IF NOT EXISTS %I ON %s (timestamp, trip_id)',
                'idx_' || replace(split_part(obj.object_identity, '.', -1), 'gtfs_trip_updates_', 'tu_') || '_time_trip',
                obj.object_identity);
                
        ELSIF obj.object_identity LIKE '%unified_transit_data_%' THEN
            EXECUTE format('CREATE INDEX CONCURRENTLY IF NOT EXISTS %I ON %s (timestamp, route_id)',
                'idx_' || replace(split_part(obj.object_identity, '.', -1), 'unified_transit_data_', 'utd_') || '_time_route',
                obj.object_identity);
            EXECUTE format('CREATE INDEX CONCURRENTLY IF NOT EXISTS %I ON %s USING GIST (geom) WHERE geom IS NOT NULL',
                'idx_' || replace(split_part(obj.object_identity, '.', -1), 'unified_transit_data_', 'utd_') || '_geom',
                obj.object_identity);
                
        ELSIF obj.object_identity LIKE '%feature_store_%' THEN
            EXECUTE format('CREATE INDEX CONCURRENTLY IF NOT EXISTS %I ON %s (entity_type, entity_id, timestamp)',
                'idx_' || replace(split_part(obj.object_identity, '.', -1), 'feature_store_', 'fs_') || '_entity_time',
                obj.object_identity);
        END IF;
    END LOOP;
END;
$$;

CREATE EVENT TRIGGER create_partition_indexes_trigger
ON ddl_command_end
WHEN TAG IN ('CREATE TABLE')
EXECUTE FUNCTION create_partition_indexes();

-- =============================================
-- TABLE STATISTICS AND MAINTENANCE
-- =============================================

-- Update table statistics function
CREATE OR REPLACE FUNCTION update_table_statistics()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    table_name text;
BEGIN
    -- Update statistics for all GTFS and transit tables
    FOR table_name IN 
        SELECT schemaname||'.'||tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND (tablename LIKE 'gtfs_%' OR tablename LIKE 'unified_%' OR tablename LIKE 'feature_store%')
    LOOP
        EXECUTE 'ANALYZE ' || table_name;
    END LOOP;
END;
$$;

-- Comments for documentation
COMMENT ON TABLE gtfs_stops IS 'GTFS stops with spatial optimization and full-text search';
COMMENT ON TABLE gtfs_routes IS 'GTFS routes with search optimization';
COMMENT ON TABLE gtfs_vehicle_positions IS 'Partitioned real-time vehicle positions';
COMMENT ON TABLE gtfs_trip_updates IS 'Partitioned real-time trip updates';
COMMENT ON TABLE unified_transit_data IS 'Unified transit data with comprehensive metrics';
COMMENT ON TABLE feature_store IS 'ML feature store with time-series partitioning';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO marta_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO marta_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO marta_user;

-- Performance monitoring view
CREATE OR REPLACE VIEW query_performance AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
WHERE query LIKE '%gtfs_%' OR query LIKE '%unified_%' OR query LIKE '%feature_%'
ORDER BY total_time DESC
LIMIT 20;

COMMENT ON VIEW query_performance IS 'Top 20 slowest queries for MARTA tables';