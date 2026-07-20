-- Fix Row Level Security policies to allow INSERT and UPDATE operations
-- This script should be run in the Supabase SQL Editor

-- Drop existing policies first
DROP POLICY IF EXISTS "Public read access" ON arrivals;
DROP POLICY IF EXISTS "Public read access" ON stations;
DROP POLICY IF EXISTS "Public read access" ON hourly_stats;
DROP POLICY IF EXISTS "Public read access" ON system_metrics;
DROP POLICY IF EXISTS "Public read access" ON predictions;

-- Create new policies that allow all operations for anonymous users
-- This is suitable for a demo/development environment

-- Arrivals table policies
CREATE POLICY "Enable all operations for arrivals" ON arrivals
    FOR ALL USING (true) WITH CHECK (true);

-- Stations table policies  
CREATE POLICY "Enable all operations for stations" ON stations
    FOR ALL USING (true) WITH CHECK (true);

-- Hourly stats table policies
CREATE POLICY "Enable all operations for hourly_stats" ON hourly_stats
    FOR ALL USING (true) WITH CHECK (true);

-- System metrics table policies
CREATE POLICY "Enable all operations for system_metrics" ON system_metrics
    FOR ALL USING (true) WITH CHECK (true);

-- Predictions table policies
CREATE POLICY "Enable all operations for predictions" ON predictions
    FOR ALL USING (true) WITH CHECK (true);

-- Verify the policies are applied
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;