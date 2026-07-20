"""
Configuration settings for MARTA Transit Analytics Platform.
Uses pydantic for validation and python-decouple for environment management.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings with validation and type hints."""
    
    # Application
    app_name: str = "MARTA Transit Analytics"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Database
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="marta_db", env="DB_NAME")
    db_user: str = Field(default="marta_user", env="DB_USER")
    db_password: str = Field(env="DB_PASSWORD")
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # MARTA API
    marta_api_key: Optional[str] = Field(default=None, env="MARTA_API_KEY")
    marta_rail_api_key: Optional[str] = Field(default=None, env="MARTA_RAIL_API_KEY")
    marta_gtfs_url: str = Field(
        default="https://itsmarta.com/google_transit.zip",
        env="MARTA_GTFS_URL"
    )
    marta_rail_api_url: str = Field(
        default="https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata",
        env="MARTA_RAIL_API_URL"
    )
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND"
    )
    
    # Feature Flags
    enable_real_time_updates: bool = Field(default=True, env="ENABLE_REAL_TIME_UPDATES")
    enable_ml_predictions: bool = Field(default=False, env="ENABLE_ML_PREDICTIONS")
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    cache_ttl_seconds: int = Field(default=300, env="CACHE_TTL_SECONDS")
    
    # Data Ingestion
    gtfs_update_schedule: str = Field(default="0 3 * * *", env="GTFS_UPDATE_SCHEDULE")
    real_time_poll_interval: int = Field(default=30, env="REAL_TIME_POLL_INTERVAL")
    max_retry_attempts: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")
    retry_delay_seconds: int = Field(default=5, env="RETRY_DELAY_SECONDS")
    
    # Performance
    max_connections_per_host: int = Field(default=10, env="MAX_CONNECTIONS_PER_HOST")
    connection_timeout: int = Field(default=30, env="CONNECTION_TIMEOUT")
    read_timeout: int = Field(default=60, env="READ_TIMEOUT")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    prometheus_enabled: bool = Field(default=False, env="PROMETHEUS_ENABLED")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields like VITE_* variables
    
    @validator("database_url", pre=True)
    def assemble_database_url(cls, v, values):
        """Construct database URL if not provided."""
        if v:
            return v
        
        # Build URL from components
        password = values.get("db_password", "")
        user = values.get("db_user", "marta_user")
        host = values.get("db_host", "localhost")
        port = values.get("db_port", 5432)
        db_name = values.get("db_name", "marta_db")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing."""
        return self.environment.lower() == "testing"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use this function to get settings throughout the application.
    """
    return Settings()


# Create a single instance for import
settings = get_settings()