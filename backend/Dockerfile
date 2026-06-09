FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install only production deps (skip dev/docs/tensorflow)
RUN pip install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "sqlalchemy>=2.0.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "bcrypt==4.0.1" \
    "python-multipart>=0.0.6" \
    "httpx>=0.26.0" \
    "numpy>=1.24.0" \
    "pandas>=2.0.0" \
    "scikit-learn>=1.3.0" \
    "xgboost>=2.0.0" \
    "structlog>=24.1.0" \
    "python-dotenv>=1.0.0" \
    "orjson>=3.9.0" \
    "email-validator>=2.1.0" \
    "tenacity>=8.2.0"

COPY backend/ ./backend/

ENV PORT=8080 PYTHONPATH=/app
EXPOSE 8080

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
