"""
MARTA Platform - SQLAlchemy Database Models
Defines all database models for the MARTA transit platform
"""
import uuid
from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, DateTime, Date, Time,
    Interval, JSON, ForeignKey, Index, CheckConstraint, UniqueConstraint,
    event, func, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, validates
from geoalchemy2 import Geometry
import structlog

# Configure logging
logger = structlog.get_logger(__name__)

# Create declarative base
Base = declarative_base()

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class GTFSAgency(Base, TimestampMixin):
    """GTFS Agency information"""
    __tablename__ = 'gtfs_agencies'
    
    agency_id = Column(String(255), primary_key=True)
    agency_name = Column(String(255), nullable=False)
    agency_url = Column(Text, nullable=False)
    agency_timezone = Column(String(100), nullable=False)
    agency_lang = Column(String(10))
    agency_phone = Column(String(50))
    agency_fare_url = Column(Text)
    agency_email = Column(String(255))
    
    # Relationships
    routes = relationship("GTFSRoute", back_populates="agency", cascade="all, delete-orphan")

class GTFSStop(Base, TimestampMixin):
    """GTFS Stop with spatial optimization"""
    __tablename__ = 'gtfs_stops'
    
    stop_id = Column(String(255), primary_key=True)
    stop_code = Column(String(255))
    stop_name = Column(String(255), nullable=False)
    stop_desc = Column(Text)
    stop_lat = Column(Numeric(10, 7), nullable=False)
    stop_lon = Column(Numeric(10, 7), nullable=False)
    zone_id = Column(String(255))
    stop_url = Column(Text)
    location_type = Column(Integer, default=0)
    parent_station = Column(String(255))
    wheelchair_boarding = Column(Integer, default=0)
    platform_code = Column(String(255))
    
    # Spatial geometry column
    geom = Column(Geometry('POINT', srid=4326))
    
    # Full-text search column
    stop_name_search = Column('stop_name_search', sa.Text)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('stop_lat >= -90 AND stop_lat <= 90', name='chk_stop_lat'),
        CheckConstraint('stop_lon >= -180 AND stop_lon <= 180', name='chk_stop_lon'),
        CheckConstraint('location_type IN (0,1,2,3,4)', name='chk_location_type'),
        Index('idx_gtfs_stops_geom', 'geom', postgresql_using='gist'),
        Index('idx_gtfs_stops_name_search', 'stop_name_search', postgresql_using='gin'),
        Index('idx_gtfs_stops_zone', 'zone_id'),
    )
    
    # Relationships
    stop_times = relationship("GTFSStopTime", back_populates="stop")
    
    @validates('stop_lat')
    def validate_latitude(self, key, latitude):
        if not -90 <= latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return latitude
    
    @validates('stop_lon')
    def validate_longitude(self, key, longitude):
        if not -180 <= longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return longitude

class GTFSRoute(Base, TimestampMixin):
    """GTFS Route with search optimization"""
    __tablename__ = 'gtfs_routes'
    
    route_id = Column(String(255), primary_key=True)
    agency_id = Column(String(255), ForeignKey('gtfs_agencies.agency_id', ondelete='CASCADE'))
    route_short_name = Column(String(255))
    route_long_name = Column(String(255))
    route_desc = Column(Text)
    route_type = Column(Integer, nullable=False)
    route_url = Column(Text)
    route_color = Column(String(6), default='FFFFFF')
    route_text_color = Column(String(6), default='000000')
    route_sort_order = Column(Integer)
    continuous_pickup = Column(Integer, default=1)
    continuous_dropoff = Column(Integer, default=1)
    
    # Search optimization
    route_search = Column('route_search', sa.Text)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('route_type IN (0,1,2,3,4,5,6,7,11,12)', name='chk_route_type'),
        CheckConstraint('route_short_name IS NOT NULL OR route_long_name IS NOT NULL', name='chk_route_has_name'),
        Index('idx_gtfs_routes_type', 'route_type'),
        Index('idx_gtfs_routes_search', 'route_search', postgresql_using='gin'),
        Index('idx_gtfs_routes_agency', 'agency_id'),
    )
    
    # Relationships
    agency = relationship("GTFSAgency", back_populates="routes")
    trips = relationship("GTFSTrip", back_populates="route", cascade="all, delete-orphan")

class GTFSCalendar(Base, TimestampMixin):
    """GTFS Calendar with optimized date handling"""
    __tablename__ = 'gtfs_calendar'
    
    service_id = Column(String(255), primary_key=True)
    monday = Column(Boolean, nullable=False, default=False)
    tuesday = Column(Boolean, nullable=False, default=False)
    wednesday = Column(Boolean, nullable=False, default=False)
    thursday = Column(Boolean, nullable=False, default=False)
    friday = Column(Boolean, nullable=False, default=False)
    saturday = Column(Boolean, nullable=False, default=False)
    sunday = Column(Boolean, nullable=False, default=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Computed columns
    weekdays_only = Column(Boolean, nullable=True)  # Will be computed in trigger
    weekends_only = Column(Boolean, nullable=True)  # Will be computed in trigger
    
    # Constraints
    __table_args__ = (
        CheckConstraint('start_date <= end_date', name='chk_date_range'),
        Index('idx_gtfs_calendar_service_dates', 'service_id', 'start_date', 'end_date'),
    )

class GTFSCalendarDate(Base, TimestampMixin):
    """GTFS Calendar exceptions"""
    __tablename__ = 'gtfs_calendar_dates'
    
    service_id = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    exception_type = Column(Integer, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('exception_type IN (1,2)', name='chk_exception_type'),
        Index('idx_gtfs_calendar_dates', 'date', 'service_id'),
    )

class GTFSTrip(Base, TimestampMixin):
    """GTFS Trip"""
    __tablename__ = 'gtfs_trips'
    
    trip_id = Column(String(255), primary_key=True)
    route_id = Column(String(255), ForeignKey('gtfs_routes.route_id', ondelete='CASCADE'), nullable=False)
    service_id = Column(String(255), nullable=False)
    trip_headsign = Column(String(255))
    trip_short_name = Column(String(255))
    direction_id = Column(Integer, default=0)
    block_id = Column(String(255))
    shape_id = Column(String(255))
    wheelchair_accessible = Column(Integer, default=0)
    bikes_allowed = Column(Integer, default=0)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('direction_id IN (0,1)', name='chk_direction_id'),
        CheckConstraint('wheelchair_accessible IN (0,1,2)', name='chk_wheelchair'),
        CheckConstraint('bikes_allowed IN (0,1,2)', name='chk_bikes'),
        Index('idx_gtfs_trips_route', 'route_id'),
        Index('idx_gtfs_trips_service', 'service_id'),
        Index('idx_gtfs_trips_direction', 'route_id', 'direction_id'),
    )
    
    # Relationships
    route = relationship("GTFSRoute", back_populates="trips")
    stop_times = relationship("GTFSStopTime", back_populates="trip", cascade="all, delete-orphan")

class GTFSStopTime(Base, TimestampMixin):
    """GTFS Stop Times with optimized time handling"""
    __tablename__ = 'gtfs_stop_times'
    
    trip_id = Column(String(255), ForeignKey('gtfs_trips.trip_id', ondelete='CASCADE'), primary_key=True)
    stop_sequence = Column(Integer, primary_key=True)
    stop_id = Column(String(255), ForeignKey('gtfs_stops.stop_id', ondelete='CASCADE'), nullable=False)
    arrival_time = Column(Interval)
    departure_time = Column(Interval)
    stop_headsign = Column(String(255))
    pickup_type = Column(Integer, default=0)
    drop_off_type = Column(Integer, default=0)
    continuous_pickup = Column(Integer, default=1)
    continuous_drop_off = Column(Integer, default=1)
    shape_dist_traveled = Column(Numeric)
    timepoint = Column(Integer, default=1)
    
    # Computed columns for faster queries (will be handled by triggers)
    arrival_seconds = Column(Integer)
    departure_seconds = Column(Integer)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('pickup_type IN (0,1,2,3)', name='chk_pickup_type'),
        CheckConstraint('drop_off_type IN (0,1,2,3)', name='chk_drop_off_type'),
        CheckConstraint('timepoint IN (0,1)', name='chk_timepoint'),
        Index('idx_gtfs_stop_times_trip', 'trip_id'),
        Index('idx_gtfs_stop_times_stop', 'stop_id'),
        Index('idx_gtfs_stop_times_arrival', 'arrival_seconds'),
        Index('idx_gtfs_stop_times_departure', 'departure_seconds'),
    )
    
    # Relationships
    trip = relationship("GTFSTrip", back_populates="stop_times")
    stop = relationship("GTFSStop", back_populates="stop_times")

class GTFSShape(Base, TimestampMixin):
    """GTFS Shapes with spatial optimization"""
    __tablename__ = 'gtfs_shapes'
    
    shape_id = Column(String(255), primary_key=True)
    shape_pt_sequence = Column(Integer, primary_key=True)
    shape_pt_lat = Column(Numeric(10, 7), nullable=False)
    shape_pt_lon = Column(Numeric(10, 7), nullable=False)
    shape_dist_traveled = Column(Numeric)
    
    # Spatial geometry
    geom = Column(Geometry('POINT', srid=4326))
    
    # Constraints
    __table_args__ = (
        CheckConstraint('shape_pt_lat >= -90 AND shape_pt_lat <= 90', name='chk_shape_lat'),
        CheckConstraint('shape_pt_lon >= -180 AND shape_pt_lon <= 180', name='chk_shape_lon'),
        Index('idx_gtfs_shapes_geom', 'geom', postgresql_using='gist'),
        Index('idx_gtfs_shapes_sequence', 'shape_id', 'shape_pt_sequence'),
    )

class GTFSVehiclePosition(Base, TimestampMixin):
    """Partitioned GTFS Vehicle Positions"""
    __tablename__ = 'gtfs_vehicle_positions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    trip_id = Column(String(255))
    route_id = Column(String(255))
    vehicle_id = Column(String(255), nullable=False)
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    bearing = Column(Numeric(5, 2))
    speed = Column(Numeric(6, 2))
    current_stop_sequence = Column(Integer)
    current_status = Column(Integer)
    occupancy_status = Column(Integer)
    congestion_level = Column(Integer)
    
    # Spatial geometry
    geom = Column(Geometry('POINT', srid=4326))
    
    # Constraints
    __table_args__ = (
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='chk_vp_lat'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='chk_vp_lon'),
        # Partition by timestamp (handled in raw SQL)
        # Indexes will be created per partition
    )

class GTFSTripUpdate(Base, TimestampMixin):
    """Partitioned GTFS Trip Updates"""
    __tablename__ = 'gtfs_trip_updates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    trip_id = Column(String(255), nullable=False)
    route_id = Column(String(255))
    vehicle_id = Column(String(255))
    stop_id = Column(String(255))
    stop_sequence = Column(Integer)
    arrival_delay = Column(Integer)
    departure_delay = Column(Integer)
    schedule_relationship = Column(Integer)
    
    # Constraints
    __table_args__ = (
        # Partition by timestamp (handled in raw SQL)
        # Indexes will be created per partition
    )

class UnifiedTransitData(Base, TimestampMixin):
    """Enhanced unified transit data with comprehensive metrics"""
    __tablename__ = 'unified_transit_data'
    
    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    date_partition = Column(Date)  # Generated column for partitioning
    trip_id = Column(String(255))
    route_id = Column(String(255))
    stop_id = Column(String(255))
    vehicle_id = Column(String(255))
    stop_sequence = Column(Integer)
    
    # Location data
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    geom = Column(Geometry('POINT', srid=4326))
    
    # Timing data
    scheduled_arrival_time = Column(DateTime)
    actual_arrival_time = Column(DateTime)
    scheduled_departure_time = Column(DateTime)
    actual_departure_time = Column(DateTime)
    arrival_delay_seconds = Column(Integer)
    departure_delay_seconds = Column(Integer)
    dwell_time_seconds = Column(Integer)
    
    # Operational metrics
    passenger_load = Column(Integer)
    passenger_count = Column(Integer)
    occupancy_status = Column(Integer)
    door_state = Column(Integer)
    
    # External factors
    weather_condition = Column(String(100))
    temperature_celsius = Column(Numeric(4, 1))
    precipitation_mm = Column(Numeric(6, 2))
    wind_speed_kmh = Column(Numeric(5, 1))
    visibility_km = Column(Numeric(4, 1))
    
    # Event flags
    event_flag = Column(Boolean, default=False)
    holiday_flag = Column(Boolean, default=False)
    special_service_flag = Column(Boolean, default=False)
    
    # Temporal features
    day_of_week = Column(Integer)
    hour_of_day = Column(Integer)
    minute_of_hour = Column(Integer)
    is_weekend = Column(Boolean)
    is_rush_hour = Column(Boolean)
    
    # Derived metrics
    headway_adherence = Column(Numeric(5, 2))
    schedule_adherence = Column(Numeric(5, 2))
    service_reliability = Column(Numeric(5, 2))
    
    # Metadata
    data_source = Column(String(50))
    quality_score = Column(Numeric(3, 2))
    
    # Constraints
    __table_args__ = (
        # Partition by timestamp (handled in raw SQL)
        # Indexes will be created per partition
    )

class FeatureStore(Base, TimestampMixin):
    """ML Feature store with time-series partitioning"""
    __tablename__ = 'feature_store'
    
    feature_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False)
    entity_type = Column(String(50), nullable=False)  # 'stop', 'route', 'trip'
    entity_id = Column(String(255), nullable=False)
    
    # Time-based features
    hour_sin = Column(Numeric(8, 6))
    hour_cos = Column(Numeric(8, 6))
    day_sin = Column(Numeric(8, 6))
    day_cos = Column(Numeric(8, 6))
    month_sin = Column(Numeric(8, 6))
    month_cos = Column(Numeric(8, 6))
    
    # Lag features
    demand_lag_1h = Column(Numeric)
    demand_lag_24h = Column(Numeric)
    demand_lag_168h = Column(Numeric)  # 1 week
    
    # Rolling statistics
    demand_rolling_mean_3h = Column(Numeric)
    demand_rolling_mean_24h = Column(Numeric)
    demand_rolling_std_24h = Column(Numeric)
    demand_rolling_max_24h = Column(Numeric)
    demand_rolling_min_24h = Column(Numeric)
    
    # External features
    temperature = Column(Numeric(4, 1))
    precipitation = Column(Numeric(6, 2))
    wind_speed = Column(Numeric(5, 1))
    visibility = Column(Numeric(4, 1))
    weather_category = Column(String(50))
    
    # Operational features
    service_frequency_1h = Column(Integer)
    avg_headway_1h = Column(Numeric)
    schedule_adherence_1h = Column(Numeric)
    
    # Event features
    is_event_day = Column(Boolean)
    event_type = Column(String(100))
    event_distance_km = Column(Numeric(6, 2))
    
    # Computed features
    demand_anomaly_score = Column(Numeric(8, 4))
    service_disruption_flag = Column(Boolean)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'timestamp', name='uq_feature_store_entity_time'),
        # Partition by timestamp (handled in raw SQL)
        # Indexes will be created per partition
    )

class ModelPrediction(Base, TimestampMixin):
    """Model predictions storage"""
    __tablename__ = 'model_predictions'
    
    prediction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False)
    stop_id = Column(String(255), ForeignKey('gtfs_stops.stop_id'))
    route_id = Column(String(255), ForeignKey('gtfs_routes.route_id'))
    predicted_riders = Column(Integer)
    demand_level = Column(String(50))
    model_name = Column(String(100))
    confidence_score = Column(Numeric)
    
    # Relationships
    stop = relationship("GTFSStop")
    route = relationship("GTFSRoute")
    
    # Constraints
    __table_args__ = (
        Index('idx_model_predictions_timestamp', 'timestamp'),
        Index('idx_model_predictions_stop', 'stop_id'),
        Index('idx_model_predictions_route', 'route_id'),
        Index('idx_model_predictions_model', 'model_name'),
    )

class RouteOptimizationResult(Base, TimestampMixin):
    """Route optimization results"""
    __tablename__ = 'route_optimization_results'
    
    optimization_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False)
    original_route_id = Column(String(255), ForeignKey('gtfs_routes.route_id'))
    proposed_route_id = Column(String(255))
    optimization_type = Column(String(100))
    impact_metrics = Column(JSONB)
    status = Column(String(50))
    
    # Relationships
    original_route = relationship("GTFSRoute")
    
    # Constraints
    __table_args__ = (
        Index('idx_route_optimization_timestamp', 'timestamp'),
        Index('idx_route_optimization_original', 'original_route_id'),
        Index('idx_route_optimization_type', 'optimization_type'),
    )

# Event listeners for computed columns and triggers
@event.listens_for(GTFSStop, 'before_insert')
@event.listens_for(GTFSStop, 'before_update')
def update_stop_computed_fields(mapper, connection, target):
    """Update computed fields for GTFSStop"""
    if target.stop_lat is not None and target.stop_lon is not None:
        # Geometry will be handled by database trigger
        pass
    
    if target.stop_name:
        # Search vector will be handled by database trigger
        pass

@event.listens_for(GTFSRoute, 'before_insert')
@event.listens_for(GTFSRoute, 'before_update')
def update_route_computed_fields(mapper, connection, target):
    """Update computed fields for GTFSRoute"""
    # Search vector will be handled by database trigger
    pass


class APCPassengerCount(Base, TimestampMixin):
    """Automated Passenger Counter - aggregated passenger counts per stop/time"""
    __tablename__ = 'apc_passenger_counts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, index=True)
    route_id = Column(String(255), index=True)
    stop_id = Column(String(255), index=True)
    vehicle_id = Column(String(255), index=True)
    boarding_count = Column(Integer, default=0)
    alighting_count = Column(Integer, default=0)
    passenger_count = Column(Integer, default=0)  # net onboard after stop
    occupancy_percentage = Column(Numeric(5, 2))

    __table_args__ = (
        Index('idx_apc_counts_stop_time', 'stop_id', 'timestamp'),
        Index('idx_apc_counts_route_time', 'route_id', 'timestamp'),
    )


class VehicleOccupancy(Base, TimestampMixin):
    """Real-time vehicle occupancy snapshots"""
    __tablename__ = 'vehicle_occupancy'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, index=True)
    route_id = Column(String(255), index=True)
    vehicle_id = Column(String(255), index=True)
    stop_id = Column(String(255))
    capacity = Column(Integer)
    current_occupancy = Column(Integer)
    occupancy_percentage = Column(Numeric(5, 2))
    crowding_level = Column(String(20))  # e.g., low/medium/high/critical

    __table_args__ = (
        Index('idx_vehicle_occupancy_vehicle_time', 'vehicle_id', 'timestamp'),
        Index('idx_vehicle_occupancy_route_time', 'route_id', 'timestamp'),
    )

@event.listens_for(GTFSShape, 'before_insert')
@event.listens_for(GTFSShape, 'before_update')
def update_shape_computed_fields(mapper, connection, target):
    """Update computed fields for GTFSShape"""
    if target.shape_pt_lat is not None and target.shape_pt_lon is not None:
        # Geometry will be handled by database trigger
        pass

@event.listens_for(UnifiedTransitData, 'before_insert')
@event.listens_for(UnifiedTransitData, 'before_update')
def update_unified_data_computed_fields(mapper, connection, target):
    """Update computed fields for UnifiedTransitData"""
    if target.timestamp:
        target.date_partition = target.timestamp.date()
    
    if target.latitude is not None and target.longitude is not None:
        # Geometry will be handled by database trigger
        pass