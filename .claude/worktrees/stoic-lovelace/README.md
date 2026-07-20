# MARTA Transit Analytics Dashboard

A real-time transit analytics platform for Atlanta's MARTA rail system. Live predictions, delay alerts, demand forecasting, and interactive route visualization — deployed publicly for real riders and planners.

## Live App

The frontend is deployed on Vercel. The backend runs on Supabase Edge Functions connecting to the official MARTA Developer API.

## What It Does

- **Live arrival boards** — real-time train arrivals from the MARTA API, refreshed every 30 seconds
- **Interactive map** — all 38 MARTA rail stations across Red, Gold, Blue, and Green lines, with stop-level demand overlays
- **Demand forecasting** — ML-powered predictions showing current vs. predicted passenger load
- **Delay alerts** — automatic alerts when trains are running more than 2 minutes late
- **Route optimization** — simulated route scheduling improvements with before/after metrics
- **Dynamic stops** — demand-triggered temporary stops that appear when ridership spikes
- **Live arrivals ticker** — scrolling bar showing next trains from Five Points (system hub)
- **PWA support** — installable as a mobile app with push notifications

## Architecture

```
MARTA Developer API (GTFS-RT)
       │
       ▼
Supabase Edge Functions
 ├── marta-arrivals        → real-time train arrivals
 ├── predict-arrival       → ML arrival predictions
 ├── delay-patterns        → historical delay analysis
 ├── demand-forecast       → passenger demand forecast
 └── analytics-performance → system health metrics
       │
       ▼
React Frontend (Vercel)
 ├── Interactive Mapbox map with route lines and stop markers
 ├── Live arrivals board with ML confidence scores
 ├── Demand charts (Recharts)
 ├── Route optimization UI
 └── Real-time Supabase subscriptions
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| Styling | Tailwind CSS, Radix UI |
| Maps | Mapbox GL JS |
| Charts | Recharts |
| Animations | Framer Motion |
| State | Zustand |
| Data fetching | TanStack React Query |
| Backend | Supabase Edge Functions (Deno) |
| Database | Supabase Postgres |
| Real-time | Supabase Realtime |
| Deployment | Vercel (frontend) + Supabase (backend) |

## Local Development

### Prerequisites

- Node.js 18+
- A Supabase project (free tier works)
- A Mapbox account (free tier works)
- MARTA Developer API key (register at developerservices.itsmarta.com)

### Setup

```bash
# Clone and install
git clone <repo-url>
cd MARTA-fresh/frontend
npm install

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start dev server
npm run dev
# Open http://localhost:5173
```

### Environment Variables

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
VITE_MAPBOX_TOKEN=your-mapbox-token
VITE_API_BASE_URL=http://localhost:8001
```

### Build for Production

```bash
cd frontend
npm run build   # outputs to frontend/dist/
npm run preview # preview the production build locally
```

### Run Tests

```bash
cd frontend
npm test              # unit tests with Jest
npm run test:e2e      # end-to-end tests with Playwright
npm run test:coverage # coverage report
```

## Project Structure

```
MARTA-fresh/
├── frontend/                    # React application (deployed to Vercel)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout/          # MainLayout — header, map wrapper, ticker
│   │   │   ├── Map/             # TransitMap — Mapbox integration
│   │   │   ├── Drawer/          # Swipeable bottom panel
│   │   │   │   └── tabs/        # Overview, Demand, Optimization, Analytics
│   │   │   ├── RealTime/        # ArrivalBoard, LiveArrivalsBar
│   │   │   ├── Search/          # Stop and route search
│   │   │   ├── DynamicStops/    # Dynamic stop management UI
│   │   │   └── PWA/             # Install prompt
│   │   ├── data/
│   │   │   └── martaData.ts     # All 38 MARTA stations + 4 rail lines
│   │   ├── hooks/               # WebSocket, Supabase realtime, push notifications
│   │   ├── lib/
│   │   │   └── api.ts           # Supabase edge function client
│   │   ├── pages/               # Route-level page components
│   │   └── store/               # Zustand global state
│   ├── vercel.json              # Vercel deployment config + security headers
│   └── .env.example             # Required environment variables
├── supabase/
│   └── functions/               # Deno edge functions
│       ├── marta-arrivals/      # Proxies MARTA API with caching
│       ├── predict-arrival/     # ML arrival time prediction
│       ├── delay-patterns/      # Historical delay analysis
│       ├── demand-forecast/     # Demand prediction endpoint
│       └── analytics-performance/ # System health metrics
├── src/                         # Python ML backend (optional, local only)
│   ├── models/                  # LSTM + XGBoost demand forecasters
│   ├── optimization/            # Route optimization engine
│   └── data_ingestion/          # GTFS and GTFS-RT parsers
└── requirements.txt             # Python dependencies
```

## Deploying

### Frontend (Vercel)

```bash
cd frontend
npx vercel --prod
```

The `vercel.json` already configures:
- SPA routing rewrites
- Security headers (X-Frame-Options, CSP, etc.)
- Static asset caching

### Supabase Edge Functions

See `SUPABASE_DEPLOYMENT.md` for step-by-step deployment of the Deno edge functions.

```bash
# Deploy all edge functions
supabase functions deploy marta-arrivals
supabase functions deploy predict-arrival
supabase functions deploy delay-patterns
supabase functions deploy demand-forecast
supabase functions deploy analytics-performance
```

## MARTA Data

All station data is sourced from MARTA's official GTFS feed:

- **38 rail stations** across the Atlanta metro area
- **4 rail lines**: Red (Airport–North Springs), Gold (Airport–Doraville), Blue (H.E. Holmes–Indian Creek), Green (Bankhead–Edgewood)
- Real-time arrivals via MARTA Developer API (GTFS-RT)
- Historical delay patterns stored in Supabase Postgres

## Security

- Supabase anon key is intentionally included in the frontend bundle — it only grants public read access to published data (this is Supabase's intended use pattern)
- Service role key is never exposed to the frontend
- All API endpoints run through Supabase Edge Functions, not directly to MARTA's API
- Security headers configured in `vercel.json`

## License

MIT — built for better public transit in Atlanta.
