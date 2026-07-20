# Supabase Deployment Guide for MARTA Analytics

## Overview
This guide walks through deploying the entire MARTA Analytics Platform using Supabase (backend + database) and Vercel (frontend).

## Prerequisites
- Supabase project created (✅ Done)
- Supabase CLI installed locally
- GitHub repository connected

## Step 1: Fix Row Level Security (RLS) Policies

**IMPORTANT: Do this first to allow data writes!**

1. Go to Supabase SQL Editor: https://vglychbweuowsovboxyf.supabase.co/project/vglychbweuowsovboxyf/sql
2. Run the following SQL:

```sql
-- Disable RLS for all tables (development/demo only!)
ALTER TABLE arrivals DISABLE ROW LEVEL SECURITY;
ALTER TABLE stations DISABLE ROW LEVEL SECURITY;
ALTER TABLE hourly_stats DISABLE ROW LEVEL SECURITY;
ALTER TABLE system_metrics DISABLE ROW LEVEL SECURITY;
ALTER TABLE predictions DISABLE ROW LEVEL SECURITY;
```

## Step 2: Deploy Edge Functions

### Install Supabase CLI
```bash
brew install supabase/tap/supabase
```

### Link to your project
```bash
supabase link --project-ref vglychbweuowsovboxyf
```

### Deploy the Edge Function
```bash
supabase functions deploy marta-api
```

### Set secrets
```bash
supabase secrets set MARTA_API_KEY=ff98ada7-0436-42c5-b9bf-1071245ad1a0
```

## Step 3: Test the Deployment

Your API endpoints will be available at:
- `https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api/arrivals` - Get real-time arrivals
- `https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api/stations` - Get stations
- `https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api/metrics` - Get system metrics
- `https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api/collect` - Trigger data collection

## Step 4: Set Up Automated Data Collection

### Option A: Supabase Cron Jobs (Recommended)
Create a database function to collect data:

```sql
-- Create a function to call the Edge Function
CREATE OR REPLACE FUNCTION collect_marta_data()
RETURNS void AS $$
BEGIN
  PERFORM net.http_post(
    url := 'https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api/collect',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.settings.anon_key')
    )
  );
END;
$$ LANGUAGE plpgsql;

-- Schedule it to run every 30 minutes
SELECT cron.schedule(
  'collect-marta-data',
  '*/30 * * * *',
  'SELECT collect_marta_data();'
);
```

### Option B: GitHub Actions
The workflow is already set up in `.github/workflows/collect_data_supabase.yml`

Add these secrets to your GitHub repository:
- `MARTA_API_KEY`: ff98ada7-0436-42c5-b9bf-1071245ad1a0
- `SUPABASE_URL`: https://vglychbweuowsovboxyf.supabase.co
- `SUPABASE_ANON_KEY`: [your anon key]

## Step 5: Update Frontend

Update the frontend to use the new Supabase endpoint:

```javascript
// In your frontend code, replace:
const API_URL = 'https://marta-production.up.railway.app'

// With:
const API_URL = 'https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api'
```

## Step 6: Test Data Collection

Run a manual test:
```bash
source venv/bin/activate
export $(cat .env.supabase | grep -v '^#' | xargs)
python3 collect_data_supabase.py
```

## Monitoring

View your data in Supabase:
1. Go to Table Editor: https://vglychbweuowsovboxyf.supabase.co/project/vglychbweuowsovboxyf/editor
2. Check the `arrivals` table for recent data
3. Check the `stations` table for station information

## Advantages of Supabase Deployment

1. **Single Platform**: Database + API in one place
2. **Built-in Auth**: Can add user authentication easily
3. **Real-time**: Get real-time updates via websockets
4. **Edge Functions**: Serverless functions close to your data
5. **Free Tier**: 500MB database, 2GB bandwidth, 500K function invocations
6. **Auto-scaling**: Handles traffic spikes automatically

## Cost Breakdown (Free Tier)

- **Database**: 500MB storage ✅
- **API Requests**: 500K Edge Function invocations/month ✅
- **Bandwidth**: 2GB/month ✅
- **Real-time**: 200 concurrent connections ✅

For MARTA Analytics with data collection every 30 minutes:
- ~1,440 collections/month (well under 500K limit)
- ~100MB storage for 30 days of data
- Minimal bandwidth usage

All within free tier limits! 🎉