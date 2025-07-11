"""
Configuration settings for MARTA Demand Forecasting & Route Optimization Platform
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://marta_user:marta_password@localhost:5432/marta_db")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_NAME: str = os.getenv("DB_NAME", "marta_db")
    DB_USER: str = os.getenv("DB_USER", "marta_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "marta_password")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    
    # MARTA API Configuration
    MARTA_API_KEY: Optional[str] = os.getenv("MARTA_API_KEY")
    MARTA_GTFS_STATIC_URL: str = "https://itsmarta.com/app-developer-resources.aspx"
    MARTA_GTFS_RT_VEHICLE_URL: str = Field(os.getenv("MARTA_GTFS_RT_VEHICLE_URL", "https://itsmarta.com/gtfs-rt/vehicle-positions/vehicle.pb"))
    MARTA_GTFS_RT_TRIP_URL: str = Field(os.getenv("MARTA_GTFS_RT_TRIP_URL", "https://itsmarta.com/gtfs-rt/trip-updates/tripupdate.pb"))
    MARTA_KPI_URL: str = "https://itsmarta.com/KPIRidership.aspx"
    
    # External APIs
    OPENWEATHER_API_KEY: Optional[str] = os.getenv("OPENWEATHER_API_KEY")
    ATLANTA_LAT: float = 33.7490
    ATLANTA_LON: float = -84.3880
    
    # Data Lake Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "marta-data-lake")
    
    # Model Configuration
    MODEL_VERSION: str = "v1.0"
    SEQUENCE_LENGTH: int = 24  # Hours of historical data for LSTM
    PREDICTION_HORIZON: int = 1  # Hours ahead to predict
    TRAIN_TEST_SPLIT: float = 0.8
    RANDOM_SEED: int = 42
    
    # GTFS-RT Configuration
    GTFS_RT_POLL_INTERVAL: int = 30  # seconds
    GTFS_RT_MAX_AGE: int = 90  # seconds
    
    # Monitoring Configuration
    ALERT_WEBHOOK_URL: Optional[str] = os.getenv("ALERT_WEBHOOK_URL")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "True").lower() == "true"
    
    # Streamlit Configuration
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))
    
    # File Paths
    DATA_DIR: str = "data"
    RAW_DATA_DIR: str = "data/raw"
    PROCESSED_DATA_DIR: str = "data/processed"
    EXTERNAL_DATA_DIR: str = "data/external"
    LOGS_DIR: str = "logs"
    MODELS_DIR: str = "models"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings() 