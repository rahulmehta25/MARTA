
# 🛠️ MVP: MARTA Demand Forecasting & Route Optimization Platform

## 🎯 Objective
Build a machine learning system that uses historical and real-time MARTA data to forecast stop-level rider demand, identify overcrowding patterns, and simulate optimized routes to improve service efficiency and reduce congestion.

---

## 🔗 Datasets Required

### 1. GTFS Static Data (MARTA)
- **Source**: [MARTA Developer Portal](https://itsmarta.com/app-developer-resources.aspx)
- **Format**: ZIP (CSV files)
- **Files Needed**:  
  - `stops.txt`: Stop locations (lat/lon, stop_id, stop_name)  
  - `routes.txt`: Route metadata (route_id, names)  
  - `trips.txt`: Trips per route  
  - `stop_times.txt`: Stop order and times for each trip  
  - `calendar.txt`: Service availability  
  - `shapes.txt`: Geographic shape of routes

### 2. GTFS-Realtime (MARTA)
- **Source**: [MARTA GTFS-RT API](https://itsmarta.com/app-developer-resources.aspx)  
- **Feeds Used**:  
  - Vehicle Positions (`vehicle.pb`)
  - Trip Updates (`tripupdate.pb`)
- **Format**: Protocol Buffers (parse with GTFS-RT tools)

### 3. Ridership Metrics (MARTA)
- **Source**: [Monthly KPI Reports](https://itsmarta.com/KPIRidership.aspx)
- **Format**: HTML or CSV (scrape or extract)
- **Use**: Monthly boardings by mode — validate model predictions

### 4. GIS Layers (Atlanta Regional Commission)
- **Source**: [opendata.atlantaregional.com](https://opendata.atlantaregional.com/datasets/marta-rail-stations)  
- **Data Used**:
  - MARTA station shapefiles (GeoJSON)
  - Transit corridors and boundaries
- **Purpose**: Spatial mapping and zone-based modeling

### 5. External (Optional but High Value)
- **Weather Data**: Use OpenWeatherMap API or NOAA data for ATL  
- **Event Data**: Scrape event schedules for major venues (Mercedes-Benz Stadium, Georgia Tech, etc.)

---

## 🧱 Step-by-Step Implementation

### ✅ Step 1: Data Ingestion & Normalization
- Ingest static GTFS into relational schema (PostgreSQL, SQLite, or Pandas)
- Ingest GTFS-RT feeds (vehicle positions, trip updates) continuously or in batches
- Parse realtime feeds using `gtfs-realtime-bindings` in Python (protobuf)
- Normalize output into a unified table with:
  - `trip_id`, `stop_id`, `timestamp`, `route_id`, `lat/lon`, `vehicle_id`, `delay`, `stop_sequence`

---

### ✅ Step 2: Reconstruct Historical Trips
- Join GTFS static + realtime data by `trip_id` and `stop_sequence`
- Estimate dwell times at each stop using:
  - Arrival vs. departure time difference
  - Vehicle position stalling near stops
- Infer demand from dwell time (proxy signal for boarding volume)

---

### ✅ Step 3: Feature Engineering

#### 🚍 Trip-Level Features
- `route_id`, `trip_id`, `start_time`, `day_of_week`, `delay_minutes`, `trip_duration`
- `trip_distance` (from `shapes.txt`)
- `realized_vs_scheduled_time_diff`

#### 🛑 Stop-Level Features
- `stop_id`, `stop_lat`, `stop_lon`, `stop_sequence`, `zone_id` (via GIS)
- `nearby_POIs_count` (optional via OSM)
- `historical_dwell_time`, `historical_headway`

#### 🌦️ Contextual Features
- `weather_condition`, `precipitation`, `temperature` (from weather API)
- `event_flag` (binary flag for large events near stops)

---

### ✅ Step 4: Demand Forecasting Model

#### 📈 Model Type
- MVP: Start with LSTM or XGBoost (forecast demand per stop per 15-min window)
- Advanced: Upgrade to Spatio-Temporal GCN + LSTM Hybrid for full graph-based demand forecasting

#### 🎯 Output
- Predicted number of riders per `stop_id` × `timestamp`
- Classification of stop load: Underloaded, Normal, Overloaded

---

### ✅ Step 5: Route Optimization Simulation

#### 🧠 Input
- Demand heatmap (forecasted)
- Route topology (from GTFS `shapes.txt`)
- Bus capacity assumptions

#### 🔄 Logic
- Heuristic or greedy optimizer:
  - Reroute low-utilization trips
  - Add short-turn loops or shuttles on overloaded segments
  - Simulate headway adjustments

#### 📊 Output
- Proposed new/modified routes
- Simulation of load balancing
- Impact metrics (passenger wait time, coverage score, vehicle utilization)

---

### ✅ Step 6: Visualization & Validation

- Build dashboards with:
  - Predicted vs. actual heatmaps (stop-level demand)
  - Route change simulation overlays
  - KPI comparisons with official MARTA metrics

- Tools: Streamlit or Dash for interactive UI, Plotly/Folium for mapping

---

## 📦 MVP Deliverables

| Deliverable | Description |
|-------------|-------------|
| GTFS + GTFS-RT Unified Dataset | Normalized, queryable trip-stop-level dataset with inferred demand |
| Forecasting Model | ML model predicting future demand per stop |
| Optimization Engine | Algorithm proposing new routes based on predicted demand |
| Validation Dashboard | Visual and numeric comparison vs. actual ridership data |
| Technical Notebook | Well-documented Python notebook for the full ML/data pipeline |

---

## 🧠 Optional Enhancements (Post-MVP)

- Train a transformer-based temporal model (e.g. Temporal Fusion Transformer)
- Use real APC (Automatic Passenger Counter) data if accessible
- Integrate rider surveys for socio-demographic targeting
- Deploy on cloud with scheduled GTFS-RT polling + live prediction
