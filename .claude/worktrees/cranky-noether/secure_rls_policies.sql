-- More Secure RLS Policies for MARTA Analytics
-- This provides a better balance between functionality and security

-- Option 1: Allow reads for everyone, writes only with API key
-- (Recommended for production)

-- First, ensure RLS is enabled
ALTER TABLE arrivals ENABLE ROW LEVEL SECURITY;
ALTER TABLE stations ENABLE ROW LEVEL SECURITY;
ALTER TABLE hourly_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all operations for arrivals" ON arrivals;
DROP POLICY IF EXISTS "Enable all operations for stations" ON stations;
DROP POLICY IF EXISTS "Enable all operations for hourly_stats" ON hourly_stats;
DROP POLICY IF EXISTS "Enable all operations for system_metrics" ON system_metrics;
DROP POLICY IF EXISTS "Enable all operations for predictions" ON predictions;

-- Create more secure policies

-- Arrivals: Public read, authenticated write
CREATE POLICY "Public can read arrivals" ON arrivals
    FOR SELECT USING (true);

CREATE POLICY "Service role can insert arrivals" ON arrivals
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role' OR 
        auth.role() = 'authenticated'
    );

-- Stations: Public read, authenticated write
CREATE POLICY "Public can read stations" ON stations
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage stations" ON stations
    FOR ALL USING (
        auth.role() = 'service_role' OR 
        auth.role() = 'authenticated'
    );

-- Hourly stats: Public read, service write
CREATE POLICY "Public can read hourly_stats" ON hourly_stats
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage hourly_stats" ON hourly_stats
    FOR ALL USING (auth.role() = 'service_role');

-- System metrics: Public read, service write
CREATE POLICY "Public can read system_metrics" ON system_metrics
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage system_metrics" ON system_metrics
    FOR ALL USING (auth.role() = 'service_role');

-- Predictions: Public read, service write
CREATE POLICY "Public can read predictions" ON predictions
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage predictions" ON predictions
    FOR ALL USING (auth.role() = 'service_role');

-- Option 2: If you need the anon key to write data (less secure but simpler)
-- Uncomment these policies instead:

/*
-- Allow anon users to insert arrivals (needed for GitHub Actions)
CREATE POLICY "Anon can insert arrivals" ON arrivals
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Anon can update stations" ON stations
    FOR INSERT WITH CHECK (true);
    
CREATE POLICY "Anon can update stations existing" ON stations
    FOR UPDATE USING (true);
*/