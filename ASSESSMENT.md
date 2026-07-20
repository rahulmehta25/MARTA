# MARTA Transit Analytics Platform — Professional Assessment
**Date:** April 10, 2026  
**Assessor:** Claude Code (claude-sonnet-4-6)  
**Project Root:** `/MARTA-fresh/`

---

## Executive Summary

This project is an ambitious full-stack transit analytics platform built around Atlanta's MARTA rail system. The concept is solid, the technology choices are modern, and significant engineering effort has gone into it. However, the project is in a state that can best be described as **an impressive prototype with production-grade aspirations, but critical gaps that prevent it from being professionally deployable.** The most severe issues are a hardcoded API key in committed frontend source code, a deeply fragmented architecture with multiple competing versions of core files, and analytics UI that displays fabricated static data instead of real values.

---

## 1. What Is This Project? — Grade: B+

The MARTA Demand Forecasting & Route Optimization Platform is a web application that:

- Displays an **interactive Mapbox map** of Atlanta MARTA rail stations and routes
- Shows **real-time train arrivals** pulled from the official MARTA API
- Provides **demand forecasting** powered by ML models (scikit-learn Random Forest / Gradient Boosting)
- Offers **analytics dashboards** for system performance, congestion, and delay patterns
- Runs **automated data collection** every 30 minutes via GitHub Actions into a Supabase PostgreSQL database
- Supports **PWA installation** with service worker and offline caching
- Exposes **Supabase Edge Functions** (Deno/TypeScript) for serverless analytics computation

The concept is legitimate and valuable. Real MARTA API data is being collected (540+ arrival records, 38 stations). The transit map, connection status indicator, and real-time arrivals appear to work in production at `marta-eta.vercel.app`. This is a real, interesting project — not a toy.

---

## 2. Tech Stack & Architecture — Grade: C+

### What's Chosen

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite + SWC |
| UI Components | Radix UI, Tailwind CSS, Framer Motion |
| Maps | Mapbox GL v3 |
| State | Zustand v5 |
| Data Fetching | React Query v4 + Axios |
| Backend (Production) | Flask 3.0 on Railway |
| Backend (Unused) | FastAPI + SQLAlchemy (full `src/` dir) |
| Database (Production) | Supabase PostgreSQL (free tier) |
| Database (Dev/Fallback) | SQLite (`marta_data.db`) |
| Edge Functions | Supabase Edge Functions (Deno TypeScript) |
| CI/CD | GitHub Actions |
| Deployment | Vercel (frontend), Railway (backend) |
| ML | scikit-learn, pandas, numpy |

The technology choices are **individually excellent.** React 18 + TypeScript + Vite is a strong modern frontend stack. Supabase for a zero-cost PostgreSQL + realtime + edge function host is a clever choice. Using Mapbox GL for transit visualization is appropriate.

### The Architecture Problem

There are **two completely separate backend architectures** coexisting in this repo that were never reconciled:

**Architecture A (Production, in use):** `app.py` — a flat Flask 3.0 app, ~573 lines, using SQLite locally and Supabase via REST calls. `requirements.txt` has only 4 dependencies. This is what Railway runs.

**Architecture B (Unused, elaborate):** The `src/` directory — a full FastAPI + SQLAlchemy + PostgreSQL + Redis + Celery architecture with 82 Python files and 7,270+ lines. `requirements 2.txt` lists 30+ packages including TensorFlow, PyTorch, PostGIS, and Prometheus. `docker-compose.yml` spins up 10 services. A full Alembic migration system exists. None of this connects to production.

This split is the single biggest architectural problem. Architecture B represents a significant amount of work that is entirely disconnected from the live system. Architecture A is minimal but functional. The project needs to commit to one.

---

## 3. Current State: Build & Run — Grade: D

### Frontend

- A `dist/` directory exists, indicating the frontend **has been built** previously.
- **Critical missing file:** `tsconfig.json` is absent from the `frontend/` directory. Only `tsconfig.node.json` exists (which only covers `vite.config.ts`). This means the TypeScript compiler has no app-level configuration. Vite's SWC plugin bypasses this for builds, which is why Vite builds succeed, but `tsc --noEmit` type checking and IDE integration are broken.
- The `@supabase/supabase-js` package is imported in `lib/api.ts` but is **not listed in `package.json`** dependencies. This is a latent build failure waiting to happen when `node_modules` is fresh-installed.
- `puppeteer` is in `dependencies` (not `devDependencies`) — this is a 300MB+ package that will be bundled in production node installs unnecessarily.

### Backend

- `requirements.txt` lists only 4 packages: `flask`, `flask-cors`, `httpx`, `python-dotenv`.
- `app.py` imports `analytics_engine.py` which imports `pandas` and `supabase` — neither is in `requirements.txt`.
- `ml_models.py` imports `sklearn`, `joblib`, `numpy` — none in `requirements.txt`.
- A fresh Railway deploy would fail at startup when `import pandas` fails.
- The Python virtual environments (`venv/`, `marta_env_new/`, `marta_env_tf/`) are present in the repo root (though excluded from git via `.gitignore`). Their presence suggests local development works, but the `requirements.txt` does not reflect what is actually installed.

### Tests

- The `tests/conftest.py` imports `from config.settings import settings` and `from src.database.models import Base` — which belong to Architecture B (FastAPI/SQLAlchemy). These tests **cannot run** against the Flask production app without the full Architecture B dependency tree (PostgreSQL, Redis, etc.).
- Duplicate test files exist: `test_data_ingestion.py` and `test_data_ingestion 2.py` (same for models, optimization).

---

## 4. Code Quality — Grade: D+

### Root Directory Clutter

The project root contains **30+ markdown documentation files** (`DEPLOY_ANALYTICS.md`, `PHASE_4_COMPLETION.md`, `PHASE_5_COMPLETE.md`, `SUPABASE_DEPLOYMENT.md`, `MIGRATION_GUIDE.md`, etc.) plus 15+ standalone Python test scripts (`test_system.py`, `test_full_system.py`, `test_analytics_api.py`, `verify_data_loading.py`, etc.) and multiple competing app versions (`app.py`, `app_original.py`, `app_supabase.py`, `app_simple.py`). This is a working directory that was never cleaned up.

### Duplicate Files

Files with the `" 2"` suffix pattern appear throughout:
- `frontend/src/App 2.tsx`, `main 2.tsx`, `vite-env.d 2.ts`
- `tests/unit/test_data_ingestion 2.py`, `test_models 2.py`, `test_optimization 2.py`
- `tests/global-setup 2.js`, `global-teardown 2.js`
- `.coveragerc` and `.coveragerc 2`
- `requirements.txt` and `requirements 2.txt`

These appear to be macOS Finder duplicates from file copies. They should not be in the repository.

### Backend Code

- `analytics_engine.py` (300+ lines) and `ml_models.py` (600+ lines) are competently written with clear class structures. The ML model architecture using Random Forest and Gradient Boosting with feature engineering is reasonable.
- `app.py` itself is too large (573 lines). Route handlers, analytics logic, and data fetching are all in one file with no separation of concerns.
- `collect_data_supabase.py` is clean and focused — this is the best-written file in the backend.
- Error handling is inconsistent — some endpoints catch all exceptions and return 500, others let exceptions propagate.

### Frontend Code

- `TransitMap.tsx` at 500 lines is doing too much. Map initialization, layer management, event handling, and data transformation are all in one component.
- The Zustand store (`store/index.ts`) is well-typed and reasonably structured.
- Component organization under `src/components/` is logical.
- `lib/api.ts` and `lib/api-client.ts` appear to be two different API clients — duplicated functionality with no clear rationale for which to use when.

---

## 5. Feature Completeness — Grade: C

### Working
- Real-time MARTA rail arrivals display
- Interactive Mapbox map with station markers
- Connection status indicator
- Automated data collection (GitHub Actions, every 30 min)
- Supabase Edge Functions for demand forecasting (partially)
- PWA installation prompt and service worker registration
- Dark/Light/Satellite map style switching

### Fake / Placeholder
**This is the most important finding for the analytics features:**

`frontend/src/components/Drawer/tabs/AnalyticsTab.tsx` contains **completely hardcoded static data:**

```typescript
const performanceData = [
  { month: 'Jan', efficiency: 85, satisfaction: 78, cost: 95000 },
  { month: 'Feb', efficiency: 87, satisfaction: 81, cost: 92000 },
  // ... always the same numbers
];
const routeDistribution = [
  { name: 'Red Line', value: 35, color: '...' },
  // ... hardcoded percentages
];
```

The analytics dashboard that appears to show "Performance Analytics," "System Efficiency: 94%," and "Passenger Satisfaction: 94%" is displaying fake static numbers every time regardless of actual data. This is not connected to the real Supabase data that is being collected.

Similarly, `OverviewTab.tsx`, `DemandTab.tsx`, and `OptimizationTab.tsx` need to be audited for the same pattern.

### Half-Built
- ML predictions exist in code but are behind feature flags (`ENABLE_ML_PREDICTIONS=False` in `.env.backend`)
- Route optimization algorithms (`src/optimization/`) exist but are in Architecture B (disconnected from production)
- Bus stop/route tracking (`MARTA_ENDPOINTS.bus` is defined but never called with real data)
- Trip planner component exists but backend trip planning API is not implemented

---

## 6. UI/UX Assessment — Grade: B-

### Strengths
- The header design with gradient, animated connection indicator, and quick stats badges is polished and professional-looking.
- Map style switching (Light/Dark/Satellite) is a nice touch.
- Framer Motion animations add polish without being excessive.
- Radix UI components ensure baseline accessibility for primitives (dialogs, dropdowns, etc.).
- Mobile-responsive layout with BottomDrawer pattern is appropriate for a transit app.
- Screenshots in the repo (`assessment-main-page.png`, `assessment-analytics.png`) confirm the UI renders well.

### Weaknesses
- **No loading states or skeleton screens** — when data is fetching, the map likely shows empty or stale state with no user feedback.
- **No error states** — if the backend is down, the user gets `Reconnecting...` but no actionable message.
- **Analytics tab displays fake data** (see Feature Completeness above) — a professional-quality app cannot show fabricated metrics.
- The "AI Optimized" badge in the header is marketing copy that does not correspond to any actual live ML inference in the current deployment.
- Accessibility beyond Radix UI primitives is not tested — focus management, screen reader labels for the map, and keyboard navigation for the drawer are unknown.

---

## 7. Performance Concerns — Grade: C

- **Caching is explicitly disabled:** `.env.backend` sets `ENABLE_CACHING=False`. Redis is configured but not active.
- **No rate limiting** on the Flask API — the MARTA external API calls in `app.py` are unthrottled.
- **Bundle size risk:** `puppeteer` in production dependencies will inflate Vercel's serverless function if SSR is ever added. The frontend bundle currently uses Vite's `manualChunks` splitting (vendor, ui, router, query) which is a good start.
- **MARTA API polling:** Data collection runs every 30 minutes via GitHub Actions, which means the displayed data can be up to 30 minutes stale. The "Real-time Data" badge is misleading.
- **No database connection pooling** in Flask — each request opens a new Supabase REST connection via `httpx`.
- **`mapbox-gl` v3** is imported but the Mapbox token handling is in a separate `SET_TOKEN.sh` script — it's unclear if the token is properly set in the production Vercel environment without manual intervention.

---

## 8. Security Issues — Grade: F

**CRITICAL — Hardcoded credentials in committed source code:**

`frontend/src/lib/api.ts` (lines 4–11) contains:

```typescript
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'; // Full JWT hardcoded

const MARTA_API_KEY = 'ff98ada7-0436-42c5-b9bf-1071245ad1a0'; // Hardcoded
```

These values are committed to git history and will be bundled into the compiled JavaScript that is served to every visitor. Anyone who views source on the production site or runs `grep -r` on this repo can extract the MARTA API key and Supabase project URL. The MARTA API key should be rotated immediately and the git history should be cleaned.

**Additional security issues:**

- `.env.backend` contains `SECRET_KEY=dev-secret-key-change-in-production` — if this ever reaches Railway as-is, JWT tokens are signed with a known secret.
- `ENABLE_REAL_TIME_UPDATES=False` and `ENABLE_ML_PREDICTIONS=False` in production config means security-sensitive features are disabled, but the flags are not documented as production toggles.
- No input validation on Flask API endpoints — `station_id`, `date`, and `hour` parameters in analytics endpoints are passed directly to database queries. SQL injection risk depends on how the Supabase client constructs queries.
- `flask-cors` is configured with origins `marta-eta.vercel.app` and localhost — this is correct, but CORS alone does not protect API endpoints from server-side requests.
- The `allow_anon_writes.sql` file suggests the Supabase RLS policies were at some point relaxed to allow unauthenticated writes — this file should be reviewed and removed if it represents an insecure policy state.

---

## 9. Documentation Quality — Grade: D

The project has the **opposite of a documentation problem** — it has too much documentation. There are 30+ markdown files at the root level, many with overlapping content:

`DEPLOYMENT_README.md`, `SUPABASE_DEPLOYMENT.md`, `SUPABASE_SETUP.md`, `QUICK_START.md`, `NEXT_STEPS.md`, `PHASE_4_COMPLETION.md`, `PHASE_5_COMPLETE.md`, `ANALYTICS_DOCUMENTATION.md`, `ANALYTICS_DEPLOYMENT_SUCCESS.md`, `COMPLETION_SUMMARY.md`, `FINAL_VERIFICATION_REPORT.md`, `IMPLEMENTATION_PROGRESS.md`, `VERIFY_DEPLOYMENT.md`, `DEPLOY_ANALYTICS.md`, `DEPLOY_ANALYTICS_NOW.md`...

These appear to be session-by-session progress notes from an AI-assisted development workflow. They document the state of the project *at a point in time* rather than the current state. They cannot be trusted as accurate documentation because they contradict each other and reference deployment states that may have changed.

The `README.md` (12KB) is comprehensive and covers setup, architecture, and deployment, but it describes both Architecture A and Architecture B as if they are both in use, which is misleading.

There is **no API documentation** (no OpenAPI/Swagger spec for the Flask endpoints), no contribution guide, no architecture decision record.

---

## 10. Specific Improvements Ranked by Impact

### Priority 1 — Immediate (Security / Correctness)

1. **Rotate the MARTA API key** — it is exposed in git history and in the compiled frontend JS. Get a new key, store it only as a Vercel environment variable (`VITE_MARTA_API_KEY`), never as a fallback string in source.
2. **Remove hardcoded Supabase credentials from `frontend/src/lib/api.ts`** — use only `import.meta.env.VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`, with a build-time error if they are missing.
3. **Fix `requirements.txt`** — add `pandas`, `numpy`, `scikit-learn`, `joblib`, `supabase`, `python-dateutil`. The production backend will fail on a fresh deploy without these.
4. **Connect analytics tabs to real data** — `AnalyticsTab.tsx`, `OverviewTab.tsx`, `DemandTab.tsx` must fetch from real Supabase endpoints and display actual metrics. Static hardcoded data cannot be in a production application.

### Priority 2 — Architecture (Stability)

5. **Create `frontend/tsconfig.json`** (separate from `tsconfig.node.json`) covering `src/**/*`. Without it, type checking does not work.
6. **Choose one backend architecture** — Either promote Architecture B (FastAPI + SQLAlchemy) to production, or delete `src/` entirely and build the needed services into `app.py` properly. The current coexistence creates confusion and maintenance burden.
7. **Move `@supabase/supabase-js` to `package.json` dependencies** — it is imported but not declared, which will cause `npm ci` failures on fresh installs.

### Priority 3 — Code Quality (Maintainability)

8. **Delete all `* 2.*` duplicate files** — `App 2.tsx`, `test_models 2.py`, `.coveragerc 2`, etc. are Finder artifacts that pollute the codebase.
9. **Archive or delete root-level documentation clutter** — move all the `PHASE_*.md`, `DEPLOY_*.md`, `COMPLETION_*.md` files to a `docs/archive/` directory and replace with a single accurate `README.md`.
10. **Remove competing app files** — `app_original.py`, `app_supabase.py`, `api_simple.py`, `demo_platform.py`, `disable_synthetic_data.py` should be deleted. Only `app.py` is canonical.
11. **Move `puppeteer` to `devDependencies`** — it has no place in production frontend dependencies.

### Priority 4 — Features (Completeness)

12. **Enable ML predictions** — set `ENABLE_ML_PREDICTIONS=True` and wire the `/api/v1/analytics/demand-forecast` endpoint to the frontend Demand tab.
13. **Implement real-time data flow** — the "Real-time Data" badge should reflect actual recency. Consider using Supabase Realtime subscriptions (already partially implemented in `realtime-service.ts`) instead of polling.
14. **Add loading and error states** — every data-fetching component needs skeleton loaders and user-friendly error messages.
15. **Validate the Mapbox token pipeline** — document exactly where `VITE_MAPBOX_TOKEN` must be set in Vercel to ensure the map loads on first deploy.

---

## Category Grades Summary

| Category | Grade | Key Finding |
|---|---|---|
| Project Identity & Purpose | B+ | Clear, legitimate use case with real data |
| Tech Stack & Architecture | C+ | Good individual choices, two incompatible architectures coexist |
| Build & Run Status | D | Missing tsconfig.json, requirements.txt incomplete, @supabase missing from package.json |
| Code Quality | D+ | Duplicate files everywhere, 30+ doc files at root, multiple competing app versions |
| Feature Completeness | C | Real-time data works; analytics UI shows hardcoded fake numbers |
| UI/UX Design | B- | Polished visuals, but fake data and no loading/error states undermine it |
| Performance | C | Caching disabled, 30-min data latency called "Real-time", no perf testing |
| Security | **F** | MARTA API key and Supabase credentials hardcoded in committed frontend source |
| Documentation | D | 30+ overlapping outdated doc files; no API spec; README describes phantom architecture |
| **Overall** | **C-** | Strong concept and UI foundation, but not professionally deployable in current state |

---

## Conclusion

This project demonstrates real ambition and technical capability. The frontend design is genuinely attractive, the real-time data pipeline works, and the ML modeling work in `analytics_engine.py` and `ml_models.py` is substantive. However, it reads like a project developed in rapid sprints with AI assistance where each session added features without cleaning up the previous session's scaffolding.

To bring it to professional quality, the work falls into two clear phases: **first, fix the correctness and security issues** (hardcoded keys, missing dependencies, fake analytics data) — these are table-stakes for any production application. **Second, consolidate the architecture** — delete the dead code, commit to one backend, and make the test suite actually run against the production stack.

The bones are good. The surface needs significant work.
