#!/usr/bin/env python3
"""
Test script for MARTA Demand Forecasting Platform
Tests core components without requiring database or external APIs
"""
import sys
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_configuration():
    """Test configuration loading"""
    logger.info("Testing configuration...")
    
    try:
        # Test basic settings
        assert settings.DB_HOST == "localhost"
        assert settings.DB_NAME == "marta_db"
        assert settings.SEQUENCE_LENGTH == 24
        assert settings.RANDOM_SEED == 42
        
        logger.info("✅ Configuration test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

def test_data_structures():
    """Test data structure creation"""
    logger.info("Testing data structures...")
    
    try:
        # Create sample GTFS data
        stops_data = pd.DataFrame({
            'stop_id': ['stop_1', 'stop_2', 'stop_3'],
            'stop_name': ['Stop A', 'Stop B', 'Stop C'],
            'stop_lat': [33.7490, 33.7500, 33.7510],
            'stop_lon': [-84.3880, -84.3890, -84.3900]
        })
        
        # Create sample real-time data
        realtime_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='H'),
            'stop_id': ['stop_1'] * 100,
            'delay_minutes': np.random.normal(2, 1, 100),
            'hour_of_day': np.random.randint(0, 24, 100),
            'is_weekend': np.random.choice([True, False], 100)
        })
        
        assert len(stops_data) == 3
        assert len(realtime_data) == 100
        assert 'stop_id' in stops_data.columns
        assert 'delay_minutes' in realtime_data.columns
        
        logger.info("✅ Data structures test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Data structures test failed: {e}")
        return False

def test_feature_engineering():
    """Test feature engineering logic"""
    logger.info("Testing feature engineering...")
    
    try:
        # Create sample data
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=50, freq='H'),
            'delay_minutes': np.random.normal(2, 1, 50),
            'stop_id': ['stop_1'] * 50
        })
        
        # Add temporal features
        df['day_of_week'] = df['timestamp'].dt.day_name()
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['is_weekend'] = df['timestamp'].dt.dayofweek >= 5
        
        # Add cyclical features
        df['hour_sin'] = np.sin(2 * np.pi * df['hour_of_day'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour_of_day'] / 24)
        
        # Add lag features
        df['delay_lag_1'] = df['delay_minutes'].shift(1)
        df['delay_lag_24'] = df['delay_minutes'].shift(24)
        
        # Add rolling features
        df['delay_rolling_mean_3'] = df['delay_minutes'].rolling(window=3, min_periods=1).mean()
        
        assert 'hour_sin' in df.columns
        assert 'delay_lag_1' in df.columns
        assert 'delay_rolling_mean_3' in df.columns
        assert len(df) == 50
        
        logger.info("✅ Feature engineering test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Feature engineering test failed: {e}")
        return False

def test_model_logic():
    """Test model logic without training"""
    logger.info("Testing model logic...")
    
    try:
        # Create sample training data
        X = np.random.randn(100, 10)  # 100 samples, 10 features
        y = np.random.randn(100)      # 100 targets
        
        # Test data splitting
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=settings.RANDOM_SEED
        )
        
        assert len(X_train) == 80
        assert len(X_test) == 20
        assert len(y_train) == 80
        assert len(y_test) == 20
        
        # Test demand classification logic
        def classify_demand(delay_value):
            if delay_value > 5:
                return 'High'
            elif delay_value > 2:
                return 'Medium'
            else:
                return 'Low'
        
        test_delays = [1, 3, 6]
        classifications = [classify_demand(d) for d in test_delays]
        expected = ['Low', 'Medium', 'High']
        
        assert classifications == expected
        
        logger.info("✅ Model logic test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Model logic test failed: {e}")
        return False

def test_visualization_data():
    """Test visualization data preparation"""
    logger.info("Testing visualization data...")
    
    try:
        # Create sample data for visualization
        dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='H')
        actual_data = np.random.normal(3, 1, len(dates))
        predicted_data = actual_data + np.random.normal(0, 0.3, len(dates))
        
        comparison_df = pd.DataFrame({
            'timestamp': dates,
            'actual': actual_data,
            'predicted': predicted_data
        })
        
        # Calculate metrics
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        rmse = np.sqrt(mean_squared_error(comparison_df['actual'], comparison_df['predicted']))
        mae = mean_absolute_error(comparison_df['actual'], comparison_df['predicted'])
        r2 = r2_score(comparison_df['actual'], comparison_df['predicted'])
        
        assert rmse > 0
        assert mae > 0
        assert r2 <= 1.0
        
        logger.info(f"✅ Visualization test passed - RMSE: {rmse:.3f}, MAE: {mae:.3f}, R²: {r2:.3f}")
        return True
    except Exception as e:
        logger.error(f"❌ Visualization test failed: {e}")
        return False

def test_monitoring():
    """Test monitoring functionality"""
    logger.info("Testing monitoring...")
    
    try:
        from src.monitoring.data_quality_monitor import DataQualityMonitor
        
        monitor = DataQualityMonitor()
        
        # Test system status
        status = monitor.get_system_status()
        assert isinstance(status, dict)
        assert 'database' in status
        assert 'gtfs_rt' in status
        assert 'models' in status
        assert 'api' in status
        
        # Test health check
        health = monitor.run_health_check()
        assert isinstance(health, dict)
        
        logger.info("✅ Monitoring test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Monitoring test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting MARTA Demand Forecasting Platform Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Data Structures", test_data_structures),
        ("Feature Engineering", test_feature_engineering),
        ("Model Logic", test_model_logic),
        ("Visualization", test_visualization_data),
        ("Monitoring", test_monitoring)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} test ERROR: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! System is ready for development.")
        return True
    else:
        logger.warning("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 