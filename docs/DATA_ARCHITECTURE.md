# MARTA Data Pipeline Architecture

## Overview

The MARTA Transit Analytics Platform features a comprehensive data pipeline infrastructure designed for real-time transit data ingestion, processing, quality monitoring, and ML feature generation.

## Architecture Diagram

```
                                    +------------------+
                                    |   External APIs  |
                                    +------------------+
                                           |
        +----------------------------------+----------------------------------+
        |                    |                    |                          |
   GTFS Static          GTFS-RT            Weather API              Events API
   (Daily 3AM)         (90s poll)          (30m poll)               (Daily)
        |                    |                    |                          |
        v                    v                    v                          v
+-----------------------------------------------------------------------+
|                        RAW ZONE (Immutable)                            |
|  - gtfs_static/       - gtfs_realtime/      - weather/    - events/   |
|  - Timestamped files  - Vehicle positions   - Forecasts   - Calendar  |
|  - Full history       - Trip updates        - Historical  - Venues    |
+-----------------------------------------------------------------------+
                                    |
                          [Data Quality Checks]
                          [Schema Validation]
                          [Anomaly Detection]
                                    |
                                    v
+-----------------------------------------------------------------------+
|                       PROCESSED ZONE (Cleaned)                         |
|  - Deduplicated       - Validated coordinates  - Enriched data        |
|  - Null handling      - Referential integrity  - Standardized schema  |
+-----------------------------------------------------------------------+
                                    |
                          [Feature Engineering]
                          [Aggregations]
                          [Correlations]
                                    |
                                    v
+-----------------------------------------------------------------------+
|                       FEATURE ZONE (ML-Ready)                          |
|  - Demand features    - Delay patterns      - Weather correlation     |
|  - Lag features       - Rolling averages    - Event impact            |
|  - Cyclical encoding  - Statistical summaries                         |
+-----------------------------------------------------------------------+
                                    |
                                    v
                    +-------------------------------+
                    |    PostgreSQL + Materialized  |
                    |         Views + CDC           |
                    +-------------------------------+
```

## Data Sources

### GTFS Static Data
- **Source**: MARTA Developer Portal
- **Frequency**: Daily at 3:00 AM EST
- **Contents**:
  - `stops.txt` - Station/stop locations
  - `routes.txt` - Route definitions
  - `trips.txt` - Trip schedules
  - `stop_times.txt` - Stop arrival/departure times
  - `calendar.txt` - Service schedules
  - `shapes.txt` - Route geometry

### GTFS Realtime Data
- **Source**: MARTA GTFS-RT API
- **Frequency**: Every 90 seconds
- **Contents**:
  - Vehicle Positions - Real-time vehicle locations
  - Trip Updates - Arrival/departure predictions
  - Service Alerts - Disruption notifications

### Weather Data
- **Source**: OpenWeatherMap API
- **Frequency**: Every 30 minutes
- **Contents**:
  - Current conditions
  - 48-hour forecast
  - Historical data

### Event Data
- **Source**: Atlanta venue websites
- **Frequency**: Daily
- **Contents**:
  - Mercedes-Benz Stadium events
  - State Farm Arena events
  - Major venue calendars

## Data Lake Zones

### Raw Zone
**Path**: `data/lake/raw/`

Immutable storage for incoming data exactly as received.

| Subdirectory | Contents |
|-------------|----------|
| `gtfs_static/` | GTFS ZIP files with timestamps |
| `gtfs_realtime/` | Protobuf feeds converted to JSONL |
| `weather/` | Weather API responses |
| `events/` | Scraped event data |
| `kpi/` | MARTA KPI reports |

### Processed Zone
**Path**: `data/lake/processed/`

Cleaned, validated, and deduplicated data.

| Subdirectory | Contents |
|-------------|----------|
| `gtfs/` | Combined GTFS static data |
| `weather/` | Standardized weather records |
| `events/` | Normalized event data |
| `unified/` | Merged transit data |

### Feature Zone
**Path**: `data/lake/feature/`

ML-ready feature sets.

| Subdirectory | Contents |
|-------------|----------|
| `demand/` | Demand prediction features |
| `delay/` | Delay prediction features |
| `service/` | Service quality metrics |
| `ml_training/` | Training datasets |

## Database Schema

### Core GTFS Tables

```sql
gtfs_stops (stop_id, stop_name, stop_lat, stop_lon, ...)
gtfs_routes (route_id, route_short_name, route_long_name, route_type, ...)
gtfs_trips (trip_id, route_id, service_id, direction_id, ...)
gtfs_stop_times (trip_id, stop_id, arrival_time, departure_time, ...)
gtfs_calendar (service_id, monday, tuesday, ..., start_date, end_date)
```

### Realtime Tables

```sql
gtfs_vehicle_positions (vehicle_id, trip_id, route_id, lat, lon, timestamp, ...)
gtfs_trip_updates (trip_id, stop_id, arrival_delay, departure_delay, ...)
unified_realtime_data (record_id, timestamp, trip_id, route_id, stop_id, ...)
```

### External Data Tables

```sql
weather_data (timestamp, temperature_c, precipitation_mm, weather_main, ...)
weather_forecast (forecast_timestamp, temperature_c, precipitation_probability, ...)
atlanta_events_data (venue_name, event_name, event_date, estimated_attendance, ...)
```

### Pipeline Infrastructure Tables

```sql
pipeline_job_status (job_name, status, started_at, completed_at, ...)
pipeline_logs (timestamp, pipeline_name, stage, level, message, ...)
pipeline_runs (run_id, pipeline_name, status, started_at, ...)
data_quality_metrics (check_name, check_type, status, metric_value, ...)
cdc_change_log (table_name, change_type, primary_key, old_data, new_data, ...)
retention_policies (table_name, retention_days, action, ...)
```

## Pipeline Components

### Pipeline Orchestrator
**Location**: `src/pipeline/core/pipeline_orchestrator.py`

Central scheduler for all pipeline jobs.

```python
from src.pipeline import PipelineOrchestrator

orchestrator = PipelineOrchestrator()

# Register jobs
orchestrator.register_job(
    name="gtfs_static_ingestion",
    func=ingest_gtfs_static,
    schedule_type="daily",
    schedule_value="03:00"
)

orchestrator.start()
```

### Data Quality Monitor
**Location**: `src/pipeline/monitoring/data_quality_monitor.py`

Comprehensive quality checks:

| Check Type | Description |
|-----------|-------------|
| Completeness | Required columns populated |
| Freshness | Data age within threshold |
| Schema | Column types and constraints |
| Uniqueness | Duplicate detection |
| Referential | Foreign key integrity |
| Range | Values within bounds |
| Anomaly | Volume/pattern anomalies |

### Change Data Capture (CDC)
**Location**: `src/pipeline/cdc/change_data_capture.py`

Tracks all data changes with triggers:

```sql
-- Captured for each change
- table_name
- change_type (INSERT/UPDATE/DELETE)
- primary_key
- old_data (JSON)
- new_data (JSON)
- change_timestamp
- transaction_id
```

### Retention Manager
**Location**: `src/pipeline/core/retention_manager.py`

Configurable retention policies:

| Table | Retention | Action |
|-------|-----------|--------|
| `gtfs_vehicle_positions` | 30 days | Archive |
| `gtfs_trip_updates` | 30 days | Archive |
| `unified_realtime_data` | 90 days | Archive |
| `pipeline_logs` | 60 days | Delete |
| `cdc_change_log` | 30 days | Delete |
| `weather_data` | 365 days | Archive |

## Materialized Views

### Real-time Operations

| View | Refresh | Purpose |
|------|---------|---------|
| `mv_fleet_status` | 1 min | Active vehicles, occupancy |
| `mv_stop_utilization` | 30 min | Stop activity heatmap |

### Analytics

| View | Refresh | Purpose |
|------|---------|---------|
| `mv_hourly_delay_patterns` | 15 min | Delay by route/hour/day |
| `mv_weather_transit_impact` | 1 hour | Weather correlation |
| `mv_event_transit_impact` | Daily | Event impact analysis |

### ML Features

| View | Refresh | Purpose |
|------|---------|---------|
| `mv_ml_demand_features` | 1 hour | Pre-computed ML features |

## Data Dictionary

### Key Dimensions

| Field | Type | Description |
|-------|------|-------------|
| `stop_id` | VARCHAR | Unique stop identifier |
| `route_id` | VARCHAR | Unique route identifier |
| `trip_id` | VARCHAR | Unique trip identifier |
| `vehicle_id` | VARCHAR | Vehicle identifier |

### Key Metrics

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `arrival_delay` | INTEGER | seconds | Delay from schedule |
| `departure_delay` | INTEGER | seconds | Departure delay |
| `speed` | NUMERIC | m/s | Vehicle speed |
| `temperature_c` | NUMERIC | Celsius | Temperature |
| `precipitation_mm` | NUMERIC | mm | Precipitation |

### Feature Encodings

| Feature | Encoding | Range |
|---------|----------|-------|
| `hour_sin` | sin(2*pi*hour/24) | [-1, 1] |
| `hour_cos` | cos(2*pi*hour/24) | [-1, 1] |
| `dow_sin` | sin(2*pi*dow/7) | [-1, 1] |
| `dow_cos` | cos(2*pi*dow/7) | [-1, 1] |
| `is_weekend` | Binary | 0/1 |
| `is_precipitation` | Binary | 0/1 |

## Monitoring

### Pipeline Health Metrics

```python
from src.pipeline.monitoring import PipelineStatusTracker

tracker = PipelineStatusTracker()
health = tracker.get_pipeline_health()

# Returns:
{
    'status': 'healthy',  # healthy/degraded/unhealthy
    'health_score': 0.95,
    'last_hour': {
        'jobs_total': 40,
        'jobs_successful': 39,
        'error_count': 2
    }
}
```

### Data Quality Dashboard

```python
from src.pipeline.monitoring import DataQualityMonitor

monitor = DataQualityMonitor()
summary = monitor.get_quality_summary(hours=24)

# Returns:
{
    'pass_rate': 0.98,
    'status_counts': {'passed': 450, 'warning': 8, 'failed': 2},
    'unacknowledged_alerts': 1
}
```

### Table Freshness

```python
tracker.get_all_table_freshness()

# Returns:
[
    {'table_name': 'gtfs_vehicle_positions', 'age_seconds': 45, 'is_stale': False},
    {'table_name': 'weather_data', 'age_seconds': 1200, 'is_stale': False},
    ...
]
```

## Configuration

### Environment Variables

```bash
# Database
DB_HOST=localhost
DB_NAME=marta_db
DB_USER=marta_user
DB_PASSWORD=your_password
DB_PORT=5432

# APIs
MARTA_API_KEY=your_marta_api_key
OPENWEATHER_API_KEY=your_weather_api_key

# Pipeline
GTFS_RT_POLL_INTERVAL=90
LOG_LEVEL=INFO
```

### Retention Configuration

Edit retention policies in `src/pipeline/core/retention_manager.py`:

```python
RetentionPolicy(
    table_name="gtfs_vehicle_positions",
    retention_days=30,
    action=RetentionAction.ARCHIVE,
    partition_column="timestamp"
)
```

## Running the Pipeline

### Start Pipeline Orchestrator

```bash
# Start all scheduled jobs
python -m src.pipeline.core.pipeline_orchestrator

# Run specific job manually
python -c "
from src.pipeline import PipelineOrchestrator
orch = PipelineOrchestrator()
orch.run_job_now('gtfs_realtime_ingestion')
"
```

### Manual Data Ingestion

```bash
# GTFS Static
python run_real_data_ingestion.py --gtfs-static

# GTFS Realtime (single fetch)
python run_real_data_ingestion.py --gtfs-realtime

# Weather
python -m src.data_ingestion.weather_integration
```

### Quality Checks

```bash
python -m src.pipeline.monitoring.data_quality_monitor
```

### Retention Cleanup

```bash
python -m src.pipeline.core.retention_manager
```

## Troubleshooting

### Common Issues

**Pipeline jobs failing**
```sql
-- Check recent errors
SELECT * FROM pipeline_logs
WHERE level IN ('ERROR', 'CRITICAL')
ORDER BY timestamp DESC LIMIT 20;
```

**Data freshness alerts**
```sql
-- Check last ingestion times
SELECT * FROM ingestion_timestamps
ORDER BY last_successful_ingestion DESC;
```

**Quality check failures**
```sql
-- Get failed quality checks
SELECT * FROM data_quality_metrics
WHERE status IN ('failed', 'error')
ORDER BY check_timestamp DESC LIMIT 20;
```

### Replay CDC Changes

```python
from src.pipeline.cdc import ChangeDataCapture

cdc = ChangeDataCapture()
cdc.replay_changes(
    table_name='gtfs_stops',
    since=datetime(2024, 1, 1),
    target_table='gtfs_stops_replay'
)
```

## Performance Tuning

### Materialized View Refresh

Adjust refresh intervals in `database/enhanced_materialized_views.sql`:

```sql
-- High frequency views (every 5 min)
mv_fleet_status
mv_pipeline_health

-- Medium frequency (every 15 min)
mv_hourly_delay_patterns

-- Low frequency (hourly/daily)
mv_weather_transit_impact
mv_event_transit_impact
```

### Database Indexes

Key indexes are created automatically. For additional optimization:

```sql
-- Add covering index for common queries
CREATE INDEX idx_trip_updates_route_time
ON gtfs_trip_updates(route_id, timestamp)
INCLUDE (arrival_delay, stop_id);
```

## Security

- Service role key required for write operations
- Row-level security on Supabase tables
- API keys stored in environment variables
- No credentials in code or logs
