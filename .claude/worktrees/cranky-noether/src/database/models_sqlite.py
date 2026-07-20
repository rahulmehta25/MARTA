"""
Simplified SQLAlchemy Database Models for SQLite
Compatible with SQLite without PostGIS/PostgreSQL specific features
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.database.connection import Base


class Route(Base):
    """MARTA Route Model"""
    __tablename__ = 'routes'
    
    id = Column(Integer, primary_key=True)
    route_id = Column(String(50), unique=True, nullable=False)
    route_short_name = Column(String(50))
    route_long_name = Column(String(255))
    route_type = Column(Integer, default=3)  # 3 = Bus, 1 = Subway/Metro
    route_color = Column(String(6), default='FF0000')
    route_text_color = Column(String(6), default='FFFFFF')
    
    # Relationships
    trips = relationship("Trip", back_populates="route", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "route_id": self.route_id,
            "route_short_name": self.route_short_name,
            "route_long_name": self.route_long_name,
            "route_type": self.route_type,
            "route_color": self.route_color,
            "route_text_color": self.route_text_color
        }


class Stop(Base):
    """MARTA Stop Model"""
    __tablename__ = 'stops'
    
    id = Column(Integer, primary_key=True)
    stop_id = Column(String(50), unique=True, nullable=False)
    stop_code = Column(String(50))
    stop_name = Column(String(255), nullable=False)
    stop_desc = Column(Text)
    stop_lat = Column(Float, nullable=False)
    stop_lon = Column(Float, nullable=False)
    zone_id = Column(String(50))
    location_type = Column(Integer, default=0)  # 0 = Stop, 1 = Station
    
    # Relationships
    stop_times = relationship("StopTime", back_populates="stop", cascade="all, delete-orphan")
    arrivals = relationship("RealTimeArrival", back_populates="stop", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "stop_id": self.stop_id,
            "stop_code": self.stop_code,
            "stop_name": self.stop_name,
            "stop_desc": self.stop_desc,
            "stop_lat": self.stop_lat,
            "stop_lon": self.stop_lon,
            "zone_id": self.zone_id,
            "location_type": self.location_type
        }


class Trip(Base):
    """MARTA Trip Model"""
    __tablename__ = 'trips'
    
    id = Column(Integer, primary_key=True)
    trip_id = Column(String(50), unique=True, nullable=False)
    route_id = Column(String(50), ForeignKey('routes.route_id'), nullable=False)
    service_id = Column(String(50), nullable=False)
    trip_headsign = Column(String(255))
    direction_id = Column(Integer, default=0)  # 0 = Outbound, 1 = Inbound
    block_id = Column(String(50))
    shape_id = Column(String(50))
    
    # Relationships
    route = relationship("Route", back_populates="trips")
    stop_times = relationship("StopTime", back_populates="trip", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "service_id": self.service_id,
            "trip_headsign": self.trip_headsign,
            "direction_id": self.direction_id,
            "block_id": self.block_id,
            "shape_id": self.shape_id
        }


class StopTime(Base):
    """MARTA Stop Time Model (Schedule)"""
    __tablename__ = 'stop_times'
    
    id = Column(Integer, primary_key=True)
    trip_id = Column(String(50), ForeignKey('trips.trip_id'), nullable=False)
    arrival_time = Column(String(8))  # HH:MM:SS format
    departure_time = Column(String(8))  # HH:MM:SS format
    stop_id = Column(String(50), ForeignKey('stops.stop_id'), nullable=False)
    stop_sequence = Column(Integer, nullable=False)
    stop_headsign = Column(String(255))
    pickup_type = Column(Integer, default=0)
    drop_off_type = Column(Integer, default=0)
    
    # Relationships
    trip = relationship("Trip", back_populates="stop_times")
    stop = relationship("Stop", back_populates="stop_times")
    
    def to_dict(self):
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "arrival_time": self.arrival_time,
            "departure_time": self.departure_time,
            "stop_id": self.stop_id,
            "stop_sequence": self.stop_sequence,
            "stop_headsign": self.stop_headsign
        }


class RealTimeArrival(Base):
    """Real-time arrival predictions"""
    __tablename__ = 'real_time_arrivals'
    
    id = Column(Integer, primary_key=True)
    stop_id = Column(String(50), ForeignKey('stops.stop_id'), nullable=False)
    route_id = Column(String(50))
    trip_id = Column(String(50))
    arrival_time = Column(DateTime, nullable=False)
    predicted_time = Column(DateTime)
    delay_seconds = Column(Integer, default=0)
    vehicle_id = Column(String(50))
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stop = relationship("Stop", back_populates="arrivals")
    
    def to_dict(self):
        return {
            "id": self.id,
            "stop_id": self.stop_id,
            "route_id": self.route_id,
            "trip_id": self.trip_id,
            "arrival_time": self.arrival_time.isoformat() if self.arrival_time else None,
            "predicted_time": self.predicted_time.isoformat() if self.predicted_time else None,
            "delay_seconds": self.delay_seconds,
            "vehicle_id": self.vehicle_id,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


class ServiceAlert(Base):
    """Service alerts and disruptions"""
    __tablename__ = 'service_alerts'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(String(50), unique=True, nullable=False)
    header_text = Column(Text)
    description_text = Column(Text)
    severity_level = Column(String(20))  # INFO, WARNING, SEVERE
    effect = Column(String(50))  # NO_SERVICE, REDUCED_SERVICE, etc.
    cause = Column(String(50))  # CONSTRUCTION, ACCIDENT, etc.
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    affected_routes = Column(JSON)  # List of route_ids
    affected_stops = Column(JSON)  # List of stop_ids
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "header_text": self.header_text,
            "description_text": self.description_text,
            "severity_level": self.severity_level,
            "effect": self.effect,
            "cause": self.cause,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "affected_routes": self.affected_routes,
            "affected_stops": self.affected_stops,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class VehiclePosition(Base):
    """Vehicle real-time positions"""
    __tablename__ = 'vehicle_positions'
    
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(String(50), nullable=False)
    trip_id = Column(String(50))
    route_id = Column(String(50))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    bearing = Column(Float)
    speed = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    occupancy_status = Column(String(20))  # EMPTY, MANY_SEATS, FEW_SEATS, STANDING_ROOM, FULL
    
    def to_dict(self):
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "bearing": self.bearing,
            "speed": self.speed,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "occupancy_status": self.occupancy_status
        }


class Calendar(Base):
    """GTFS Calendar for service schedules"""
    __tablename__ = 'calendar'
    
    id = Column(Integer, primary_key=True)
    service_id = Column(String(50), unique=True, nullable=False)
    monday = Column(Boolean, default=False)
    tuesday = Column(Boolean, default=False)
    wednesday = Column(Boolean, default=False)
    thursday = Column(Boolean, default=False)
    friday = Column(Boolean, default=False)
    saturday = Column(Boolean, default=False)
    sunday = Column(Boolean, default=False)
    start_date = Column(String(8), nullable=False)  # YYYYMMDD format
    end_date = Column(String(8), nullable=False)  # YYYYMMDD format
    
    def to_dict(self):
        return {
            "id": self.id,
            "service_id": self.service_id,
            "monday": self.monday,
            "tuesday": self.tuesday,
            "wednesday": self.wednesday,
            "thursday": self.thursday,
            "friday": self.friday,
            "saturday": self.saturday,
            "sunday": self.sunday,
            "start_date": self.start_date,
            "end_date": self.end_date
        }