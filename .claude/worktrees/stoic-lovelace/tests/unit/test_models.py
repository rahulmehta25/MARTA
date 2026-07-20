"""
Unit tests for machine learning models in the MARTA platform.
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os

# Test imports
from src.models.demand_forecaster import (
    DemandForecaster,
    FeatureEngineering, 
    ModelMetrics,
    MemoryOptimizedDataLoader
)


class TestFeatureEngineering:
    """Test suite for feature engineering functionality."""
    
    def test_create_temporal_features(self, sample_ridership_data):
        """Test temporal feature creation."""
        fe = FeatureEngineering()
        
        # Add datetime column
        sample_ridership_data['datetime'] = pd.to_datetime(sample_ridership_data['date']) + \
                                          pd.to_timedelta(sample_ridership_data['hour'], unit='h')
        
        result = fe.create_temporal_features(sample_ridership_data, 'datetime')
        
        # Check that temporal features are created
        expected_features = ['hour', 'day_of_week', 'month', 'quarter', 'is_weekend', 'is_peak_hour']
        for feature in expected_features:
            assert feature in result.columns, f"Missing temporal feature: {feature}"
        
        # Test specific values
        assert result['is_weekend'].dtype == bool
        assert result['is_peak_hour'].dtype == bool
        assert result['hour'].min() >= 0
        assert result['hour'].max() <= 23
        assert result['day_of_week'].min() >= 0
        assert result['day_of_week'].max() <= 6
    
    def test_create_lag_features(self, sample_ridership_data):
        """Test lag feature creation."""
        fe = FeatureEngineering()
        
        # Sort data properly for lag features
        sample_ridership_data = sample_ridership_data.sort_values(['route', 'date', 'hour'])
        
        result = fe.create_lag_features(
            sample_ridership_data, 
            target_col='ridership', 
            group_cols=['route'],
            lags=[1, 7, 24]
        )
        
        # Check lag features exist
        assert 'ridership_lag_1' in result.columns
        assert 'ridership_lag_7' in result.columns
        assert 'ridership_lag_24' in result.columns
        
        # Check that lags have proper null handling
        assert result['ridership_lag_1'].isna().sum() > 0  # Should have some nulls at the beginning
    
    def test_create_rolling_features(self, sample_ridership_data):
        """Test rolling window feature creation."""
        fe = FeatureEngineering()
        
        sample_ridership_data = sample_ridership_data.sort_values(['route', 'date', 'hour'])
        
        result = fe.create_rolling_features(
            sample_ridership_data,
            target_col='ridership',
            group_cols=['route'],
            windows=[3, 7, 24]
        )
        
        # Check rolling features exist
        expected_features = [
            'ridership_rolling_mean_3', 'ridership_rolling_std_3',
            'ridership_rolling_mean_7', 'ridership_rolling_std_7',
            'ridership_rolling_mean_24', 'ridership_rolling_std_24'
        ]
        
        for feature in expected_features:
            assert feature in result.columns, f"Missing rolling feature: {feature}"
        
        # Check that rolling means are reasonable
        assert result['ridership_rolling_mean_3'].min() >= 0
        assert not result['ridership_rolling_mean_3'].isna().all()
    
    def test_create_weather_features(self, sample_weather_data):
        """Test weather feature engineering."""
        fe = FeatureEngineering()
        
        result = fe.create_weather_features(sample_weather_data)
        
        # Check weather-derived features
        expected_features = [
            'temp_category', 'weather_severity_score', 'is_extreme_weather'
        ]
        
        for feature in expected_features:
            assert feature in result.columns, f"Missing weather feature: {feature}"
        
        # Test categorical encoding
        assert result['temp_category'].dtype == 'category'
        assert result['weather_severity_score'].min() >= 0
        assert result['weather_severity_score'].max() <= 10


class TestModelMetrics:
    """Test suite for model metrics calculation."""
    
    def test_calculate_regression_metrics(self):
        """Test regression metrics calculation."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 2.2, 2.8, 4.1, 4.9])
        
        metrics = ModelMetrics.calculate_regression_metrics(y_true, y_pred)
        
        # Check that all expected metrics are present
        expected_metrics = ['mse', 'rmse', 'mae', 'r2', 'mape']
        for metric in expected_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
        
        # Check metric values are reasonable
        assert 0 <= metrics['r2'] <= 1
        assert metrics['rmse'] >= 0
        assert metrics['mae'] >= 0
        assert metrics['mse'] >= 0
        assert metrics['mape'] >= 0
    
    def test_calculate_time_series_metrics(self):
        """Test time series specific metrics."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 2.2, 2.8, 4.1, 4.9])
        
        metrics = ModelMetrics.calculate_time_series_metrics(y_true, y_pred)
        
        # Check time series metrics
        assert 'directional_accuracy' in metrics
        assert 'trend_accuracy' in metrics
        
        assert 0 <= metrics['directional_accuracy'] <= 1
        assert 0 <= metrics['trend_accuracy'] <= 1
    
    def test_calculate_business_metrics(self):
        """Test business-specific metrics."""
        y_true = np.array([100, 200, 150, 300, 250])
        y_pred = np.array([110, 190, 160, 290, 240])
        
        metrics = ModelMetrics.calculate_business_metrics(y_true, y_pred)
        
        assert 'underestimation_rate' in metrics
        assert 'overestimation_rate' in metrics
        assert 'peak_hour_accuracy' in metrics
        
        # Business metrics should be between 0 and 1
        assert 0 <= metrics['underestimation_rate'] <= 1
        assert 0 <= metrics['overestimation_rate'] <= 1


class TestMemoryOptimizedDataLoader:
    """Test suite for memory-optimized data loading."""
    
    def test_batch_data_generator(self, sample_ridership_data):
        """Test batch data generation."""
        loader = MemoryOptimizedDataLoader(batch_size=10)
        
        # Convert to generator
        batches = list(loader.batch_data_generator(sample_ridership_data))
        
        # Check batch sizes
        for i, batch in enumerate(batches[:-1]):  # All but last batch
            assert len(batch) == 10, f"Batch {i} has incorrect size"
        
        # Last batch might be smaller
        assert len(batches[-1]) <= 10
        
        # Check total records
        total_records = sum(len(batch) for batch in batches)
        assert total_records == len(sample_ridership_data)
    
    def test_memory_efficient_preprocessing(self, sample_ridership_data):
        """Test memory-efficient preprocessing."""
        loader = MemoryOptimizedDataLoader(batch_size=50)
        
        def simple_preprocessor(df):
            return df.assign(ridership_scaled=df['ridership'] / 100)
        
        result = loader.memory_efficient_preprocessing(
            sample_ridership_data, 
            simple_preprocessor
        )
        
        # Check preprocessing was applied
        assert 'ridership_scaled' in result.columns
        assert len(result) == len(sample_ridership_data)
        
        # Check scaling
        expected_scaled = sample_ridership_data['ridership'] / 100
        pd.testing.assert_series_equal(
            result['ridership_scaled'], 
            expected_scaled, 
            check_names=False
        )


class TestDemandForecaster:
    """Test suite for the main demand forecaster class."""
    
    @pytest.fixture
    def forecaster(self):
        """Create a demand forecaster instance for testing."""
        return DemandForecaster(
            model_type='xgboost',
            config={
                'n_estimators': 10,  # Small for testing
                'max_depth': 3,
                'learning_rate': 0.1
            }
        )
    
    def test_forecaster_initialization(self, forecaster):
        """Test forecaster initialization."""
        assert forecaster.model_type == 'xgboost'
        assert forecaster.config['n_estimators'] == 10
        assert forecaster.model is None  # Not trained yet
        assert forecaster.scaler is not None
    
    def test_prepare_features(self, forecaster, ml_test_data):
        """Test feature preparation."""
        X, y = ml_test_data
        
        # Add some temporal columns
        X['datetime'] = pd.date_range('2024-01-01', periods=len(X), freq='H')
        
        features, target = forecaster.prepare_features(X, y, target_col=None)
        
        # Check output types
        assert isinstance(features, pd.DataFrame)
        assert isinstance(target, (pd.Series, np.ndarray))
        
        # Check shapes match
        assert len(features) == len(target)
        
        # Check for temporal features
        temporal_features = ['hour', 'day_of_week', 'month']
        for feature in temporal_features:
            assert feature in features.columns, f"Missing temporal feature: {feature}"
    
    @patch('src.models.demand_forecaster.xgb.XGBRegressor')
    def test_train_model(self, mock_xgb, forecaster, ml_test_data):
        """Test model training."""
        X, y = ml_test_data
        
        # Mock the XGBoost model
        mock_model = Mock()
        mock_xgb.return_value = mock_model
        
        # Train the model
        forecaster.train(X, y)
        
        # Check that model was created and trained
        mock_xgb.assert_called_once()
        mock_model.fit.assert_called_once()
        
        # Check internal state
        assert forecaster.model is not None
        assert forecaster.is_trained
    
    def test_predict_without_training(self, forecaster, ml_test_data):
        """Test prediction fails without training."""
        X, _ = ml_test_data
        
        with pytest.raises(ValueError, match="Model has not been trained"):
            forecaster.predict(X)
    
    @patch('src.models.demand_forecaster.xgb.XGBRegressor')
    def test_predict_with_training(self, mock_xgb, forecaster, ml_test_data):
        """Test prediction after training."""
        X, y = ml_test_data
        
        # Mock the XGBoost model
        mock_model = Mock()
        mock_model.predict.return_value = np.random.rand(len(X))
        mock_xgb.return_value = mock_model
        
        # Train and predict
        forecaster.train(X, y)
        predictions = forecaster.predict(X)
        
        # Check predictions
        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == len(X)
        assert all(pred >= 0 for pred in predictions)  # Ridership should be non-negative
    
    def test_evaluate_model(self, forecaster, ml_test_data):
        """Test model evaluation."""
        X, y = ml_test_data
        
        # Create mock predictions
        y_pred = y + np.random.normal(0, 0.1 * np.std(y), len(y))
        
        metrics = forecaster.evaluate(y, y_pred)
        
        # Check evaluation metrics
        expected_metrics = ['mse', 'rmse', 'mae', 'r2', 'mape']
        for metric in expected_metrics:
            assert metric in metrics, f"Missing evaluation metric: {metric}"
        
        assert all(isinstance(v, (int, float)) for v in metrics.values())
    
    def test_cross_validation(self, forecaster, ml_test_data):
        """Test cross-validation functionality."""
        X, y = ml_test_data
        
        # Mock cross-validation results
        with patch.object(forecaster, '_perform_cv') as mock_cv:
            mock_cv.return_value = {
                'test_mse': [0.1, 0.15, 0.12, 0.09, 0.11],
                'test_r2': [0.8, 0.75, 0.78, 0.82, 0.79]
            }
            
            cv_results = forecaster.cross_validate(X, y, cv_folds=5)
            
            # Check CV results structure
            assert 'test_mse' in cv_results
            assert 'test_r2' in cv_results
            assert len(cv_results['test_mse']) == 5
            assert len(cv_results['test_r2']) == 5
    
    def test_feature_importance(self, forecaster, ml_test_data):
        """Test feature importance extraction."""
        X, y = ml_test_data
        
        # Mock trained model with feature importance
        mock_model = Mock()
        mock_model.feature_importances_ = np.random.rand(len(X.columns))
        forecaster.model = mock_model
        forecaster.is_trained = True
        forecaster.feature_names = X.columns.tolist()
        
        importance = forecaster.get_feature_importance()
        
        # Check importance structure
        assert isinstance(importance, pd.DataFrame)
        assert 'feature' in importance.columns
        assert 'importance' in importance.columns
        assert len(importance) == len(X.columns)
        assert importance['importance'].sum() > 0
    
    def test_save_and_load_model(self, forecaster, ml_test_data):
        """Test model persistence."""
        X, y = ml_test_data
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, 'test_model.pkl')
            
            # Mock trained model
            mock_model = Mock()
            forecaster.model = mock_model
            forecaster.is_trained = True
            forecaster.feature_names = X.columns.tolist()
            
            # Save model
            forecaster.save_model(model_path)
            assert os.path.exists(model_path)
            
            # Load model in new forecaster instance
            new_forecaster = DemandForecaster(model_type='xgboost')
            new_forecaster.load_model(model_path)
            
            # Check loaded state
            assert new_forecaster.is_trained
            assert new_forecaster.feature_names == X.columns.tolist()
    
    def test_hyperparameter_optimization(self, forecaster, ml_test_data):
        """Test hyperparameter optimization."""
        X, y = ml_test_data
        
        param_grid = {
            'n_estimators': [5, 10],
            'max_depth': [2, 3],
            'learning_rate': [0.1, 0.2]
        }
        
        # Mock optimization results
        with patch.object(forecaster, '_optimize_hyperparameters') as mock_opt:
            mock_opt.return_value = {
                'best_params': {'n_estimators': 10, 'max_depth': 3, 'learning_rate': 0.1},
                'best_score': 0.85,
                'cv_results': {}
            }
            
            results = forecaster.optimize_hyperparameters(X, y, param_grid)
            
            # Check optimization results
            assert 'best_params' in results
            assert 'best_score' in results
            assert 'cv_results' in results
            assert isinstance(results['best_score'], (int, float))
    
    def test_prediction_intervals(self, forecaster, ml_test_data):
        """Test prediction interval calculation."""
        X, y = ml_test_data
        
        # Mock trained model with prediction intervals
        mock_model = Mock()
        mock_model.predict.return_value = np.random.rand(len(X))
        forecaster.model = mock_model
        forecaster.is_trained = True
        
        # Mock uncertainty estimation
        with patch.object(forecaster, '_calculate_prediction_intervals') as mock_intervals:
            mock_intervals.return_value = {
                'predictions': np.random.rand(len(X)),
                'lower_bound': np.random.rand(len(X)),
                'upper_bound': np.random.rand(len(X)) + 1,
                'confidence_level': 0.95
            }
            
            intervals = forecaster.predict_with_intervals(X, confidence_level=0.95)
            
            # Check interval structure
            assert 'predictions' in intervals
            assert 'lower_bound' in intervals
            assert 'upper_bound' in intervals
            assert 'confidence_level' in intervals
            
            # Check bounds relationship
            assert all(intervals['lower_bound'] <= intervals['upper_bound'])


class TestLSTMDemandForecaster:
    """Test suite for LSTM-specific functionality."""
    
    @pytest.fixture
    def lstm_forecaster(self):
        """Create LSTM forecaster for testing."""
        return DemandForecaster(
            model_type='lstm',
            config={
                'sequence_length': 24,
                'lstm_units': 32,
                'dropout_rate': 0.2,
                'epochs': 2,  # Small for testing
                'batch_size': 32
            }
        )
    
    def test_lstm_sequence_preparation(self, lstm_forecaster, ml_test_data):
        """Test LSTM sequence data preparation."""
        X, y = ml_test_data
        
        # Sort data for time series
        X = X.sort_values('hour').reset_index(drop=True)
        y = y.iloc[X.index]
        
        sequences, targets = lstm_forecaster._prepare_sequences(X, y, sequence_length=24)
        
        # Check sequence shapes
        assert sequences.ndim == 3  # (samples, time_steps, features)
        assert targets.ndim == 1   # (samples,)
        assert sequences.shape[0] == targets.shape[0]
        assert sequences.shape[1] == 24  # sequence length
        assert sequences.shape[2] == X.shape[1]  # number of features
    
    @patch('tensorflow.keras.models.Sequential')
    def test_lstm_model_creation(self, mock_sequential, lstm_forecaster):
        """Test LSTM model architecture creation."""
        mock_model = Mock()
        mock_sequential.return_value = mock_model
        
        lstm_forecaster._build_lstm_model(input_shape=(24, 10))
        
        # Check that model was created
        mock_sequential.assert_called_once()
        mock_model.add.assert_called()  # Should add layers
        mock_model.compile.assert_called_once()  # Should compile model
    
    def test_lstm_data_scaling(self, lstm_forecaster, ml_test_data):
        """Test data scaling for LSTM."""
        X, y = ml_test_data
        
        X_scaled = lstm_forecaster._scale_features(X)
        
        # Check scaling
        assert X_scaled.shape == X.shape
        assert isinstance(X_scaled, np.ndarray)
        
        # Check that data is normalized (approximately between 0 and 1)
        assert X_scaled.min() >= -2  # Allow some tolerance
        assert X_scaled.max() <= 2


@pytest.mark.integration
class TestDemandForecasterIntegration:
    """Integration tests for demand forecaster with real-like data."""
    
    def test_end_to_end_xgboost_workflow(self, sample_ridership_data, sample_weather_data):
        """Test complete workflow with XGBoost model."""
        # Prepare data
        data = sample_ridership_data.copy()
        data['datetime'] = pd.to_datetime(data['date']) + pd.to_timedelta(data['hour'], unit='h')
        
        # Add weather data
        weather_daily = sample_weather_data.groupby('date').first().reset_index()
        data = data.merge(weather_daily, on='date', how='left')
        
        # Initialize forecaster
        forecaster = DemandForecaster(
            model_type='xgboost',
            config={
                'n_estimators': 50,
                'max_depth': 6,
                'learning_rate': 0.1,
                'random_state': 42
            }
        )
        
        # Split data
        train_size = int(0.8 * len(data))
        train_data = data[:train_size]
        test_data = data[train_size:]
        
        # Train model
        X_train = train_data.drop(['ridership'], axis=1)
        y_train = train_data['ridership']
        
        forecaster.train(X_train, y_train)
        
        # Make predictions
        X_test = test_data.drop(['ridership'], axis=1)
        y_test = test_data['ridership']
        
        predictions = forecaster.predict(X_test)
        
        # Evaluate
        metrics = forecaster.evaluate(y_test, predictions)
        
        # Check results are reasonable
        assert metrics['r2'] > 0.3  # Should have some predictive power
        assert metrics['mape'] < 50  # Should be reasonably accurate
        assert len(predictions) == len(y_test)
        assert all(p >= 0 for p in predictions)  # Non-negative predictions
    
    def test_feature_engineering_pipeline(self, sample_ridership_data, sample_weather_data):
        """Test complete feature engineering pipeline."""
        fe = FeatureEngineering()
        
        # Prepare base data
        data = sample_ridership_data.copy()
        data['datetime'] = pd.to_datetime(data['date']) + pd.to_timedelta(data['hour'], unit='h')
        data = data.sort_values(['route', 'datetime'])
        
        # Apply feature engineering
        data = fe.create_temporal_features(data, 'datetime')
        data = fe.create_lag_features(data, 'ridership', ['route'], [1, 24])
        data = fe.create_rolling_features(data, 'ridership', ['route'], [3, 24])
        
        # Add weather features
        weather_features = fe.create_weather_features(sample_weather_data)
        weather_daily = weather_features.groupby('date').first().reset_index()
        data = data.merge(weather_daily, on='date', how='left')
        
        # Check final feature set
        assert 'hour' in data.columns
        assert 'is_weekend' in data.columns
        assert 'ridership_lag_1' in data.columns
        assert 'ridership_rolling_mean_24' in data.columns
        assert 'temp_category' in data.columns
        
        # Check data quality
        assert data['ridership'].isna().sum() == 0  # Target should not have nulls
        assert data.shape[0] > 0  # Should have data
        assert data.shape[1] > 10  # Should have many features