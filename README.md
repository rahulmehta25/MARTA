# MARTA Transit Analytics Platform

A real-time transit analytics platform for the Metropolitan Atlanta Rapid Transit Authority (MARTA) system. This platform provides real-time tracking, route optimization, and demand forecasting using official MARTA data feeds.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+

### Backend Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/marta-analytics.git
cd marta-analytics
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up PostgreSQL database**
```bash
# Create database
createdb marta_db

# Run migrations (coming in Week 2)
alembic upgrade head
```

6. **Start Redis**
```bash
redis-server
```

7. **Run the backend server**
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start development server**
```bash
npm run dev
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📁 Project Structure

```
marta-analytics/
├── src/                    # Backend source code
│   ├── api/               # FastAPI application
│   ├── config/            # Configuration management
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   ├── data_ingestion/    # GTFS and real-time data
│   └── utils/             # Utility functions
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/        # Page components
│   │   ├── store/        # State management
│   │   └── utils/        # Frontend utilities
│   └── public/           # Static assets
├── tests/                # Test files
├── migrations/           # Database migrations
├── docs/                 # Documentation
├── requirements.txt      # Python dependencies
├── requirements-dev.txt  # Development dependencies
└── .env.example         # Environment variables template
```

## 🔧 Configuration

### Required Environment Variables

- `DB_PASSWORD`: PostgreSQL database password
- `SECRET_KEY`: Application secret key (min 32 characters)
- `MARTA_API_KEY`: MARTA API key ([Register here](https://itsmarta.com/developer-reg-rtt.aspx))

### Optional Configuration

See `.env.example` for all available configuration options.

## 🧪 Testing

Run tests with:
```bash
# Backend tests
pytest

# Frontend tests
cd frontend && npm test
```

## 📊 Data Sources

This platform integrates with official MARTA data feeds:

- **GTFS Static Data**: [https://itsmarta.com/google_transit.zip](https://itsmarta.com/google_transit.zip)
- **Real-time Rail API**: Requires API key from [MARTA Developer Portal](https://itsmarta.com/developer-reg-rtt.aspx)

## 🚧 Development Status

Currently implementing according to the [Implementation Guide](docs/MARTA%20Transit%20Analytics%20Implementation%20Guide.md):

### ✅ Week 1 - Complete
- Infrastructure cleanup
- Dependency management
- Environment configuration
- Development documentation

### 🔄 Week 2 - In Progress
- Database setup
- Migration system
- SQLAlchemy models

### 📅 Upcoming
- Week 3: API restructuring
- Week 4: Frontend improvements
- Week 5-8: GTFS and real-time data integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- MARTA for providing public transit data
- OpenStreetMap for geographic data
- The open-source community for the amazing tools

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the [Implementation Guide](docs/MARTA%20Transit%20Analytics%20Implementation%20Guide.md)
- Review the API documentation at `/docs` when the server is running