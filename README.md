# MARTA Delay Predictor

Real-time delay prediction for Atlanta's bus and rail network. Ingests the MARTA GTFS-realtime feed, trains XGBoost against historical patterns, serves a Mapbox dashboard that shows where the next bus really is, and when it really will arrive.

## What it does

- Pulls vehicle positions and trip updates every 30 seconds from MARTA GTFS-realtime
- Joins against the static GTFS schedule to compute observed delays
- Serves a Mapbox dashboard showing live vehicles and per-stop delay predictions
- XGBoost model trained on 30 days of historical delays, retrained nightly
- Predictions update in under 500ms end-to-end

## Tech

- Python 3.11, FastAPI (backend), Pydantic v2
- Supabase Postgres + PostGIS for spatial queries
- Supabase Edge Functions for GTFS ingestion (migrated off Railway)
- XGBoost for delay regression, features include hour-of-day, day-of-week, route, weather
- Mapbox GL JS for the dashboard
- Deployed on Cloud Run (backend) + Vercel (frontend)

## Architecture

![System architecture](docs/architecture.png)

See [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md) for the full design rationale, including why PostGIS, why XGBoost over LSTM, and why Edge Functions over Railway.

## Run it locally

```bash
git clone https://github.com/rmehta2500/marta
cd marta
cp .env.example .env
# add Supabase + MARTA API keys
uv sync
supabase start
make seed  # 30 days of seeded historical delays
make ingest  # start GTFS-realtime worker
make dev  # start FastAPI + frontend
```

## Demo

[Watch the 2-minute walkthrough](docs/demos/marta-demo.mp4)

Live: [marta.vercel.app](https://marta.vercel.app)

## Screenshots

![Live Mapbox dashboard with active vehicles](docs/screenshots/dashboard.png)
![Predicted vs actual delays for a route](docs/screenshots/predictions.png)
![Ingestion health](docs/screenshots/ingestion.png)

## Data sources

- MARTA GTFS-static: [itsmarta.com/app-developer-resources](https://www.itsmarta.com/app-developer-resources.aspx)
- MARTA GTFS-realtime: requires API key

## Status

Portfolio-quality. Predictions are calibrated against held-out test data; MAE is reported in the dashboard metrics panel.

MIT licensed.
