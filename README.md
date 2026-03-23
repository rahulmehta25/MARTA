# MARTA Demand Forecasting & Route Optimization Platform

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-FF6600?logo=xgboost&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-FF6F00?logo=tensorflow&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Mapbox](https://img.shields.io/badge/Mapbox-GL-000000?logo=mapbox&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript&logoColor=white)

ML system for transit rider demand prediction using real-time MARTA GTFS data. Forecasts stop-level ridership and optimizes routes through an ensemble of LSTM and XGBoost models.

## Overview

This platform ingests MARTA's GTFS Static and GTFS-RT feeds alongside weather data to predict passenger demand at the stop level. The ML pipeline combines LSTM networks for capturing temporal patterns with XGBoost for tabular feature analysis. Predictions feed into a route optimization engine that simulates schedule adjustments to reduce overcrowding and improve service efficiency.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                     │
├────────────────────┬────────────────────┬────────────────────────────────────┤
│   GTFS Static      │    GTFS-RT         │         Weather API                │
│   (Schedules)      │ (Vehicle Positions)│    (OpenWeatherMap)                │
└─────────┬──────────┴─────────┬──────────┴──────────────┬─────────────────────┘
          │                    │                         │
          ▼                    ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION PIPELINE                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │ gtfs_ingestor   │  │ gtfs_realtime   │  │ weather_fetcher │               │
│  │ (static data)   │  │ (live positions)│  │ (conditions)    │               │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘               │
└───────────┼────────────────────┼────────────────────┼────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         FEATURE ENGINEERING                                   │
│  • Temporal features (hour, day, week, holidays)                             │
│  • Spatial features (stop proximity, route density)                          │
│  • Weather encoding (temperature, precipitation)                             │
│  • Lag features (historical demand patterns)                                 │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           ML ENSEMBLE                                         │
│  ┌───────────────────────┐      ┌───────────────────────┐                    │
│  │        LSTM           │      │       XGBoost         │                    │
│  │  (Temporal Patterns)  │      │  (Tabular Features)   │                    │
│  │                       │      │                       │                    │
│  │  • Sequence length 24 │      │  • Gradient boosting  │                    │
│  │  • Attention layers   │      │  • SHAP explainability│                    │
│  │  • Batch normalization│      │  • Feature importance │                    │
│  └───────────┬───────────┘      └───────────┬───────────┘                    │
│              │                              │                                │
│              └──────────┬───────────────────┘                                │
│                         ▼                                                    │
│              ┌─────────────────────┐                                         │
│              │  Ensemble Combiner  │                                         │
│              │  (Weighted Average) │                                         │
│              └──────────┬──────────┘                                         │
└─────────────────────────┼────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI PREDICTION SERVER                                │
│  • REST endpoints (/api/v1/*)           • WebSocket (real-time updates)      │
│  • Async request handling               • Model serving & caching            │
│  • Health checks & monitoring           • Rate limiting                      │
└──────────────────────────────────────────┬───────────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         REACT FRONTEND                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │  Mapbox GL      │  │  Demand Charts  │  │  Route Optimizer│               │
│  │  (Interactive)  │  │  (Recharts)     │  │  (Simulator)    │               │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Why This Architecture

**LSTM + XGBoost Ensemble**: LSTM captures sequential dependencies in time-series data (rush hour patterns, weekly cycles), while XGBoost excels at learning from tabular features (weather, day type, stop characteristics). The ensemble outperforms either model alone.

**GTFS Standard**: MARTA publishes data in General Transit Feed Specification format, the industry standard for transit data. Using GTFS ensures compatibility with other transit agencies and third-party tools.

**FastAPI**: Async request handling is essential for real-time predictions. FastAPI's automatic OpenAPI documentation simplifies API development and testing.

**Mapbox GL**: Production-grade vector tile rendering with smooth zooming and panning. Supports custom styling for demand heatmaps and route visualization.

**Zustand + TanStack Query**: Lightweight state management without Redux boilerplate. TanStack Query handles caching, background refetching, and optimistic updates for API data.

## Features

### Demand Forecasting
- Stop-level ridership predictions up to 24 hours ahead
- Confidence intervals for uncertainty quantification
- SHAP-based feature importance for model explainability
- Anomaly detection for unusual demand patterns

### Route Optimization
- Heuristic algorithms for schedule adjustments
- Discrete event simulation for impact analysis
- Capacity constraints and operational limits
- Performance metrics (wait times, utilization, coverage)

### Real-Time Tracking
- Live vehicle positions via GTFS-RT
- WebSocket updates for arrival predictions
- Service alerts and disruption notifications

### Data Quality Monitoring
- GTFS-RT feed freshness checks
- Data validation and anomaly alerts
- Model performance drift detection

## Tech Stack

**Backend**
- Python 3.9+
- FastAPI (async API server)
- TensorFlow/Keras (LSTM models)
- XGBoost (gradient boosting)
- SQLAlchemy + PostgreSQL/SQLite
- Redis (caching, optional)

**Frontend**
- React 18 + TypeScript
- Vite (build tool)
- Mapbox GL JS (maps)
- Recharts (charts)
- Tailwind CSS + Radix UI
- Zustand (state)
- TanStack Query (data fetching)

**Infrastructure**
- Docker + Docker Compose
- GCP Cloud Run (production)
- GitHub Actions (CI/CD)

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL with PostGIS (optional, SQLite works for development)

### Quick Start

```bash
# Clone and enter directory
git clone https://github.com/rahulmehta25/MARTA.git
cd MARTA

# Backend setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
cd ..

# Configure environment
cp env.example .env
# Edit .env with your API keys (MARTA_API_KEY, OPENWEATHER_API_KEY)

# Start backend (port 8001)
python run_api.py

# Start frontend (port 3000, separate terminal)
cd frontend && npm run dev
```

### Environment Variables

```env
# Database
DATABASE_URL=sqlite:///./marta.db  # or postgresql://user:pass@localhost/marta

# MARTA GTFS-RT (optional, uses static data without)
MARTA_API_KEY=your_key_here

# Weather data (optional)
OPENWEATHER_API_KEY=your_key_here

# Logging
LOG_LEVEL=INFO
```

## API Reference

Base URL: `http://localhost:8001/api/v1`

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/health/db` | GET | Database connectivity |

### Routes & Stops

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/routes` | GET | List all routes |
| `/routes/{route_id}` | GET | Route details |
| `/stops` | GET | List all stops |
| `/stops/{stop_id}` | GET | Stop details with predictions |

### Predictions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predictions/{stop_id}` | GET | Demand forecast for stop |
| `/predictions/batch` | POST | Batch predictions |

### Real-Time

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/realtime/vehicles` | GET | Current vehicle positions |
| `/realtime/arrivals/{stop_id}` | GET | Arrival predictions |
| `/marta/rail-arrivals` | GET | Rail arrival times |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8001/ws/real-time` | Live arrival updates |
| `ws://localhost:8001/ws/alerts` | Service alerts |
| `ws://localhost:8001/ws/analytics` | Analytics stream |

Full API documentation: `http://localhost:8001/docs`

## Deployment

### Docker

```bash
docker-compose up --build
```

### Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/marta-backend

# Deploy
gcloud run deploy marta-backend \
  --image gcr.io/PROJECT_ID/marta-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2
```

### Frontend (Vercel)

```bash
cd frontend
vercel --prod
```

Set `VITE_API_URL` in Vercel project settings to point to your backend.

## Testing

```bash
# Backend tests
pytest

# With coverage
pytest --cov=src

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## License

MIT License. See [LICENSE](LICENSE) for details.

---

Built by [Rahul Mehta](https://github.com/rahulmehta25)
