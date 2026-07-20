# Edge Function Deployment Guide

Since the Supabase CLI requires database password, here's how to deploy the Edge Function via the dashboard:

## Manual Deployment (5 minutes)

1. **Go to Functions Page**
   https://supabase.com/dashboard/project/vglychbweuowsovboxyf/functions

2. **Create New Function**
   - Click "New Function"
   - Name: `marta-api`
   - Click "Create"

3. **Copy the Code**
   - Copy all content from `supabase/functions/marta-api/index.ts`
   - Paste it into the function editor

4. **Set Environment Variables**
   - Click on "Settings" tab
   - Add secret: `MARTA_API_KEY` = `ff98ada7-0436-42c5-b9bf-1071245ad1a0`
   - Click "Save"

5. **Deploy**
   - Click "Deploy" button
   - Wait for deployment to complete

## Your API Endpoints

Once deployed, your endpoints will be:

```
BASE URL: https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api

GET  /arrivals  - Get real-time arrivals
GET  /stations  - Get station list
GET  /metrics   - Get system metrics
POST /collect   - Trigger data collection
GET  /predictions?station_id=STATION_NAME - Get predictions
```

## Testing the Endpoints

```bash
# Test arrivals endpoint
curl https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api/arrivals

# Test with authorization header (if needed)
curl https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api/arrivals \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY"
```

## Alternative: Keep Using Railway

Your Railway deployment is already working at:
`https://marta-production.up.railway.app`

If you prefer to keep using Railway (which is simpler), just:
1. Add these env vars to Railway:
   - `SUPABASE_URL`: https://vglychbweuowsovboxyf.supabase.co
   - `SUPABASE_SERVICE_KEY`: [your service key from .env.supabase]
2. The updated `app.py` already has Supabase integration

## Which Should You Choose?

**Use Supabase Edge Functions if:**
- You want everything in one platform
- You want to minimize costs
- You want real-time features

**Keep Railway if:**
- It's already working fine
- You prefer Python/Flask
- You want simpler deployment

Both are free and will work great!