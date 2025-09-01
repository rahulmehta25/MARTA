# Update Frontend API Endpoint

## Option 1: Use Supabase Edge Functions (Recommended)

### Update Environment Variable on Vercel

1. Go to: https://vercel.com/dashboard
2. Select your MARTA project
3. Go to Settings → Environment Variables
4. Add or update:
   ```
   VITE_API_URL = https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api
   ```
5. Redeploy the frontend

### Update Local Development

Edit `frontend/.env.development`:
```bash
VITE_API_URL=https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api
```

## Option 2: Continue Using Railway

Your Railway backend at `https://marta-production.up.railway.app` is already configured and working.

To enable Supabase storage with Railway:
1. Go to Railway dashboard
2. Add environment variables:
   - `SUPABASE_URL`: https://vglychbweuowsovboxyf.supabase.co
   - `SUPABASE_SERVICE_KEY`: [your service key]

## Option 3: Support Both (Flexible)

Update `frontend/src/config/api.ts` to support multiple backends: