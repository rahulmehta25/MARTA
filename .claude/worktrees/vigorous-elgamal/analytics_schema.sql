-- Advanced Analytics Schema for MARTA Transit Platform
-- This extends the base schema with analytics-specific tables

-- Performance Metrics Table (Aggregated hourly)
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    station_id TEXT NOT NULL,
    line TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    date DATE NOT NULL,
    
    -- Performance Indicators
    total_arrivals INTEGER DEFAULT 0,
    on_time_arrivals INTEGER DEFAULT 0,
    delayed_arrivals INTEGER DEFAULT 0,
    cancelled_arrivals INTEGER DEFAULT 0,
    
    -- Timing Metrics
    avg_delay_seconds DECIMAL(10, 2),
    max_delay_seconds INTEGER,
    min_delay_seconds INTEGER,
    median_delay_seconds DECIMAL(10, 2),
    std_dev_delay DECIMAL(10, 2),
    
    -- Reliability Metrics
    on_time_percentage DECIMAL(5, 2),
    reliability_score DECIMAL(5, 2), -- Custom weighted score
    
    -- Capacity Metrics
    avg_headway_seconds DECIMAL(10, 2), -- Time between trains
    capacity_utilization DECIMAL(5, 2), -- Estimated crowding
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    UNIQUE(station_id, line, hour, date)
);

-- Delay Patterns Table
CREATE TABLE IF NOT EXISTS delay_patterns (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    pattern_type TEXT NOT NULL, -- 'cascade', 'isolated', 'systemic'
    line TEXT NOT NULL,
    origin_station TEXT,
    
    -- Pattern Details
    pattern_signature JSONB, -- Pattern characteristics
    frequency INTEGER DEFAULT 1, -- How often this pattern occurs
    avg_impact_minutes DECIMAL(10, 2), -- Average delay caused
    affected_stations TEXT[], -- Stations typically affected
    
    -- Temporal Patterns
    common_hours INTEGER[], -- Hours when pattern occurs
    common_days INTEGER[], -- Days of week (0-6)
    weather_correlation DECIMAL(5, 2), -- Correlation with weather
    
    first_observed TIMESTAMP WITH TIME ZONE,
    last_observed TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    UNIQUE(pattern_type, line, pattern_signature)
);

-- Prediction Models Metadata
CREATE TABLE IF NOT EXISTS ml_models (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    model_name TEXT NOT NULL UNIQUE,
    model_type TEXT NOT NULL, -- 'arrival_prediction', 'demand_forecast', 'delay_prediction'
    version TEXT NOT NULL,
    
    -- Model Performance
    accuracy DECIMAL(5, 2),
    precision_score DECIMAL(5, 2),
    recall_score DECIMAL(5, 2),
    f1_score DECIMAL(5, 2),
    mean_absolute_error DECIMAL(10, 2),
    
    -- Model Details
    features_used TEXT[],
    training_samples INTEGER,
    validation_samples INTEGER,
    parameters JSONB,
    
    -- Deployment Info
    deployed_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT false,
    model_path TEXT, -- S3 or local path to model file
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Arrival Predictions Table
CREATE TABLE IF NOT EXISTS arrival_predictions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    station_id TEXT NOT NULL,
    line TEXT NOT NULL,
    train_id TEXT,
    
    -- Prediction Details
    predicted_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    predicted_arrival TIMESTAMP WITH TIME ZONE NOT NULL,
    scheduled_arrival TIMESTAMP WITH TIME ZONE,
    actual_arrival TIMESTAMP WITH TIME ZONE,
    
    -- Confidence Metrics
    confidence DECIMAL(3, 2) CHECK (confidence >= 0 AND confidence <= 1),
    prediction_method TEXT, -- 'ml_model', 'statistical', 'schedule_based'
    model_version TEXT,
    
    -- Accuracy Tracking
    error_seconds INTEGER, -- Actual - Predicted (null until actual arrives)
    was_accurate BOOLEAN -- Within acceptable threshold
);

-- Create index for arrival_predictions
CREATE INDEX idx_predictions_lookup ON arrival_predictions (station_id, line, predicted_at DESC);

-- Demand Forecasts Table
CREATE TABLE IF NOT EXISTS demand_forecasts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    station_id TEXT NOT NULL,
    line TEXT,
    
    -- Forecast Period
    forecast_date DATE NOT NULL,
    forecast_hour INTEGER CHECK (forecast_hour >= 0 AND forecast_hour <= 23),
    
    -- Predictions
    predicted_riders INTEGER,
    predicted_congestion_level INTEGER CHECK (predicted_congestion_level BETWEEN 1 AND 5),
    predicted_wait_time_seconds INTEGER,
    
    -- Factors Considered
    is_holiday BOOLEAN DEFAULT false,
    is_event_day BOOLEAN DEFAULT false,
    weather_factor DECIMAL(5, 2),
    historical_average INTEGER,
    
    -- Confidence
    confidence DECIMAL(3, 2) CHECK (confidence >= 0 AND confidence <= 1),
    model_version TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    UNIQUE(station_id, line, forecast_date, forecast_hour)
);

-- User Analytics Table
CREATE TABLE IF NOT EXISTS user_analytics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID,
    session_id TEXT,
    
    -- User Actions
    action_type TEXT NOT NULL, -- 'search', 'view_station', 'plan_trip', etc.
    action_details JSONB,
    
    -- Context
    station_id TEXT,
    line TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    -- Device Info
    platform TEXT, -- 'web', 'mobile', 'pwa'
    device_type TEXT,
    browser TEXT
);

-- System Health Metrics (Enhanced)
CREATE TABLE IF NOT EXISTS system_health_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    metric_time TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    -- System Status
    active_trains INTEGER,
    active_stations INTEGER,
    total_delays INTEGER,
    major_delays INTEGER, -- > 15 minutes
    
    -- Performance Metrics
    system_on_time_pct DECIMAL(5, 2),
    avg_delay_seconds DECIMAL(10, 2),
    max_delay_seconds INTEGER,
    
    -- Line-specific Health
    red_line_health INTEGER CHECK (red_line_health BETWEEN 0 AND 100),
    gold_line_health INTEGER CHECK (gold_line_health BETWEEN 0 AND 100),
    blue_line_health INTEGER CHECK (blue_line_health BETWEEN 0 AND 100),
    green_line_health INTEGER CHECK (green_line_health BETWEEN 0 AND 100),
    
    -- Predictive Indicators
    delay_risk_score DECIMAL(5, 2), -- 0-100 risk of delays
    congestion_forecast DECIMAL(5, 2), -- Expected congestion level
    
    -- Alert Counts
    active_alerts INTEGER DEFAULT 0,
    active_warnings INTEGER DEFAULT 0
);

-- Create indexes for performance
CREATE INDEX idx_performance_metrics_lookup ON performance_metrics(station_id, line, date DESC);
CREATE INDEX idx_performance_metrics_date ON performance_metrics(date DESC);
CREATE INDEX idx_delay_patterns_line ON delay_patterns(line);
CREATE INDEX idx_delay_patterns_observed ON delay_patterns(last_observed DESC);
CREATE INDEX idx_ml_models_active ON ml_models(is_active, model_type);
CREATE INDEX idx_demand_forecasts_date ON demand_forecasts(forecast_date, station_id);
CREATE INDEX idx_system_health_time ON system_health_metrics(metric_time DESC);
CREATE INDEX idx_user_analytics_user ON user_analytics(user_id, timestamp DESC);
CREATE INDEX idx_user_analytics_session ON user_analytics(session_id, timestamp DESC);

-- Create views for common queries

-- Daily Performance Summary
CREATE OR REPLACE VIEW daily_performance_summary AS
SELECT 
    date,
    line,
    COUNT(DISTINCT station_id) as stations_reporting,
    SUM(total_arrivals) as total_arrivals,
    AVG(on_time_percentage) as avg_on_time_pct,
    AVG(avg_delay_seconds) as avg_delay,
    MAX(max_delay_seconds) as worst_delay,
    AVG(reliability_score) as avg_reliability
FROM performance_metrics
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date, line
ORDER BY date DESC, line;

-- Current System Status (Enhanced)
CREATE OR REPLACE VIEW current_system_status_enhanced AS
SELECT 
    COUNT(DISTINCT a.station_id) as active_stations,
    COUNT(DISTINCT a.train_id) as active_trains,
    COUNT(*) as recent_arrivals,
    AVG(a.delay_seconds) as avg_delay,
    COUNT(CASE WHEN a.delay_seconds > 300 THEN 1 END) as major_delays,
    COUNT(CASE WHEN a.delay_seconds <= 60 THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) * 100 as on_time_pct,
    MAX(a.delay_seconds) as max_current_delay,
    COUNT(DISTINCT a.line) as active_lines
FROM arrivals a
WHERE a.collected_at > NOW() - INTERVAL '30 minutes';

-- Station Performance Ranking
CREATE OR REPLACE VIEW station_performance_ranking AS
SELECT 
    station_id,
    AVG(on_time_percentage) as avg_on_time_pct,
    AVG(reliability_score) as avg_reliability,
    COUNT(DISTINCT date) as days_tracked,
    RANK() OVER (ORDER BY AVG(on_time_percentage) DESC) as on_time_rank,
    RANK() OVER (ORDER BY AVG(reliability_score) DESC) as reliability_rank
FROM performance_metrics
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY station_id
HAVING COUNT(DISTINCT date) >= 3
ORDER BY avg_on_time_pct DESC;

-- Prediction Accuracy Tracking
CREATE OR REPLACE VIEW prediction_accuracy_summary AS
SELECT 
    DATE(predicted_at) as prediction_date,
    prediction_method,
    COUNT(*) as total_predictions,
    COUNT(actual_arrival) as completed_predictions,
    AVG(ABS(error_seconds)) FILTER (WHERE error_seconds IS NOT NULL) as mean_abs_error,
    COUNT(*) FILTER (WHERE was_accurate = true)::FLOAT / 
        NULLIF(COUNT(*) FILTER (WHERE was_accurate IS NOT NULL), 0) * 100 as accuracy_pct
FROM arrival_predictions
WHERE predicted_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(predicted_at), prediction_method
ORDER BY prediction_date DESC;

-- Enable RLS for new tables
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE delay_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE arrival_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE demand_forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_health_metrics ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access
CREATE POLICY "Public read performance" ON performance_metrics FOR SELECT USING (true);
CREATE POLICY "Public read patterns" ON delay_patterns FOR SELECT USING (true);
CREATE POLICY "Public read models" ON ml_models FOR SELECT USING (true);
CREATE POLICY "Public read predictions" ON arrival_predictions FOR SELECT USING (true);
CREATE POLICY "Public read forecasts" ON demand_forecasts FOR SELECT USING (true);
CREATE POLICY "Public read health" ON system_health_metrics FOR SELECT USING (true);

-- User analytics requires authentication
CREATE POLICY "Users read own analytics" ON user_analytics 
    FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Service role can write to all tables
CREATE POLICY "Service write performance" ON performance_metrics 
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write patterns" ON delay_patterns 
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write models" ON ml_models 
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write predictions" ON arrival_predictions 
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write forecasts" ON demand_forecasts 
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write analytics" ON user_analytics 
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write health" ON system_health_metrics 
    FOR ALL USING (auth.role() = 'service_role');