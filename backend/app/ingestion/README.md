# MARTA GTFS-realtime ingestion

A Cloud Run-friendly worker that pulls MARTA's GTFS-realtime VehiclePositions
and TripUpdates feeds every 30 seconds and writes them into the Cloud SQL
`marta` database (`vehicle_positions`, `arrivals`).

## Dependencies

Add to `backend/requirements.txt` if not already present:

```
asyncpg>=0.29.0
httpx>=0.27.0
gtfs-realtime-bindings>=1.0.0
```

## Local run

```bash
export DATABASE_URL=postgresql://postgres:...@127.0.0.1:5432/marta
# scripts/db-proxy.sh in another terminal
python -m app.ingestion.gtfs_realtime
```

Exits after one ingestion cycle. Loop it via shell for local soak tests:

```bash
while true; do python -m app.ingestion.gtfs_realtime; sleep 30; done
```

## Deploy

```bash
gcloud run deploy marta-gtfs-worker \
  --source . \
  --region us-east1 \
  --command python,-m,app.ingestion.gtfs_realtime \
  --set-secrets DATABASE_URL=marta-database-url:latest

gcloud scheduler jobs create http marta-gtfs-tick \
  --schedule "*/1 * * * *" \
  --location us-east1 \
  --uri https://marta-gtfs-worker-XXXXXX.a.run.app/ \
  --http-method POST
```

MARTA's published GTFS-realtime feeds live at:

- `https://gtfs-rt.itsmarta.com/vehiclePositions.pb`
- `https://gtfs-rt.itsmarta.com/tripUpdates.pb`

Override via env if MARTA rotates URLs.
