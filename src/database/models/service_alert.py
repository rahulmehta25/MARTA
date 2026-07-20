"""
ServiceAlert model for MARTA service alerts and disruptions.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from src.database.connection import Base


class ServiceAlert(Base):
    """Service alert model for disruptions and notifications."""
    
    __tablename__ = "service_alerts"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Alert identification
    alert_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Alert details
    header_text = Column(String(500), nullable=False)
    description_text = Column(Text, nullable=False)
    url = Column(String(255), nullable=True)
    
    # Alert categorization
    cause = Column(String(50), nullable=True)  # e.g., 'CONSTRUCTION', 'ACCIDENT', 'WEATHER'
    effect = Column(String(50), nullable=True)  # e.g., 'NO_SERVICE', 'REDUCED_SERVICE', 'SIGNIFICANT_DELAYS'
    severity_level = Column(String(20), nullable=True)  # 'INFO', 'WARNING', 'SEVERE'
    
    # Affected entities
    route_id = Column(String(50), nullable=True, index=True)
    stop_id = Column(String(50), nullable=True, index=True)
    trip_id = Column(String(100), nullable=True)
    agency_id = Column(String(50), nullable=True)
    
    # Time periods
    active_period_start = Column(DateTime, nullable=True)
    active_period_end = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Language support
    language = Column(String(10), default='en')
    
    # Additional information
    informed_entity = Column(Text, nullable=True)  # JSON string of affected entities
    
    def __repr__(self):
        return f"<ServiceAlert(alert_id='{self.alert_id}', header='{self.header_text[:50]}...')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "header_text": self.header_text,
            "description_text": self.description_text,
            "url": self.url,
            "cause": self.cause,
            "effect": self.effect,
            "severity_level": self.severity_level,
            "route_id": self.route_id,
            "stop_id": self.stop_id,
            "trip_id": self.trip_id,
            "active_period_start": self.active_period_start.isoformat() if self.active_period_start else None,
            "active_period_end": self.active_period_end.isoformat() if self.active_period_end else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "language": self.language
        }
    
    @property
    def is_current(self):
        """Check if alert is currently active."""
        now = datetime.utcnow()
        if not self.is_active:
            return False
        if self.active_period_start and now < self.active_period_start:
            return False
        if self.active_period_end and now > self.active_period_end:
            return False
        return True
    
    @property
    def affects_entire_system(self):
        """Check if alert affects entire system."""
        return not any([self.route_id, self.stop_id, self.trip_id])