#!/usr/bin/env bash
# Launch the Cloud SQL Auth Proxy for the MARTA database.
#
# Connects to osmoti-auth:us-east1:portfolio-pg and exposes Postgres on
# localhost:5432. Use with DATABASE_URL=postgresql://postgres:<pwd>@127.0.0.1:5432/marta
# in backend/api/.env.
#
# Pull the postgres password from Secret Manager:
#   gcloud secrets versions access latest --secret=portfolio-pg-postgres-password --project=osmoti-auth

set -euo pipefail

INSTANCE="osmoti-auth:us-east1:portfolio-pg"
PORT="${PORT:-5432}"

if ! command -v cloud-sql-proxy >/dev/null 2>&1; then
  echo "cloud-sql-proxy not installed. Run: brew install cloud-sql-proxy" >&2
  exit 1
fi

echo "Starting Cloud SQL Auth Proxy for ${INSTANCE} on 127.0.0.1:${PORT}..."
exec cloud-sql-proxy --port="${PORT}" "${INSTANCE}"
