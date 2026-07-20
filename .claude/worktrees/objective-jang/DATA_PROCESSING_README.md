# 🚇 MARTA Data Processing & Feature Engineering System

## Overview

This system transforms raw ingested data into ML-ready features through historical trip reconstruction and comprehensive feature engineering. It creates a unified dataset that combines static GTFS data with real-time updates, weather, events, and engineered features.

## 🔄 Processing Pipeline

### Phase 1: Trip Reconstruction
- **Input**: GTFS static data + GTFS-RT data + external data (weather, events)
- **Process**: Aligns real-time updates with scheduled data
- **Output**: Unified trip records with calculated metrics
- **Tables**: `unified_data`

### Phase 2: Feature Engineering
- **Input**: Unified trip data
- **Process**: Creates comprehensive ML features
- **Output**: ML-ready feature dataset
- **Tables**: `ml_features`

## 📊 Data Flow

```
Raw GTFS Static Data
       ↓
Raw GTFS-RT Data
       ↓
External Data (Weather, Events)
       ↓
[TRIP RECONSTRUCTION]
       ↓
Unified Data (unified_data table)
       ↓
[FEATURE ENGINEERING]
       ↓
ML Features (ml_features table)
       ↓
Ready for ML Model Training
```

## 🛠️ Components

### 1. Trip Reconstruction Module (`trip_reconstruction.py`)

**Purpose**: Reconstructs historical trips by aligning real-time data with static schedules.

**Key Functions**:
- `load_static_gtfs_data()`: Loads GTFS static data
- `load_realtime_data()`: Loads recent GTFS-RT data
- `reconstruct_trips()`: Aligns and combines data
- `calculate_dwell_time()`: Calculates vehicle dwell times
- `infer_demand_level()`: Infers demand from dwell times

**Output Schema**:
```sql
CREATE TABLE unified_data (
    record_id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    trip_id TEXT,
    route_id TEXT,
    stop_id TEXT,
    stop_sequence INTEGER,
    vehicle_id TEXT,
    latitude NUMERIC,
    longitude NUMERIC,
    scheduled_arrival_time TIMESTAMP,
    actual_arrival_time TIMESTAMP,
    scheduled_departure_time TIMESTAMP,
    actual_departure_time TIMESTAMP,
    delay_minutes NUMERIC,
    inferred_dwell_time_seconds NUMERIC,
    inferred_demand_level TEXT,
    weather_condition TEXT,
    temperature_celsius NUMERIC,
    precipitation_mm NUMERIC,
    event_flag BOOLEAN,
    day_of_week TEXT,
    hour_of_day INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    zone_id TEXT,
    nearby_pois_count INTEGER,
    historical_dwell_time_avg NUMERIC,
    historical_headway_avg NUMERIC
);
```

### 2. Feature Engineering Module (`feature_engineering.py`)

**Purpose**: Creates comprehensive ML-ready features from unified data.

**Feature Categories**:

#### Trip-Level Features
- `trip_duration_minutes`: Scheduled trip duration
- `trip_distance_km`: Trip distance (placeholder)
- `delay_minutes`: Actual vs scheduled delay
- `realized_vs_scheduled_time_diff`: Time adherence

#### Stop-Level Features
- `stop_sequence`: Order within trip
- `zone_id`: Geographic zone
- `nearby_pois_count`: Points of interest count
- `historical_dwell_time_avg`: Historical average dwell time
- `historical_headway_avg`: Historical average headway

#### Contextual Features
- `weather_condition`: Current weather
- `temperature_celsius`: Temperature
- `precipitation_mm`: Precipitation amount
- `event_flag`: Nearby events
- `weather_severity`: Weather severity score
- `temperature_category`: Temperature category

#### Time Features
- `day_of_week`: Day of week
- `hour_of_day`: Hour of day
- `is_weekend`: Weekend flag
- `is_holiday`: Holiday flag
- `month`: Month number
- `day_of_month`: Day of month

#### Cyclical Features
- `sin_hour_of_day`, `cos_hour_of_day`: Hour cyclical encoding
- `sin_day_of_week`, `cos_day_of_week`: Day cyclical encoding
- `sin_month`, `cos_month`: Month cyclical encoding

#### Lag Features
- `lag_dwell_time_1hr`: Dwell time 1 hour ago
- `lag_dwell_time_24hr`: Dwell time 24 hours ago
- `lag_dwell_time_7days`: Dwell time 7 days ago
- `lag_demand_level_1hr`: Demand level 1 hour ago
- `lag_demand_level_24hr`: Demand level 24 hours ago

#### Rolling Window Features
- `rolling_avg_dwell_time_3hr`: 3-hour rolling average
- `rolling_avg_dwell_time_24hr`: 24-hour rolling average
- `rolling_std_dwell_time_3hr`: 3-hour rolling std dev
- `rolling_max_dwell_time_3hr`: 3-hour rolling max
- `rolling_min_dwell_time_3hr`: 3-hour rolling min

#### Route-Level Features
- `route_type`: Bus or Rail
- `route_frequency_avg`: Average route frequency
- `route_delay_avg`: Average route delay

#### Stop-Level Aggregations
- `stop_demand_level_avg`: Average demand at stop
- `stop_delay_avg`: Average delay at stop
- `stop_headway_avg`: Average headway at stop

**Output Schema**:
```sql
CREATE TABLE ml_features (
    feature_id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    stop_id TEXT,
    route_id TEXT,
    trip_id TEXT,
    
    -- Target variables
    target_demand_level TEXT,
    target_dwell_time_seconds NUMERIC,
    
    -- All engineered features (50+ features)
    trip_duration_minutes NUMERIC,
    delay_minutes NUMERIC,
    weather_condition TEXT,
    temperature_celsius NUMERIC,
    event_flag BOOLEAN,
    sin_hour_of_day NUMERIC,
    cos_hour_of_day NUMERIC,
    lag_dwell_time_1hr NUMERIC,
    rolling_avg_dwell_time_3hr NUMERIC,
    -- ... and many more
);
```

### 3. Processing Orchestrator (`data_processing_orchestrator.py`)

**Purpose**: Coordinates all processing workflows with error handling and monitoring.

**Features**:
- Sequential script execution
- Data availability checks
- Comprehensive logging
- Summary report generation
- Error handling and recovery

## 🚀 Running the System

### Option 1: Run All Processing (Recommended)

```bash
python3 run_data_processing.py
```

This will:
- Check environment variables
- Verify data availability
- Run trip reconstruction
- Run feature engineering
- Generate summary report

### Option 2: Run Individual Components

```bash
# Trip reconstruction only
python3 src/data_processing/trip_reconstruction.py

# Feature engineering only
python3 src/data_processing/feature_engineering.py

# Full orchestrator
python3 src/data_processing/data_processing_orchestrator.py
```

### Option 3: Manual Database Queries

```sql
-- Check unified data
SELECT COUNT(*) FROM unified_data;
SELECT * FROM unified_data LIMIT 5;

-- Check ML features
SELECT COUNT(*) FROM ml_features;
SELECT target_demand_level, COUNT(*) FROM ml_features GROUP BY target_demand_level;
```

## 📁 File Structure

```
src/data_processing/
├── trip_reconstruction.py           # Historical trip reconstruction
├── feature_engineering.py           # ML feature creation
└── data_processing_orchestrator.py  # Orchestrates all processes

logs/
└── data_processing.log              # Processing logs

run_data_processing.py               # Simple runner script
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
export DB_HOST=localhost
export DB_NAME=marta_db
export DB_USER=marta_user
export DB_PASSWORD=marta_password
```

### Processing Parameters

**Trip Reconstruction**:
- `hours_back`: How much GTFS-RT data to process (default: 24)
- Dwell time thresholds for demand inference
- Weather and event context windows

**Feature Engineering**:
- `days_back`: How much unified data to process (default: 30)
- Rolling window sizes (3hr, 24hr, 7days)
- Lag feature periods (1hr, 24hr, 7days)

## 📊 Data Quality & Validation

### Data Quality Checks

1. **Completeness**: Check for missing required fields
2. **Consistency**: Validate time relationships
3. **Accuracy**: Verify geographic coordinates
4. **Timeliness**: Ensure data freshness

### Validation Metrics

- **Trip Reconstruction Success Rate**: % of GTFS-RT records successfully aligned
- **Feature Completeness**: % of features with valid values
- **Data Freshness**: Time since last update
- **Coverage**: % of stops/routes with data

## 🔄 Scheduling & Automation

### Automated Processing

```bash
# Daily processing (cron job)
0 3 * * * cd /path/to/marta && python3 run_data_processing.py

# Real-time processing (continuous)
nohup python3 src/data_processing/trip_reconstruction.py &
```

### Monitoring

Monitor `logs/data_processing.log` for:
- Processing success/failure rates
- Data volume trends
- Error patterns
- Performance metrics

## 🎯 Target Variables

The system creates two main target variables for ML models:

### 1. Demand Level Classification
- **Target**: `target_demand_level`
- **Classes**: Low, Normal, High, Overloaded
- **Use Case**: Categorical demand prediction

### 2. Dwell Time Regression
- **Target**: `target_dwell_time_seconds`
- **Type**: Continuous numeric
- **Use Case**: Precise dwell time prediction

## 📈 Performance Optimization

### Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_unified_data_stop_time ON unified_data(stop_id, timestamp);
CREATE INDEX idx_ml_features_stop_time ON ml_features(stop_id, timestamp);
CREATE INDEX idx_ml_features_target ON ml_features(target_demand_level);
```

### Processing Optimization

- **Batch Processing**: Process data in chunks
- **Parallel Processing**: Use multiprocessing for large datasets
- **Memory Management**: Stream data for large files
- **Caching**: Cache frequently accessed data

## 🚨 Error Handling

### Common Issues

1. **Missing Data**: Graceful handling with defaults
2. **Time Alignment**: Robust timestamp matching
3. **Geographic Errors**: Coordinate validation
4. **Database Errors**: Connection retry logic

### Recovery Strategies

- **Partial Failures**: Continue with available data
- **Data Corruption**: Skip problematic records
- **Network Issues**: Retry with exponential backoff
- **Resource Limits**: Process in smaller batches

## 🔮 Future Enhancements

### Planned Features

1. **Real-time Processing**: Stream processing with Apache Kafka
2. **Advanced Features**: Deep learning embeddings
3. **Feature Store**: Integration with Feast/Hopsworks
4. **Data Lineage**: Track data transformations
5. **A/B Testing**: Feature experimentation framework

### Scalability Improvements

1. **Distributed Processing**: Apache Spark integration
2. **Cloud Storage**: S3/Cloud Storage integration
3. **Containerization**: Docker deployment
4. **Monitoring**: Prometheus/Grafana integration

## 📞 Support

For issues or questions:
1. Check `logs/data_processing.log` for errors
2. Verify database connectivity
3. Ensure data ingestion is complete
4. Check environment variables

---

**Status**: ✅ Complete and Ready for ML Model Training 