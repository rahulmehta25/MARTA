"""
Stop model for MARTA transit stops/stations.
Based on GTFS stop specification.
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, Text
from sqlalchemy.orm import relationship
from src.database.connection import Base


class Stop(Base):
    """Transit stop/station model."""
    
    __tablename__ = "stops"
    
    # Primary key
    stop_id = Column(String(50), primary_key=True, index=True)
    
    # Stop information
    stop_code = Column(String(50), nullable=True)
    stop_name = Column(String(255), nullable=False, index=True)
    stop_desc = Column(Text, nullable=True)
    
    # Geographic location
    stop_lat = Column(Float, nullable=False, index=True)
    stop_lon = Column(Float, nullable=False, index=True)
    
    # Stop details
    zone_id = Column(String(50), nullable=True)
    stop_url = Column(String(255), nullable=True)
    location_type = Column(Integer, nullable=True)  # 0=Stop, 1=Station
    parent_station = Column(String(50), nullable=True)
    stop_timezone = Column(String(50), nullable=True)
    
    # Accessibility
    wheelchair_boarding = Column(Integer, nullable=True)  # 0=No info, 1=Accessible, 2=Not accessible
    
    # Platform information
    platform_code = Column(String(50), nullable=True)
    
    # Additional MARTA-specific fields
    has_bike_parking = Column(Boolean, default=False)
    has_car_parking = Column(Boolean, default=False)
    parking_capacity = Column(Integer, nullable=True)
    
    # Demand metrics (calculated/cached)
    avg_daily_boardings = Column(Integer, nullable=True)
    peak_hour_demand = Column(Integer, nullable=True)
    demand_level = Column(String(20), nullable=True)  # 'low', 'medium', 'high'
    
    # Relationships
    stop_times = relationship("StopTime", back_populates="stop", cascade="all, delete-orphan")
    real_time_arrivals = relationship("RealTimeArrival", back_populates="stop", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Stop(stop_id='{self.stop_id}', name='{self.stop_name}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "stop_id": self.stop_id,
            "stop_code": self.stop_code,
            "stop_name": self.stop_name,
            "stop_desc": self.stop_desc,
            "stop_lat": self.stop_lat,
            "stop_lon": self.stop_lon,
            "location_type": self.location_type,
            "parent_station": self.parent_station,
            "wheelchair_boarding": self.wheelchair_boarding,
            "has_bike_parking": self.has_bike_parking,
            "has_car_parking": self.has_car_parking,
            "parking_capacity": self.parking_capacity,
            "avg_daily_boardings": self.avg_daily_boardings,
            "peak_hour_demand": self.peak_hour_demand,
            "demand_level": self.demand_level
        }
    
    @property
    def coordinates(self):
        """Return coordinates as tuple."""
        return (self.stop_lat, self.stop_lon)