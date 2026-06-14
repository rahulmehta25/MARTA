-- MARTA Platform - Enhanced Materialized Views
-- Improved analytics queries with weather/event correlation and pipeline monitoring

-- =============================================
-- DROP EXISTING VIEWS FOR RECREATION
-- =============================================
-- (Only drop if exists to allow safe re-run)

-- =============================================
-- REAL-TIME OPERATIONS DASHBOARD
-- =============================================

-- Current Fleet Status (Refresh every minute)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_fleet_status AS
SELECT
    vp.route_id,
    r.route_short_name,
    r.route_long_name,
    COUNT(DISTINCT vp.vehicle_id) as active_vehicles,
    COUNT(DISTINCT vp.trip_id) as active_trips,

    -- Position metrics
    AVG(vp.speed) as avg_speed_mps,
    MAX(vp.timestamp) as last_position_update,

    -- Status breakdown
    SUM(CASE WHEN vp.current_status = 'STOPPED_AT' THEN 1 ELSE 0 END) as vehicles_at_stop,
    SUM(CASE WHEN vp.current_status = 'IN_TRANSIT_TO' THEN 1 ELSE 0 END) as vehicles_in_transit,

    -- Congestion levels
    SUM(CASE WHEN vp.congestion_level = 'CONGESTION' THEN 1 ELSE 0 END) as congested_vehicles,

    -- Occupancy
    AVG(CASE vp.occupancy_status
        WHEN 'EMPTY' THEN 0
        WHEN 'MANY_SEATS_AVAILABLE' THEN 25
        WHEN 'FEW_SEATS_AVAILABLE' THEN 50
        WHEN 'STANDING_ROOM_ONLY' THEN 75
        WHEN 'CRUSHED_STANDING_ROOM_ONLY' THEN 90
        WHEN 'FULL' THEN 100
        ELSE NULL
    END) as avg_occupancy_percent,

    CURRENT_TIMESTAMP as snapshot_time

FROM gtfs_vehicle_positions vp
LEFT JOIN gtfs_routes r ON vp.route_id = r.route_id
WHERE vp.timestamp >= CURRENT_TIMESTAMP - INTERVAL '15 minutes'
GROUP BY vp.route_id, r.route_short_name, r.route_long_name;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_fleet_status_pk
    ON mv_fleet_status (route_id);

-- =============================================
-- DELAY ANALYSIS VIEWS
-- =============================================

-- Hourly Delay Patterns by Route (Refresh every 15 minutes)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_delay_patterns AS
SELECT
    tu.route_id,
    r.route_short_name,
    EXTRACT(hour FROM tu.timestamp) as hour_of_day,
    EXTRACT(dow FROM tu.timestamp) as day_of_week,

    -- Delay statistics
    COUNT(*) as observation_count,
    AVG(tu.arrival_delay) as avg_arrival_delay_sec,
    AVG(tu.departure_delay) as avg_departure_delay_sec,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tu.arrival_delay) as median_delay_sec,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY tu.arrival_delay) as p90_delay_sec,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tu.arrival_delay) as p95_delay_sec,
    STDDEV(tu.arrival_delay) as delay_volatility,

    -- On-time performance (within 5 minutes)
    COUNT(CASE WHEN ABS(tu.arrival_delay) <= 300 THEN 1 END)::FLOAT /
        NULLIF(COUNT(*), 0) as on_time_rate,

    -- Severe delays (>10 minutes)
    COUNT(CASE WHEN tu.arrival_delay > 600 THEN 1 END) as severe_delay_count,

    CURRENT_TIMESTAMP as last_updated

FROM gtfs_trip_updates tu
JOIN gtfs_routes r ON tu.route_id = r.route_id
WHERE tu.timestamp >= CURRENT_DATE - INTERVAL '14 days'
    AND tu.arrival_delay IS NOT NULL
GROUP BY
    tu.route_id, r.route_short_name,
    EXTRACT(hour FROM tu.timestamp),
    EXTRACT(dow FROM tu.timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_delay_patterns_pk
    ON mv_hourly_delay_patterns (route_id, hour_of_day, day_of_week);

-- =============================================
-- WEATHER-TRANSIT CORRELATION VIEWS
-- =============================================

-- Weather Impact on Transit (Refresh hourly)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weather_transit_impact AS
WITH hourly_transit AS (
    SELECT
        DATE_TRUNC('hour', tu.timestamp) as hour,
        COUNT(*) as trip_updates,
        AVG(tu.arrival_delay) as avg_delay,
        COUNT(CASE WHEN tu.arrival_delay > 300 THEN 1 END) as delayed_trips
    FROM gtfs_trip_updates tu
    WHERE tu.timestamp >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE_TRUNC('hour', tu.timestamp)
),
hourly_weather AS (
    SELECT
        DATE_TRUNC('hour', timestamp) as hour,
        AVG(temperature_c) as avg_temp,
        MAX(precipitation_mm) as max_precip,
        MAX(wind_speed_mps) as max_wind,
        MODE() WITHIN GROUP (ORDER BY weather_main) as primary_condition,
        BOOL_OR(is_precipitation) as had_precipitation,
        BOOL_OR(is_severe_weather) as had_severe_weather
    FROM weather_data
    WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE_TRUNC('hour', timestamp)
)
SELECT
    hw.hour,
    hw.avg_temp,
    hw.max_precip,
    hw.max_wind,
    hw.primary_condition,
    hw.had_precipitation,
    hw.had_severe_weather,
    ht.trip_updates,
    ht.avg_delay,
    ht.delayed_trips,

    -- Delay impact factor (compared to average)
    ht.avg_delay / NULLIF(AVG(ht.avg_delay) OVER (), 0) as delay_impact_factor,

    CURRENT_TIMESTAMP as last_updated

FROM hourly_weather hw
LEFT JOIN hourly_transit ht ON hw.hour = ht.hour
WHERE ht.trip_updates IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_weather_impact_pk
    ON mv_weather_transit_impact (hour);

-- Weather Condition Summary (for dashboard)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weather_condition_summary AS
SELECT
    weather_main as condition,
    COUNT(*) as occurrence_count,
    AVG(temperature_c) as avg_temp,
    AVG(precipitation_mm) as avg_precip,

    -- Transit impact when this condition occurs
    AVG(wtc.avg_delay_seconds) as avg_transit_delay,
    AVG(wtc.avg_ridership) as avg_ridership

FROM weather_data wd
LEFT JOIN weather_transit_correlation wtc
    ON DATE(wd.timestamp) = wtc.date
    AND EXTRACT(hour FROM wd.timestamp) = wtc.hour
WHERE wd.timestamp >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY weather_main
ORDER BY occurrence_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_weather_summary_pk
    ON mv_weather_condition_summary (condition);

-- =============================================
-- EVENT IMPACT VIEWS
-- =============================================

-- Event Impact on Transit (Refresh daily)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_event_transit_impact AS
WITH event_hours AS (
    SELECT
        event_date,
        EXTRACT(hour FROM event_time) as event_hour,
        venue_name,
        event_type,
        estimated_attendance,
        venue_lat,
        venue_lon
    FROM atlanta_events_data
    WHERE event_date >= CURRENT_DATE - INTERVAL '90 days'
),
nearby_stops AS (
    SELECT
        eh.*,
        s.stop_id,
        ST_Distance(
            ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)::geography,
            ST_SetSRID(ST_MakePoint(eh.venue_lon, eh.venue_lat), 4326)::geography
        ) as distance_meters
    FROM event_hours eh
    CROSS JOIN gtfs_stops s
    WHERE ST_DWithin(
        ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)::geography,
        ST_SetSRID(ST_MakePoint(eh.venue_lon, eh.venue_lat), 4326)::geography,
        1500  -- 1.5km radius
    )
)
SELECT
    ns.event_date,
    ns.venue_name,
    ns.event_type,
    ns.estimated_attendance,
    COUNT(DISTINCT ns.stop_id) as nearby_stops,
    AVG(ns.distance_meters) as avg_distance_to_stops,

    CURRENT_TIMESTAMP as last_updated

FROM nearby_stops ns
GROUP BY ns.event_date, ns.venue_name, ns.event_type, ns.estimated_attendance;

CREATE INDEX IF NOT EXISTS idx_mv_event_impact_date
    ON mv_event_transit_impact (event_date);

-- =============================================
-- STOP UTILIZATION VIEWS
-- =============================================

-- Stop Utilization Heatmap Data (Refresh every 30 minutes)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_stop_utilization AS
SELECT
    s.stop_id,
    s.stop_name,
    s.stop_lat,
    s.stop_lon,
    EXTRACT(hour FROM tu.timestamp) as hour_of_day,

    -- Activity metrics
    COUNT(*) as stop_events,
    COUNT(DISTINCT tu.trip_id) as unique_trips,
    COUNT(DISTINCT tu.route_id) as routes_serving,

    -- Delay at stop
    AVG(tu.arrival_delay) as avg_delay_at_stop,

    -- Busyness category
    CASE
        WHEN COUNT(*) > 100 THEN 'very_high'
        WHEN COUNT(*) > 50 THEN 'high'
        WHEN COUNT(*) > 20 THEN 'medium'
        ELSE 'low'
    END as utilization_level,

    CURRENT_TIMESTAMP as last_updated

FROM gtfs_stops s
LEFT JOIN gtfs_trip_updates tu ON s.stop_id = tu.stop_id
WHERE tu.timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY
    s.stop_id, s.stop_name, s.stop_lat, s.stop_lon,
    EXTRACT(hour FROM tu.timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_stop_util_pk
    ON mv_stop_utilization (stop_id, hour_of_day);
CREATE INDEX IF NOT EXISTS idx_mv_stop_util_level
    ON mv_stop_utilization (utilization_level);

-- =============================================
-- PIPELINE MONITORING VIEWS
-- =============================================

-- Pipeline Health Dashboard (Refresh every 5 minutes)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_pipeline_health AS
WITH job_stats AS (
    SELECT
        job_name,
        COUNT(*) as total_runs,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
        AVG(duration_seconds) as avg_duration,
        MAX(completed_at) as last_run,
        SUM(records_processed) as total_records
    FROM pipeline_job_status
    WHERE started_at >= NOW() - INTERVAL '24 hours'
    GROUP BY job_name
),
quality_stats AS (
    SELECT
        COUNT(*) as total_checks,
        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed_checks,
        SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) as failed_checks
    FROM data_quality_metrics
    WHERE check_timestamp >= NOW() - INTERVAL '24 hours'
),
freshness_stats AS (
    SELECT
        COUNT(*) as tables_tracked,
        SUM(CASE WHEN last_successful_ingestion >= NOW() - INTERVAL '1 hour' THEN 1 ELSE 0 END) as fresh_tables
    FROM ingestion_timestamps
)
SELECT
    (SELECT SUM(total_runs) FROM job_stats) as total_pipeline_runs,
    (SELECT SUM(successful_runs) FROM job_stats) as successful_runs,
    (SELECT SUM(failed_runs) FROM job_stats) as failed_runs,
    (SELECT AVG(avg_duration) FROM job_stats) as avg_job_duration,
    (SELECT total_checks FROM quality_stats) as quality_checks_run,
    (SELECT passed_checks FROM quality_stats) as quality_checks_passed,
    (SELECT tables_tracked FROM freshness_stats) as tables_monitored,
    (SELECT fresh_tables FROM freshness_stats) as tables_fresh,
    CURRENT_TIMESTAMP as snapshot_time;

-- Data Quality Trends (Refresh hourly)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_quality_trends AS
SELECT
    DATE_TRUNC('hour', check_timestamp) as hour,
    check_type,
    COUNT(*) as check_count,
    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'warning' THEN 1 ELSE 0 END) as warnings,
    SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) as failures,
    AVG(metric_value) as avg_metric_value,

    CURRENT_TIMESTAMP as last_updated

FROM data_quality_metrics
WHERE check_timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', check_timestamp), check_type;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_quality_trends_pk
    ON mv_quality_trends (hour, check_type);

-- =============================================
-- ML FEATURE STORE VIEWS
-- =============================================

-- Pre-computed ML Features (Refresh hourly)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ml_demand_features AS
WITH base_data AS (
    SELECT
        tu.stop_id,
        tu.route_id,
        tu.timestamp,
        tu.arrival_delay,

        -- Temporal features
        EXTRACT(hour FROM tu.timestamp) as hour,
        EXTRACT(dow FROM tu.timestamp) as dow,
        EXTRACT(day FROM tu.timestamp) as day_of_month,
        EXTRACT(month FROM tu.timestamp) as month,

        -- Weather join
        w.temperature_c,
        w.precipitation_mm,
        w.is_precipitation,
        w.comfort_index,
        w.weather_main

    FROM gtfs_trip_updates tu
    LEFT JOIN LATERAL (
        SELECT * FROM weather_data wd
        WHERE wd.timestamp <= tu.timestamp
        ORDER BY wd.timestamp DESC
        LIMIT 1
    ) w ON true
    WHERE tu.timestamp >= CURRENT_DATE - INTERVAL '30 days'
)
SELECT
    stop_id,
    route_id,
    hour,
    dow,

    -- Demand aggregates
    COUNT(*) as trip_count,
    AVG(arrival_delay) as avg_delay,

    -- Temporal encodings
    SIN(2 * PI() * hour / 24) as hour_sin,
    COS(2 * PI() * hour / 24) as hour_cos,
    SIN(2 * PI() * dow / 7) as dow_sin,
    COS(2 * PI() * dow / 7) as dow_cos,

    -- Weather features
    AVG(temperature_c) as avg_temp,
    AVG(precipitation_mm) as avg_precip,
    MAX(is_precipitation::int) as had_precipitation,
    AVG(comfort_index) as avg_comfort_index,

    -- Is weekend flag
    CASE WHEN dow IN (0, 6) THEN 1 ELSE 0 END as is_weekend,

    CURRENT_TIMESTAMP as last_updated

FROM base_data
GROUP BY stop_id, route_id, hour, dow;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ml_features_pk
    ON mv_ml_demand_features (stop_id, route_id, hour, dow);

-- =============================================
-- REFRESH FUNCTIONS
-- =============================================

-- Automated refresh scheduler
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    start_time TIMESTAMP;
BEGIN
    start_time := CURRENT_TIMESTAMP;

    -- High frequency (every 5 minutes)
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_fleet_status;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pipeline_health;

    -- Medium frequency (every 15 minutes)
    IF EXTRACT(minute FROM CURRENT_TIMESTAMP) % 15 < 5 THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_delay_patterns;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stop_utilization;
    END IF;

    -- Hourly
    IF EXTRACT(minute FROM CURRENT_TIMESTAMP) < 5 THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_weather_transit_impact;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_weather_condition_summary;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_quality_trends;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ml_demand_features;
    END IF;

    -- Daily (at 2 AM)
    IF EXTRACT(hour FROM CURRENT_TIMESTAMP) = 2 AND EXTRACT(minute FROM CURRENT_TIMESTAMP) < 5 THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_event_transit_impact;
    END IF;

    RAISE NOTICE 'Materialized views refreshed in % seconds',
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - start_time));
END;
$$;

-- Grant appropriate permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO PUBLIC;

-- Comments for documentation
COMMENT ON MATERIALIZED VIEW mv_fleet_status IS 'Real-time fleet status with vehicle positions and occupancy';
COMMENT ON MATERIALIZED VIEW mv_hourly_delay_patterns IS 'Delay patterns by route, hour, and day of week';
COMMENT ON MATERIALIZED VIEW mv_weather_transit_impact IS 'Correlation between weather conditions and transit delays';
COMMENT ON MATERIALIZED VIEW mv_weather_condition_summary IS 'Summary statistics by weather condition type';
COMMENT ON MATERIALIZED VIEW mv_event_transit_impact IS 'Impact of local events on nearby transit stops';
COMMENT ON MATERIALIZED VIEW mv_stop_utilization IS 'Stop utilization heatmap data by hour';
COMMENT ON MATERIALIZED VIEW mv_pipeline_health IS 'Pipeline monitoring dashboard data';
COMMENT ON MATERIALIZED VIEW mv_quality_trends IS 'Data quality check trends over time';
COMMENT ON MATERIALIZED VIEW mv_ml_demand_features IS 'Pre-computed features for ML demand forecasting';
