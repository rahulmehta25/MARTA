"""
Route model for MARTA transit routes.
Based on GTFS route specification.
"""
from sqlalchemy import Column, String, Integer, Text, Float
from sqlalchemy.orm import relationship
from src.database.connection import Base


class Route(Base):
    """Transit route model."""
    
    __tablename__ = "routes"
    
    # Primary key
    route_id = Column(String(50), primary_key=True, index=True)
    
    # Route information
    route_short_name = Column(String(50), nullable=False)  # e.g., "Red", "Gold"
    route_long_name = Column(String(255), nullable=False)  # e.g., "Red Line - North Springs to Airport"
    route_desc = Column(Text, nullable=True)
    route_type = Column(Integer, nullable=False)  # 1 = Subway/Metro
    route_url = Column(String(255), nullable=True)
    route_color = Column(String(6), nullable=True)  # Hex color without #
    route_text_color = Column(String(6), nullable=True)
    
    # Additional MARTA-specific fields
    route_sort_order = Column(Integer, nullable=True)
    continuous_pickup = Column(Integer, nullable=True)
    continuous_drop_off = Column(Integer, nullable=True)
    
    # Performance metrics (calculated/cached)
    avg_delay_minutes = Column(Float, nullable=True)
    on_time_performance = Column(Float, nullable=True)  # Percentage
    daily_ridership = Column(Integer, nullable=True)
    
    # Relationships
    trips = relationship("Trip", back_populates="route", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Route(route_id='{self.route_id}', name='{self.route_short_name}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "route_id": self.route_id,
            "route_short_name": self.route_short_name,
            "route_long_name": self.route_long_name,
            "route_desc": self.route_desc,
            "route_type": self.route_type,
            "route_color": self.route_color,
            "route_text_color": self.route_text_color,
            "avg_delay_minutes": self.avg_delay_minutes,
            "on_time_performance": self.on_time_performance,
            "daily_ridership": self.daily_ridership
        }