-- Create ML-related tables for MARTA Analytics

-- Table for storing stop metrics and historical data
CREATE TABLE IF NOT EXISTS stop_metrics (
  id BIGSERIAL PRIMARY KEY,
  stop_id VARCHAR(50) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  passenger_count INTEGER DEFAULT 0,
  boarding_count INTEGER DEFAULT 0,
  alighting_count INTEGER DEFAULT 0,
  dwell_time_seconds INTEGER,
  occupancy_percentage DECIMAL(5,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(stop_id, timestamp)
);

-- Index for efficient queries
CREATE INDEX idx_stop_metrics_stop_time ON stop_metrics(stop_id, timestamp DESC);
CREATE INDEX idx_stop_metrics_timestamp ON stop_metrics(timestamp DESC);

-- Table for demand predictions
CREATE TABLE IF NOT EXISTS demand_predictions (
  id BIGSERIAL PRIMARY KEY,
  stop_id VARCHAR(50) NOT NULL,
  predictions JSONB NOT NULL,
  model_version VARCHAR(20),
  model_confidence DECIMAL(3,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);

CREATE INDEX idx_demand_predictions_stop ON demand_predictions(stop_id, created_at DESC);

-- Table for surge events
CREATE TABLE IF NOT EXISTS surge_events (
  id BIGSERIAL PRIMARY KEY,
  location_id VARCHAR(50) NOT NULL,
  location_type VARCHAR(20) DEFAULT 'stop',
  surge_magnitude DECIMAL(5,2) NOT NULL,
  surge_start_time TIMESTAMPTZ NOT NULL,
  surge_end_time TIMESTAMPTZ,
  confidence DECIMAL(3,2),
  contributing_factors TEXT[],
  affected_areas TEXT[],
  recommended_actions TEXT[],
  external_factors JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_surge_events_location ON surge_events(location_id, surge_start_time DESC);
CREATE INDEX idx_surge_events_time ON surge_events(surge_start_time DESC);

-- Table for crowding alerts
CREATE TABLE IF NOT EXISTS crowding_alerts (
  id BIGSERIAL PRIMARY KEY,
  stop_id VARCHAR(50) NOT NULL,
  route_id VARCHAR(50) NOT NULL,
  vehicle_id VARCHAR(50),
  crowding_level VARCHAR(20) NOT NULL,
  current_occupancy INTEGER NOT NULL,
  capacity INTEGER NOT NULL,
  occupancy_percentage DECIMAL(5,2),
  predicted_duration_minutes INTEGER,
  recommended_actions TEXT[],
  affected_stops TEXT[],
  alternative_routes TEXT[],
  alert_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_time TIMESTAMPTZ,
  status VARCHAR(20) DEFAULT 'active'
);

CREATE INDEX idx_crowding_alerts_stop_route ON crowding_alerts(stop_id, route_id, alert_time DESC);
CREATE INDEX idx_crowding_alerts_status ON crowding_alerts(status, alert_time DESC);

-- Table for route optimization results
CREATE TABLE IF NOT EXISTS route_optimizations (
  id BIGSERIAL PRIMARY KEY,
  route_id VARCHAR(50) NOT NULL,
  optimization_type VARCHAR(50),
  original_config JSONB,
  optimized_config JSONB,
  improvements JSONB,
  expected_wait_time DECIMAL(5,2),
  expected_travel_time DECIMAL(5,2),
  capacity_utilization DECIMAL(5,2),
  improvement_percentage DECIMAL(5,2),
  status VARCHAR(20) DEFAULT 'proposed',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  implemented_at TIMESTAMPTZ
);

CREATE INDEX idx_route_optimizations_route ON route_optimizations(route_id, created_at DESC);

-- Table for fleet repositioning commands
CREATE TABLE IF NOT EXISTS fleet_repositioning (
  id BIGSERIAL PRIMARY KEY,
  vehicle_id VARCHAR(50) NOT NULL,
  from_location VARCHAR(100),
  to_location VARCHAR(100) NOT NULL,
  reason TEXT,
  surge_magnitude DECIMAL(5,2),
  priority VARCHAR(20) DEFAULT 'normal',
  estimated_arrival TIMESTAMPTZ,
  command_time TIMESTAMPTZ DEFAULT NOW(),
  execution_time TIMESTAMPTZ,
  completion_time TIMESTAMPTZ,
  status VARCHAR(20) DEFAULT 'pending'
);

CREATE INDEX idx_fleet_repositioning_vehicle ON fleet_repositioning(vehicle_id, command_time DESC);
CREATE INDEX idx_fleet_repositioning_status ON fleet_repositioning(status, command_time DESC);

-- Table for ML model performance metrics
CREATE TABLE IF NOT EXISTS ml_model_metrics (
  id BIGSERIAL PRIMARY KEY,
  model_name VARCHAR(50) NOT NULL,
  model_version VARCHAR(20) NOT NULL,
  metric_type VARCHAR(50) NOT NULL,
  metric_value DECIMAL(10,4),
  evaluation_data JSONB,
  evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ml_model_metrics ON ml_model_metrics(model_name, model_version, evaluated_at DESC);

-- Real-time data aggregation view
CREATE OR REPLACE VIEW current_system_status AS
SELECT
  (SELECT COUNT(*) FROM crowding_alerts WHERE status = 'active') as active_crowding_alerts,
  (SELECT COUNT(*) FROM surge_events WHERE surge_end_time IS NULL) as active_surges,
  (SELECT COUNT(*) FROM fleet_repositioning WHERE status = 'pending') as pending_repositions,
  (SELECT AVG(occupancy_percentage) FROM stop_metrics WHERE timestamp > NOW() - INTERVAL '1 hour') as avg_system_occupancy,
  (SELECT COUNT(DISTINCT stop_id) FROM stop_metrics WHERE timestamp > NOW() - INTERVAL '5 minutes') as reporting_stops,
  NOW() as last_updated;

-- Function to clean up old predictions
CREATE OR REPLACE FUNCTION cleanup_old_predictions()
RETURNS void AS $$
BEGIN
  DELETE FROM demand_predictions WHERE expires_at < NOW();
  DELETE FROM stop_metrics WHERE timestamp < NOW() - INTERVAL '90 days';
  DELETE FROM surge_events WHERE surge_start_time < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to run cleanup (requires pg_cron extension)
-- SELECT cron.schedule('cleanup-predictions', '0 2 * * *', 'SELECT cleanup_old_predictions();');