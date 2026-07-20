-- Database tables for external data sources integration
-- This migration creates tables for APC, Weather, and Traffic data

-- =====================================================
-- APC (Automated Passenger Counter) Data Tables
-- =====================================================

-- Raw APC data from API
CREATE TABLE IF NOT EXISTS apc_raw_data (
  id BIGSERIAL PRIMARY KEY,
  vehicle_id VARCHAR(50),
  route_id VARCHAR(50),
  stop_id VARCHAR(50),
  timestamp TIMESTAMPTZ NOT NULL,
  passenger_count INTEGER,
  boarding_count INTEGER,
  alighting_count INTEGER,
  occupancy_percentage DECIMAL(5,2),
  door_open_duration_seconds INTEGER,
  raw_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_apc_raw_vehicle_time ON apc_raw_data(vehicle_id, timestamp DESC);
CREATE INDEX idx_apc_raw_route_time ON apc_raw_data(route_id, timestamp DESC);
CREATE INDEX idx_apc_raw_stop_time ON apc_raw_data(stop_id, timestamp DESC);

-- Processed passenger counts by stop
CREATE TABLE IF NOT EXISTS passenger_counts (
  id BIGSERIAL PRIMARY KEY,
  stop_id VARCHAR(50) NOT NULL,
  route_id VARCHAR(50),
  direction VARCHAR(20),
  timestamp TIMESTAMPTZ NOT NULL,
  hour_of_day INTEGER,
  day_of_week INTEGER,
  passenger_count INTEGER,
  boarding_count INTEGER,
  alighting_count INTEGER,
  occupancy_percentage DECIMAL(5,2),
  is_peak_hour BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(stop_id, route_id, timestamp)
);

CREATE INDEX idx_passenger_counts_stop ON passenger_counts(stop_id, timestamp DESC);
CREATE INDEX idx_passenger_counts_route ON passenger_counts(route_id, timestamp DESC);
CREATE INDEX idx_passenger_counts_time ON passenger_counts(timestamp DESC);

-- Vehicle occupancy tracking
CREATE TABLE IF NOT EXISTS vehicle_occupancy (
  id BIGSERIAL PRIMARY KEY,
  vehicle_id VARCHAR(50) NOT NULL,
  route_id VARCHAR(50),
  timestamp TIMESTAMPTZ NOT NULL,
  current_stop_id VARCHAR(50),
  passenger_count INTEGER,
  capacity INTEGER,
  occupancy_percentage DECIMAL(5,2),
  lat DECIMAL(10, 7),
  lon DECIMAL(10, 7),
  speed_kmh DECIMAL(5,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vehicle_occupancy_vehicle ON vehicle_occupancy(vehicle_id, timestamp DESC);
CREATE INDEX idx_vehicle_occupancy_time ON vehicle_occupancy(timestamp DESC);

-- =====================================================
-- Weather Data Tables
-- =====================================================

-- Current and historical weather observations
CREATE TABLE IF NOT EXISTS weather_data (
  id BIGSERIAL PRIMARY KEY,
  location_name VARCHAR(100),
  lat DECIMAL(10, 7) NOT NULL,
  lon DECIMAL(10, 7) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  temperature_c DECIMAL(5,2),
  feels_like_c DECIMAL(5,2),
  humidity_percent INTEGER,
  pressure_hpa INTEGER,
  weather_main VARCHAR(50),
  weather_description VARCHAR(200),
  weather_id INTEGER,
  wind_speed_ms DECIMAL(5,2),
  wind_direction_deg INTEGER,
  rain_1h_mm DECIMAL(6,2),
  rain_3h_mm DECIMAL(6,2),
  snow_1h_mm DECIMAL(6,2),
  snow_3h_mm DECIMAL(6,2),
  visibility_m INTEGER,
  cloudiness_percent INTEGER,
  weather_severity INTEGER, -- 0-10 scale
  raw_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(lat, lon, timestamp)
);

CREATE INDEX idx_weather_location_time ON weather_data(lat, lon, timestamp DESC);
CREATE INDEX idx_weather_time ON weather_data(timestamp DESC);
CREATE INDEX idx_weather_severity ON weather_data(weather_severity, timestamp DESC);

-- Weather forecasts
CREATE TABLE IF NOT EXISTS weather_forecasts (
  id BIGSERIAL PRIMARY KEY,
  location_name VARCHAR(100),
  lat DECIMAL(10, 7) NOT NULL,
  lon DECIMAL(10, 7) NOT NULL,
  forecast_time TIMESTAMPTZ NOT NULL,
  forecast_type VARCHAR(20), -- hourly, daily
  temperature_c DECIMAL(5,2),
  feels_like_c DECIMAL(5,2),
  humidity_percent INTEGER,
  weather_main VARCHAR(50),
  weather_description VARCHAR(200),
  precipitation_probability DECIMAL(3,2),
  rain_volume_mm DECIMAL(6,2),
  snow_volume_mm DECIMAL(6,2),
  wind_speed_ms DECIMAL(5,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  UNIQUE(lat, lon, forecast_time, forecast_type)
);

CREATE INDEX idx_weather_forecast_location ON weather_forecasts(lat, lon, forecast_time DESC);
CREATE INDEX idx_weather_forecast_time ON weather_forecasts(forecast_time DESC);

-- =====================================================
-- Traffic Data Tables
-- =====================================================

-- Real-time traffic flow data
CREATE TABLE IF NOT EXISTS traffic_flow (
  id BIGSERIAL PRIMARY KEY,
  road_segment_id VARCHAR(100),
  lat DECIMAL(10, 7),
  lon DECIMAL(10, 7),
  timestamp TIMESTAMPTZ NOT NULL,
  current_speed_kmh DECIMAL(5,2),
  free_flow_speed_kmh DECIMAL(5,2),
  current_travel_time_seconds INTEGER,
  free_flow_travel_time_seconds INTEGER,
  congestion_level VARCHAR(20), -- free_flow, light, moderate, heavy, severe
  congestion_ratio DECIMAL(3,2),
  confidence DECIMAL(3,2),
  raw_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_traffic_flow_segment ON traffic_flow(road_segment_id, timestamp DESC);
CREATE INDEX idx_traffic_flow_location ON traffic_flow(lat, lon, timestamp DESC);
CREATE INDEX idx_traffic_flow_time ON traffic_flow(timestamp DESC);
CREATE INDEX idx_traffic_flow_congestion ON traffic_flow(congestion_level, timestamp DESC);

-- Traffic incidents and events
CREATE TABLE IF NOT EXISTS traffic_incidents (
  id BIGSERIAL PRIMARY KEY,
  incident_id VARCHAR(100) UNIQUE,
  lat DECIMAL(10, 7),
  lon DECIMAL(10, 7),
  timestamp TIMESTAMPTZ NOT NULL,
  incident_type VARCHAR(50),
  severity INTEGER, -- 1-5 scale
  description TEXT,
  road_closed BOOLEAN,
  start_time TIMESTAMPTZ,
  end_time TIMESTAMPTZ,
  delay_minutes INTEGER,
  affected_routes TEXT[],
  raw_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_traffic_incidents_location ON traffic_incidents(lat, lon, timestamp DESC);
CREATE INDEX idx_traffic_incidents_time ON traffic_incidents(timestamp DESC);
CREATE INDEX idx_traffic_incidents_severity ON traffic_incidents(severity, timestamp DESC);

-- Route-specific traffic conditions
CREATE TABLE IF NOT EXISTS route_traffic (
  id BIGSERIAL PRIMARY KEY,
  route_id VARCHAR(50) NOT NULL,
  segment_id VARCHAR(100),
  timestamp TIMESTAMPTZ NOT NULL,
  origin_lat DECIMAL(10, 7),
  origin_lon DECIMAL(10, 7),
  dest_lat DECIMAL(10, 7),
  dest_lon DECIMAL(10, 7),
  route_length_meters INTEGER,
  travel_time_seconds INTEGER,
  traffic_delay_seconds INTEGER,
  delay_ratio DECIMAL(3,2),
  traffic_index DECIMAL(3,1), -- 0-10 scale
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_route_traffic_route ON route_traffic(route_id, timestamp DESC);
CREATE INDEX idx_route_traffic_time ON route_traffic(timestamp DESC);

-- =====================================================
-- Data Quality and Monitoring Tables
-- =====================================================

-- Data ingestion logs
CREATE TABLE IF NOT EXISTS data_ingestion_logs (
  id BIGSERIAL PRIMARY KEY,
  source_type VARCHAR(50), -- apc, weather, traffic
  ingestion_time TIMESTAMPTZ NOT NULL,
  records_processed INTEGER,
  records_failed INTEGER,
  start_time TIMESTAMPTZ,
  end_time TIMESTAMPTZ,
  status VARCHAR(20), -- success, partial, failed
  error_message TEXT,
  execution_time_seconds DECIMAL(10,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ingestion_logs_source ON data_ingestion_logs(source_type, ingestion_time DESC);
CREATE INDEX idx_ingestion_logs_status ON data_ingestion_logs(status, ingestion_time DESC);

-- Data quality metrics
CREATE TABLE IF NOT EXISTS data_quality_metrics (
  id BIGSERIAL PRIMARY KEY,
  source_type VARCHAR(50),
  metric_name VARCHAR(100),
  metric_value DECIMAL(10,4),
  threshold_value DECIMAL(10,4),
  is_passing BOOLEAN,
  evaluated_at TIMESTAMPTZ NOT NULL,
  details JSONB
);

CREATE INDEX idx_quality_metrics_source ON data_quality_metrics(source_type, evaluated_at DESC);
CREATE INDEX idx_quality_metrics_passing ON data_quality_metrics(is_passing, evaluated_at DESC);

-- =====================================================
-- Views for Easy Data Access
-- =====================================================

-- Current weather conditions view
CREATE OR REPLACE VIEW current_weather AS
SELECT DISTINCT ON (lat, lon)
  lat,
  lon,
  location_name,
  timestamp,
  temperature_c,
  weather_main,
  weather_description,
  weather_severity,
  wind_speed_ms,
  rain_1h_mm
FROM weather_data
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY lat, lon, timestamp DESC;

-- Current traffic conditions view
CREATE OR REPLACE VIEW current_traffic_conditions AS
SELECT DISTINCT ON (road_segment_id)
  road_segment_id,
  lat,
  lon,
  timestamp,
  current_speed_kmh,
  free_flow_speed_kmh,
  congestion_level,
  congestion_ratio
FROM traffic_flow
WHERE timestamp > NOW() - INTERVAL '15 minutes'
ORDER BY road_segment_id, timestamp DESC;

-- Stop occupancy trends view
CREATE OR REPLACE VIEW stop_occupancy_trends AS
SELECT
  stop_id,
  DATE_TRUNC('hour', timestamp) as hour,
  AVG(passenger_count) as avg_passengers,
  MAX(passenger_count) as max_passengers,
  AVG(occupancy_percentage) as avg_occupancy,
  COUNT(*) as sample_count
FROM passenger_counts
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY stop_id, DATE_TRUNC('hour', timestamp)
ORDER BY stop_id, hour DESC;

-- =====================================================
-- Row Level Security Policies
-- =====================================================

-- Enable RLS on external data tables
ALTER TABLE weather_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE traffic_flow ENABLE ROW LEVEL SECURITY;
ALTER TABLE traffic_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE passenger_counts ENABLE ROW LEVEL SECURITY;

-- Public read access for weather data
CREATE POLICY "Public read weather data" ON weather_data
  FOR SELECT USING (true);

CREATE POLICY "Public read weather forecasts" ON weather_forecasts
  FOR SELECT USING (true);

-- Public read access for traffic data
CREATE POLICY "Public read traffic flow" ON traffic_flow
  FOR SELECT USING (true);

CREATE POLICY "Public read traffic incidents" ON traffic_incidents
  FOR SELECT USING (true);

-- Public read access for aggregated passenger data
CREATE POLICY "Public read passenger counts" ON passenger_counts
  FOR SELECT USING (true);

-- =====================================================
-- Functions for Data Management
-- =====================================================

-- Function to clean up old external data
CREATE OR REPLACE FUNCTION cleanup_old_external_data()
RETURNS void AS $$
BEGIN
  -- Clean up old weather data (keep 90 days)
  DELETE FROM weather_data WHERE timestamp < NOW() - INTERVAL '90 days';
  DELETE FROM weather_forecasts WHERE expires_at < NOW();

  -- Clean up old traffic data (keep 30 days)
  DELETE FROM traffic_flow WHERE timestamp < NOW() - INTERVAL '30 days';
  DELETE FROM traffic_incidents WHERE end_time < NOW() - INTERVAL '30 days';

  -- Clean up old APC data (keep 180 days raw, aggregate older)
  DELETE FROM apc_raw_data WHERE timestamp < NOW() - INTERVAL '180 days';

  -- Clean up old logs (keep 30 days)
  DELETE FROM data_ingestion_logs WHERE ingestion_time < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT ON current_weather TO anon, authenticated;
GRANT SELECT ON current_traffic_conditions TO anon, authenticated;
GRANT SELECT ON stop_occupancy_trends TO anon, authenticated;

SELECT 'External data tables created successfully!' as status;