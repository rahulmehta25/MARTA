"""
Global test configuration and fixtures for the MARTA platform test suite.
"""
import os
import sys
import pytest
import tempfile
import shutil
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import psycopg2
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.settings import settings
from src.database.models import Base
from src.database.connection_pool import ConnectionPool


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session") 
def temp_dir():
    """Create temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture(scope="session")
def test_db_url():
    """Database URL for testing."""
    return f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/test_{settings.DB_NAME}"


@pytest.fixture(scope="session")
def test_engine(test_db_url):
    """Create test database engine."""
    engine = create_engine(test_db_url, echo=False)
    
    # Create test database if it doesn't exist
    admin_engine = create_engine(f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/postgres")
    with admin_engine.connect() as conn:
        conn.execute("commit")
        try:
            conn.execute(f"CREATE DATABASE test_{settings.DB_NAME}")
        except Exception:
            pass  # Database already exists
    
    # Create tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    
    # Start transaction
    transaction = session.begin()
    
    yield session
    
    # Rollback transaction
    transaction.rollback()
    session.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_client = Mock()
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = True
    mock_client.exists.return_value = False
    mock_client.expire.return_value = True
    return mock_client


@pytest.fixture
def mock_external_apis():
    """Mock external API calls."""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        
        # Mock GTFS API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'status': 'success',
            'data': []
        }
        
        # Mock weather API response  
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'weather': [{'main': 'Clear', 'description': 'clear sky'}],
            'main': {'temp': 20.5, 'humidity': 65}
        }
        
        yield {'get': mock_get, 'post': mock_post}


@pytest.fixture
def sample_gtfs_data():
    """Generate sample GTFS data for testing."""
    return {
        'stops': pd.DataFrame({
            'stop_id': ['stop1', 'stop2', 'stop3'],
            'stop_name': ['Downtown Station', 'Midtown Station', 'Airport Station'],
            'stop_lat': [33.7490, 33.7701, 33.6367],
            'stop_lon': [-84.3880, -84.3850, -84.4281],
            'location_type': [0, 0, 0],
            'parent_station': ['', '', '']
        }),
        'routes': pd.DataFrame({
            'route_id': ['route1', 'route2'],
            'route_short_name': ['Red', 'Gold'],
            'route_long_name': ['Red Line', 'Gold Line'],
            'route_type': [1, 1],
            'route_color': ['FF0000', 'FFD700']
        }),
        'trips': pd.DataFrame({
            'trip_id': ['trip1', 'trip2', 'trip3'],
            'route_id': ['route1', 'route1', 'route2'],
            'service_id': ['service1', 'service1', 'service2'],
            'direction_id': [0, 1, 0],
            'shape_id': ['shape1', 'shape2', 'shape3']
        }),
        'stop_times': pd.DataFrame({
            'trip_id': ['trip1', 'trip1', 'trip2', 'trip2'],
            'stop_id': ['stop1', 'stop2', 'stop2', 'stop3'],
            'arrival_time': ['08:00:00', '08:15:00', '09:00:00', '09:20:00'],
            'departure_time': ['08:01:00', '08:16:00', '09:01:00', '09:21:00'],
            'stop_sequence': [1, 2, 1, 2]
        })
    }


@pytest.fixture
def sample_ridership_data():
    """Generate sample ridership data for testing."""
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    hours = list(range(24))
    
    data = []
    for date in dates:
        for hour in hours:
            for route in ['Red', 'Gold', 'Blue', 'Green']:
                ridership = np.random.poisson(50 + hour * 2 + np.random.normal(0, 5))
                data.append({
                    'date': date.date(),
                    'hour': hour,
                    'route': route,
                    'ridership': max(0, ridership),
                    'day_of_week': date.dayofweek,
                    'is_weekend': date.dayofweek >= 5
                })
    
    return pd.DataFrame(data)


@pytest.fixture 
def sample_weather_data():
    """Generate sample weather data for testing."""
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    
    return pd.DataFrame({
        'date': dates,
        'temperature': np.random.normal(20, 10, len(dates)),
        'humidity': np.random.uniform(30, 90, len(dates)),
        'precipitation': np.random.exponential(2, len(dates)),
        'wind_speed': np.random.gamma(2, 2, len(dates)),
        'weather_condition': np.random.choice(['Clear', 'Rain', 'Cloudy', 'Snow'], len(dates))
    })


@pytest.fixture
def sample_realtime_data():
    """Generate sample real-time transit data."""
    current_time = datetime.now()
    
    return {
        'vehicle_positions': [
            {
                'vehicle_id': 'vehicle_1',
                'route_id': 'route1',
                'trip_id': 'trip1',
                'latitude': 33.7490,
                'longitude': -84.3880,
                'timestamp': current_time.timestamp(),
                'speed': 35.5,
                'bearing': 180
            },
            {
                'vehicle_id': 'vehicle_2', 
                'route_id': 'route2',
                'trip_id': 'trip3',
                'latitude': 33.7701,
                'longitude': -84.3850,
                'timestamp': current_time.timestamp(),
                'speed': 28.2,
                'bearing': 90
            }
        ],
        'trip_updates': [
            {
                'trip_id': 'trip1',
                'route_id': 'route1',
                'stop_time_updates': [
                    {
                        'stop_id': 'stop1',
                        'arrival_delay': 120,  # 2 minutes late
                        'departure_delay': 130
                    }
                ]
            }
        ]
    }


@pytest.fixture
def ml_test_data():
    """Generate test data for ML models."""
    n_samples = 1000
    features = pd.DataFrame({
        'hour': np.random.randint(0, 24, n_samples),
        'day_of_week': np.random.randint(0, 7, n_samples), 
        'temperature': np.random.normal(20, 10, n_samples),
        'precipitation': np.random.exponential(2, n_samples),
        'is_weekend': np.random.choice([0, 1], n_samples),
        'is_holiday': np.random.choice([0, 1], n_samples, p=[0.95, 0.05]),
        'route_popularity': np.random.normal(0.5, 0.2, n_samples)
    })
    
    # Generate target variable (ridership) with realistic relationships
    target = (
        50 +  # base ridership
        features['hour'] * 2 +  # peak hours effect
        features['day_of_week'] * 5 +  # weekday effect  
        features['temperature'] * 0.5 +  # weather effect
        features['route_popularity'] * 100 +  # route popularity
        np.random.normal(0, 10, n_samples)  # noise
    )
    target = np.maximum(0, target)  # no negative ridership
    
    return features, target


@pytest.fixture
def optimization_test_data():
    """Generate test data for route optimization."""
    return {
        'routes': [
            {
                'route_id': 'route1',
                'stops': ['stop1', 'stop2', 'stop3'],
                'frequency': 10,  # minutes
                'capacity': 200,
                'operating_cost': 100.0
            },
            {
                'route_id': 'route2', 
                'stops': ['stop2', 'stop4', 'stop5'],
                'frequency': 15,
                'capacity': 150,
                'operating_cost': 80.0
            }
        ],
        'demand_matrix': np.random.poisson(20, (5, 5)),  # 5x5 stop demand matrix
        'travel_times': np.random.uniform(5, 20, (5, 5)),  # travel times between stops
        'constraints': {
            'max_frequency': 5,  # minimum 5 minute headways
            'budget': 1000.0,
            'service_coverage': 0.95
        }
    }


class DatabaseTestHelper:
    """Helper class for database testing operations."""
    
    @staticmethod
    def clear_tables(session):
        """Clear all tables for clean test state."""
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    
    @staticmethod
    def create_test_data(session, data_dict):
        """Create test data in database."""
        for model_class, records in data_dict.items():
            for record in records:
                session.add(model_class(**record))
        session.commit()


@pytest.fixture
def db_helper():
    """Database test helper fixture."""
    return DatabaseTestHelper


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CACHE_ENABLED", "false")
    monkeypatch.setenv("EXTERNAL_APIS_ENABLED", "false")


@pytest.fixture
def performance_config():
    """Configuration for performance tests."""
    return {
        'load_test_users': 10,
        'load_test_duration': 30,  # seconds
        'response_time_threshold': 2.0,  # seconds
        'throughput_threshold': 100,  # requests per second
        'memory_threshold': 500,  # MB
        'cpu_threshold': 80  # percent
    }