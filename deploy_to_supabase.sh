#!/bin/bash

# MARTA Analytics - Supabase Deployment Script
# This script deploys the ML infrastructure to your Supabase project

echo "🚀 Deploying MARTA ML Infrastructure to Supabase"
echo "================================================"
echo ""

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found. Please install it first:"
    echo "   npm install -g supabase"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "supabase/config.toml" ]; then
    echo "❌ Please run this script from the MARTA project root directory"
    exit 1
fi

# Step 1: Deploy Edge Functions
echo "📦 Deploying Edge Functions..."
echo "------------------------------"

# Deploy demand-forecast function
if [ -d "supabase/functions/demand-forecast" ]; then
    echo "Deploying demand-forecast function..."
    supabase functions deploy demand-forecast --no-verify-jwt
    if [ $? -eq 0 ]; then
        echo "✅ demand-forecast deployed successfully"
    else
        echo "⚠️  Failed to deploy demand-forecast"
    fi
fi

# Deploy surge-detection function
if [ -d "supabase/functions/surge-detection" ]; then
    echo "Deploying surge-detection function..."
    supabase functions deploy surge-detection --no-verify-jwt
    if [ $? -eq 0 ]; then
        echo "✅ surge-detection deployed successfully"
    else
        echo "⚠️  Failed to deploy surge-detection"
    fi
fi

echo ""
echo "📊 Creating Database Tables..."
echo "------------------------------"

# Create SQL script for manual execution
cat > supabase/deploy_ml_tables.sql << 'EOF'
-- MARTA ML Infrastructure Tables

-- Drop existing tables if needed (be careful in production!)
-- DROP TABLE IF EXISTS ml_model_metrics CASCADE;
-- DROP TABLE IF EXISTS fleet_repositioning CASCADE;
-- DROP TABLE IF EXISTS route_optimizations CASCADE;
-- DROP TABLE IF EXISTS crowding_alerts CASCADE;
-- DROP TABLE IF EXISTS surge_events CASCADE;
-- DROP TABLE IF EXISTS demand_predictions CASCADE;
-- DROP TABLE IF EXISTS stop_metrics CASCADE;

-- Create tables
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

CREATE TABLE IF NOT EXISTS demand_predictions (
  id BIGSERIAL PRIMARY KEY,
  stop_id VARCHAR(50) NOT NULL,
  predictions JSONB NOT NULL,
  model_version VARCHAR(20),
  model_confidence DECIMAL(3,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);

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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_stop_metrics_stop_time ON stop_metrics(stop_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_demand_predictions_stop ON demand_predictions(stop_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_surge_events_location ON surge_events(location_id, surge_start_time DESC);
CREATE INDEX IF NOT EXISTS idx_crowding_alerts_status ON crowding_alerts(status, alert_time DESC);

-- Enable Row Level Security
ALTER TABLE demand_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE crowding_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE surge_events ENABLE ROW LEVEL SECURITY;

-- Create policies for public read access
CREATE POLICY "Public read access" ON demand_predictions
  FOR SELECT USING (true);

CREATE POLICY "Public read access" ON crowding_alerts
  FOR SELECT USING (true);

CREATE POLICY "Public read access" ON surge_events
  FOR SELECT USING (true);

-- Create view for system status
CREATE OR REPLACE VIEW current_system_status AS
SELECT
  (SELECT COUNT(*) FROM crowding_alerts WHERE status = 'active') as active_crowding_alerts,
  (SELECT COUNT(*) FROM surge_events WHERE surge_end_time IS NULL) as active_surges,
  (SELECT AVG(occupancy_percentage) FROM stop_metrics WHERE timestamp > NOW() - INTERVAL '1 hour') as avg_system_occupancy,
  NOW() as last_updated;

GRANT SELECT ON current_system_status TO anon, authenticated;

-- Insert sample data for testing
INSERT INTO stop_metrics (stop_id, timestamp, passenger_count, occupancy_percentage)
VALUES
  ('FIVE_POINTS', NOW() - INTERVAL '1 hour', 75, 62.5),
  ('FIVE_POINTS', NOW() - INTERVAL '30 minutes', 95, 79.2),
  ('FIVE_POINTS', NOW(), 110, 91.7),
  ('MIDTOWN', NOW() - INTERVAL '1 hour', 45, 37.5),
  ('MIDTOWN', NOW() - INTERVAL '30 minutes', 60, 50.0),
  ('MIDTOWN', NOW(), 55, 45.8)
ON CONFLICT (stop_id, timestamp) DO NOTHING;

SELECT 'ML tables created successfully!' as status;
EOF

echo "✅ SQL script created: supabase/deploy_ml_tables.sql"
echo ""
echo "Please run this SQL in your Supabase SQL Editor:"
echo "1. Go to your Supabase Dashboard"
echo "2. Navigate to SQL Editor"
echo "3. Copy and paste the contents of supabase/deploy_ml_tables.sql"
echo "4. Click 'Run'"

echo ""
echo "📱 Frontend Setup"
echo "-----------------"

# Check if frontend dependencies need updating
if [ -d "frontend" ]; then
    cd frontend

    # Check if @supabase/supabase-js is installed
    if ! grep -q "@supabase/supabase-js" package.json; then
        echo "Installing Supabase client library..."
        npm install @supabase/supabase-js
    fi

    # Check if recharts is installed
    if ! grep -q "recharts" package.json; then
        echo "Installing recharts for visualizations..."
        npm install recharts
    fi

    cd ..
    echo "✅ Frontend dependencies ready"
fi

echo ""
echo "🎉 Deployment Complete!"
echo "======================="
echo ""
echo "✅ Edge Functions deployed (if Supabase project is linked)"
echo "📋 SQL script ready for database setup"
echo "📦 Frontend dependencies installed"
echo ""
echo "🔧 Final Steps:"
echo "1. Ensure your .env file has your Supabase credentials"
echo "2. Run the SQL script in Supabase SQL Editor"
echo "3. Test the Edge Functions:"
echo "   curl YOUR_SUPABASE_URL/functions/v1/demand-forecast"
echo "4. Start the frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "📊 Visit the ML Dashboard at http://localhost:5173"