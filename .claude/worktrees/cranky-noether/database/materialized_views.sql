-- MARTA Platform - Materialized Views for Performance Optimization
-- These views pre-compute frequently accessed aggregations and statistics

-- =============================================
-- ROUTE PERFORMANCE VIEWS
-- =============================================

-- Route Performance Summary (Updated every 15 minutes)
CREATE MATERIALIZED VIEW mv_route_performance_summary AS
SELECT 
    r.route_id,
    r.route_short_name,
    r.route_long_name,
    r.route_type,
    -- Time-based metrics
    DATE_TRUNC('hour', utd.timestamp) as hour_bucket,
    COUNT(*) as total_observations,
    
    -- Delay metrics
    AVG(utd.arrival_delay_seconds) as avg_arrival_delay_seconds,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY utd.arrival_delay_seconds) as median_arrival_delay_seconds,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY utd.arrival_delay_seconds) as p95_arrival_delay_seconds,
    STDDEV(utd.arrival_delay_seconds) as stddev_arrival_delay_seconds,
    
    -- Schedule adherence
    AVG(utd.schedule_adherence) as avg_schedule_adherence,
    COUNT(CASE WHEN ABS(utd.arrival_delay_seconds) <= 300 THEN 1 END)::FLOAT / COUNT(*) as on_time_performance,
    
    -- Service reliability
    AVG(utd.service_reliability) as avg_service_reliability,
    
    -- Passenger metrics
    AVG(utd.passenger_count) as avg_passenger_count,
    MAX(utd.passenger_count) as max_passenger_count,
    AVG(utd.dwell_time_seconds) as avg_dwell_time_seconds,
    
    -- Geographic coverage
    COUNT(DISTINCT utd.stop_id) as unique_stops_served,
    
    -- Data quality
    AVG(utd.quality_score) as avg_data_quality,
    
    -- Update timestamp
    CURRENT_TIMESTAMP as last_updated
    
FROM gtfs_routes r
JOIN unified_transit_data utd ON r.route_id = utd.route_id
WHERE utd.timestamp >= CURRENT_DATE - INTERVAL '7 days'
    AND utd.timestamp < DATE_TRUNC('hour', CURRENT_TIMESTAMP)
GROUP BY 
    r.route_id, r.route_short_name, r.route_long_name, r.route_type,
    DATE_TRUNC('hour', utd.timestamp);

-- Unique index for fast refreshes
CREATE UNIQUE INDEX idx_mv_route_perf_summary_pk 
    ON mv_route_performance_summary (route_id, hour_bucket);

-- Additional indexes for common queries
CREATE INDEX idx_mv_route_perf_summary_hour 
    ON mv_route_performance_summary (hour_bucket);
CREATE INDEX idx_mv_route_perf_summary_otp 
    ON mv_route_performance_summary (on_time_performance DESC);

-- =============================================
-- STOP PERFORMANCE VIEWS
-- =============================================

-- Stop Performance Summary (Updated every 15 minutes)
CREATE MATERIALIZED VIEW mv_stop_performance_summary AS
SELECT 
    s.stop_id,
    s.stop_name,
    s.stop_lat,
    s.stop_lon,
    s.zone_id,
    -- Time-based metrics
    DATE_TRUNC('hour', utd.timestamp) as hour_bucket,
    COUNT(*) as total_observations,
    
    -- Delay metrics
    AVG(utd.arrival_delay_seconds) as avg_arrival_delay_seconds,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY utd.arrival_delay_seconds) as median_arrival_delay_seconds,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY utd.arrival_delay_seconds) as p95_arrival_delay_seconds,
    
    -- Passenger metrics
    AVG(utd.passenger_count) as avg_passenger_count,
    MAX(utd.passenger_count) as max_passenger_count,
    SUM(utd.passenger_count) as total_passenger_count,
    AVG(utd.dwell_time_seconds) as avg_dwell_time_seconds,
    
    -- Service frequency
    COUNT(DISTINCT utd.trip_id) as unique_trips,
    COUNT(DISTINCT utd.route_id) as unique_routes,
    
    -- Schedule adherence
    AVG(utd.schedule_adherence) as avg_schedule_adherence,
    COUNT(CASE WHEN ABS(utd.arrival_delay_seconds) <= 300 THEN 1 END)::FLOAT / COUNT(*) as on_time_performance,
    
    -- Operational metrics
    AVG(CASE WHEN utd.occupancy_status IS NOT NULL THEN utd.occupancy_status END) as avg_occupancy_status,
    
    -- Update timestamp
    CURRENT_TIMESTAMP as last_updated
    
FROM gtfs_stops s
JOIN unified_transit_data utd ON s.stop_id = utd.stop_id
WHERE utd.timestamp >= CURRENT_DATE - INTERVAL '7 days'
    AND utd.timestamp < DATE_TRUNC('hour', CURRENT_TIMESTAMP)
GROUP BY 
    s.stop_id, s.stop_name, s.stop_lat, s.stop_lon, s.zone_id,
    DATE_TRUNC('hour', utd.timestamp);

-- Indexes for stop performance view
CREATE UNIQUE INDEX idx_mv_stop_perf_summary_pk 
    ON mv_stop_performance_summary (stop_id, hour_bucket);
CREATE INDEX idx_mv_stop_perf_summary_hour 
    ON mv_stop_performance_summary (hour_bucket);
CREATE INDEX idx_mv_stop_perf_summary_ridership 
    ON mv_stop_performance_summary (total_passenger_count DESC);

-- =============================================
-- DEMAND FORECASTING VIEWS
-- =============================================

-- Hourly Demand Patterns (Updated every hour)
CREATE MATERIALIZED VIEW mv_hourly_demand_patterns AS
WITH hourly_stats AS (
    SELECT 
        route_id,
        stop_id,
        EXTRACT(hour FROM timestamp) as hour_of_day,
        EXTRACT(dow FROM timestamp) as day_of_week,
        DATE_TRUNC('day', timestamp) as date_bucket,
        
        -- Demand metrics
        AVG(passenger_count) as avg_passenger_count,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY passenger_count) as median_passenger_count,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY passenger_count) as p95_passenger_count,
        MAX(passenger_count) as max_passenger_count,
        COUNT(*) as observations,
        
        -- Service metrics
        AVG(dwell_time_seconds) as avg_dwell_time,
        AVG(arrival_delay_seconds) as avg_delay,
        
        -- External factors
        AVG(temperature_celsius) as avg_temperature,
        AVG(precipitation_mm) as avg_precipitation,
        BOOL_OR(event_flag) as has_events,
        BOOL_OR(holiday_flag) as is_holiday
        
    FROM unified_transit_data
    WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
        AND passenger_count IS NOT NULL
    GROUP BY route_id, stop_id, 
             EXTRACT(hour FROM timestamp), 
             EXTRACT(dow FROM timestamp),
             DATE_TRUNC('day', timestamp)
)
SELECT 
    route_id,
    stop_id,
    hour_of_day,
    day_of_week,
    
    -- Statistical aggregations across days
    AVG(avg_passenger_count) as typical_demand,
    STDDEV(avg_passenger_count) as demand_volatility,
    PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY avg_passenger_count) as demand_p10,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_passenger_count) as demand_median,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY avg_passenger_count) as demand_p90,
    MAX(max_passenger_count) as peak_demand,
    
    -- Service pattern analysis
    AVG(avg_dwell_time) as typical_dwell_time,
    AVG(avg_delay) as typical_delay,
    
    -- Environmental correlations
    CORR(avg_passenger_count, avg_temperature) as temp_correlation,
    CORR(avg_passenger_count, avg_precipitation) as precip_correlation,
    
    -- Event impact
    AVG(CASE WHEN has_events THEN avg_passenger_count END) as demand_with_events,
    AVG(CASE WHEN NOT has_events THEN avg_passenger_count END) as demand_without_events,
    AVG(CASE WHEN is_holiday THEN avg_passenger_count END) as demand_on_holidays,
    
    -- Data quality metrics
    COUNT(*) as days_of_data,
    SUM(observations) as total_observations,
    
    -- Update timestamp
    CURRENT_TIMESTAMP as last_updated
    
FROM hourly_stats
GROUP BY route_id, stop_id, hour_of_day, day_of_week
HAVING COUNT(*) >= 5; -- At least 5 days of data

-- Indexes for demand patterns
CREATE UNIQUE INDEX idx_mv_demand_patterns_pk 
    ON mv_hourly_demand_patterns (route_id, stop_id, hour_of_day, day_of_week);
CREATE INDEX idx_mv_demand_patterns_route_hour 
    ON mv_hourly_demand_patterns (route_id, hour_of_day);
CREATE INDEX idx_mv_demand_patterns_peak 
    ON mv_hourly_demand_patterns (peak_demand DESC);

-- =============================================
-- REAL-TIME ANALYTICS VIEWS
-- =============================================

-- Current System Status (Updated every 5 minutes)
CREATE MATERIALIZED VIEW mv_current_system_status AS
WITH recent_data AS (
    SELECT *
    FROM unified_transit_data
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '15 minutes'
),
route_status AS (
    SELECT 
        route_id,
        COUNT(*) as active_vehicles,
        COUNT(DISTINCT trip_id) as active_trips,
        AVG(arrival_delay_seconds) as avg_delay,
        AVG(passenger_count) as avg_occupancy,
        COUNT(CASE WHEN ABS(arrival_delay_seconds) > 600 THEN 1 END) as severely_delayed_trips,
        MAX(timestamp) as last_update
    FROM recent_data
    WHERE route_id IS NOT NULL
    GROUP BY route_id
)
SELECT 
    rs.route_id,
    r.route_short_name,
    r.route_long_name,
    rs.active_vehicles,
    rs.active_trips,
    rs.avg_delay,
    rs.avg_occupancy,
    rs.severely_delayed_trips,
    rs.last_update,
    
    -- Service status classification
    CASE 
        WHEN rs.avg_delay IS NULL THEN 'NO_DATA'
        WHEN rs.avg_delay <= 300 THEN 'ON_TIME'
        WHEN rs.avg_delay <= 600 THEN 'MINOR_DELAYS'
        ELSE 'MAJOR_DELAYS'
    END as service_status,
    
    -- Capacity status
    CASE 
        WHEN rs.avg_occupancy IS NULL THEN 'UNKNOWN'
        WHEN rs.avg_occupancy < 0.5 THEN 'LOW'
        WHEN rs.avg_occupancy < 0.8 THEN 'MODERATE'
        ELSE 'HIGH'
    END as capacity_status,
    
    CURRENT_TIMESTAMP as snapshot_time
    
FROM route_status rs
JOIN gtfs_routes r ON rs.route_id = r.route_id
ORDER BY rs.route_id;

-- Indexes for current status
CREATE UNIQUE INDEX idx_mv_current_status_pk 
    ON mv_current_system_status (route_id);
CREATE INDEX idx_mv_current_status_service 
    ON mv_current_system_status (service_status);

-- =============================================
-- GEOSPATIAL ANALYTICS VIEWS
-- =============================================

-- Stop Catchment Areas and Service Coverage
CREATE MATERIALIZED VIEW mv_stop_service_areas AS
WITH stop_buffers AS (
    SELECT 
        stop_id,
        stop_name,
        geom,
        -- 400m walking buffer (typical transit catchment)
        ST_Buffer(geom::geography, 400)::geometry as walk_buffer,
        -- 800m cycling buffer
        ST_Buffer(geom::geography, 800)::geometry as bike_buffer
    FROM gtfs_stops
),
service_metrics AS (
    SELECT 
        stop_id,
        COUNT(DISTINCT route_id) as routes_served,
        COUNT(DISTINCT trip_id) as daily_trips,
        AVG(passenger_count) as avg_ridership
    FROM unified_transit_data
    WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY stop_id
)
SELECT 
    sb.stop_id,
    sb.stop_name,
    sb.geom as stop_location,
    sb.walk_buffer,
    sb.bike_buffer,
    ST_Area(sb.walk_buffer::geography) / 1000000 as walk_catchment_km2,
    ST_Area(sb.bike_buffer::geography) / 1000000 as bike_catchment_km2,
    
    -- Service metrics
    COALESCE(sm.routes_served, 0) as routes_served,
    COALESCE(sm.daily_trips, 0) as daily_trips,
    COALESCE(sm.avg_ridership, 0) as avg_ridership,
    
    -- Service density
    COALESCE(sm.daily_trips, 0) / GREATEST(ST_Area(sb.walk_buffer::geography) / 1000000, 0.001) as service_density,
    
    CURRENT_TIMESTAMP as last_updated
    
FROM stop_buffers sb
LEFT JOIN service_metrics sm ON sb.stop_id = sm.stop_id;

-- Spatial indexes
CREATE UNIQUE INDEX idx_mv_service_areas_pk 
    ON mv_stop_service_areas (stop_id);
CREATE INDEX idx_mv_service_areas_walk_geom 
    ON mv_stop_service_areas USING GIST (walk_buffer);
CREATE INDEX idx_mv_service_areas_bike_geom 
    ON mv_stop_service_areas USING GIST (bike_buffer);

-- =============================================
-- PREDICTIVE ANALYTICS VIEWS
-- =============================================

-- Feature Engineering for ML Models
CREATE MATERIALIZED VIEW mv_ml_features AS
WITH base_features AS (
    SELECT 
        stop_id,
        route_id,
        timestamp,
        passenger_count,
        
        -- Temporal features
        EXTRACT(hour FROM timestamp) as hour,
        EXTRACT(dow FROM timestamp) as dow,
        EXTRACT(day FROM timestamp) as day,
        EXTRACT(month FROM timestamp) as month,
        
        -- Cyclical encodings
        SIN(2 * PI() * EXTRACT(hour FROM timestamp) / 24) as hour_sin,
        COS(2 * PI() * EXTRACT(hour FROM timestamp) / 24) as hour_cos,
        SIN(2 * PI() * EXTRACT(dow FROM timestamp) / 7) as dow_sin,
        COS(2 * PI() * EXTRACT(dow FROM timestamp) / 7) as dow_cos,
        
        -- Weather features
        temperature_celsius,
        precipitation_mm,
        
        -- Service features
        arrival_delay_seconds,
        dwell_time_seconds,
        
        -- Event features
        event_flag,
        holiday_flag
        
    FROM unified_transit_data
    WHERE timestamp >= CURRENT_DATE - INTERVAL '60 days'
        AND passenger_count IS NOT NULL
),
lagged_features AS (
    SELECT 
        *,
        -- Lag features
        LAG(passenger_count, 1) OVER (
            PARTITION BY stop_id, route_id 
            ORDER BY timestamp
        ) as demand_lag_1,
        LAG(passenger_count, 24) OVER (
            PARTITION BY stop_id, route_id 
            ORDER BY timestamp
        ) as demand_lag_24,
        LAG(passenger_count, 168) OVER (
            PARTITION BY stop_id, route_id 
            ORDER BY timestamp
        ) as demand_lag_168,
        
        -- Rolling averages
        AVG(passenger_count) OVER (
            PARTITION BY stop_id, route_id 
            ORDER BY timestamp 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) as demand_rolling_12h,
        AVG(passenger_count) OVER (
            PARTITION BY stop_id, route_id 
            ORDER BY timestamp 
            ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
        ) as demand_rolling_24h,
        
        -- Rolling standard deviation
        STDDEV(passenger_count) OVER (
            PARTITION BY stop_id, route_id 
            ORDER BY timestamp 
            ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
        ) as demand_rolling_std_24h
        
    FROM base_features
)
SELECT 
    stop_id,
    route_id,
    timestamp,
    passenger_count as target,
    
    -- All features
    hour, dow, day, month,
    hour_sin, hour_cos, dow_sin, dow_cos,
    temperature_celsius,
    precipitation_mm,
    arrival_delay_seconds,
    dwell_time_seconds,
    event_flag::INTEGER as event_flag,
    holiday_flag::INTEGER as holiday_flag,
    demand_lag_1,
    demand_lag_24,
    demand_lag_168,
    demand_rolling_12h,
    demand_rolling_24h,
    demand_rolling_std_24h,
    
    CURRENT_TIMESTAMP as last_updated
    
FROM lagged_features
WHERE demand_lag_24 IS NOT NULL; -- Ensure we have sufficient history

-- Indexes for ML features
CREATE INDEX idx_mv_ml_features_entity_time 
    ON mv_ml_features (stop_id, route_id, timestamp);
CREATE INDEX idx_mv_ml_features_timestamp 
    ON mv_ml_features (timestamp);

-- =============================================
-- AUTOMATED REFRESH PROCEDURES
-- =============================================

-- Refresh schedule function
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- High-frequency updates (every 5 minutes)
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_current_system_status;
    
    -- Medium-frequency updates (every 15 minutes)
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_route_performance_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stop_performance_summary;
    
    -- Low-frequency updates (every hour)
    IF EXTRACT(minute FROM CURRENT_TIMESTAMP) < 5 THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_demand_patterns;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ml_features;
        
        -- Daily updates
        IF EXTRACT(hour FROM CURRENT_TIMESTAMP) = 1 THEN
            REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stop_service_areas;
        END IF;
    END IF;
    
    -- Log refresh completion
    RAISE NOTICE 'Materialized views refresh completed at %', CURRENT_TIMESTAMP;
END;
$$;

-- Create refresh monitoring table
CREATE TABLE IF NOT EXISTS mv_refresh_log (
    id SERIAL PRIMARY KEY,
    view_name TEXT NOT NULL,
    refresh_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    refresh_end TIMESTAMP,
    success BOOLEAN,
    error_message TEXT,
    rows_affected BIGINT
);

-- Enhanced refresh function with logging
CREATE OR REPLACE FUNCTION refresh_mv_with_logging(view_name TEXT)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    start_time TIMESTAMP;
    row_count BIGINT;
    log_id INTEGER;
BEGIN
    start_time := CURRENT_TIMESTAMP;
    
    -- Insert start log
    INSERT INTO mv_refresh_log (view_name, refresh_start)
    VALUES (view_name, start_time)
    RETURNING id INTO log_id;
    
    BEGIN
        -- Refresh the view
        EXECUTE 'REFRESH MATERIALIZED VIEW CONCURRENTLY ' || view_name;
        
        -- Get row count
        EXECUTE 'SELECT COUNT(*) FROM ' || view_name INTO row_count;
        
        -- Update log with success
        UPDATE mv_refresh_log
        SET refresh_end = CURRENT_TIMESTAMP,
            success = TRUE,
            rows_affected = row_count
        WHERE id = log_id;
        
    EXCEPTION WHEN OTHERS THEN
        -- Update log with failure
        UPDATE mv_refresh_log
        SET refresh_end = CURRENT_TIMESTAMP,
            success = FALSE,
            error_message = SQLERRM
        WHERE id = log_id;
        
        RAISE;
    END;
END;
$$;

-- Comments for documentation
COMMENT ON MATERIALIZED VIEW mv_route_performance_summary IS 'Hourly route performance metrics with delay and ridership analysis';
COMMENT ON MATERIALIZED VIEW mv_stop_performance_summary IS 'Hourly stop performance metrics with passenger and service data';
COMMENT ON MATERIALIZED VIEW mv_hourly_demand_patterns IS 'Historical demand patterns by route, stop, hour, and day of week';
COMMENT ON MATERIALIZED VIEW mv_current_system_status IS 'Real-time system status with service and capacity indicators';
COMMENT ON MATERIALIZED VIEW mv_stop_service_areas IS 'Stop catchment areas and service coverage analysis';
COMMENT ON MATERIALIZED VIEW mv_ml_features IS 'Pre-computed features for machine learning models';