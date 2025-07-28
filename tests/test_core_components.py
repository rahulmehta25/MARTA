"""
Comprehensive test suite for MARTA Demand Forecasting & Route Optimization Platform
"""
import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.settings import Settings
from src.data_ingestion.gtfs_ingestor import GTFSIngestor
from src.data_processing.feature_engineering import FeatureEngineering
from src.models.demand_forecaster import DemandForecaster
from src.optimization.route_optimizer import RouteOptimizer
from src.api.optimization_api import app


class TestSettings:
    """Test configuration settings"""
    
    def test_settings_initialization(self):
        """Test that settings can be initialized with defaults"""
        settings = Settings()
        assert settings.DB_HOST == "localhost"
        assert settings.DB_NAME == "marta_db"
        assert settings.API_PORT == 8000
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults"""
        with patch.dict(os.environ, {'DB_HOST': 'test-host', 'API_PORT': '9000'}):
            settings = Settings()
            assert settings.DB_HOST == "test-host"
            assert settings.API_PORT == 9000


class TestGTFSIngestor:
    """Test GTFS data ingestion"""
    
    @pytest.fixture
    def mock_ingestor(self):
        """Create a mock GTFS ingestor"""
        with patch('src.data_ingestion.gtfs_ingestor.psycopg2.connect') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            ingestor = GTFSIngestor()
            yield ingestor, mock_conn, mock_cursor
    
    def test_ingestor_initialization(self, mock_ingestor):
        """Test GTFS ingestor can be initialized"""
        ingestor, mock_conn, mock_cursor = mock_ingestor
        assert ingestor is not None
    
    def test_validate_gtfs_data(self, mock_ingestor):
        """Test GTFS data validation"""
        ingestor, mock_conn, mock_cursor = mock_ingestor
        
        # Mock GTFS data
        mock_gtfs_data = {
            'stops': [{'stop_id': '1', 'stop_name': 'Test Stop'}],
            'routes': [{'route_id': '1', 'route_name': 'Test Route'}],
            'trips': [{'trip_id': '1', 'route_id': '1'}]
        }
        
        result = ingestor.validate_gtfs_data(mock_gtfs_data)
        assert result is True


class TestFeatureEngineering:
    """Test feature engineering pipeline"""
    
    @pytest.fixture
    def feature_engineer(self):
        """Create a feature engineering instance"""
        return FeatureEngineering()
    
    def test_feature_engineering_initialization(self, feature_engineer):
        """Test feature engineering can be initialized"""
        assert feature_engineer is not None
    
    def test_create_temporal_features(self, feature_engineer):
        """Test temporal feature creation"""
        # Mock timestamp data
        timestamps = [
            datetime(2023, 1, 1, 8, 0, 0),
            datetime(2023, 1, 1, 9, 0, 0),
            datetime(2023, 1, 1, 10, 0, 0)
        ]
        
        features = feature_engineer.create_temporal_features(timestamps)
        
        assert 'hour' in features.columns
        assert 'day_of_week' in features.columns
        assert 'month' in features.columns
        assert len(features) == 3
    
    def test_create_weather_features(self, feature_engineer):
        """Test weather feature creation"""
        # Mock weather data
        weather_data = {
            'temperature': [70, 75, 80],
            'humidity': [60, 65, 70],
            'precipitation': [0, 0.1, 0]
        }
        
        features = feature_engineer.create_weather_features(weather_data)
        
        assert 'temperature' in features.columns
        assert 'humidity' in features.columns
        assert 'precipitation' in features.columns
        assert len(features) == 3


class TestDemandForecaster:
    """Test demand forecasting models"""
    
    @pytest.fixture
    def forecaster(self):
        """Create a demand forecaster instance"""
        return DemandForecaster()
    
    def test_forecaster_initialization(self, forecaster):
        """Test demand forecaster can be initialized"""
        assert forecaster is not None
    
    @patch('src.models.demand_forecaster.xgboost.XGBRegressor')
    def test_xgboost_model_training(self, mock_xgb, forecaster):
        """Test XGBoost model training"""
        # Mock training data
        X_train = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        y_train = [10, 20, 30]
        
        # Mock XGBoost model
        mock_model = Mock()
        mock_xgb.return_value = mock_model
        
        result = forecaster.train_xgboost_model(X_train, y_train)
        
        assert mock_model.fit.called
        assert result is not None
    
    @patch('src.models.demand_forecaster.tensorflow.keras.models.Sequential')
    def test_lstm_model_training(self, mock_lstm, forecaster):
        """Test LSTM model training"""
        # Mock training data
        X_train = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
        y_train = [10, 20]
        
        # Mock LSTM model
        mock_model = Mock()
        mock_lstm.return_value = mock_model
        
        result = forecaster.train_lstm_model(X_train, y_train)
        
        assert mock_model.fit.called
        assert result is not None


class TestRouteOptimizer:
    """Test route optimization"""
    
    @pytest.fixture
    def optimizer(self):
        """Create a route optimizer instance"""
        return RouteOptimizer()
    
    def test_optimizer_initialization(self, optimizer):
        """Test route optimizer can be initialized"""
        assert optimizer is not None
    
    def test_route_optimization(self, optimizer):
        """Test basic route optimization"""
        # Mock route data
        routes = [
            {'route_id': '1', 'stops': ['A', 'B', 'C'], 'demand': 100},
            {'route_id': '2', 'stops': ['D', 'E', 'F'], 'demand': 150}
        ]
        
        constraints = {
            'max_routes': 2,
            'max_stops_per_route': 5,
            'capacity': 200
        }
        
        result = optimizer.optimize_routes(routes, constraints)
        
        assert result is not None
        assert 'optimized_routes' in result
        assert 'total_demand' in result


class TestAPI:
    """Test API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        from fastapi.testclient import TestClient
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_optimize_routes_endpoint(self, client):
        """Test route optimization endpoint"""
        test_data = {
            "routes": [
                {"route_id": "1", "stops": ["A", "B", "C"], "demand": 100}
            ],
            "constraints": {
                "max_routes": 1,
                "max_stops_per_route": 5,
                "capacity": 200
            }
        }
        
        response = client.post("/optimize/routes", json=test_data)
        assert response.status_code == 200
    
    def test_forecast_demand_endpoint(self, client):
        """Test demand forecasting endpoint"""
        test_data = {
            "route_id": "1",
            "date": "2023-01-01",
            "features": {
                "hour": 8,
                "day_of_week": 1,
                "temperature": 70
            }
        }
        
        response = client.post("/forecast/demand", json=test_data)
        assert response.status_code == 200


class TestDataQuality:
    """Test data quality monitoring"""
    
    def test_data_validation(self):
        """Test data validation functions"""
        from src.monitoring.data_quality_monitor import DataQualityMonitor
        
        monitor = DataQualityMonitor()
        
        # Test valid data
        valid_data = {
            'stops': [{'stop_id': '1', 'stop_name': 'Test'}],
            'routes': [{'route_id': '1', 'route_name': 'Test'}]
        }
        
        result = monitor.validate_data(valid_data)
        assert result['is_valid'] is True
        
        # Test invalid data
        invalid_data = {
            'stops': [],
            'routes': [{'route_id': '1'}]  # Missing required field
        }
        
        result = monitor.validate_data(invalid_data)
        assert result['is_valid'] is False


class TestIntegration:
    """Integration tests"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_end_to_end_pipeline(self, temp_db):
        """Test end-to-end data pipeline"""
        # This would test the complete pipeline from data ingestion
        # through processing to model training
        assert True  # Placeholder for actual integration test


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 