# Supabase Setup Guide for MARTA Analytics

## 1. Create Free Supabase Account
1. Go to [supabase.com](https://supabase.com)
2. Sign up for free account
3. Create new project (name: `marta-analytics`)

## 2. Get Your Credentials
After project creation, go to Settings → API:
- **Project URL**: `https://xxxxx.supabase.co`
- **Anon/Public Key**: `eyJhbGc...` (long string)

## 3. Set Up Database Schema
1. Go to SQL Editor in Supabase dashboard
2. Copy contents of `supabase_schema.sql`
3. Run the SQL to create all tables

## 4. Configure Environment Variables

### For Local Development:
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key-here"
export MARTA_API_KEY="your-marta-api-key"
```

### For Railway:
Add these in Railway dashboard → Variables:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `MARTA_API_KEY`

### For GitHub Actions:
Add as repository secrets:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `MARTA_API_KEY`

## 5. Test Data Collection
```bash
# Install dependencies
pip install httpx

# Run data collection
python collect_data_supabase.py
```

## 6. Set Up Automated Collection

### Option A: GitHub Actions (Free)
The `.github/workflows/collect_data_supabase.yml` will run every 30 minutes

### Option B: Supabase Edge Functions (Free tier)
Create edge function for scheduled collection

### Option C: Railway Cron (If using paid tier)
Add cron schedule to Railway

## 7. Updated API Endpoints

Your Flask app now has these endpoints:

### Real-time Data (from MARTA):
- `GET /api/v1/marta/rail/arrivals` - Live arrivals
- `GET /api/v1/marta/rail/stations` - Station list
- `GET /api/v1/marta/rail/status` - System status

### Analytics (from Supabase):
- `GET /api/v1/analytics/station/<station_id>` - Station analytics
- `GET /api/v1/analytics/system` - System metrics
- `GET /api/v1/analytics/predictions/<station_id>` - Arrival predictions

### Data Management:
- `POST /api/v1/data/collect` - Trigger collection manually

## 8. Frontend Integration

The frontend can now:
1. Fetch real-time data from your backend
2. Get historical analytics from Supabase
3. Subscribe to real-time updates (using Supabase client)

## Free Tier Limits
- **Database**: 500MB (enough for ~6 months of data)
- **API Requests**: Unlimited
- **Bandwidth**: 2GB/month
- **Edge Functions**: 500K invocations/month
- **Real-time**: 200 concurrent connections

## Data Retention
- Arrivals: 30 days (configurable)
- Hourly stats: Permanent
- System metrics: 90 days

## Monitoring
Check your data in Supabase:
1. Table Editor → View arrivals table
2. SQL Editor → Run queries
3. Logs → Monitor API usage