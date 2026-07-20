"""Initial MARTA database schema migration

Revision ID: 001_initial_migration
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '001_initial_migration'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema"""
    
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gin"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    
    # Create GTFS Agencies table
    op.create_table(
        'gtfs_agencies',
        sa.Column('agency_id', sa.String(255), primary_key=True),
        sa.Column('agency_name', sa.String(255), nullable=False),
        sa.Column('agency_url', sa.Text, nullable=False),
        sa.Column('agency_timezone', sa.String(100), nullable=False),
        sa.Column('agency_lang', sa.String(10)),
        sa.Column('agency_phone', sa.String(50)),
        sa.Column('agency_fare_url', sa.Text),
        sa.Column('agency_email', sa.String(255)),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create GTFS Stops table
    op.create_table(
        'gtfs_stops',
        sa.Column('stop_id', sa.String(255), primary_key=True),
        sa.Column('stop_code', sa.String(255)),
        sa.Column('stop_name', sa.String(255), nullable=False),
        sa.Column('stop_desc', sa.Text),
        sa.Column('stop_lat', sa.Numeric(10, 7), nullable=False),
        sa.Column('stop_lon', sa.Numeric(10, 7), nullable=False),
        sa.Column('zone_id', sa.String(255)),
        sa.Column('stop_url', sa.Text),
        sa.Column('location_type', sa.Integer, default=0),
        sa.Column('parent_station', sa.String(255)),
        sa.Column('wheelchair_boarding', sa.Integer, default=0),
        sa.Column('platform_code', sa.String(255)),
        sa.Column('geom', geoalchemy2.Geometry('POINT', srid=4326)),
        sa.Column('stop_name_search', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp()),
        
        sa.CheckConstraint('stop_lat >= -90 AND stop_lat <= 90', name='chk_stop_lat'),
        sa.CheckConstraint('stop_lon >= -180 AND stop_lon <= 180', name='chk_stop_lon'),
        sa.CheckConstraint('location_type IN (0,1,2,3,4)', name='chk_location_type')
    )
    
    # Create GTFS Routes table
    op.create_table(
        'gtfs_routes',
        sa.Column('route_id', sa.String(255), primary_key=True),
        sa.Column('agency_id', sa.String(255), sa.ForeignKey('gtfs_agencies.agency_id', ondelete='CASCADE')),
        sa.Column('route_short_name', sa.String(255)),
        sa.Column('route_long_name', sa.String(255)),
        sa.Column('route_desc', sa.Text),
        sa.Column('route_type', sa.Integer, nullable=False),
        sa.Column('route_url', sa.Text),
        sa.Column('route_color', sa.String(6), default='FFFFFF'),
        sa.Column('route_text_color', sa.String(6), default='000000'),
        sa.Column('route_sort_order', sa.Integer),
        sa.Column('continuous_pickup', sa.Integer, default=1),
        sa.Column('continuous_dropoff', sa.Integer, default=1),
        sa.Column('route_search', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp()),
        
        sa.CheckConstraint('route_type IN (0,1,2,3,4,5,6,7,11,12)', name='chk_route_type'),
        sa.CheckConstraint('route_short_name IS NOT NULL OR route_long_name IS NOT NULL', name='chk_route_has_name')
    )
    
    # Create GTFS Calendar table
    op.create_table(
        'gtfs_calendar',
        sa.Column('service_id', sa.String(255), primary_key=True),
        sa.Column('monday', sa.Boolean, nullable=False, default=False),
        sa.Column('tuesday', sa.Boolean, nullable=False, default=False),
        sa.Column('wednesday', sa.Boolean, nullable=False, default=False),
        sa.Column('thursday', sa.Boolean, nullable=False, default=False),
        sa.Column('friday', sa.Boolean, nullable=False, default=False),
        sa.Column('saturday', sa.Boolean, nullable=False, default=False),
        sa.Column('sunday', sa.Boolean, nullable=False, default=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('weekdays_only', sa.Boolean),
        sa.Column('weekends_only', sa.Boolean),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp()),
        
        sa.CheckConstraint('start_date <= end_date', name='chk_date_range')
    )
    
    # Create GTFS Calendar Dates table
    op.create_table(
        'gtfs_calendar_dates',
        sa.Column('service_id', sa.String(255), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('exception_type', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp()),
        
        sa.PrimaryKeyConstraint('service_id', 'date'),
        sa.CheckConstraint('exception_type IN (1,2)', name='chk_exception_type')
    )
    
    # Create GTFS Trips table
    op.create_table(
        'gtfs_trips',
        sa.Column('trip_id', sa.String(255), primary_key=True),
        sa.Column('route_id', sa.String(255), sa.ForeignKey('gtfs_routes.route_id', ondelete='CASCADE'), nullable=False),
        sa.Column('service_id', sa.String(255), nullable=False),
        sa.Column('trip_headsign', sa.String(255)),
        sa.Column('trip_short_name', sa.String(255)),
        sa.Column('direction_id', sa.Integer, default=0),
        sa.Column('block_id', sa.String(255)),
        sa.Column('shape_id', sa.String(255)),
        sa.Column('wheelchair_accessible', sa.Integer, default=0),
        sa.Column('bikes_allowed', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp()),
        
        sa.CheckConstraint('direction_id IN (0,1)', name='chk_direction_id'),
        sa.CheckConstraint('wheelchair_accessible IN (0,1,2)', name='chk_wheelchair'),
        sa.CheckConstraint('bikes_allowed IN (0,1,2)', name='chk_bikes')
    )
    
    # Create GTFS Stop Times table
    op.create_table(
        'gtfs_stop_times',
        sa.Column('trip_id', sa.String(255), sa.ForeignKey('gtfs_trips.trip_id', ondelete='CASCADE')),
        sa.Column('stop_sequence', sa.Integer),
        sa.Column('stop_id', sa.String(255), sa.ForeignKey('gtfs_stops.stop_id', ondelete='CASCADE'), nullable=False),
        sa.Column('arrival_time', sa.Interval),
        sa.Column('departure_time', sa.Interval),
        sa.Column('stop_headsign', sa.String(255)),
        sa.Column('pickup_type', sa.Integer, default=0),
        sa.Column('drop_off_type', sa.Integer, default=0),
        sa.Column('continuous_pickup', sa.Integer, default=1),
        sa.Column('continuous_drop_off', sa.Integer, default=1),
        sa.Column('shape_dist_traveled', sa.Numeric),
        sa.Column('timepoint', sa.Integer, default=1),
        sa.Column('arrival_seconds', sa.Integer),
        sa.Column('departure_seconds', sa.Integer),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp()),
        
        sa.PrimaryKeyConstraint('trip_id', 'stop_sequence'),
        sa.CheckConstraint('pickup_type IN (0,1,2,3)', name='chk_pickup_type'),
        sa.CheckConstraint('drop_off_type IN (0,1,2,3)', name='chk_drop_off_type'),
        sa.CheckConstraint('timepoint IN (0,1)', name='chk_timepoint')
    )
    
    # Create GTFS Shapes table
    op.create_table(
        'gtfs_shapes',
        sa.Column('shape_id', sa.String(255)),
        sa.Column('shape_pt_sequence', sa.Integer),
        sa.Column('shape_pt_lat', sa.Numeric(10, 7), nullable=False),
        sa.Column('shape_pt_lon', sa.Numeric(10, 7), nullable=False),
        sa.Column('shape_dist_traveled', sa.Numeric),
        sa.Column('geom', geoalchemy2.Geometry('POINT', srid=4326)),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp()),
        
        sa.PrimaryKeyConstraint('shape_id', 'shape_pt_sequence'),
        sa.CheckConstraint('shape_pt_lat >= -90 AND shape_pt_lat <= 90', name='chk_shape_lat'),
        sa.CheckConstraint('shape_pt_lon >= -180 AND shape_pt_lon <= 180', name='chk_shape_lon')
    )
    
    # Create basic indexes
    op.create_index('idx_gtfs_stops_geom', 'gtfs_stops', ['geom'], postgresql_using='gist')
    op.create_index('idx_gtfs_stops_name_search', 'gtfs_stops', ['stop_name_search'], postgresql_using='gin')
    op.create_index('idx_gtfs_stops_zone', 'gtfs_stops', ['zone_id'])
    
    op.create_index('idx_gtfs_routes_type', 'gtfs_routes', ['route_type'])
    op.create_index('idx_gtfs_routes_search', 'gtfs_routes', ['route_search'], postgresql_using='gin')
    op.create_index('idx_gtfs_routes_agency', 'gtfs_routes', ['agency_id'])
    
    op.create_index('idx_gtfs_trips_route', 'gtfs_trips', ['route_id'])
    op.create_index('idx_gtfs_trips_service', 'gtfs_trips', ['service_id'])
    op.create_index('idx_gtfs_trips_direction', 'gtfs_trips', ['route_id', 'direction_id'])
    
    op.create_index('idx_gtfs_stop_times_trip', 'gtfs_stop_times', ['trip_id'])
    op.create_index('idx_gtfs_stop_times_stop', 'gtfs_stop_times', ['stop_id'])
    op.create_index('idx_gtfs_stop_times_arrival', 'gtfs_stop_times', ['arrival_seconds'])
    op.create_index('idx_gtfs_stop_times_departure', 'gtfs_stop_times', ['departure_seconds'])
    
    op.create_index('idx_gtfs_shapes_geom', 'gtfs_shapes', ['geom'], postgresql_using='gist')
    op.create_index('idx_gtfs_shapes_sequence', 'gtfs_shapes', ['shape_id', 'shape_pt_sequence'])
    
    op.create_index('idx_gtfs_calendar_dates', 'gtfs_calendar_dates', ['date', 'service_id'])
    op.create_index('idx_gtfs_calendar_service_dates', 'gtfs_calendar', ['service_id', 'start_date', 'end_date'])
    
    # Create triggers for computed columns
    create_triggers()


def create_triggers():
    """Create database triggers for computed columns"""
    
    # Trigger function for updating stop geometry and search vector
    op.execute("""
    CREATE OR REPLACE FUNCTION update_stop_computed_fields() RETURNS TRIGGER AS $$
    BEGIN
        NEW.geom = ST_SetSRID(ST_MakePoint(NEW.stop_lon, NEW.stop_lat), 4326);
        NEW.stop_name_search = to_tsvector('english', COALESCE(NEW.stop_name, '') || ' ' || COALESCE(NEW.stop_desc, ''));
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
    CREATE TRIGGER trg_update_stop_computed_fields
        BEFORE INSERT OR UPDATE ON gtfs_stops
        FOR EACH ROW EXECUTE FUNCTION update_stop_computed_fields();
    """)
    
    # Trigger function for updating route search vector
    op.execute("""
    CREATE OR REPLACE FUNCTION update_route_computed_fields() RETURNS TRIGGER AS $$
    BEGIN
        NEW.route_search = to_tsvector('english', 
            COALESCE(NEW.route_short_name, '') || ' ' || 
            COALESCE(NEW.route_long_name, '') || ' ' || 
            COALESCE(NEW.route_desc, '')
        );
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
    CREATE TRIGGER trg_update_route_computed_fields
        BEFORE INSERT OR UPDATE ON gtfs_routes
        FOR EACH ROW EXECUTE FUNCTION update_route_computed_fields();
    """)
    
    # Trigger function for updating shape geometry
    op.execute("""
    CREATE OR REPLACE FUNCTION update_shape_computed_fields() RETURNS TRIGGER AS $$
    BEGIN
        NEW.geom = ST_SetSRID(ST_MakePoint(NEW.shape_pt_lon, NEW.shape_pt_lat), 4326);
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
    CREATE TRIGGER trg_update_shape_computed_fields
        BEFORE INSERT OR UPDATE ON gtfs_shapes
        FOR EACH ROW EXECUTE FUNCTION update_shape_computed_fields();
    """)
    
    # Trigger function for updating stop times computed fields
    op.execute("""
    CREATE OR REPLACE FUNCTION update_stop_times_computed_fields() RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.arrival_time IS NOT NULL THEN
            NEW.arrival_seconds = EXTRACT(epoch FROM NEW.arrival_time)::INTEGER;
        END IF;
        
        IF NEW.departure_time IS NOT NULL THEN
            NEW.departure_seconds = EXTRACT(epoch FROM NEW.departure_time)::INTEGER;
        END IF;
        
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
    CREATE TRIGGER trg_update_stop_times_computed_fields
        BEFORE INSERT OR UPDATE ON gtfs_stop_times
        FOR EACH ROW EXECUTE FUNCTION update_stop_times_computed_fields();
    """)


def downgrade() -> None:
    """Downgrade database schema"""
    
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS trg_update_stop_computed_fields ON gtfs_stops')
    op.execute('DROP TRIGGER IF EXISTS trg_update_route_computed_fields ON gtfs_routes')
    op.execute('DROP TRIGGER IF EXISTS trg_update_shape_computed_fields ON gtfs_shapes')
    op.execute('DROP TRIGGER IF EXISTS trg_update_stop_times_computed_fields ON gtfs_stop_times')
    
    # Drop trigger functions
    op.execute('DROP FUNCTION IF EXISTS update_stop_computed_fields()')
    op.execute('DROP FUNCTION IF EXISTS update_route_computed_fields()')
    op.execute('DROP FUNCTION IF EXISTS update_shape_computed_fields()')
    op.execute('DROP FUNCTION IF EXISTS update_stop_times_computed_fields()')
    
    # Drop tables in reverse order
    op.drop_table('gtfs_shapes')
    op.drop_table('gtfs_stop_times')
    op.drop_table('gtfs_trips')
    op.drop_table('gtfs_calendar_dates')
    op.drop_table('gtfs_calendar')
    op.drop_table('gtfs_routes')
    op.drop_table('gtfs_stops')
    op.drop_table('gtfs_agencies')