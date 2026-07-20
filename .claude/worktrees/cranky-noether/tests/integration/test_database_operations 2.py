"""
Integration tests for database operations in the MARTA platform.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch
import psycopg2
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import asyncio

# Test imports
from src.database.models import (
    GTFSStop, GTFSRoute, GTFSTrip, GTFSStopTime,
    RidershipData, WeatherData, OptimizationResult
)
from src.database.connection_pool import ConnectionPool
from src.database.migration_manager import MigrationManager
from src.database.spatial_queries import SpatialQueryManager
from src.database.redis_cache import RedisCache


class TestDatabaseModels:
    """Test database model operations."""
    
    def test_gtfs_stop_model(self, db_session):
        """Test GTFS stop model operations."""
        # Create test stop
        stop = GTFSStop(
            stop_id='test_stop_001',
            stop_name='Test Station',
            stop_lat=33.7490,
            stop_lon=-84.3880,
            location_type=0,
            parent_station=None
        )
        
        db_session.add(stop)
        db_session.commit()
        
        # Query stop
        retrieved_stop = db_session.query(GTFSStop).filter(
            GTFSStop.stop_id == 'test_stop_001'
        ).first()
        
        assert retrieved_stop is not None
        assert retrieved_stop.stop_name == 'Test Station'
        assert retrieved_stop.stop_lat == 33.7490
        assert retrieved_stop.stop_lon == -84.3880
    
    def test_gtfs_route_model(self, db_session):
        """Test GTFS route model operations."""
        # Create test route
        route = GTFSRoute(
            route_id='test_route_001',
            agency_id='MARTA',
            route_short_name='TEST',
            route_long_name='Test Line',
            route_type=1,  # Rail
            route_color='FF0000'
        )
        
        db_session.add(route)
        db_session.commit()
        
        # Query route
        retrieved_route = db_session.query(GTFSRoute).filter(
            GTFSRoute.route_id == 'test_route_001'
        ).first()
        
        assert retrieved_route is not None
        assert retrieved_route.route_short_name == 'TEST'
        assert retrieved_route.route_type == 1
    
    def test_ridership_data_model(self, db_session):
        """Test ridership data model operations."""
        # Create test ridership record
        ridership = RidershipData(
            date=date.today(),
            hour=8,
            route_id='test_route_001',
            stop_id='test_stop_001',
            ridership=150,
            day_of_week=1,
            is_weekend=False,
            is_holiday=False
        )
        
        db_session.add(ridership)
        db_session.commit()
        
        # Query ridership
        retrieved_ridership = db_session.query(RidershipData).filter(
            RidershipData.route_id == 'test_route_001',
            RidershipData.hour == 8
        ).first()
        
        assert retrieved_ridership is not None
        assert retrieved_ridership.ridership == 150
        assert not retrieved_ridership.is_weekend
    
    def test_weather_data_model(self, db_session):
        """Test weather data model operations."""
        # Create test weather record
        weather = WeatherData(
            timestamp=datetime.now(),
            temperature_f=72.5,
            humidity=65.0,
            precipitation_inches=0.0,
            wind_speed_mph=5.2,
            weather_condition='Clear',
            is_severe_weather=False
        )
        
        db_session.add(weather)
        db_session.commit()
        
        # Query weather
        retrieved_weather = db_session.query(WeatherData).filter(
            WeatherData.weather_condition == 'Clear'
        ).first()
        
        assert retrieved_weather is not None
        assert retrieved_weather.temperature_f == 72.5
        assert not retrieved_weather.is_severe_weather
    
    def test_optimization_result_model(self, db_session):
        """Test optimization result model operations."""
        # Create test optimization result
        result = OptimizationResult(
            optimization_id='opt_test_001',
            timestamp=datetime.now(),
            method='genetic_algorithm',
            fitness_score=0.85,
            parameters={'population_size': 50, 'generations': 100},
            solution={'routes': [{'route_id': 'route_001', 'frequency': 10}]},
            metrics={'cost_reduction': 15.3, 'coverage_increase': 8.7},
            duration_seconds=120
        )
        
        db_session.add(result)
        db_session.commit()
        
        # Query result
        retrieved_result = db_session.query(OptimizationResult).filter(
            OptimizationResult.optimization_id == 'opt_test_001'
        ).first()
        
        assert retrieved_result is not None
        assert retrieved_result.fitness_score == 0.85
        assert retrieved_result.method == 'genetic_algorithm'
        assert 'cost_reduction' in retrieved_result.metrics
    
    def test_model_relationships(self, db_session):
        """Test relationships between models."""
        # Create related records
        stop = GTFSStop(
            stop_id='rel_stop_001',
            stop_name='Related Stop',
            stop_lat=33.7490,
            stop_lon=-84.3880
        )
        
        route = GTFSRoute(
            route_id='rel_route_001',
            route_short_name='REL',
            route_long_name='Related Route',
            route_type=1
        )
        
        trip = GTFSTrip(
            trip_id='rel_trip_001',
            route_id='rel_route_001',
            service_id='service_001',
            direction_id=0
        )
        
        stop_time = GTFSStopTime(
            trip_id='rel_trip_001',
            stop_id='rel_stop_001',
            arrival_time='08:00:00',
            departure_time='08:01:00',
            stop_sequence=1
        )
        
        db_session.add_all([stop, route, trip, stop_time])
        db_session.commit()
        
        # Test relationships
        retrieved_trip = db_session.query(GTFSTrip).filter(
            GTFSTrip.trip_id == 'rel_trip_001'
        ).first()
        
        assert retrieved_trip is not None
        assert retrieved_trip.route_id == 'rel_route_001'
        
        # Test stop times relationship
        stop_times = db_session.query(GTFSStopTime).filter(
            GTFSStopTime.trip_id == 'rel_trip_001'
        ).all()
        
        assert len(stop_times) == 1
        assert stop_times[0].stop_id == 'rel_stop_001'


class TestConnectionPool:
    """Test database connection pool operations."""
    
    @pytest.fixture
    def connection_pool(self):
        """Create connection pool for testing."""
        return ConnectionPool(
            host='localhost',
            database='test_marta_db',
            user='test_user',
            password='test_password',
            min_connections=1,
            max_connections=5
        )
    
    def test_connection_pool_initialization(self, connection_pool):
        """Test connection pool initialization."""
        assert connection_pool.min_connections == 1
        assert connection_pool.max_connections == 5
        assert connection_pool.host == 'localhost'
    
    def test_get_connection(self, connection_pool):
        """Test getting connection from pool."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            conn = connection_pool.get_connection()
            
            assert conn is not None
            mock_connect.assert_called_once()
    
    def test_return_connection(self, connection_pool):
        """Test returning connection to pool."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            conn = connection_pool.get_connection()
            connection_pool.return_connection(conn)
            
            # Connection should be returned to pool
            assert len(connection_pool._available_connections) > 0
    
    def test_connection_pool_exhaustion(self, connection_pool):
        """Test behavior when connection pool is exhausted."""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.return_value = Mock()
            
            # Exhaust the pool
            connections = []
            for _ in range(connection_pool.max_connections):
                connections.append(connection_pool.get_connection())
            
            # Should raise exception or wait for available connection
            with pytest.raises((Exception, TimeoutError)):
                connection_pool.get_connection(timeout=1)
    
    def test_connection_health_check(self, connection_pool):
        """Test connection health checking."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_conn.closed = 0  # Connection is open
            mock_connect.return_value = mock_conn
            
            conn = connection_pool.get_connection()
            is_healthy = connection_pool.check_connection_health(conn)
            
            assert is_healthy
    
    def test_connection_cleanup(self, connection_pool):
        """Test connection cleanup and closing."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            conn = connection_pool.get_connection()
            connection_pool.close_all_connections()
            
            mock_conn.close.assert_called()


class TestMigrationManager:
    """Test database migration operations."""
    
    @pytest.fixture
    def migration_manager(self):
        """Create migration manager for testing."""
        return MigrationManager(
            db_config={
                'host': 'localhost',
                'database': 'test_marta_db',
                'user': 'test_user',
                'password': 'test_password'
            }
        )
    
    def test_migration_manager_initialization(self, migration_manager):
        """Test migration manager initialization."""
        assert migration_manager.db_config['host'] == 'localhost'
        assert hasattr(migration_manager, 'migration_history')
    
    def test_create_migration(self, migration_manager):
        """Test creating new migration."""
        migration_name = "add_performance_indexes"
        migration_sql = """
        CREATE INDEX idx_ridership_date_hour ON ridership_data(date, hour);
        CREATE INDEX idx_weather_timestamp ON weather_data(timestamp);
        """
        
        migration_file = migration_manager.create_migration(migration_name, migration_sql)
        
        assert migration_file is not None
        assert migration_name in migration_file
        assert migration_file.endswith('.sql')
    
    def test_apply_migration(self, migration_manager):
        """Test applying database migration."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            migration_sql = "CREATE TABLE test_migration(id SERIAL PRIMARY KEY);"
            migration_id = "001_test_migration"
            
            result = migration_manager.apply_migration(migration_id, migration_sql)
            
            assert result is True
            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called()
    
    def test_rollback_migration(self, migration_manager):
        """Test rolling back database migration."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            rollback_sql = "DROP TABLE IF EXISTS test_migration;"
            migration_id = "001_test_migration"
            
            result = migration_manager.rollback_migration(migration_id, rollback_sql)
            
            assert result is True
            mock_cursor.execute.assert_called()
    
    def test_get_migration_status(self, migration_manager):
        """Test getting migration status."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock migration history
            mock_cursor.fetchall.return_value = [
                ('001_initial_schema', datetime.now(), 'applied'),
                ('002_add_indexes', datetime.now(), 'applied')
            ]
            
            status = migration_manager.get_migration_status()
            
            assert len(status) == 2
            assert status[0]['id'] == '001_initial_schema'
            assert status[0]['status'] == 'applied'
    
    def test_pending_migrations(self, migration_manager):
        """Test identifying pending migrations."""
        # Mock available migrations
        available_migrations = [
            '001_initial_schema.sql',
            '002_add_indexes.sql', 
            '003_performance_optimizations.sql'
        ]
        
        # Mock applied migrations
        applied_migrations = ['001_initial_schema', '002_add_indexes']
        
        with patch.object(migration_manager, 'get_available_migrations', return_value=available_migrations), \
             patch.object(migration_manager, 'get_applied_migrations', return_value=applied_migrations):
            
            pending = migration_manager.get_pending_migrations()
            
            assert len(pending) == 1
            assert '003_performance_optimizations.sql' in pending


class TestSpatialQueries:
    """Test spatial database operations."""
    
    @pytest.fixture
    def spatial_manager(self):
        """Create spatial query manager for testing."""
        return SpatialQueryManager(
            db_config={
                'host': 'localhost',
                'database': 'test_marta_db',
                'user': 'test_user',
                'password': 'test_password'
            }
        )
    
    def test_spatial_manager_initialization(self, spatial_manager):
        """Test spatial manager initialization."""
        assert spatial_manager.db_config['host'] == 'localhost'
        assert hasattr(spatial_manager, 'srid')  # Spatial reference system ID
    
    def test_find_nearby_stops(self, spatial_manager):
        """Test finding stops within radius."""
        center_lat, center_lon = 33.7490, -84.3880
        radius_meters = 1000
        
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock query results
            mock_cursor.fetchall.return_value = [
                ('stop_001', 'Downtown Station', 33.7490, -84.3880, 0),
                ('stop_002', 'Nearby Station', 33.7500, -84.3890, 150)
            ]
            
            nearby_stops = spatial_manager.find_nearby_stops(
                center_lat, center_lon, radius_meters
            )
            
            assert len(nearby_stops) == 2
            assert nearby_stops[0]['stop_id'] == 'stop_001'
            assert nearby_stops[1]['distance_meters'] == 150
    
    def test_calculate_route_coverage(self, spatial_manager):
        """Test calculating route coverage area."""
        route_id = 'route_001'
        buffer_meters = 800  # 800m walking distance to stops
        
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock coverage area result
            mock_cursor.fetchone.return_value = (15.5,)  # Coverage area in sq km
            
            coverage_area = spatial_manager.calculate_route_coverage(
                route_id, buffer_meters
            )
            
            assert coverage_area == 15.5
            mock_cursor.execute.assert_called()
    
    def test_find_stops_in_polygon(self, spatial_manager):
        """Test finding stops within a geographic polygon."""
        polygon_coordinates = [
            [33.7400, -84.3900],
            [33.7600, -84.3900], 
            [33.7600, -84.3800],
            [33.7400, -84.3800],
            [33.7400, -84.3900]  # Close polygon
        ]
        
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock polygon query results
            mock_cursor.fetchall.return_value = [
                ('stop_001', 'Station A', 33.7450, -84.3850),
                ('stop_002', 'Station B', 33.7550, -84.3860)
            ]
            
            stops_in_polygon = spatial_manager.find_stops_in_polygon(polygon_coordinates)
            
            assert len(stops_in_polygon) == 2
            assert stops_in_polygon[0]['stop_id'] == 'stop_001'
    
    def test_calculate_accessibility_metrics(self, spatial_manager):
        """Test calculating transit accessibility metrics."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock accessibility metrics
            mock_cursor.fetchall.return_value = [
                ('downtown', 0.95, 8.5, 12),  # area_name, accessibility_score, avg_walk_time, stop_count
                ('midtown', 0.87, 10.2, 8),
                ('airport', 0.72, 15.8, 4)
            ]
            
            accessibility_metrics = spatial_manager.calculate_accessibility_metrics()
            
            assert len(accessibility_metrics) == 3
            assert accessibility_metrics[0]['accessibility_score'] == 0.95
            assert accessibility_metrics[2]['avg_walk_time_minutes'] == 15.8


class TestRedisCache:
    """Test Redis caching operations."""
    
    @pytest.fixture
    def redis_cache(self, mock_redis):
        """Create Redis cache instance for testing."""
        return RedisCache(redis_client=mock_redis)
    
    def test_cache_initialization(self, redis_cache):
        """Test Redis cache initialization."""
        assert redis_cache.client is not None
        assert hasattr(redis_cache, 'default_ttl')
    
    def test_cache_set_get(self, redis_cache, mock_redis):
        """Test setting and getting cached values."""
        key = 'test_ridership_data'
        value = {'route_001': [100, 120, 95]}
        
        # Mock Redis responses
        mock_redis.set.return_value = True
        mock_redis.get.return_value = '{"route_001": [100, 120, 95]}'
        
        # Set cache
        result = redis_cache.set(key, value, ttl=3600)
        assert result is True
        
        # Get from cache
        cached_value = redis_cache.get(key)
        assert cached_value == value
    
    def test_cache_delete(self, redis_cache, mock_redis):
        """Test deleting cached values."""
        key = 'test_key'
        
        mock_redis.delete.return_value = 1
        
        result = redis_cache.delete(key)
        assert result is True
        mock_redis.delete.assert_called_with(key)
    
    def test_cache_exists(self, redis_cache, mock_redis):
        """Test checking if key exists in cache."""
        key = 'existing_key'
        
        mock_redis.exists.return_value = 1
        
        exists = redis_cache.exists(key)
        assert exists is True
        mock_redis.exists.assert_called_with(key)
    
    def test_cache_expire(self, redis_cache, mock_redis):
        """Test setting cache expiration."""
        key = 'expiring_key'
        ttl = 1800  # 30 minutes
        
        mock_redis.expire.return_value = True
        
        result = redis_cache.expire(key, ttl)
        assert result is True
        mock_redis.expire.assert_called_with(key, ttl)
    
    def test_cache_pattern_operations(self, redis_cache, mock_redis):
        """Test pattern-based cache operations."""
        pattern = 'ridership:*'
        
        mock_redis.keys.return_value = [
            b'ridership:route_001',
            b'ridership:route_002',
            b'ridership:route_003'
        ]
        
        keys = redis_cache.get_keys_by_pattern(pattern)
        
        assert len(keys) == 3
        assert 'ridership:route_001' in keys
        mock_redis.keys.assert_called_with(pattern)
    
    def test_cache_bulk_operations(self, redis_cache, mock_redis):
        """Test bulk cache operations."""
        data = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3'
        }
        
        mock_redis.mset.return_value = True
        mock_redis.mget.return_value = [b'value1', b'value2', b'value3']
        
        # Bulk set
        result = redis_cache.mset(data)
        assert result is True
        
        # Bulk get
        values = redis_cache.mget(list(data.keys()))
        assert len(values) == 3
        assert values[0] == 'value1'


class TestDatabasePerformance:
    """Test database performance and optimization."""
    
    def test_query_performance_optimization(self, db_session):
        """Test query performance with indexes."""
        # This would test actual query performance
        # For now, we'll test the structure
        
        # Create test data
        test_data = []
        for i in range(100):
            ridership = RidershipData(
                date=date.today() - timedelta(days=i % 30),
                hour=i % 24,
                route_id=f'route_{i % 10:03d}',
                stop_id=f'stop_{i % 50:03d}',
                ridership=np.random.randint(10, 200),
                day_of_week=(i % 7),
                is_weekend=(i % 7) >= 5,
                is_holiday=False
            )
            test_data.append(ridership)
        
        db_session.add_all(test_data)
        db_session.commit()
        
        # Test indexed query performance
        import time
        start_time = time.time()
        
        results = db_session.query(RidershipData).filter(
            RidershipData.date >= date.today() - timedelta(days=7),
            RidershipData.hour >= 7,
            RidershipData.hour <= 9
        ).all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        assert len(results) > 0
        assert query_time < 1.0  # Should complete within 1 second
    
    def test_bulk_insert_performance(self, db_session):
        """Test bulk insert operations."""
        import time
        
        # Generate large dataset
        bulk_data = []
        for i in range(1000):
            ridership = RidershipData(
                date=date.today(),
                hour=i % 24,
                route_id=f'bulk_route_{i % 10:03d}',
                stop_id=f'bulk_stop_{i % 100:03d}',
                ridership=np.random.randint(10, 200),
                day_of_week=1,
                is_weekend=False,
                is_holiday=False
            )
            bulk_data.append(ridership)
        
        start_time = time.time()
        db_session.bulk_save_objects(bulk_data)
        db_session.commit()
        end_time = time.time()
        
        insert_time = end_time - start_time
        
        # Should handle bulk inserts efficiently
        assert insert_time < 5.0  # Should complete within 5 seconds
        
        # Verify data was inserted
        count = db_session.query(RidershipData).filter(
            RidershipData.route_id.like('bulk_route_%')
        ).count()
        
        assert count == 1000
    
    def test_connection_pooling_performance(self, connection_pool):
        """Test connection pool performance under load."""
        import concurrent.futures
        import time
        
        def execute_query():
            with patch('psycopg2.connect') as mock_connect:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [(1,)]
                mock_conn.cursor.return_value = mock_cursor
                mock_connect.return_value = mock_conn
                
                conn = connection_pool.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchall()
                connection_pool.return_connection(conn)
                return len(result)
        
        # Execute concurrent queries
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(execute_query) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # All queries should succeed
        assert len(results) == 50
        assert all(r == 1 for r in results)
        
        # Should handle concurrent queries efficiently
        assert execution_time < 10.0


@pytest.mark.integration
class TestDatabaseIntegration:
    """Full integration tests for database operations."""
    
    def test_gtfs_data_ingestion_integration(self, db_session, sample_gtfs_data):
        """Test complete GTFS data ingestion workflow."""
        # Insert GTFS data
        for _, stop in sample_gtfs_data['gtfs_stops'].iterrows():
            db_stop = GTFSStop(**stop.to_dict())
            db_session.add(db_stop)
        
        for _, route in sample_gtfs_data['gtfs_routes'].iterrows():
            db_route = GTFSRoute(**route.to_dict())
            db_session.add(db_route)
        
        db_session.commit()
        
        # Verify data integrity
        stop_count = db_session.query(GTFSStop).count()
        route_count = db_session.query(GTFSRoute).count()
        
        assert stop_count == len(sample_gtfs_data['gtfs_stops'])
        assert route_count == len(sample_gtfs_data['gtfs_routes'])
    
    def test_ridership_analytics_integration(self, db_session, sample_ridership_data):
        """Test ridership data analytics queries."""
        # Insert ridership data
        for _, row in sample_ridership_data.iterrows():
            ridership = RidershipData(**row.to_dict())
            db_session.add(ridership)
        
        db_session.commit()
        
        # Test analytics queries
        # Peak hour ridership
        peak_ridership = db_session.query(RidershipData).filter(
            RidershipData.hour.in_([7, 8, 17, 18])
        ).all()
        
        # Weekend vs weekday comparison
        weekend_ridership = db_session.query(RidershipData).filter(
            RidershipData.is_weekend == True
        ).all()
        
        weekday_ridership = db_session.query(RidershipData).filter(
            RidershipData.is_weekend == False
        ).all()
        
        assert len(peak_ridership) > 0
        assert len(weekend_ridership) > 0
        assert len(weekday_ridership) > 0
    
    def test_optimization_results_storage_integration(self, db_session):
        """Test storing and retrieving optimization results."""
        # Store optimization result
        opt_result = OptimizationResult(
            optimization_id='integration_test_001',
            timestamp=datetime.now(),
            method='genetic_algorithm',
            fitness_score=0.89,
            parameters={
                'population_size': 50,
                'generations': 100,
                'mutation_rate': 0.1
            },
            solution={
                'routes': [
                    {'route_id': 'route_001', 'frequency': 8, 'cost': 150.0},
                    {'route_id': 'route_002', 'frequency': 12, 'cost': 120.0}
                ]
            },
            metrics={
                'total_cost': 270.0,
                'coverage_score': 0.94,
                'efficiency_score': 0.87
            },
            duration_seconds=95
        )
        
        db_session.add(opt_result)
        db_session.commit()
        
        # Retrieve and verify
        retrieved_result = db_session.query(OptimizationResult).filter(
            OptimizationResult.optimization_id == 'integration_test_001'
        ).first()
        
        assert retrieved_result is not None
        assert retrieved_result.fitness_score == 0.89
        assert len(retrieved_result.solution['routes']) == 2
        assert retrieved_result.metrics['total_cost'] == 270.0