# MARTA Demand Forecasting & Route Optimization Platform
# Multi-stage Docker build for production deployment

# Stage 1: Base image with Python and system dependencies
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Development image
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    mypy

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p logs models optimization_results

# Set permissions
RUN chmod +x *.py src/*/*.py

# Expose ports
EXPOSE 8000 8001 8501

# Development command
CMD ["python", "run_api.py"]

# Stage 3: Production image
FROM base as production

# Create non-root user
RUN useradd --create-home --shell /bin/bash marta

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p logs models optimization_results && \
    chown -R marta:marta /app

# Switch to non-root user
USER marta

# Expose ports
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Production command
CMD ["python", "run_api.py"]

# Stage 4: API-only image
FROM base as api

# Copy API-specific files
COPY src/api/ ./src/api/
COPY src/optimization/ ./src/optimization/
COPY src/data_ingestion/ ./src/data_ingestion/
COPY src/data_processing/ ./src/data_processing/
COPY src/models/ ./src/models/
COPY run_api.py .
COPY requirements.txt .

# Create necessary directories
RUN mkdir -p logs models optimization_results

# Expose API port
EXPOSE 8001

# API command
CMD ["python", "run_api.py"]

# Stage 5: Dashboard-only image
FROM base as dashboard

# Install Streamlit
RUN pip install --no-cache-dir streamlit

# Copy dashboard files
COPY src/visualization/ ./src/visualization/
COPY frontend/ ./frontend/
COPY run_dashboard.py .

# Expose dashboard port
EXPOSE 8501

# Dashboard command
CMD ["streamlit", "run", "src/visualization/demo_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"] 