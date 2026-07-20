#!/usr/bin/env python3
"""
MARTA Feature Engineering Module
Creates comprehensive features for machine learning models
"""
import os
import logging
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import sys
from sklearn.preprocessing import StandardScaler, LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# Feature store table
FEATURE_TABLE = "ml_features"

CREATE_FEATURE_TABLE = f'''
CREATE TABLE IF NOT EXISTS {FEATURE_TABLE} (
    feature_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMP,
    stop_id TEXT,
    route_id TEXT,
    trip_id TEXT,
    
    -- Target variable
    target_demand_level TEXT,
    target_dwell_time_seconds NUMERIC,
    
    -- Trip-level features
    trip_duration_minutes NUMERIC,
    trip_distance_km NUMERIC,
    delay_minutes NUMERIC,
    realized_vs_scheduled_time_diff NUMERIC,
    
    -- Stop-level features
    stop_sequence INTEGER,
    zone_id TEXT,
    nearby_pois_count INTEGER,
    historical_dwell_time_avg NUMERIC,
    historical_headway_avg NUMERIC,
    
    -- Contextual features
    weather_condition TEXT,
    temperature_celsius NUMERIC,
    precipitation_mm NUMERIC,
    event_flag BOOLEAN,
    
    -- Time features
    day_of_week TEXT,
    hour_of_day INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    month INTEGER,
    day_of_month INTEGER,
    
    -- Cyclical features
    sin_hour_of_day NUMERIC,
    cos_hour_of_day NUMERIC,
    sin_day_of_week NUMERIC,
    cos_day_of_week NUMERIC,
    sin_month NUMERIC,
    cos_month NUMERIC,
    
    -- Lag features
    lag_dwell_time_1hr NUMERIC,
    lag_dwell_time_24hr NUMERIC,
    lag_dwell_time_7days NUMERIC,
    lag_demand_level_1hr TEXT,
    lag_demand_level_24hr TEXT,
    
    -- Rolling window features
    rolling_avg_dwell_time_3hr NUMERIC,
    rolling_avg_dwell_time_24hr NUMERIC,
    rolling_std_dwell_time_3hr NUMERIC,
    rolling_max_dwell_time_3hr NUMERIC,
    rolling_min_dwell_time_3hr NUMERIC,
    
    -- Route-level features
    route_type TEXT,
    route_frequency_avg NUMERIC,
    route_delay_avg NUMERIC,
    
    -- Stop-level aggregations
    stop_demand_level_avg NUMERIC,
    stop_delay_avg NUMERIC,
    stop_headway_avg NUMERIC,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

def create_db_connection():
    """Create database connection"""
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

def setup_feature_table(conn):
    """Create feature table if it doesn't exist"""
    with conn.cursor() as cursor:
        cursor.execute(CREATE_FEATURE_TABLE)
        conn.commit()
        logging.info(f"Ensured feature table {FEATURE_TABLE} exists.")

def load_unified_data(conn, days_back: int = 30) -> pd.DataFrame:
    """Load unified data for feature engineering"""
    logging.info(f"Loading unified data from last {days_back} days...")
    
    cutoff_time = datetime.now() - timedelta(days=days_back)
    
    query = f"""
    SELECT * FROM unified_data 
    WHERE timestamp >= %s
    ORDER BY stop_id, timestamp
    """
    
    df = pd.read_sql(query, conn, params=[cutoff_time])
    logging.info(f"Loaded {len(df)} unified records")
    
    return df

def create_trip_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create trip-level features"""
    logging.info("Creating trip-level features...")
    
    # Trip duration (using scheduled times)
    df['trip_duration_minutes'] = (
        pd.to_datetime(df['scheduled_departure_time']) - 
        pd.to_datetime(df['scheduled_arrival_time'])
    ).dt.total_seconds() / 60
    
    # Realized vs scheduled time difference
    df['realized_vs_scheduled_time_diff'] = df['delay_minutes']
    
    # Trip distance (simplified - would need shapes.txt for accurate calculation)
    # Using Haversine distance between consecutive stops
    df['trip_distance_km'] = 0.0  # Placeholder
    
    return df

def create_stop_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create stop-level features"""
    logging.info("Creating stop-level features...")
    
    # Historical dwell time average (by stop, hour, day of week)
    df['historical_dwell_time_avg'] = df.groupby(['stop_id', 'hour_of_day', 'day_of_week'])[
        'inferred_dwell_time_seconds'
    ].transform(lambda x: x.rolling(window=7, min_periods=1).mean().shift(1))
    
    # Historical headway average (simplified)
    df['historical_headway_avg'] = df.groupby(['stop_id', 'hour_of_day'])[
        'timestamp'
    ].transform(lambda x: x.diff().dt.total_seconds().rolling(window=10, min_periods=1).mean().shift(1))
    
    # Nearby POIs count (placeholder)
    df['nearby_pois_count'] = 0
    
    return df

def create_contextual_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create contextual features"""
    logging.info("Creating contextual features...")
    
    # Weather features are already in unified data
    # Event flag is already in unified data
    
    # Add weather severity
    df['weather_severity'] = df['weather_condition'].map({
        'Clear': 0,
        'Clouds': 1,
        'Rain': 2,
        'Snow': 3,
        'Thunderstorm': 4,
        'Unknown': 1
    }).fillna(1)
    
    # Temperature categories
    df['temperature_category'] = pd.cut(
        df['temperature_celsius'], 
        bins=[-np.inf, 0, 10, 20, 30, np.inf],
        labels=['Very Cold', 'Cold', 'Cool', 'Warm', 'Hot']
    )
    
    return df

def create_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create time-based features"""
    logging.info("Creating time features...")
    
    # Extract time components
    df['month'] = df['timestamp'].dt.month
    df['day_of_month'] = df['timestamp'].dt.day
    
    # Cyclical features
    df['sin_hour_of_day'] = np.sin(2 * np.pi * df['hour_of_day'] / 24)
    df['cos_hour_of_day'] = np.cos(2 * np.pi * df['hour_of_day'] / 24)
    
    # Day of week (0=Monday, 6=Sunday)
    day_of_week_num = df['timestamp'].dt.dayofweek
    df['sin_day_of_week'] = np.sin(2 * np.pi * day_of_week_num / 7)
    df['cos_day_of_week'] = np.cos(2 * np.pi * day_of_week_num / 7)
    
    # Month
    df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
    df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)
    
    return df

def create_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create lag features"""
    logging.info("Creating lag features...")
    
    # Sort by stop_id and timestamp
    df = df.sort_values(['stop_id', 'timestamp'])
    
    # Lag features for dwell time
    df['lag_dwell_time_1hr'] = df.groupby('stop_id')['inferred_dwell_time_seconds'].shift(1)
    df['lag_dwell_time_24hr'] = df.groupby('stop_id')['inferred_dwell_time_seconds'].shift(24)
    df['lag_dwell_time_7days'] = df.groupby('stop_id')['inferred_dwell_time_seconds'].shift(24*7)
    
    # Lag features for demand level
    df['lag_demand_level_1hr'] = df.groupby('stop_id')['inferred_demand_level'].shift(1)
    df['lag_demand_level_24hr'] = df.groupby('stop_id')['inferred_demand_level'].shift(24)
    
    return df

def create_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create rolling window features"""
    logging.info("Creating rolling window features...")
    
    # Sort by stop_id and timestamp
    df = df.sort_values(['stop_id', 'timestamp'])
    
    # Rolling averages
    df['rolling_avg_dwell_time_3hr'] = df.groupby('stop_id')['inferred_dwell_time_seconds'].transform(
        lambda x: x.rolling(window=3, min_periods=1).mean().shift(1)
    )
    df['rolling_avg_dwell_time_24hr'] = df.groupby('stop_id')['inferred_dwell_time_seconds'].transform(
        lambda x: x.rolling(window=24, min_periods=1).mean().shift(1)
    )
    
    # Rolling statistics
    df['rolling_std_dwell_time_3hr'] = df.groupby('stop_id')['inferred_dwell_time_seconds'].transform(
        lambda x: x.rolling(window=3, min_periods=1).std().shift(1)
    )
    df['rolling_max_dwell_time_3hr'] = df.groupby('stop_id')['inferred_dwell_time_seconds'].transform(
        lambda x: x.rolling(window=3, min_periods=1).max().shift(1)
    )
    df['rolling_min_dwell_time_3hr'] = df.groupby('stop_id')['inferred_dwell_time_seconds'].transform(
        lambda x: x.rolling(window=3, min_periods=1).min().shift(1)
    )
    
    return df

def create_route_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create route-level features"""
    logging.info("Creating route-level features...")
    
    # Route type (from route_id pattern)
    df['route_type'] = df['route_id'].str.extract(r'(\d+)').astype(int).apply(
        lambda x: 'Rail' if x < 100 else 'Bus'
    )
    
    # Route frequency average
    route_freq = df.groupby('route_id')['timestamp'].count() / df.groupby('route_id')['timestamp'].nunique()
    df['route_frequency_avg'] = df['route_id'].map(route_freq)
    
    # Route delay average
    route_delay = df.groupby('route_id')['delay_minutes'].mean()
    df['route_delay_avg'] = df['route_id'].map(route_delay)
    
    return df

def create_stop_aggregations(df: pd.DataFrame) -> pd.DataFrame:
    """Create stop-level aggregations"""
    logging.info("Creating stop-level aggregations...")
    
    # Stop demand level average (encoded)
    demand_level_map = {'Low': 0, 'Normal': 1, 'High': 2, 'Overloaded': 3}
    df['demand_level_encoded'] = df['inferred_demand_level'].map(demand_level_map)
    
    stop_demand_avg = df.groupby('stop_id')['demand_level_encoded'].mean()
    df['stop_demand_level_avg'] = df['stop_id'].map(stop_demand_avg)
    
    # Stop delay average
    stop_delay_avg = df.groupby('stop_id')['delay_minutes'].mean()
    df['stop_delay_avg'] = df['stop_id'].map(stop_delay_avg)
    
    # Stop headway average
    stop_headway_avg = df.groupby('stop_id')['historical_headway_avg'].mean()
    df['stop_headway_avg'] = df['stop_id'].map(stop_headway_avg)
    
    return df

def prepare_target_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare target variables for ML models"""
    logging.info("Preparing target variables...")
    
    # Target 1: Demand level classification
    df['target_demand_level'] = df['inferred_demand_level']
    
    # Target 2: Dwell time regression
    df['target_dwell_time_seconds'] = df['inferred_dwell_time_seconds']
    
    return df

def clean_features(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and handle missing values in features"""
    logging.info("Cleaning features...")
    
    # Handle missing values
    numeric_features = df.select_dtypes(include=[np.number]).columns
    df[numeric_features] = df[numeric_features].fillna(0)
    
    # Handle categorical features
    categorical_features = df.select_dtypes(include=['object']).columns
    for col in categorical_features:
        df[col] = df[col].fillna('Unknown')
    
    # Remove infinite values
    df = df.replace([np.inf, -np.inf], 0)
    
    return df

def store_features(conn, df: pd.DataFrame):
    """Store engineered features in database"""
    if df.empty:
        logging.warning("No features to store")
        return
    
    logging.info(f"Storing {len(df)} feature records...")
    
    # Select relevant columns for storage
    feature_columns = [
        'timestamp', 'stop_id', 'route_id', 'trip_id',
        'target_demand_level', 'target_dwell_time_seconds',
        'trip_duration_minutes', 'trip_distance_km', 'delay_minutes', 'realized_vs_scheduled_time_diff',
        'stop_sequence', 'zone_id', 'nearby_pois_count', 'historical_dwell_time_avg', 'historical_headway_avg',
        'weather_condition', 'temperature_celsius', 'precipitation_mm', 'event_flag',
        'day_of_week', 'hour_of_day', 'is_weekend', 'is_holiday', 'month', 'day_of_month',
        'sin_hour_of_day', 'cos_hour_of_day', 'sin_day_of_week', 'cos_day_of_week', 'sin_month', 'cos_month',
        'lag_dwell_time_1hr', 'lag_dwell_time_24hr', 'lag_dwell_time_7days', 'lag_demand_level_1hr', 'lag_demand_level_24hr',
        'rolling_avg_dwell_time_3hr', 'rolling_avg_dwell_time_24hr', 'rolling_std_dwell_time_3hr',
        'rolling_max_dwell_time_3hr', 'rolling_min_dwell_time_3hr',
        'route_type', 'route_frequency_avg', 'route_delay_avg',
        'stop_demand_level_avg', 'stop_delay_avg', 'stop_headway_avg'
    ]
    
    # Ensure all columns exist
    for col in feature_columns:
        if col not in df.columns:
            df[col] = None
    
    with conn.cursor() as cursor:
        for _, record in df[feature_columns].iterrows():
            cursor.execute(f'''
                INSERT INTO {FEATURE_TABLE} (
                    timestamp, stop_id, route_id, trip_id,
                    target_demand_level, target_dwell_time_seconds,
                    trip_duration_minutes, trip_distance_km, delay_minutes, realized_vs_scheduled_time_diff,
                    stop_sequence, zone_id, nearby_pois_count, historical_dwell_time_avg, historical_headway_avg,
                    weather_condition, temperature_celsius, precipitation_mm, event_flag,
                    day_of_week, hour_of_day, is_weekend, is_holiday, month, day_of_month,
                    sin_hour_of_day, cos_hour_of_day, sin_day_of_week, cos_day_of_week, sin_month, cos_month,
                    lag_dwell_time_1hr, lag_dwell_time_24hr, lag_dwell_time_7days, lag_demand_level_1hr, lag_demand_level_24hr,
                    rolling_avg_dwell_time_3hr, rolling_avg_dwell_time_24hr, rolling_std_dwell_time_3hr,
                    rolling_max_dwell_time_3hr, rolling_min_dwell_time_3hr,
                    route_type, route_frequency_avg, route_delay_avg,
                    stop_demand_level_avg, stop_delay_avg, stop_headway_avg
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stop_id, timestamp) DO UPDATE SET
                    target_demand_level = EXCLUDED.target_demand_level,
                    target_dwell_time_seconds = EXCLUDED.target_dwell_time_seconds,
                    trip_duration_minutes = EXCLUDED.trip_duration_minutes,
                    delay_minutes = EXCLUDED.delay_minutes,
                    weather_condition = EXCLUDED.weather_condition,
                    temperature_celsius = EXCLUDED.temperature_celsius,
                    event_flag = EXCLUDED.event_flag
            ''', tuple(record.values))
        
        conn.commit()
        logging.info("Features stored successfully")

def generate_feature_summary(df: pd.DataFrame) -> Dict:
    """Generate summary of engineered features"""
    summary = {
        'total_records': len(df),
        'unique_stops': df['stop_id'].nunique(),
        'unique_routes': df['route_id'].nunique(),
        'date_range': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
        'feature_columns': len(df.columns),
        'missing_values': df.isnull().sum().sum(),
        'demand_level_distribution': df['target_demand_level'].value_counts().to_dict(),
        'avg_dwell_time': df['target_dwell_time_seconds'].mean(),
        'avg_delay': df['delay_minutes'].mean()
    }
    
    return summary

def main():
    """Main feature engineering process"""
    logging.info("🚀 Starting MARTA Feature Engineering")
    
    conn = create_db_connection()
    setup_feature_table(conn)
    
    try:
        # Load unified data
        df = load_unified_data(conn, days_back=30)
        
        if df.empty:
            logging.warning("⚠️ No unified data available for feature engineering")
            return
        
        # Create features
        df = create_trip_features(df)
        df = create_stop_features(df)
        df = create_contextual_features(df)
        df = create_time_features(df)
        df = create_lag_features(df)
        df = create_rolling_features(df)
        df = create_route_features(df)
        df = create_stop_aggregations(df)
        df = prepare_target_variables(df)
        df = clean_features(df)
        
        # Generate summary
        summary = generate_feature_summary(df)
        logging.info("📊 Feature Engineering Summary:")
        for key, value in summary.items():
            logging.info(f"  {key}: {value}")
        
        # Store features
        store_features(conn, df)
        
        logging.info("✅ Feature engineering completed successfully")
        
    except Exception as e:
        logging.error(f"❌ Feature engineering failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main() 