#!/bin/bash

# Set environment variables
export ENVIRONMENT=development
export DEBUG=True
export LOG_LEVEL=INFO
export API_HOST=0.0.0.0
export API_PORT=8000
export API_PREFIX=/api/v1
export DATABASE_URL=sqlite:///./marta_data.db
export DB_PASSWORD=dummy
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export MARTA_API_KEY=ff98ada7-0436-42c5-b9bf-1071245ad1a0
export MARTA_GTFS_URL=https://itsmarta.com/google_transit.zip
export SECRET_KEY=dev-secret-key-change-in-production
export JWT_ALGORITHM=HS256
export JWT_EXPIRATION_HOURS=24
export CORS_ORIGINS='["http://localhost:3000","http://localhost:5173","https://marta-eta.vercel.app"]'
export ENABLE_REAL_TIME_UPDATES=True
export ENABLE_ML_PREDICTIONS=False
export ENABLE_CACHING=False
export CACHE_TTL_SECONDS=300
export GTFS_UPDATE_SCHEDULE="0 3 * * *"
export REAL_TIME_POLL_INTERVAL=30
export MAX_RETRY_ATTEMPTS=3
export RETRY_DELAY_SECONDS=5

# Start the server
python3.12 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000