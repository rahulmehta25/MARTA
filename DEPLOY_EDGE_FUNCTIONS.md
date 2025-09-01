# 🚀 Deploy Supabase Edge Functions

## Overview
We're using Supabase Edge Functions instead of Railway for our API endpoints. This keeps everything within the Supabase ecosystem.

## Edge Functions Created

1. **marta-arrivals** - Fetches real-time MARTA arrivals and stores in database
2. **analytics-performance** - Returns system performance metrics
3. **analytics-insights** - Generates system insights and recommendations

## Deployment Steps

### Prerequisites
Install Supabase CLI if not already installed:
```bash
brew install supabase/tap/supabase
```

### Step 1: Link to Your Project
```bash
cd /Users/rahulmehta/Desktop/AI-ML\ Projects/MARTA-fresh
supabase login
supabase link --project-ref vglychbweuowsovboxyf
```

### Step 2: Deploy Edge Functions
Deploy each function:
```bash
# Deploy marta-arrivals function
supabase functions deploy marta-arrivals

# Deploy analytics-performance function  
supabase functions deploy analytics-performance

# Deploy analytics-insights function
supabase functions deploy analytics-insights
```

Or deploy all at once:
```bash
supabase functions deploy
```

### Step 3: Set Environment Variables
The functions need access to your service role key:
```bash
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjY5MDk5MywiZXhwIjoyMDcyMjY2OTkzfQ.g65JH484ZiQ17phNpPnyhlco5XnopjyJegIWD15kQ8Q
```

## Verify Deployment

### Test marta-arrivals function:
```bash
curl -L -X GET 'https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-arrivals?station=FIVE%20POINTS' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY'
```

### Test analytics-performance function:
```bash
curl -L -X GET 'https://vglychbweuowsovboxyf.supabase.co/functions/v1/analytics-performance' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY'
```

### Test analytics-insights function:
```bash
curl -L -X GET 'https://vglychbweuowsovboxyf.supabase.co/functions/v1/analytics-insights' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY'
```

## Frontend Configuration

The frontend is already configured to use these endpoints:

```typescript
// In .env.production
VITE_SUPABASE_URL=https://vglychbweuowsovboxyf.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## API Endpoints

Once deployed, your endpoints will be:

- **Real-time arrivals**: `https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-arrivals`
- **Performance metrics**: `https://vglychbweuowsovboxyf.supabase.co/functions/v1/analytics-performance`
- **System insights**: `https://vglychbweuowsovboxyf.supabase.co/functions/v1/analytics-insights`

All endpoints require the Authorization header with the anon key.

## Monitoring

View function logs in Supabase Dashboard:
1. Go to https://vglychbweuowsovboxyf.supabase.co/project/vglychbweuowsovboxyf/functions
2. Click on each function to view logs
3. Monitor invocations and errors

## Benefits of Supabase Edge Functions

1. **Integrated**: No separate backend to manage
2. **Scalable**: Auto-scales with demand
3. **Secure**: Built-in auth with Supabase
4. **Fast**: Edge locations for low latency
5. **Free tier**: 500K invocations/month

## Troubleshooting

If functions don't work:
1. Check logs in Supabase Dashboard
2. Verify service role key is set
3. Ensure CORS headers are present
4. Check function deployment status

## Next Steps

After deployment:
1. Test all endpoints with curl
2. Verify frontend can connect
3. Check analytics page at https://marta-eta.vercel.app/analytics
4. Monitor function invocations