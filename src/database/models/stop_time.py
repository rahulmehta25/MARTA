"""
StopTime model for MARTA transit stop times.
Based on GTFS stop_times specification.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Time, Float
from sqlalchemy.orm import relationship
from src.database.connection import Base


class StopTime(Base):
    """Transit stop time model."""
    
    __tablename__ = "stop_times"
    
    # Composite primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    trip_id = Column(String(100), ForeignKey("trips.trip_id"), nullable=False, index=True)
    stop_id = Column(String(50), ForeignKey("stops.stop_id"), nullable=False, index=True)
    
    # Schedule information
    arrival_time = Column(Time, nullable=False)
    departure_time = Column(Time, nullable=False)
    stop_sequence = Column(Integer, nullable=False)
    
    # Stop details
    stop_headsign = Column(String(255), nullable=True)
    pickup_type = Column(Integer, default=0)  # 0=Regular, 1=No pickup, 2=Phone, 3=Driver
    drop_off_type = Column(Integer, default=0)  # 0=Regular, 1=No drop-off, 2=Phone, 3=Driver
    continuous_pickup = Column(Integer, nullable=True)
    continuous_drop_off = Column(Integer, nullable=True)
    
    # Distance
    shape_dist_traveled = Column(Float, nullable=True)
    
    # Timepoint
    timepoint = Column(Integer, nullable=True)  # 0=Approximate, 1=Exact
    
    # Relationships
    trip = relationship("Trip", back_populates="stop_times")
    stop = relationship("Stop", back_populates="stop_times")
    
    def __repr__(self):
        return f"<StopTime(trip_id='{self.trip_id}', stop_id='{self.stop_id}', sequence={self.stop_sequence})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "stop_id": self.stop_id,
            "arrival_time": str(self.arrival_time) if self.arrival_time else None,
            "departure_time": str(self.departure_time) if self.departure_time else None,
            "stop_sequence": self.stop_sequence,
            "stop_headsign": self.stop_headsign,
            "pickup_type": self.pickup_type,
            "drop_off_type": self.drop_off_type,
            "shape_dist_traveled": self.shape_dist_traveled,
            "timepoint": self.timepoint
        }