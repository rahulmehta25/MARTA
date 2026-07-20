-- MARTA Platform - Optimized Stored Procedures and Query Patterns
-- High-performance procedures for common operations and analytics

-- =============================================
-- REAL-TIME QUERY PROCEDURES
-- =============================================

-- Get current vehicle positions with route information
CREATE OR REPLACE FUNCTION get_current_vehicle_positions(
    p_route_ids TEXT[] DEFAULT NULL,
    p_max_age_minutes INTEGER DEFAULT 5
)
RETURNS TABLE (
    vehicle_id VARCHAR(255),
    trip_id VARCHAR(255),
    route_id VARCHAR(255),
    route_short_name VARCHAR(255),
    latitude NUMERIC,
    longitude NUMERIC,
    bearing REAL,
    speed REAL,
    timestamp TIMESTAMP,
    age_minutes NUMERIC
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    WITH recent_positions AS (
        SELECT DISTINCT ON (vp.vehicle_id)
            vp.vehicle_id,
            vp.trip_id,
            vp.route_id,
            vp.latitude,
            vp.longitude,
            vp.bearing,
            vp.speed,
            vp.timestamp,
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - vp.timestamp)) / 60.0 as age_minutes
        FROM gtfs_vehicle_positions vp
        WHERE vp.timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
            AND (p_route_ids IS NULL OR vp.route_id = ANY(p_route_ids))
        ORDER BY vp.vehicle_id, vp.timestamp DESC
    )
    SELECT 
        rp.vehicle_id,
        rp.trip_id,
        rp.route_id,
        r.route_short_name,
        rp.latitude,
        rp.longitude,
        rp.bearing,
        rp.speed,
        rp.timestamp,
        rp.age_minutes
    FROM recent_positions rp
    LEFT JOIN gtfs_routes r ON rp.route_id = r.route_id
    WHERE rp.age_minutes <= p_max_age_minutes
    ORDER BY rp.route_id, rp.vehicle_id;
END;
$$;

-- Get real-time arrivals for a stop
CREATE OR REPLACE FUNCTION get_stop_arrivals(
    p_stop_id VARCHAR(255),
    p_max_arrivals INTEGER DEFAULT 10,
    p_time_window_minutes INTEGER DEFAULT 60
)
RETURNS TABLE (
    trip_id VARCHAR(255),
    route_id VARCHAR(255),
    route_short_name VARCHAR(255),
    headsign VARCHAR(255),
    scheduled_arrival TIMESTAMP,
    predicted_arrival TIMESTAMP,
    delay_minutes NUMERIC,
    vehicle_id VARCHAR(255),
    occupancy_status INTEGER
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    current_time TIMESTAMP := CURRENT_TIMESTAMP;
BEGIN
    RETURN QUERY
    WITH trip_updates AS (
        SELECT DISTINCT ON (tu.trip_id)
            tu.trip_id,
            tu.route_id,
            tu.vehicle_id,
            tu.arrival_delay,
            tu.timestamp as update_time
        FROM gtfs_trip_updates tu
        WHERE tu.stop_id = p_stop_id
            AND tu.timestamp >= current_time - INTERVAL '30 minutes'
        ORDER BY tu.trip_id, tu.timestamp DESC
    ),
    scheduled_arrivals AS (
        SELECT 
            st.trip_id,
            t.route_id,
            t.trip_headsign as headsign,
            -- Convert interval to timestamp for today
            (CURRENT_DATE + st.arrival_time) as scheduled_arrival,
            st.arrival_seconds
        FROM gtfs_stop_times st
        JOIN gtfs_trips t ON st.trip_id = t.trip_id
        WHERE st.stop_id = p_stop_id
            AND (CURRENT_DATE + st.arrival_time) BETWEEN 
                current_time AND current_time + INTERVAL '1 hour' * p_time_window_minutes / 60
    )
    SELECT 
        sa.trip_id,
        sa.route_id,
        r.route_short_name,
        sa.headsign,
        sa.scheduled_arrival,
        CASE 
            WHEN tu.arrival_delay IS NOT NULL 
            THEN sa.scheduled_arrival + INTERVAL '1 second' * tu.arrival_delay
            ELSE sa.scheduled_arrival
        END as predicted_arrival,
        COALESCE(tu.arrival_delay / 60.0, 0) as delay_minutes,
        tu.vehicle_id,
        vp.occupancy_status
    FROM scheduled_arrivals sa
    LEFT JOIN trip_updates tu ON sa.trip_id = tu.trip_id
    LEFT JOIN gtfs_routes r ON sa.route_id = r.route_id
    LEFT JOIN LATERAL (
        SELECT occupancy_status
        FROM gtfs_vehicle_positions vp
        WHERE vp.vehicle_id = tu.vehicle_id
            AND vp.timestamp >= current_time - INTERVAL '10 minutes'
        ORDER BY vp.timestamp DESC
        LIMIT 1
    ) vp ON true
    ORDER BY 
        CASE 
            WHEN tu.arrival_delay IS NOT NULL 
            THEN sa.scheduled_arrival + INTERVAL '1 second' * tu.arrival_delay
            ELSE sa.scheduled_arrival
        END
    LIMIT p_max_arrivals;
END;
$$;

-- =============================================
-- DEMAND ANALYSIS PROCEDURES
-- =============================================

-- Get demand forecast for a specific stop and time
CREATE OR REPLACE FUNCTION get_demand_forecast(
    p_stop_id VARCHAR(255),
    p_route_id VARCHAR(255) DEFAULT NULL,
    p_forecast_timestamp TIMESTAMP DEFAULT NULL,
    p_horizon_hours INTEGER DEFAULT 2
)
RETURNS TABLE (
    forecast_timestamp TIMESTAMP,
    predicted_demand NUMERIC,
    confidence_lower NUMERIC,
    confidence_upper NUMERIC,
    historical_average NUMERIC,
    demand_category VARCHAR(20)
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    target_time TIMESTAMP;
    target_hour INTEGER;
    target_dow INTEGER;
BEGIN
    -- Default to next hour if no timestamp provided
    target_time := COALESCE(p_forecast_timestamp, DATE_TRUNC('hour', CURRENT_TIMESTAMP + INTERVAL '1 hour'));
    target_hour := EXTRACT(hour FROM target_time);
    target_dow := EXTRACT(dow FROM target_time);
    
    RETURN QUERY
    WITH historical_pattern AS (
        SELECT 
            typical_demand,
            demand_volatility,
            demand_p10,
            demand_p90
        FROM mv_hourly_demand_patterns
        WHERE stop_id = p_stop_id
            AND (p_route_id IS NULL OR route_id = p_route_id)
            AND hour_of_day = target_hour
            AND day_of_week = target_dow
        LIMIT 1
    ),
    weather_adjustment AS (
        SELECT 
            -- Simple weather adjustment factor
            CASE 
                WHEN temperature_celsius < 0 THEN 0.9
                WHEN temperature_celsius > 35 THEN 0.85
                WHEN precipitation_mm > 5 THEN 1.15
                ELSE 1.0
            END as weather_factor
        FROM unified_transit_data
        WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
            AND temperature_celsius IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 1
    )
    SELECT 
        target_time as forecast_timestamp,
        COALESCE(hp.typical_demand * wa.weather_factor, 0) as predicted_demand,
        COALESCE(hp.demand_p10 * wa.weather_factor, 0) as confidence_lower,
        COALESCE(hp.demand_p90 * wa.weather_factor, 0) as confidence_upper,
        COALESCE(hp.typical_demand, 0) as historical_average,
        CASE 
            WHEN COALESCE(hp.typical_demand * wa.weather_factor, 0) < 10 THEN 'LOW'
            WHEN COALESCE(hp.typical_demand * wa.weather_factor, 0) < 30 THEN 'MEDIUM'
            ELSE 'HIGH'
        END as demand_category
    FROM historical_pattern hp
    CROSS JOIN weather_adjustment wa;
END;
$$;

-- Get route demand trends
CREATE OR REPLACE FUNCTION get_route_demand_trends(
    p_route_id VARCHAR(255),
    p_start_date DATE DEFAULT CURRENT_DATE - INTERVAL '7 days',
    p_end_date DATE DEFAULT CURRENT_DATE,
    p_aggregation_level VARCHAR(10) DEFAULT 'hour' -- 'hour' or 'day'
)
RETURNS TABLE (
    time_bucket TIMESTAMP,
    total_demand BIGINT,
    avg_demand NUMERIC,
    peak_demand NUMERIC,
    unique_stops INTEGER,
    service_hours NUMERIC
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    bucket_interval INTERVAL;
BEGIN
    -- Set aggregation interval
    bucket_interval := CASE p_aggregation_level 
        WHEN 'day' THEN INTERVAL '1 day'
        ELSE INTERVAL '1 hour'
    END;
    
    RETURN QUERY
    SELECT 
        DATE_TRUNC(p_aggregation_level, utd.timestamp) as time_bucket,
        SUM(utd.passenger_count)::BIGINT as total_demand,
        AVG(utd.passenger_count) as avg_demand,
        MAX(utd.passenger_count) as peak_demand,
        COUNT(DISTINCT utd.stop_id)::INTEGER as unique_stops,
        COUNT(DISTINCT DATE_TRUNC('hour', utd.timestamp))::NUMERIC as service_hours
    FROM unified_transit_data utd
    WHERE utd.route_id = p_route_id
        AND utd.timestamp::DATE BETWEEN p_start_date AND p_end_date
        AND utd.passenger_count IS NOT NULL
    GROUP BY DATE_TRUNC(p_aggregation_level, utd.timestamp)
    ORDER BY time_bucket;
END;
$$;

-- =============================================
-- PERFORMANCE ANALYSIS PROCEDURES
-- =============================================

-- Get route performance metrics
CREATE OR REPLACE FUNCTION get_route_performance(
    p_route_id VARCHAR(255),
    p_start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP - INTERVAL '24 hours',
    p_end_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
RETURNS TABLE (
    route_id VARCHAR(255),
    route_name VARCHAR(255),
    total_trips INTEGER,
    on_time_trips INTEGER,
    delayed_trips INTEGER,
    on_time_percentage NUMERIC,
    avg_delay_minutes NUMERIC,
    median_delay_minutes NUMERIC,
    p95_delay_minutes NUMERIC,
    total_passengers BIGINT,
    avg_passengers_per_trip NUMERIC,
    service_reliability NUMERIC
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        utd.route_id,
        r.route_short_name as route_name,
        COUNT(DISTINCT utd.trip_id)::INTEGER as total_trips,
        COUNT(CASE WHEN ABS(utd.arrival_delay_seconds) <= 300 THEN 1 END)::INTEGER as on_time_trips,
        COUNT(CASE WHEN ABS(utd.arrival_delay_seconds) > 300 THEN 1 END)::INTEGER as delayed_trips,
        ROUND(
            COUNT(CASE WHEN ABS(utd.arrival_delay_seconds) <= 300 THEN 1 END)::NUMERIC 
            / GREATEST(COUNT(*), 1) * 100, 2
        ) as on_time_percentage,
        ROUND(AVG(utd.arrival_delay_seconds / 60.0), 2) as avg_delay_minutes,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY utd.arrival_delay_seconds / 60.0), 2) as median_delay_minutes,
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY utd.arrival_delay_seconds / 60.0), 2) as p95_delay_minutes,
        COALESCE(SUM(utd.passenger_count), 0)::BIGINT as total_passengers,
        ROUND(AVG(utd.passenger_count), 2) as avg_passengers_per_trip,
        ROUND(AVG(utd.service_reliability), 2) as service_reliability
    FROM unified_transit_data utd
    JOIN gtfs_routes r ON utd.route_id = r.route_id
    WHERE utd.route_id = p_route_id
        AND utd.timestamp BETWEEN p_start_time AND p_end_time
        AND utd.arrival_delay_seconds IS NOT NULL
    GROUP BY utd.route_id, r.route_short_name;
END;
$$;

-- Get system-wide performance dashboard
CREATE OR REPLACE FUNCTION get_system_performance_dashboard()
RETURNS TABLE (
    metric_name VARCHAR(50),
    current_value NUMERIC,
    target_value NUMERIC,
    status VARCHAR(20),
    trend VARCHAR(10)
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    current_otp NUMERIC;
    previous_otp NUMERIC;
    current_delay NUMERIC;
    current_reliability NUMERIC;
    active_vehicles INTEGER;
    total_routes INTEGER;
BEGIN
    -- Calculate current metrics
    SELECT 
        COUNT(CASE WHEN ABS(arrival_delay_seconds) <= 300 THEN 1 END)::NUMERIC 
        / GREATEST(COUNT(*), 1) * 100,
        AVG(arrival_delay_seconds / 60.0),
        AVG(service_reliability)
    INTO current_otp, current_delay, current_reliability
    FROM unified_transit_data
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '2 hours';
    
    -- Calculate previous period for trend
    SELECT 
        COUNT(CASE WHEN ABS(arrival_delay_seconds) <= 300 THEN 1 END)::NUMERIC 
        / GREATEST(COUNT(*), 1) * 100
    INTO previous_otp
    FROM unified_transit_data
    WHERE timestamp BETWEEN CURRENT_TIMESTAMP - INTERVAL '4 hours' 
                      AND CURRENT_TIMESTAMP - INTERVAL '2 hours';
    
    -- Get active vehicles and routes
    SELECT 
        COUNT(DISTINCT vehicle_id),
        COUNT(DISTINCT route_id)
    INTO active_vehicles, total_routes
    FROM gtfs_vehicle_positions
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '15 minutes';
    
    -- Return dashboard metrics
    RETURN QUERY VALUES
        ('On-Time Performance', current_otp, 85.0, 
         CASE WHEN current_otp >= 85 THEN 'GOOD' 
              WHEN current_otp >= 75 THEN 'WARNING' 
              ELSE 'CRITICAL' END,
         CASE WHEN current_otp > previous_otp THEN 'UP'
              WHEN current_otp < previous_otp THEN 'DOWN'
              ELSE 'STABLE' END),
        ('Average Delay (min)', ABS(current_delay), 3.0,
         CASE WHEN ABS(current_delay) <= 3 THEN 'GOOD'
              WHEN ABS(current_delay) <= 6 THEN 'WARNING'
              ELSE 'CRITICAL' END, 'STABLE'),
        ('Service Reliability', current_reliability, 90.0,
         CASE WHEN current_reliability >= 90 THEN 'GOOD'
              WHEN current_reliability >= 80 THEN 'WARNING'
              ELSE 'CRITICAL' END, 'STABLE'),
        ('Active Vehicles', active_vehicles::NUMERIC, total_routes::NUMERIC * 0.8,
         CASE WHEN active_vehicles >= total_routes * 0.8 THEN 'GOOD'
              WHEN active_vehicles >= total_routes * 0.6 THEN 'WARNING'
              ELSE 'CRITICAL' END, 'STABLE');
END;
$$;

-- =============================================
-- GEOSPATIAL QUERY PROCEDURES
-- =============================================

-- Find nearby stops within walking distance
CREATE OR REPLACE FUNCTION get_nearby_stops(
    p_latitude NUMERIC,
    p_longitude NUMERIC,
    p_radius_meters INTEGER DEFAULT 800,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    stop_id VARCHAR(255),
    stop_name VARCHAR(255),
    distance_meters NUMERIC,
    routes_served INTEGER,
    avg_daily_ridership NUMERIC,
    walking_time_minutes INTEGER
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    search_point GEOMETRY;
BEGIN
    search_point := ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326);
    
    RETURN QUERY
    WITH nearby AS (
        SELECT 
            s.stop_id,
            s.stop_name,
            s.geom,
            ST_Distance(s.geom::geography, search_point::geography) as distance_meters
        FROM gtfs_stops s
        WHERE ST_DWithin(s.geom::geography, search_point::geography, p_radius_meters)
    ),
    stop_metrics AS (
        SELECT 
            stop_id,
            COUNT(DISTINCT route_id) as routes_served,
            AVG(passenger_count) as avg_ridership
        FROM unified_transit_data
        WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY stop_id
    )
    SELECT 
        n.stop_id,
        n.stop_name,
        ROUND(n.distance_meters, 0) as distance_meters,
        COALESCE(sm.routes_served, 0)::INTEGER as routes_served,
        ROUND(COALESCE(sm.avg_ridership, 0), 1) as avg_daily_ridership,
        -- Assume 80 meters per minute walking speed
        CEIL(n.distance_meters / 80.0)::INTEGER as walking_time_minutes
    FROM nearby n
    LEFT JOIN stop_metrics sm ON n.stop_id = sm.stop_id
    ORDER BY n.distance_meters
    LIMIT p_limit;
END;
$$;

-- Get route coverage analysis
CREATE OR REPLACE FUNCTION get_route_coverage_analysis(
    p_route_id VARCHAR(255)
)
RETURNS TABLE (
    route_id VARCHAR(255),
    total_stops INTEGER,
    route_length_km NUMERIC,
    avg_stop_spacing_m NUMERIC,
    service_area_km2 NUMERIC,
    population_served_estimate INTEGER
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    WITH route_stops AS (
        SELECT DISTINCT 
            st.stop_id,
            s.geom,
            s.stop_name
        FROM gtfs_stop_times st
        JOIN gtfs_trips t ON st.trip_id = t.trip_id
        JOIN gtfs_stops s ON st.stop_id = s.stop_id
        WHERE t.route_id = p_route_id
    ),
    route_geometry AS (
        SELECT 
            ST_MakeLine(geom ORDER BY stop_id) as route_line
        FROM route_stops
    ),
    service_buffer AS (
        SELECT 
            ST_Union(ST_Buffer(geom::geography, 400)) as service_area
        FROM route_stops
    )
    SELECT 
        p_route_id as route_id,
        COUNT(*)::INTEGER as total_stops,
        ROUND(ST_Length(rg.route_line::geography) / 1000.0, 2) as route_length_km,
        ROUND(ST_Length(rg.route_line::geography) / GREATEST(COUNT(*) - 1, 1), 0) as avg_stop_spacing_m,
        ROUND(ST_Area(sb.service_area) / 1000000.0, 2) as service_area_km2,
        -- Rough population estimate: 3000 people per km2 in service area
        ROUND(ST_Area(sb.service_area) / 1000000.0 * 3000)::INTEGER as population_served_estimate
    FROM route_stops
    CROSS JOIN route_geometry rg
    CROSS JOIN service_buffer sb
    GROUP BY p_route_id, rg.route_line, sb.service_area;
END;
$$;

-- =============================================
-- DATA QUALITY AND MONITORING PROCEDURES
-- =============================================

-- Check data quality metrics
CREATE OR REPLACE FUNCTION check_data_quality(
    p_table_name VARCHAR(100) DEFAULT 'unified_transit_data',
    p_hours_back INTEGER DEFAULT 24
)
RETURNS TABLE (
    metric_name VARCHAR(50),
    metric_value NUMERIC,
    threshold_value NUMERIC,
    status VARCHAR(20),
    details TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    record_count BIGINT;
    null_percentage NUMERIC;
    duplicate_percentage NUMERIC;
    data_freshness_minutes NUMERIC;
    temporal_gaps INTEGER;
BEGIN
    -- Get basic metrics based on table
    IF p_table_name = 'unified_transit_data' THEN
        -- Record count
        EXECUTE format('SELECT COUNT(*) FROM %I WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL ''%s hours''', 
                      p_table_name, p_hours_back) INTO record_count;
        
        -- Null percentage for critical fields
        EXECUTE format('
            SELECT 
                COUNT(CASE WHEN route_id IS NULL OR stop_id IS NULL OR timestamp IS NULL THEN 1 END)::NUMERIC 
                / GREATEST(COUNT(*), 1) * 100
            FROM %I 
            WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL ''%s hours''',
            p_table_name, p_hours_back) INTO null_percentage;
        
        -- Data freshness
        EXECUTE format('
            SELECT EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX(timestamp))) / 60.0
            FROM %I',
            p_table_name) INTO data_freshness_minutes;
            
    END IF;
    
    -- Return quality metrics
    RETURN QUERY VALUES
        ('Record Count', record_count::NUMERIC, 1000.0, 
         CASE WHEN record_count >= 1000 THEN 'GOOD' 
              WHEN record_count >= 100 THEN 'WARNING' 
              ELSE 'CRITICAL' END,
         format('Found %s records in last %s hours', record_count, p_hours_back)),
        ('Null Percentage', null_percentage, 5.0,
         CASE WHEN null_percentage <= 5 THEN 'GOOD'
              WHEN null_percentage <= 15 THEN 'WARNING'
              ELSE 'CRITICAL' END,
         format('%.2f%% of critical fields are null', null_percentage)),
        ('Data Freshness (min)', data_freshness_minutes, 15.0,
         CASE WHEN data_freshness_minutes <= 15 THEN 'GOOD'
              WHEN data_freshness_minutes <= 60 THEN 'WARNING'
              ELSE 'CRITICAL' END,
         format('Latest data is %.1f minutes old', data_freshness_minutes));
END;
$$;

-- =============================================
-- PERFORMANCE OPTIMIZATION HELPERS
-- =============================================

-- Analyze and suggest query optimizations
CREATE OR REPLACE FUNCTION analyze_query_performance(
    p_query_pattern TEXT DEFAULT '%gtfs_%',
    p_min_calls INTEGER DEFAULT 10
)
RETURNS TABLE (
    query_snippet TEXT,
    calls BIGINT,
    total_time_ms NUMERIC,
    avg_time_ms NUMERIC,
    hit_percent NUMERIC,
    optimization_suggestion TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        LEFT(pss.query, 100) as query_snippet,
        pss.calls,
        ROUND(pss.total_time, 2) as total_time_ms,
        ROUND(pss.mean_time, 2) as avg_time_ms,
        ROUND(100.0 * pss.shared_blks_hit / GREATEST(pss.shared_blks_hit + pss.shared_blks_read, 1), 1) as hit_percent,
        CASE 
            WHEN pss.mean_time > 1000 THEN 'Consider adding indexes or partitioning'
            WHEN 100.0 * pss.shared_blks_hit / GREATEST(pss.shared_blks_hit + pss.shared_blks_read, 1) < 90 
                THEN 'Low cache hit ratio - consider query optimization'
            WHEN pss.calls > 1000 AND pss.mean_time > 100 
                THEN 'High frequency query - consider materialized views'
            ELSE 'Performance acceptable'
        END as optimization_suggestion
    FROM pg_stat_statements pss
    WHERE pss.query ILIKE p_query_pattern
        AND pss.calls >= p_min_calls
    ORDER BY pss.total_time DESC
    LIMIT 20;
END;
$$;

-- Create optimized indexes based on query patterns
CREATE OR REPLACE FUNCTION create_optimization_indexes()
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    result_msg TEXT := '';
BEGIN
    -- Create commonly needed composite indexes
    BEGIN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_utd_route_time_passenger
            ON unified_transit_data (route_id, timestamp, passenger_count)
            WHERE passenger_count IS NOT NULL;
        result_msg := result_msg || 'Created route-time-passenger index. ';
    EXCEPTION WHEN OTHERS THEN
        result_msg := result_msg || 'Route-time-passenger index failed: ' || SQLERRM || '. ';
    END;
    
    BEGIN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_utd_stop_time_delay
            ON unified_transit_data (stop_id, timestamp, arrival_delay_seconds)
            WHERE arrival_delay_seconds IS NOT NULL;
        result_msg := result_msg || 'Created stop-time-delay index. ';
    EXCEPTION WHEN OTHERS THEN
        result_msg := result_msg || 'Stop-time-delay index failed: ' || SQLERRM || '. ';
    END;
    
    BEGIN
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stop_times_route_time
            ON gtfs_stop_times (stop_id, arrival_seconds, departure_seconds);
        result_msg := result_msg || 'Created stop-times route-time index. ';
    EXCEPTION WHEN OTHERS THEN
        result_msg := result_msg || 'Stop-times route-time index failed: ' || SQLERRM || '. ';
    END;
    
    RETURN result_msg;
END;
$$;

-- Comments for documentation
COMMENT ON FUNCTION get_current_vehicle_positions IS 'Get real-time vehicle positions with route information';
COMMENT ON FUNCTION get_stop_arrivals IS 'Get predicted arrivals for a specific stop';
COMMENT ON FUNCTION get_demand_forecast IS 'Forecast passenger demand using historical patterns';
COMMENT ON FUNCTION get_route_performance IS 'Analyze route performance metrics over time period';
COMMENT ON FUNCTION get_nearby_stops IS 'Find transit stops within walking distance of a location';
COMMENT ON FUNCTION check_data_quality IS 'Monitor data quality metrics and identify issues';