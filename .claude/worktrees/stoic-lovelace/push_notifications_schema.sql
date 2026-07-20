-- Push Notifications Schema for MARTA Transit Analytics
-- This schema supports web push notifications and subscription management

-- Table to store push notification subscriptions
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL DEFAULT 'anonymous',
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    -- Notification preferences
    notify_delays BOOLEAN DEFAULT true,
    notify_arrivals BOOLEAN DEFAULT true,
    notify_service BOOLEAN DEFAULT true,
    
    -- Metadata
    user_agent TEXT,
    last_used TIMESTAMP WITH TIME ZONE
);

-- Index for quick lookups
CREATE INDEX idx_push_subs_user ON push_subscriptions (user_id);
CREATE INDEX idx_push_subs_active ON push_subscriptions (is_active) WHERE is_active = true;

-- Table to log sent notifications
CREATE TABLE IF NOT EXISTS notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL, -- 'delay', 'arrival', 'alert', 'system'
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    recipients_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for notification history queries
CREATE INDEX idx_notification_logs_type ON notification_logs (type);
CREATE INDEX idx_notification_logs_created ON notification_logs (created_at DESC);

-- Table for system-wide alerts
CREATE TABLE IF NOT EXISTS system_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type VARCHAR(50) NOT NULL, -- 'service', 'emergency', 'maintenance', 'info'
    severity VARCHAR(20) DEFAULT 'info', -- 'critical', 'warning', 'info'
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    affected_lines TEXT[], -- Array of affected line colors
    affected_stations TEXT[], -- Array of affected station IDs
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for active alerts
CREATE INDEX idx_system_alerts_active ON system_alerts (is_active, severity) WHERE is_active = true;
CREATE INDEX idx_system_alerts_time ON system_alerts (start_time, end_time);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_push_subscriptions_updated_at BEFORE UPDATE ON push_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_alerts_updated_at BEFORE UPDATE ON system_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_alerts ENABLE ROW LEVEL SECURITY;

-- Policy for push_subscriptions - users can only manage their own subscriptions
CREATE POLICY "Users can view their own subscriptions" ON push_subscriptions
    FOR SELECT USING (auth.uid()::text = user_id OR user_id = 'anonymous');

CREATE POLICY "Users can insert their own subscriptions" ON push_subscriptions
    FOR INSERT WITH CHECK (auth.uid()::text = user_id OR user_id = 'anonymous');

CREATE POLICY "Users can update their own subscriptions" ON push_subscriptions
    FOR UPDATE USING (auth.uid()::text = user_id OR user_id = 'anonymous');

CREATE POLICY "Users can delete their own subscriptions" ON push_subscriptions
    FOR DELETE USING (auth.uid()::text = user_id OR user_id = 'anonymous');

-- Policy for notification_logs - read only for authenticated users
CREATE POLICY "Authenticated users can view notification logs" ON notification_logs
    FOR SELECT USING (true);

-- Policy for system_alerts - public read access
CREATE POLICY "Anyone can view active alerts" ON system_alerts
    FOR SELECT USING (is_active = true);

-- Sample data for testing
INSERT INTO system_alerts (alert_type, severity, title, message, affected_lines, affected_stations)
VALUES 
    ('maintenance', 'warning', 'Weekend Maintenance', 'Red Line will have delays this weekend due to track maintenance', ARRAY['RED'], ARRAY['AIRPORT STATION', 'COLLEGE PARK STATION']),
    ('service', 'info', 'Enhanced Service', 'Additional trains running on Gold Line during rush hours', ARRAY['GOLD'], NULL)
ON CONFLICT DO NOTHING;