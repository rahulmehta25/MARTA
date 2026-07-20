# 🚇 MARTA Demand Forecasting & Route Optimization Platform

A comprehensive machine learning system that uses historical and real-time MARTA data to forecast stop-level rider demand, identify overcrowding patterns, and simulate optimized routes to improve service efficiency and reduce congestion.

## 🎯 Project Overview

This platform provides:
- **Real-time demand forecasting** using LSTM and XGBoost models
- **Route optimization simulation** with heuristic algorithms
- **Modern React UI** with interactive maps and real-time data visualization
- **Interactive dashboards** for monitoring and visualization
- **Data quality monitoring** and alerting systems
- **Model explainability** for stakeholder trust

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │  Data Ingestion │    │  Data Storage   │
│                 │    │                 │    │                 │
│ • GTFS Static   │───▶│ • GTFS Ingestor │───▶│ • PostgreSQL    │
│ • GTFS-RT       │    │ • RT Processor  │    │ • Data Lake     │
│ • Weather API   │    │ • External APIs │    │ • Feature Store │
│ • Event Data    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ML Models     │    │  Optimization   │    │  Visualization  │
│                 │    │                 │    │                 │
│ • LSTM          │◀───│ • Route Engine  │───▶│ • Streamlit     │
│ • XGBoost       │    │ • Simulation    │    │ • Plotly        │
│ • STGCN         │    │ • Constraints   │    │ • Folium        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎨 Modern UI Features

The platform now includes a sophisticated React-based frontend with:

- **Interactive Map Visualization**: Real-time transit data on Mapbox maps
- **Demand Heatmaps**: Visual representation of passenger demand patterns
- **Route Optimization Interface**: Interactive tools for route planning
- **Real-time Data Dashboard**: Live updates of transit system status
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Dark/Light Theme Support**: User preference for different viewing modes
- **Advanced Search**: Find stops, routes, and optimization scenarios
- **Analytics Panels**: Detailed insights and performance metrics

### Frontend Technology Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **Radix UI** for accessible components
- **Mapbox GL** for interactive maps
- **Framer Motion** for animations
- **Zustand** for state management
- **React Query** for data fetching

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+ and npm
- PostgreSQL with PostGIS extension
- MARTA API key (for GTFS-RT data)
- OpenWeatherMap API key (optional)

### Automated Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MARTA
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv marta_env_new
   source marta_env_new/bin/activate
   ```

3. **Run the development startup script**
   ```bash
   ./start_development.sh
   ```
   
   This script will:
   - Install frontend dependencies
   - Start the backend API server
   - Start the frontend development server
   - Set up proxy configuration

4. **Configure API keys (Optional)**
   ```bash
   # Edit .env file with your actual API keys
   nano .env
   ```

### Manual Setup

1. **Create virtual environment**
   ```bash
   python3 -m venv marta_env_new
   source marta_env_new/bin/activate  # On Windows: marta_env_new\Scripts\activate
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database (Optional for development)**
   ```bash
   # Create PostgreSQL database
   createdb marta_db
   
   # Install PostGIS extension
   psql -d marta_db -c "CREATE EXTENSION postgis;"
   
   # Run database setup
   python setup_real_marta_data.py
   ```

### Running the System

1. **Start the API server**
   ```bash
   python run_api.py
   ```

2. **Start the frontend**
   ```bash
   cd frontend && npm start
   ```

3. **Start the dashboard**
   ```bash
   streamlit run src/visualization/demo_dashboard.py
   ```

4. **Access the platform**
   - Backend API: http://localhost:8001
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8001/docs
   - Dashboard: http://localhost:8501

3. **Launch dashboard**
   ```bash
   streamlit run src/visualization/dashboard.py
   ```

## 📊 Features

### Data Ingestion
- **GTFS Static Data**: Automated parsing and validation of MARTA schedule data
- **GTFS-RT Processing**: Real-time vehicle positions and trip updates
- **External Data**: Weather conditions and event information
- **Data Quality**: Automated validation and monitoring

### Machine Learning Models
- **LSTM Networks**: Time-series forecasting for demand prediction
- **XGBoost**: Gradient boosting for tabular data analysis
- **STGCN**: Spatio-temporal graph convolutional networks (advanced)
- **Model Explainability**: SHAP-based feature importance analysis

### Route Optimization
- **Heuristic Algorithms**: Greedy optimization for route modifications
- **Simulation Engine**: Discrete event simulation for impact analysis
- **Constraint Handling**: Operational limits and capacity constraints
- **Performance Metrics**: Wait times, utilization, coverage scores

### Visualization & Monitoring
- **Interactive Dashboard**: Real-time monitoring with Streamlit
- **Geographic Maps**: Demand heatmaps with Folium
- **Performance Charts**: Time-series analysis with Plotly
- **System Health**: Monitoring and alerting pipeline

## 📁 Project Structure

```
MARTA/
├── config/
│   └── settings.py              # Configuration management
├── src/
│   ├── data_ingestion/          # Data collection and processing
│   │   ├── gtfs_ingestor.py     # GTFS static data ingestion
│   │   └── gtfs_realtime_processor.py  # Real-time data processing
│   ├── models/                  # Machine learning models
│   │   └── demand_forecaster.py # Demand forecasting models
│   ├── optimization/            # Route optimization engine
│   ├── monitoring/              # System monitoring and alerting
│   ├── explainability/          # Model explainability tools
│   ├── data_lake/              # Data lake management
│   ├── visualization/           # Dashboard and visualization
│   └── api/                    # REST API endpoints
├── data/
│   ├── raw/                    # Raw data storage
│   ├── processed/              # Processed data
│   └── external/               # External data sources
├── models/                     # Trained model artifacts
├── logs/                       # System logs
├── tests/                      # Unit and integration tests
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database Configuration
DB_HOST=localhost
DB_NAME=marta_db
DB_USER=marta_user
DB_PASSWORD=marta_password
DB_PORT=5432

# MARTA API Configuration
MARTA_API_KEY=your_marta_api_key_here

# External APIs
OPENWEATHER_API_KEY=your_openweather_api_key_here

# Data Lake Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=marta-data-lake

# Monitoring Configuration
ALERT_WEBHOOK_URL=your_webhook_url_here
LOG_LEVEL=INFO
```

### Model Configuration

Key model parameters in `config/settings.py`:

```python
SEQUENCE_LENGTH = 24        # Hours of historical data for LSTM
PREDICTION_HORIZON = 1      # Hours ahead to predict
TRAIN_TEST_SPLIT = 0.8      # Training/test split ratio
RANDOM_SEED = 42           # Reproducibility
```

## 📈 Usage Examples

### Making Demand Predictions

```python
from src.models.demand_forecaster import DemandForecaster
from datetime import datetime

# Initialize forecaster
forecaster = DemandForecaster()
forecaster.load_models()

# Predict demand for a specific stop
prediction = forecaster.predict_demand(
    stop_id="stop_123",
    timestamp=datetime.now() + timedelta(hours=1),
    model_type="xgboost"
)

print(f"Predicted demand: {prediction['predicted_demand']}")
print(f"Demand level: {prediction['demand_level']}")
```

### Running Route Optimization

```python
from src.optimization.route_optimizer import RouteOptimizer

# Initialize optimizer
optimizer = RouteOptimizer()

# Optimize routes based on demand forecast
optimized_routes = optimizer.optimize_routes(
    demand_forecast=demand_data,
    current_routes=route_data,
    constraints=optimization_constraints
)

print(f"Optimized {len(optimized_routes)} routes")
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_demand_forecaster.py
```

## 📊 Monitoring & Alerts

The system includes comprehensive monitoring:

- **Data Quality Monitoring**: GTFS-RT freshness, vehicle data stalls
- **Model Performance**: Accuracy drift detection
- **System Health**: Database connectivity, API status
- **Alerting**: Webhook notifications for critical issues

## 🔒 Security

- API key management through environment variables
- Database connection encryption
- Input validation and sanitization
- Secure model artifact storage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- MARTA for providing GTFS data and APIs
- OpenStreetMap for geographic data
- The open-source community for the excellent libraries used in this project

## 📞 Support

For questions and support:
- Create an issue in the GitHub repository
- Contact the development team
- Check the documentation in the `docs/` folder

## 🚀 Roadmap

### Phase 1: MVP (Current)
- ✅ Basic data ingestion pipeline
- ✅ LSTM and XGBoost models
- ✅ Simple route optimization
- ✅ Streamlit dashboard

### Phase 2: Production Ready
- 🔄 Advanced monitoring and alerting
- 🔄 Data lake implementation
- 🔄 CI/CD automation
- 🔄 Model explainability

### Phase 3: Advanced Features
- 📋 STGCN implementation
- 📋 Advanced simulation engine
- 📋 Cloud deployment
- 📋 Real-time optimization

---

**Built for better public transportation** 