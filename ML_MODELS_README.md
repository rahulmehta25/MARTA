# 🚇 MARTA Machine Learning Models

## Overview

This system implements comprehensive machine learning models for MARTA demand forecasting, including LSTM time-series models, XGBoost gradient boosting, and ensemble methods. The models predict both dwell times (regression) and demand levels (classification) to support route optimization.

## 🧠 Model Architecture

### 1. LSTM Demand Forecaster (`lstm_demand_forecaster.py`)

**Purpose**: Time-series forecasting using Long Short-Term Memory networks

**Features**:
- **Architecture**: Multi-layer LSTM with dropout and batch normalization
- **Input**: 24-hour sequences of engineered features
- **Output**: Dwell time predictions (regression) or demand level classification
- **Targets**: 
  - `target_dwell_time_seconds` (regression)
  - `target_demand_level` (classification: Low, Normal, High, Overloaded)

**Model Configuration**:
```python
MODEL_CONFIG = {
    'sequence_length': 24,  # Use last 24 hours to predict next hour
    'prediction_horizon': 1,  # Predict 1 hour ahead
    'lstm_units': [128, 64, 32],
    'dropout_rate': 0.2,
    'learning_rate': 0.001,
    'batch_size': 32,
    'epochs': 100
}
```

### 2. XGBoost Demand Forecaster (`xgboost_demand_forecaster.py`)

**Purpose**: Traditional gradient boosting for demand forecasting

**Features**:
- **Architecture**: XGBoost with hyperparameter optimization
- **Input**: Engineered features with lag and rolling window statistics
- **Output**: Dwell time predictions or demand level classification
- **Comparison**: Includes Random Forest baseline for comparison

**Model Configuration**:
```python
XGBOOST_CONFIG = {
    'regression': {
        'objective': 'reg:squarederror',
        'n_estimators': 1000,
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8
    },
    'classification': {
        'objective': 'multi:softprob',
        'n_estimators': 1000,
        'max_depth': 6,
        'learning_rate': 0.05
    }
}
```

### 3. Model Ensemble (`model_ensemble.py`)

**Purpose**: Combines LSTM and XGBoost predictions for improved accuracy

**Features**:
- **Architecture**: Voting ensemble (regression) or soft voting (classification)
- **Input**: Predictions from individual models
- **Output**: Ensemble predictions with improved accuracy
- **Meta-learner**: Linear regression for regression, logistic regression for classification

## 📊 Model Performance Metrics

### Regression Metrics (Dwell Time)
- **MSE**: Mean Squared Error
- **MAE**: Mean Absolute Error  
- **RMSE**: Root Mean Squared Error
- **R² Score**: Coefficient of determination

### Classification Metrics (Demand Level)
- **Accuracy**: Overall classification accuracy
- **Precision**: Per-class precision scores
- **Recall**: Per-class recall scores
- **F1-Score**: Per-class F1 scores
- **Confusion Matrix**: Detailed classification results

## 🚀 Quick Start

### Prerequisites

1. **Environment Setup**:
```bash
# Set environment variables
export DB_HOST=localhost
export DB_NAME=marta_db
export DB_USER=marta_user
export DB_PASSWORD=marta_password

# Install dependencies
pip install tensorflow xgboost scikit-learn joblib
```

2. **Data Requirements**:
- ML features must be available in `ml_features` table
- Target variables: `target_dwell_time_seconds`, `target_demand_level`
- At least 90 days of historical data recommended

### Running Model Training

#### Option 1: Complete Training Pipeline
```bash
python run_model_training.py
```

#### Option 2: Individual Models
```bash
# Train LSTM models
python src/models/lstm_demand_forecaster.py

# Train XGBoost models
python src/models/xgboost_demand_forecaster.py

# Train ensemble models
python src/models/model_ensemble.py
```

#### Option 3: Training Orchestrator
```bash
python src/models/model_training_orchestrator.py
```

## 📁 Model Storage Structure

```
models/
├── lstm/
│   ├── lstm_dwell_time_best.h5
│   ├── lstm_dwell_time_final.h5
│   ├── lstm_demand_level_best.h5
│   ├── lstm_demand_level_final.h5
│   ├── lstm_dwell_time_info.pkl
│   └── lstm_demand_level_info.pkl
├── xgboost/
│   ├── xgboost_dwell_time_model.pkl
│   ├── xgboost_demand_level_model.pkl
│   ├── xgboost_dwell_time_info.pkl
│   └── xgboost_demand_level_info.pkl
├── ensemble/
│   ├── ensemble_dwell_time_model.pkl
│   ├── ensemble_demand_level_model.pkl
│   ├── ensemble_dwell_time_info.pkl
│   └── ensemble_demand_level_info.pkl
└── scalers/
    ├── feature_scaler_dwell_time.pkl
    ├── feature_scaler_demand_level.pkl
    ├── target_scaler_dwell_time.pkl
    └── label_encoder_demand_level.pkl
```

## 🔧 Model Configuration

### LSTM Configuration
- **Sequence Length**: 24 hours (configurable)
- **Prediction Horizon**: 1 hour ahead
- **Architecture**: 3 LSTM layers with decreasing units
- **Regularization**: Dropout (0.2) and batch normalization
- **Optimizer**: Adam with learning rate scheduling

### XGBoost Configuration
- **Estimators**: 1000 trees with early stopping
- **Max Depth**: 6 levels
- **Learning Rate**: 0.05
- **Subsampling**: 0.8 for both rows and columns
- **Cross-validation**: Built-in with early stopping

### Ensemble Configuration
- **Voting Method**: 
  - Regression: VotingRegressor (average)
  - Classification: VotingClassifier (soft voting)
- **Meta-learner**: Linear/Logistic regression as fallback
- **Weight Assignment**: Equal weights for all models

## 📈 Training Process

### Data Preparation
1. **Feature Loading**: Load engineered features from `ml_features` table
2. **Data Cleaning**: Handle missing values and outliers
3. **Scaling**: Standardize features and targets
4. **Sequence Creation**: Create time-series sequences for LSTM
5. **Train/Val/Test Split**: 70/15/15 split with temporal ordering

### Training Pipeline
1. **LSTM Training**:
   - Sequence creation and batching
   - Model architecture building
   - Training with callbacks (early stopping, checkpointing)
   - Validation and testing

2. **XGBoost Training**:
   - Feature preparation
   - Hyperparameter optimization
   - Training with cross-validation
   - Feature importance analysis

3. **Ensemble Training**:
   - Individual model prediction generation
   - Meta-learner training
   - Performance comparison and selection

### Model Evaluation
- **Cross-validation**: 5-fold CV for robust evaluation
- **Holdout Testing**: Final evaluation on unseen data
- **Performance Comparison**: Compare all models side-by-side
- **Feature Importance**: Analyze most predictive features

## 🔍 Model Monitoring

### Training Logs
- **Location**: `logs/model_training.log`
- **Content**: Training progress, metrics, errors
- **Format**: Structured logging with timestamps

### Model Artifacts
- **Model Files**: Saved models in HDF5 (LSTM) and pickle (XGBoost) formats
- **Scalers**: Feature and target scalers for consistent preprocessing
- **Metadata**: Model info, configuration, and performance metrics

### Performance Tracking
- **Metrics Storage**: All evaluation metrics saved with models
- **Model Comparison**: Side-by-side performance comparison
- **Version Control**: Model versions tracked with timestamps

## 🛠️ Usage Examples

### Loading and Using Models

```python
# Load LSTM model
from src.models.lstm_demand_forecaster import LSTMDemandForecaster

forecaster = LSTMDemandForecaster(target_type='dwell_time')
forecaster.load_model('models/lstm/lstm_dwell_time_best.h5')

# Make predictions
predictions = forecaster.predict(X_new)

# Load XGBoost model
from src.models.xgboost_demand_forecaster import XGBoostDemandForecaster

xgb_forecaster = XGBoostDemandForecaster(target_type='demand_level')
xgb_forecaster.load_model('models/xgboost/xgboost_demand_level_model.pkl')

# Get feature importance
importance_df = xgb_forecaster.get_feature_importance()

# Load ensemble model
from src.models.model_ensemble import ModelEnsemble

ensemble = ModelEnsemble(target_type='dwell_time')
ensemble.load_individual_models()
predictions = ensemble.predict(X_new)
```

### Model Comparison

```python
# Compare model performances
comparison_results = ensemble.compare_models(X_test, y_test)

for model_name, metrics in comparison_results.items():
    if 'rmse' in metrics:
        print(f"{model_name}: RMSE={metrics['rmse']:.2f}, R²={metrics['r2_score']:.3f}")
    else:
        print(f"{model_name}: Accuracy={metrics['accuracy']:.3f}")
```

## 🚨 Troubleshooting

### Common Issues

1. **Memory Errors**:
   - Reduce batch size in LSTM configuration
   - Use smaller sequence length
   - Process data in chunks

2. **Training Timeouts**:
   - Increase timeout values in orchestrator
   - Use smaller datasets for testing
   - Reduce number of epochs

3. **Poor Performance**:
   - Check data quality and feature engineering
   - Verify target variable distribution
   - Adjust hyperparameters

4. **Missing Dependencies**:
   - Install required packages: `pip install tensorflow xgboost scikit-learn joblib`
   - Check Python version compatibility

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Performance Benchmarks

### Expected Performance (with good data)
- **LSTM Dwell Time**: RMSE < 30 seconds, R² > 0.7
- **XGBoost Dwell Time**: RMSE < 25 seconds, R² > 0.75
- **Ensemble Dwell Time**: RMSE < 20 seconds, R² > 0.8
- **Demand Level Classification**: Accuracy > 0.85

### Model Selection Criteria
- **Primary**: Ensemble model (best overall performance)
- **Secondary**: XGBoost (good performance, fast inference)
- **Tertiary**: LSTM (best for time-series patterns)

## 🔄 Model Retraining

### Automatic Retraining
- **Frequency**: Weekly or monthly based on data availability
- **Trigger**: New data availability or performance degradation
- **Process**: Automated pipeline with validation

### Manual Retraining
```bash
# Retrain specific model
python src/models/lstm_demand_forecaster.py

# Retrain all models
python run_model_training.py
```

## 📋 Next Steps

1. **Model Deployment**: API endpoints for real-time predictions
2. **A/B Testing**: Compare model performance in production
3. **Continuous Monitoring**: Track model drift and performance
4. **Advanced Models**: Implement STGCN for spatial-temporal modeling
5. **Hyperparameter Tuning**: Automated hyperparameter optimization

## 📞 Support

For issues or questions:
1. Check training logs in `logs/model_training.log`
2. Verify data availability and quality
3. Review model configuration and hyperparameters
4. Test with smaller datasets first

---

**Note**: This ML system is designed to work with the MARTA data processing pipeline. Ensure data ingestion and feature engineering are complete before training models. 