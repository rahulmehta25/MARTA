# URGENT: Fix Supabase RLS Policies

## Problem
The Row Level Security (RLS) policies are blocking INSERT and UPDATE operations. The tables exist but can only be read, not written to.

## Solution
Run the following SQL in your Supabase SQL Editor:

1. Go to: https://vglychbweuowsovboxyf.supabase.co/project/vglychbweuowsovboxyf/sql
2. Click "New Query"
3. Copy and paste the contents of `fix_rls_policies.sql`
4. Click "Run"

## Alternative Quick Fix (if above doesn't work)
You can also disable RLS temporarily for testing:

```sql
-- Disable RLS for all tables (development only!)
ALTER TABLE arrivals DISABLE ROW LEVEL SECURITY;
ALTER TABLE stations DISABLE ROW LEVEL SECURITY;
ALTER TABLE hourly_stats DISABLE ROW LEVEL SECURITY;
ALTER TABLE system_metrics DISABLE ROW LEVEL SECURITY;
ALTER TABLE predictions DISABLE ROW LEVEL SECURITY;
```

## After Fixing
Once the SQL is run, test data collection again:
```bash
source venv/bin/activate
export $(cat .env.supabase | grep -v '^#' | xargs)
python3 collect_data_supabase.py
```

The data should now successfully store in Supabase!