# MARTA Platform Deployment Guide

## 🚀 Overview

This guide covers deploying the MARTA Demand Forecasting & Route Optimization Platform using Docker and Docker Compose. The platform includes data ingestion, processing, ML model training, optimization, simulation, and visualization components.

## 🏗️ Architecture

### Service Components

1. **PostgreSQL Database** - Stores GTFS data, ML features, and optimization results
2. **Redis** - Caching and message queuing
3. **MARTA API** - REST API for optimization and simulation services
4. **MARTA Dashboard** - Streamlit-based visualization interface
5. **Data Ingestion Service** - Collects and processes GTFS data
6. **Data Processing Service** - Feature engineering and data preparation
7. **Model Training Service** - Trains ML models for demand prediction
8. **Nginx** - Reverse proxy and load balancing
9. **Prometheus** - Metrics collection and monitoring
10. **Grafana** - Monitoring dashboards and visualization

### Network Architecture

```
Internet → Nginx → MARTA API → PostgreSQL/Redis
                ↓
            MARTA Dashboard
                ↓
            Monitoring Stack (Prometheus/Grafana)
```

## 📋 Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **Storage**: Minimum 50GB available space
- **CPU**: 4+ cores recommended

### Software Installation

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## 🚀 Quick Start Deployment

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd MARTA

# Create necessary directories
mkdir -p logs models optimization_results data monitoring/grafana/dashboards monitoring/grafana/datasources nginx/ssl

# Set environment variables
export DB_HOST=localhost
export DB_NAME=marta_db
export DB_USER=marta_user
export DB_PASSWORD=marta_password
```

### 2. Build and Start Services

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Verify Deployment

```bash
# Check API health
curl http://localhost:8001/health

# Check dashboard
curl http://localhost:8501

# Check database connection
docker-compose exec postgres psql -U marta_user -d marta_db -c "SELECT version();"
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration
DB_HOST=postgres
DB_NAME=marta_db
DB_USER=marta_user
DB_PASSWORD=marta_password

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001

# Dashboard Configuration
DASHBOARD_PORT=8501

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=admin

# External APIs (if needed)
MARTA_API_KEY=your_marta_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

### Service-Specific Configuration

#### PostgreSQL Configuration

```sql
-- Custom PostgreSQL settings in postgresql.conf
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### Redis Configuration

```redis
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

#### Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream marta_api {
        server marta_api:8001;
    }

    upstream marta_dashboard {
        server marta_dashboard:8501;
    }

    server {
        listen 80;
        server_name localhost;

        location /api/ {
            proxy_pass http://marta_api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /dashboard/ {
            proxy_pass http://marta_dashboard/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /health {
            proxy_pass http://marta_api/health;
        }
    }
}
```

## 📊 Monitoring Setup

### Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'marta_api'
    static_configs:
      - targets: ['marta_api:8001']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### Grafana Dashboards

Create `monitoring/grafana/datasources/prometheus.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

## 🔄 Data Pipeline Setup

### 1. Initial Data Loading

```bash
# Load GTFS static data
docker-compose exec marta_ingestion python src/data_ingestion/gtfs_ingestor.py

# Load external data sources
docker-compose exec marta_ingestion python src/data_ingestion/external_data_ingestor.py
```

### 2. Data Processing

```bash
# Run feature engineering
docker-compose exec marta_processing python src/data_processing/feature_engineering.py

# Create unified dataset
docker-compose exec marta_processing python src/data_processing/data_unification.py
```

### 3. Model Training

```bash
# Train ML models
docker-compose exec marta_training python run_model_training.py
```

### 4. Optimization Setup

```bash
# Run initial optimization
docker-compose exec marta_api python run_optimization.py
```

## 🚀 Production Deployment

### 1. Security Considerations

```bash
# Generate SSL certificates
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/nginx.key \
    -out nginx/ssl/nginx.crt

# Set proper permissions
chmod 600 nginx/ssl/nginx.key
chmod 644 nginx/ssl/nginx.crt
```

### 2. Production Environment Variables

```env
# Production settings
NODE_ENV=production
DEBUG=false
LOG_LEVEL=info

# Database (use external managed service in production)
DB_HOST=your-production-db-host
DB_NAME=marta_prod
DB_USER=marta_prod_user
DB_PASSWORD=secure_password

# Redis (use external managed service in production)
REDIS_HOST=your-production-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password

# API Keys
MARTA_API_KEY=your_production_marta_key
OPENWEATHER_API_KEY=your_production_weather_key
```

### 3. Scaling Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  marta_api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  marta_dashboard:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### 4. Backup Strategy

```bash
# Database backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec postgres pg_dump -U marta_user marta_db > backup_${DATE}.sql

# Model backup
tar -czf models_backup_${DATE}.tar.gz models/

# Configuration backup
tar -czf config_backup_${DATE}.tar.gz .env docker-compose.yml nginx/ monitoring/
```

## 🔍 Monitoring and Maintenance

### Health Checks

```bash
# Check all services
docker-compose ps

# Check specific service logs
docker-compose logs marta_api
docker-compose logs marta_dashboard

# Check resource usage
docker stats
```

### Performance Monitoring

```bash
# Access Grafana
open http://localhost:3000
# Username: admin, Password: admin

# Access Prometheus
open http://localhost:9090

# API metrics
curl http://localhost:8001/metrics
```

### Log Management

```bash
# View real-time logs
docker-compose logs -f --tail=100

# Export logs for analysis
docker-compose logs > marta_logs_$(date +%Y%m%d).log

# Rotate logs (add to crontab)
0 0 * * * find /path/to/logs -name "*.log" -mtime +7 -delete
```

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database status
   docker-compose exec postgres pg_isready -U marta_user
   
   # Restart database
   docker-compose restart postgres
   ```

2. **API Service Not Starting**
   ```bash
   # Check API logs
   docker-compose logs marta_api
   
   # Check dependencies
   docker-compose exec marta_api python -c "import psycopg2; print('DB OK')"
   ```

3. **Memory Issues**
   ```bash
   # Check memory usage
   docker stats
   
   # Increase memory limits in docker-compose.yml
   ```

4. **Port Conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :8001
   
   # Change ports in docker-compose.yml
   ```

### Debug Mode

```bash
# Run in debug mode
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up

# Access container shell
docker-compose exec marta_api bash
```

## 📈 Scaling and Performance

### Horizontal Scaling

```bash
# Scale API service
docker-compose up -d --scale marta_api=3

# Scale with load balancer
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d
```

### Performance Optimization

1. **Database Optimization**
   ```sql
   -- Add indexes for better performance
   CREATE INDEX idx_gtfs_stops_location ON gtfs_stops USING gist (ST_SetSRID(ST_MakePoint(stop_lon, stop_lat), 4326));
   CREATE INDEX idx_unified_data_timestamp ON unified_data(timestamp);
   ```

2. **Caching Strategy**
   ```python
   # Redis caching for frequently accessed data
   import redis
   r = redis.Redis(host='redis', port=6379, db=0)
   r.setex('route_data', 3600, json.dumps(route_data))
   ```

3. **API Optimization**
   ```python
   # Add response caching
   from fastapi_cache import FastAPICache
   from fastapi_cache.backends.redis import RedisBackend
   
   FastAPICache.init(RedisBackend(redis), prefix="marta-cache")
   ```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy MARTA Platform

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build and deploy
        run: |
          docker-compose build
          docker-compose up -d
      
      - name: Run tests
        run: |
          docker-compose exec marta_api python -m pytest
      
      - name: Health check
        run: |
          curl -f http://localhost:8001/health
```

## 📞 Support and Maintenance

### Regular Maintenance Tasks

1. **Daily**
   - Check service health
   - Review error logs
   - Monitor resource usage

2. **Weekly**
   - Update dependencies
   - Backup data
   - Review performance metrics

3. **Monthly**
   - Security updates
   - Performance optimization
   - Capacity planning

### Support Contacts

- **Technical Issues**: Check logs and monitoring dashboards
- **Performance Issues**: Review Grafana dashboards
- **Data Issues**: Check data ingestion logs
- **API Issues**: Check API health endpoint

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation) 