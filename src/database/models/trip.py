"""
Trip model for MARTA transit trips.
Based on GTFS trip specification.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Time
from sqlalchemy.orm import relationship
from src.database.connection import Base


class Trip(Base):
    """Transit trip model."""
    
    __tablename__ = "trips"
    
    # Primary key
    trip_id = Column(String(100), primary_key=True, index=True)
    
    # Foreign keys
    route_id = Column(String(50), ForeignKey("routes.route_id"), nullable=False, index=True)
    service_id = Column(String(50), nullable=False, index=True)
    
    # Trip information
    trip_headsign = Column(String(255), nullable=True)
    trip_short_name = Column(String(50), nullable=True)
    direction_id = Column(Integer, nullable=True)  # 0=Outbound, 1=Inbound
    block_id = Column(String(50), nullable=True)
    shape_id = Column(String(50), nullable=True)
    
    # Accessibility
    wheelchair_accessible = Column(Integer, nullable=True)  # 0=No info, 1=Accessible, 2=Not accessible
    bikes_allowed = Column(Integer, nullable=True)  # 0=No info, 1=Allowed, 2=Not allowed
    
    # Schedule information
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    
    # Performance metrics (calculated/cached)
    avg_delay_minutes = Column(Integer, nullable=True)
    completion_rate = Column(Integer, nullable=True)  # Percentage of trips completed
    
    # Relationships
    route = relationship("Route", back_populates="trips")
    stop_times = relationship("StopTime", back_populates="trip", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Trip(trip_id='{self.trip_id}', route_id='{self.route_id}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "service_id": self.service_id,
            "trip_headsign": self.trip_headsign,
            "trip_short_name": self.trip_short_name,
            "direction_id": self.direction_id,
            "block_id": self.block_id,
            "shape_id": self.shape_id,
            "wheelchair_accessible": self.wheelchair_accessible,
            "bikes_allowed": self.bikes_allowed,
            "start_time": str(self.start_time) if self.start_time else None,
            "end_time": str(self.end_time) if self.end_time else None,
            "avg_delay_minutes": self.avg_delay_minutes,
            "completion_rate": self.completion_rate
        }