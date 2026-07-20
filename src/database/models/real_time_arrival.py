"""
RealTimeArrival model for MARTA real-time train arrivals.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from src.database.connection import Base


class RealTimeArrival(Base):
    """Real-time arrival prediction model."""
    
    __tablename__ = "real_time_arrivals"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    stop_id = Column(String(50), ForeignKey("stops.stop_id"), nullable=False, index=True)
    route_id = Column(String(50), nullable=False, index=True)
    trip_id = Column(String(100), nullable=True, index=True)
    
    # Arrival information
    destination = Column(String(255), nullable=False)
    direction = Column(String(20), nullable=False)  # 'N', 'S', 'E', 'W'
    
    # Time predictions
    scheduled_time = Column(DateTime, nullable=True)
    predicted_time = Column(DateTime, nullable=False)
    arrival_time = Column(String(50), nullable=False)  # Display string like "2 min" or "Arriving"
    
    # Status
    delay_seconds = Column(Integer, default=0)
    is_delayed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # Train information
    train_id = Column(String(50), nullable=True)
    next_arrival = Column(DateTime, nullable=True)
    
    # Metadata
    event_time = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Data quality
    confidence_level = Column(Float, nullable=True)  # 0.0 to 1.0
    source = Column(String(50), default='api')  # 'api', 'calculated', 'manual'
    
    # Relationships
    stop = relationship("Stop", back_populates="real_time_arrivals")
    
    def __repr__(self):
        return f"<RealTimeArrival(stop_id='{self.stop_id}', destination='{self.destination}', arrival='{self.arrival_time}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "stop_id": self.stop_id,
            "route_id": self.route_id,
            "trip_id": self.trip_id,
            "destination": self.destination,
            "direction": self.direction,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "predicted_time": self.predicted_time.isoformat() if self.predicted_time else None,
            "arrival_time": self.arrival_time,
            "delay_seconds": self.delay_seconds,
            "is_delayed": self.is_delayed,
            "train_id": self.train_id,
            "next_arrival": self.next_arrival.isoformat() if self.next_arrival else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "confidence_level": self.confidence_level,
            "source": self.source
        }
    
    @property
    def is_arriving(self):
        """Check if train is arriving."""
        return self.arrival_time.lower() in ['arriving', 'boarding', '0 min']
    
    @property
    def minutes_away(self):
        """Get minutes until arrival."""
        if self.is_arriving:
            return 0
        try:
            # Extract number from strings like "5 min"
            return int(self.arrival_time.split()[0])
        except (ValueError, IndexError):
            return None