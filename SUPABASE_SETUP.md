# Supabase Setup Guide for MARTA Analytics

This guide will help you set up Supabase as the backend for the MARTA Transit Analytics Platform with ML capabilities.

## Prerequisites

- Supabase account (free tier works)
- Supabase CLI installed (`npm install -g supabase`)
- Node.js 18+ for Edge Functions

## Setup Steps

### 1. Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Create a new project
3. Note down your project URL and anon key

### 2. Configure Environment Variables

Copy `.env.supabase` to `.env` and update with your values:

```bash
cp .env.supabase .env
```

Update these values in `.env`:
- `SUPABASE_URL`: Your project URL
- `SUPABASE_ANON_KEY`: Your anon key
- `VITE_SUPABASE_URL`: Same as SUPABASE_URL
- `VITE_SUPABASE_ANON_KEY`: Same as SUPABASE_ANON_KEY

### 3. Initialize Supabase Locally

```bash
cd /path/to/marta-project
supabase init
supabase link --project-ref your-project-ref
```

### 4. Run Database Migrations

```bash
# Run the ML tables migration
supabase db push
```

This creates tables for:
- `stop_metrics` - Historical passenger data
- `demand_predictions` - ML demand forecasts
- `surge_events` - Detected demand surges
- `crowding_alerts` - Overcrowding notifications
- `route_optimizations` - Optimization results
- `fleet_repositioning` - Vehicle deployment commands

### 5. Deploy Edge Functions

```bash
# Deploy demand forecasting function
supabase functions deploy demand-forecast

# Deploy surge detection function
supabase functions deploy surge-detection

# Deploy route optimization function (if created)
supabase functions deploy route-optimization
```

### 6. Set Function Secrets

```bash
# Set environment variables for functions
supabase secrets set OPENWEATHER_API_KEY=your-key
supabase secrets set TRAFFIC_API_KEY=your-key
```

### 7. Enable Realtime

In Supabase Dashboard:
1. Go to Database > Replication
2. Enable replication for these tables:
   - `crowding_alerts`
   - `surge_events`
   - `fleet_repositioning`

### 8. Set Row Level Security (RLS)

```sql
-- Allow public read access to ML predictions
ALTER TABLE demand_predictions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON demand_predictions
  FOR SELECT USING (true);

-- Allow public read access to alerts
ALTER TABLE crowding_alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON crowding_alerts
  FOR SELECT USING (true);

ALTER TABLE surge_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON surge_events
  FOR SELECT USING (true);
```

## Frontend Integration

### Install Dependencies

```bash
cd frontend
npm install @supabase/supabase-js recharts
```

### Update Frontend Environment

Create `frontend/.env.local`:

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_MAPBOX_TOKEN=your-mapbox-token
```

### Use Supabase Client

```typescript
import { supabase, mlApi } from '@/lib/supabase'

// Fetch demand forecast
const forecast = await mlApi.forecastDemand('FIVE_POINTS', 24)

// Subscribe to real-time alerts
const subscription = realtimeSubscriptions.subscribeToCrowdingAlerts(
  (payload) => console.log('New alert:', payload)
)
```

## Testing the Setup

### 1. Test Edge Functions

```bash
# Test demand forecast
curl -X POST https://your-project.supabase.co/functions/v1/demand-forecast \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"stop_id": "FIVE_POINTS", "horizon_hours": 24}'

# Test surge detection
curl -X POST https://your-project.supabase.co/functions/v1/surge-detection \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"location_id": "FIVE_POINTS", "current_demand": 150, "historical_baseline": 50}'
```

### 2. Test Database Queries

```sql
-- Check system status
SELECT * FROM current_system_status;

-- View recent predictions
SELECT * FROM demand_predictions
ORDER BY created_at DESC
LIMIT 10;

-- View active alerts
SELECT * FROM crowding_alerts
WHERE status = 'active';
```

### 3. Test Real-time Subscriptions

```javascript
// In browser console
const { createClient } = supabase
const client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

client
  .channel('test')
  .on('postgres_changes',
    { event: '*', schema: 'public', table: 'crowding_alerts' },
    (payload) => console.log('Change:', payload)
  )
  .subscribe()
```

## ML Model Deployment Options

### Option 1: Edge Functions (Current)
- Lightweight predictions using simplified models
- Good for real-time inference
- Limited computational resources

### Option 2: External ML Service
- Deploy Python ML models on Railway/Render
- Call from Supabase Edge Functions
- Better for complex models

### Option 3: Scheduled Jobs
- Use pg_cron for batch predictions
- Store results in database
- Good for non-real-time forecasts

## Monitoring

### Database Metrics
- Monitor in Supabase Dashboard > Database
- Check query performance
- Watch storage usage

### Function Metrics
- View in Supabase Dashboard > Functions
- Monitor execution time
- Check error rates

### Real-time Metrics
- Monitor active connections
- Check message throughput
- Watch for disconnections

## Production Checklist

- [ ] Set production environment variables
- [ ] Enable RLS policies
- [ ] Configure CORS for your domain
- [ ] Set up database backups
- [ ] Configure rate limiting
- [ ] Set up monitoring alerts
- [ ] Test all ML endpoints
- [ ] Verify real-time subscriptions
- [ ] Load test the system
- [ ] Document API endpoints

## Troubleshooting

### Edge Functions Not Working
- Check function logs: `supabase functions logs demand-forecast`
- Verify environment variables are set
- Check CORS configuration

### Real-time Not Updating
- Ensure replication is enabled
- Check WebSocket connection
- Verify RLS policies

### Database Performance
- Add appropriate indexes
- Use connection pooling
- Optimize query patterns

## Support

For issues or questions:
- Supabase Discord: https://discord.supabase.com
- GitHub Issues: https://github.com/yourusername/marta-analytics