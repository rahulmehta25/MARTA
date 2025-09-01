-- MARTA Transit Analytics Database Schema for Supabase
-- Free tier: 500MB storage, unlimited API requests

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis"; -- For geo queries if needed

-- Stations table
CREATE TABLE IF NOT EXISTS stations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    station_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    lat DECIMAL(10, 8),
    lon DECIMAL(11, 8),
    lines JSONB DEFAULT '[]', -- Array of lines serving this station
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Create index for station lookups
CREATE INDEX idx_stations_station_id ON stations(station_id);
CREATE INDEX idx_stations_lines ON stations USING GIN(lines);

-- Real-time arrivals table
CREATE TABLE IF NOT EXISTS arrivals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    station_id TEXT NOT NULL,
    line TEXT NOT NULL,
    destination TEXT NOT NULL,
    direction TEXT,
    arrival_time TEXT,
    waiting_seconds INTEGER,
    delay_seconds INTEGER DEFAULT 0,
    train_id TEXT,
    event_time TIMESTAMP WITH TIME ZONE,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    -- Add check constraints
    CONSTRAINT valid_line CHECK (line IN ('RED', 'GOLD', 'GREEN', 'BLUE')),
    CONSTRAINT valid_direction CHECK (direction IN ('N', 'S', 'E', 'W'))
);

-- Indexes for performance
CREATE INDEX idx_arrivals_station ON arrivals(station_id);
CREATE INDEX idx_arrivals_collected_at ON arrivals(collected_at DESC);
CREATE INDEX idx_arrivals_line ON arrivals(line);
CREATE INDEX idx_arrivals_train ON arrivals(train_id);

-- Hourly statistics (materialized for performance)
CREATE TABLE IF NOT EXISTS hourly_stats (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    station_id TEXT NOT NULL,
    line TEXT,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    avg_delay_seconds DECIMAL(10, 2),
    avg_waiting_seconds DECIMAL(10, 2),
    total_arrivals INTEGER DEFAULT 0,
    on_time_percentage DECIMAL(5, 2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    -- Unique constraint for one record per station/line/hour/day
    UNIQUE(station_id, line, hour, day_of_week)
);

CREATE INDEX idx_hourly_stats_lookup ON hourly_stats(station_id, line, hour, day_of_week);

-- System health metrics (for dashboard)
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    metric_time TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    active_trains INTEGER,
    active_stations INTEGER,
    total_delays INTEGER,
    avg_delay_seconds DECIMAL(10, 2),
    lines_status JSONB DEFAULT '{}',
    health_score INTEGER CHECK (health_score >= 0 AND health_score <= 100)
);

CREATE INDEX idx_metrics_time ON system_metrics(metric_time DESC);

-- Predictions table (for ML results)
CREATE TABLE IF NOT EXISTS predictions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    station_id TEXT NOT NULL,
    line TEXT,
    prediction_time TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    predicted_arrival TIMESTAMP WITH TIME ZONE,
    confidence DECIMAL(3, 2) CHECK (confidence >= 0 AND confidence <= 1),
    model_version TEXT,
    actual_arrival TIMESTAMP WITH TIME ZONE, -- For accuracy tracking
    error_seconds INTEGER -- Prediction error in seconds
);

CREATE INDEX idx_predictions_station ON predictions(station_id, prediction_time DESC);

-- Create views for common queries

-- Current system status view
CREATE OR REPLACE VIEW current_system_status AS
SELECT 
    COUNT(DISTINCT station_id) as active_stations,
    COUNT(DISTINCT train_id) as active_trains,
    COUNT(*) as recent_arrivals,
    AVG(delay_seconds) as avg_delay,
    COUNT(CASE WHEN delay_seconds > 300 THEN 1 END) as major_delays
FROM arrivals
WHERE collected_at > NOW() - INTERVAL '30 minutes';

-- Station performance view
CREATE OR REPLACE VIEW station_performance AS
SELECT 
    station_id,
    line,
    DATE(collected_at) as date,
    COUNT(*) as total_arrivals,
    AVG(delay_seconds) as avg_delay,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delay_seconds) as median_delay,
    MAX(delay_seconds) as max_delay,
    SUM(CASE WHEN delay_seconds <= 60 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as on_time_pct
FROM arrivals
WHERE collected_at > NOW() - INTERVAL '7 days'
GROUP BY station_id, line, DATE(collected_at);

-- Enable Row Level Security (RLS)
ALTER TABLE arrivals ENABLE ROW LEVEL SECURITY;
ALTER TABLE stations ENABLE ROW LEVEL SECURITY;
ALTER TABLE hourly_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access
CREATE POLICY "Public read access" ON arrivals FOR SELECT USING (true);
CREATE POLICY "Public read access" ON stations FOR SELECT USING (true);
CREATE POLICY "Public read access" ON hourly_stats FOR SELECT USING (true);
CREATE POLICY "Public read access" ON system_metrics FOR SELECT USING (true);
CREATE POLICY "Public read access" ON predictions FOR SELECT USING (true);

-- Functions for analytics

-- Function to get station delays by hour
CREATE OR REPLACE FUNCTION get_station_delays(
    p_station_id TEXT,
    p_hours INTEGER DEFAULT 24
)
RETURNS TABLE (
    hour INTEGER,
    line TEXT,
    avg_delay DECIMAL,
    max_delay INTEGER,
    sample_size INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        EXTRACT(HOUR FROM collected_at)::INTEGER as hour,
        a.line,
        AVG(delay_seconds)::DECIMAL as avg_delay,
        MAX(delay_seconds) as max_delay,
        COUNT(*)::INTEGER as sample_size
    FROM arrivals a
    WHERE a.station_id = p_station_id
        AND a.collected_at > NOW() - (p_hours || ' hours')::INTERVAL
    GROUP BY EXTRACT(HOUR FROM collected_at), a.line
    ORDER BY hour, a.line;
END;
$$ LANGUAGE plpgsql;

-- Function to predict next arrival
CREATE OR REPLACE FUNCTION predict_next_arrival(
    p_station_id TEXT,
    p_line TEXT DEFAULT NULL
)
RETURNS TABLE (
    predicted_minutes INTEGER,
    confidence DECIMAL,
    based_on_samples INTEGER
) AS $$
DECLARE
    current_hour INTEGER;
    current_dow INTEGER;
BEGIN
    current_hour := EXTRACT(HOUR FROM NOW());
    current_dow := EXTRACT(DOW FROM NOW());
    
    RETURN QUERY
    SELECT 
        avg_waiting_seconds::INTEGER / 60 as predicted_minutes,
        LEAST(total_arrivals::DECIMAL / 20, 1.0) as confidence,
        total_arrivals as based_on_samples
    FROM hourly_stats
    WHERE station_id = p_station_id
        AND hour = current_hour
        AND day_of_week = current_dow
        AND (p_line IS NULL OR line = p_line)
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_stations_updated_at BEFORE UPDATE ON stations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to clean old data (keep 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_arrivals()
RETURNS void AS $$
BEGIN
    DELETE FROM arrivals 
    WHERE collected_at < NOW() - INTERVAL '30 days';
    
    -- Update statistics
    RAISE NOTICE 'Cleaned up arrivals older than 30 days';
END;
$$ LANGUAGE plpgsql;