-- Quick fix to allow anon key to write data
-- This is less secure but simpler for development/demo

-- Keep RLS enabled but allow anon writes for arrivals and stations
DROP POLICY IF EXISTS "Service role can insert arrivals" ON arrivals;
DROP POLICY IF EXISTS "Service role can manage stations" ON stations;

-- Allow anon users to insert arrivals
CREATE POLICY "Anon can insert arrivals" ON arrivals
    FOR INSERT WITH CHECK (true);

-- Allow anon users to manage stations (insert/update)
CREATE POLICY "Anon can insert stations" ON stations
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Anon can update stations" ON stations
    FOR UPDATE USING (true) WITH CHECK (true);

-- Verify the policies
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public' 
AND tablename IN ('arrivals', 'stations')
ORDER BY tablename, policyname;