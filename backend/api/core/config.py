"""
Configuration settings for MARTA Production API.
Environment-based configuration with validation using Pydantic v2.
"""
from typing import List, Optional
from functools import lru_cache
from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production API settings with comprehensive validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="MARTA Transit API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    api_title: str = Field(default="MARTA Transit Analytics API", env="API_TITLE")
    api_description: str = Field(
        default="Production-grade API for transit demand forecasting and route optimization",
        env="API_DESCRIPTION",
    )

    # Database
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="marta_db", env="DB_NAME")
    db_user: str = Field(default="marta_user", env="DB_USER")
    db_password: str = Field(default="", env="DB_PASSWORD")
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")

    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_enabled: bool = Field(default=False, env="REDIS_ENABLED")

    # Security
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    jwt_refresh_expiration_days: int = Field(default=7, env="JWT_REFRESH_EXPIRATION_DAYS")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    allowed_api_keys: str = Field(default="", env="ALLOWED_API_KEYS")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:8080",
        env="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: str = Field(default="*", env="CORS_ALLOW_METHODS")
    cors_allow_headers: str = Field(default="*", env="CORS_ALLOW_HEADERS")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, env="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")

    # Caching
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(default=300, env="CACHE_TTL_SECONDS")
    cache_forecast_ttl_seconds: int = Field(default=600, env="CACHE_FORECAST_TTL_SECONDS")
    cache_realtime_ttl_seconds: int = Field(default=30, env="CACHE_REALTIME_TTL_SECONDS")

    # Pagination
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

    # MARTA External APIs
    marta_api_key: Optional[str] = Field(default=None, env="MARTA_API_KEY")
    marta_rail_api_key: Optional[str] = Field(default=None, env="MARTA_RAIL_API_KEY")
    marta_gtfs_url: str = Field(
        default="https://itsmarta.com/google_transit.zip",
        env="MARTA_GTFS_URL",
    )

    # ML Models
    models_dir: str = Field(default="models", env="MODELS_DIR")
    enable_ml_predictions: bool = Field(default=True, env="ENABLE_ML_PREDICTIONS")
    model_timeout_seconds: int = Field(default=30, env="MODEL_TIMEOUT_SECONDS")

    # Feature Flags
    enable_websocket: bool = Field(default=True, env="ENABLE_WEBSOCKET")
    enable_realtime: bool = Field(default=True, env="ENABLE_REALTIME")
    enable_optimization: bool = Field(default=True, env="ENABLE_OPTIMIZATION")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins as list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return self.cors_origins

    @computed_field
    @property
    def allowed_api_keys_list(self) -> List[str]:
        """Parse allowed API keys as list."""
        if not self.allowed_api_keys:
            return []
        return [key.strip() for key in self.allowed_api_keys.split(",") if key.strip()]

    @computed_field
    @property
    def database_url_computed(self) -> str:
        """Construct database URL if not provided."""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @computed_field
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
