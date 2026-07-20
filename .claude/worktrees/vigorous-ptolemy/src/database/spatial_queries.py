"""
MARTA Platform - PostGIS Spatial Query Optimization
High-performance spatial queries for transit route and stop data analysis
"""
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

import pandas as pd
import structlog
from sqlalchemy import text
from geopy.distance import geodesic
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import transform
import pyproj
from functools import partial

from .connection_pool import execute_query, execute_to_dataframe
from .redis_cache import cached, get_cache_manager

# Configure logging
logger = structlog.get_logger(__name__)

@dataclass
class SpatialPoint:
    """Spatial point with coordinates"""
    latitude: float
    longitude: float
    
    def __post_init__(self):
        """Validate coordinates"""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")
    
    @property
    def wkt(self) -> str:
        """Well-Known Text representation"""
        return f"POINT({self.longitude} {self.latitude})"
    
    def distance_to(self, other: 'SpatialPoint') -> float:
        """Calculate distance in meters using geodesic calculation"""
        return geodesic((self.latitude, self.longitude), 
                       (other.latitude, other.longitude)).meters

@dataclass
class StopSearchResult:
    """Transit stop search result"""
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float
    distance_meters: float
    routes_served: List[str]
    avg_daily_ridership: Optional[float] = None
    walking_time_minutes: Optional[int] = None

@dataclass
class RouteGeometry:
    """Route geometry with performance metrics"""
    route_id: str
    route_name: str
    geometry: LineString
    total_length_km: float
    stop_count: int
    avg_stop_spacing_m: float

class SpatialQueryOptimizer:
    """
    Optimized spatial queries for MARTA transit data with PostGIS
    """
    
    def __init__(self):
        self.cache_manager = get_cache_manager()
        
        # Spatial Reference Systems
        self.WGS84_SRID = 4326  # Geographic coordinate system
        self.UTM_ZONE_16N_SRID = 32616  # UTM Zone 16N for Atlanta area
        
        # Search parameters
        self.DEFAULT_SEARCH_RADIUS_M = 800  # 800m walking distance
        self.MAX_SEARCH_RADIUS_M = 5000     # 5km maximum search
        self.MIN_SEARCH_RADIUS_M = 50       # 50m minimum search
        
    def find_nearby_stops(self, 
                         location: SpatialPoint,
                         radius_meters: int = None,
                         limit: int = 10,
                         include_routes: bool = True,
                         include_ridership: bool = True) -> List[StopSearchResult]:
        """
        Find transit stops near a location using optimized spatial indexing
        
        Args:
            location: Search center point
            radius_meters: Search radius in meters
            limit: Maximum number of results
            include_routes: Include route information
            include_ridership: Include ridership statistics
        """
        if radius_meters is None:
            radius_meters = self.DEFAULT_SEARCH_RADIUS_M
            
        radius_meters = max(self.MIN_SEARCH_RADIUS_M, 
                           min(self.MAX_SEARCH_RADIUS_M, radius_meters))
        
        # Use cached results for common searches
        cache_key = f"{location.latitude:.6f}_{location.longitude:.6f}_{radius_meters}_{limit}"
        cached_result = self.cache_manager.get('nearby_stops', cache_key)
        if cached_result:
            return [StopSearchResult(**stop) for stop in cached_result]
        
        # Build optimized spatial query
        base_query = """
        WITH search_point AS (
            SELECT ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326) as geom
        ),
        nearby_stops AS (
            SELECT 
                s.stop_id,
                s.stop_name,
                s.stop_lat as latitude,
                s.stop_lon as longitude,
                ST_Distance(s.geom::geography, sp.geom::geography) as distance_meters
            FROM gtfs_stops s, search_point sp
            WHERE ST_DWithin(s.geom::geography, sp.geom::geography, %(radius)s)
                AND s.location_type IN (0, 1)  -- Only stops and stations
        )
        """
        
        if include_routes:
            base_query += """
            , stop_routes AS (
                SELECT 
                    ns.stop_id,
                    array_agg(DISTINCT r.route_short_name ORDER BY r.route_short_name) as routes_served
                FROM nearby_stops ns
                JOIN gtfs_stop_times st ON ns.stop_id = st.stop_id
                JOIN gtfs_trips t ON st.trip_id = t.trip_id
                JOIN gtfs_routes r ON t.route_id = r.route_id
                GROUP BY ns.stop_id
            )
            """
        
        if include_ridership:
            base_query += """
            , stop_ridership AS (
                SELECT 
                    stop_id,
                    AVG(passenger_count) as avg_daily_ridership
                FROM unified_transit_data
                WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
                    AND passenger_count IS NOT NULL
                GROUP BY stop_id
            )
            """
        
        # Final SELECT
        select_clause = """
        SELECT 
            ns.stop_id,
            ns.stop_name,
            ns.latitude,
            ns.longitude,
            ROUND(ns.distance_meters::numeric, 1) as distance_meters
        """
        
        if include_routes:
            select_clause += ", COALESCE(sr.routes_served, ARRAY[]::varchar[]) as routes_served"
        else:
            select_clause += ", ARRAY[]::varchar[] as routes_served"
            
        if include_ridership:
            select_clause += ", ROUND(COALESCE(srd.avg_daily_ridership, 0), 1) as avg_daily_ridership"
        else:
            select_clause += ", 0 as avg_daily_ridership"
        
        from_clause = " FROM nearby_stops ns"
        
        if include_routes:
            from_clause += " LEFT JOIN stop_routes sr ON ns.stop_id = sr.stop_id"
        
        if include_ridership:
            from_clause += " LEFT JOIN stop_ridership srd ON ns.stop_id = srd.stop_id"
        
        final_query = base_query + select_clause + from_clause + """
        ORDER BY ns.distance_meters
        LIMIT %(limit)s
        """
        
        start_time = time.time()
        
        try:
            result = execute_query(
                final_query,
                params={
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'radius': radius_meters,
                    'limit': limit
                },
                fetch='all'
            )
            
            execution_time = time.time() - start_time
            logger.debug("Nearby stops query completed",
                        execution_time=execution_time,
                        result_count=len(result))
            
            stops = []
            for row in result:
                # Calculate walking time (80m/min average walking speed)
                walking_time = max(1, int(row.distance_meters / 80))
                
                stops.append(StopSearchResult(
                    stop_id=row.stop_id,
                    stop_name=row.stop_name,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    distance_meters=row.distance_meters,
                    routes_served=list(row.routes_served) if row.routes_served else [],
                    avg_daily_ridership=row.avg_daily_ridership,
                    walking_time_minutes=walking_time
                ))
            
            # Cache results for 5 minutes
            cache_data = [stop.__dict__ for stop in stops]
            self.cache_manager.set('nearby_stops', cache_data, ttl=300, cache_key)
            
            return stops
            
        except Exception as e:
            logger.error("Nearby stops query failed", 
                        error=str(e),
                        location=location.__dict__,
                        radius=radius_meters)
            return []
    
    @cached('route_geometry', ttl=3600)  # Cache for 1 hour
    def get_route_geometry(self, route_id: str) -> Optional[RouteGeometry]:
        """
        Get route geometry with performance metrics
        """
        query = """
        WITH route_stops AS (
            SELECT DISTINCT
                st.stop_id,
                s.geom,
                st.stop_sequence
            FROM gtfs_stop_times st
            JOIN gtfs_trips t ON st.trip_id = t.trip_id
            JOIN gtfs_stops s ON st.stop_id = s.stop_id
            WHERE t.route_id = %(route_id)s
            ORDER BY st.stop_sequence
        ),
        route_line AS (
            SELECT 
                ST_MakeLine(geom ORDER BY stop_sequence) as geometry
            FROM route_stops
        ),
        route_metrics AS (
            SELECT
                COUNT(*) as stop_count,
                ST_Length(rl.geometry::geography) as length_meters
            FROM route_stops rs, route_line rl
        )
        SELECT 
            r.route_id,
            COALESCE(r.route_short_name, r.route_long_name) as route_name,
            ST_AsText(rl.geometry) as geometry_wkt,
            ROUND((rm.length_meters / 1000)::numeric, 2) as total_length_km,
            rm.stop_count,
            CASE 
                WHEN rm.stop_count > 1 
                THEN ROUND((rm.length_meters / (rm.stop_count - 1))::numeric, 0)
                ELSE 0
            END as avg_stop_spacing_m
        FROM gtfs_routes r, route_line rl, route_metrics rm
        WHERE r.route_id = %(route_id)s
        """
        
        try:
            result = execute_query(query, params={'route_id': route_id}, fetch='one')
            
            if result and result.geometry_wkt:
                from shapely import wkt
                geometry = wkt.loads(result.geometry_wkt)
                
                return RouteGeometry(
                    route_id=result.route_id,
                    route_name=result.route_name,
                    geometry=geometry,
                    total_length_km=float(result.total_length_km),
                    stop_count=result.stop_count,
                    avg_stop_spacing_m=float(result.avg_stop_spacing_m)
                )
            
            return None
            
        except Exception as e:
            logger.error("Route geometry query failed", 
                        error=str(e), route_id=route_id)
            return None
    
    def find_routes_intersecting_area(self,
                                     area_polygon: Polygon,
                                     include_metrics: bool = True) -> List[Dict[str, Any]]:
        """
        Find routes that intersect with a given area polygon
        """
        # Convert polygon to WKT
        area_wkt = area_polygon.wkt
        
        query = """
        WITH search_area AS (
            SELECT ST_GeomFromText(%(area_wkt)s, 4326) as geom
        ),
        intersecting_routes AS (
            SELECT DISTINCT 
                t.route_id
            FROM gtfs_trips t
            JOIN gtfs_stop_times st ON t.trip_id = st.trip_id
            JOIN gtfs_stops s ON st.stop_id = s.stop_id
            WHERE ST_Intersects(s.geom, (SELECT geom FROM search_area))
        )
        SELECT 
            r.route_id,
            r.route_short_name,
            r.route_long_name,
            r.route_type
        FROM intersecting_routes ir
        JOIN gtfs_routes r ON ir.route_id = r.route_id
        ORDER BY r.route_short_name
        """
        
        if include_metrics:
            # Add route metrics subquery
            query = query.replace(
                "SELECT \n            r.route_id,",
                """SELECT 
            r.route_id,
            r.route_short_name,
            r.route_long_name,
            r.route_type,
            COUNT(DISTINCT s.stop_id) as stops_in_area,
            AVG(utd.passenger_count) as avg_ridership_in_area"""
            ).replace(
                "FROM intersecting_routes ir\n        JOIN gtfs_routes r ON ir.route_id = r.route_id",
                """FROM intersecting_routes ir
        JOIN gtfs_routes r ON ir.route_id = r.route_id
        LEFT JOIN gtfs_trips t ON r.route_id = t.route_id
        LEFT JOIN gtfs_stop_times st ON t.trip_id = st.trip_id
        LEFT JOIN gtfs_stops s ON st.stop_id = s.stop_id
        LEFT JOIN unified_transit_data utd ON (
            s.stop_id = utd.stop_id 
            AND utd.timestamp >= CURRENT_DATE - INTERVAL '30 days'
        )
        WHERE ST_Intersects(s.geom, (SELECT geom FROM search_area))
        GROUP BY r.route_id, r.route_short_name, r.route_long_name, r.route_type"""
            )
        
        try:
            result = execute_query(query, params={'area_wkt': area_wkt}, fetch='all')
            
            routes = []
            for row in result:
                route_data = {
                    'route_id': row.route_id,
                    'route_short_name': row.route_short_name,
                    'route_long_name': row.route_long_name,
                    'route_type': row.route_type
                }
                
                if include_metrics:
                    route_data.update({
                        'stops_in_area': getattr(row, 'stops_in_area', 0),
                        'avg_ridership_in_area': getattr(row, 'avg_ridership_in_area', 0)
                    })
                
                routes.append(route_data)
            
            return routes
            
        except Exception as e:
            logger.error("Routes in area query failed", error=str(e))
            return []
    
    def calculate_service_coverage(self,
                                  area_polygon: Polygon,
                                  service_buffer_meters: int = 400) -> Dict[str, Any]:
        """
        Calculate transit service coverage for a given area
        """
        area_wkt = area_polygon.wkt
        
        query = """
        WITH search_area AS (
            SELECT 
                ST_GeomFromText(%(area_wkt)s, 4326) as geom,
                ST_Area(ST_GeomFromText(%(area_wkt)s, 4326)::geography) as area_sqm
        ),
        stops_in_area AS (
            SELECT s.geom
            FROM gtfs_stops s, search_area sa
            WHERE ST_Intersects(s.geom, sa.geom)
                AND s.location_type IN (0, 1)
        ),
        service_coverage AS (
            SELECT 
                ST_Union(ST_Buffer(sia.geom::geography, %(buffer_meters)s)) as covered_area
            FROM stops_in_area sia
        ),
        coverage_metrics AS (
            SELECT 
                sa.area_sqm,
                ST_Area(
                    ST_Intersection(
                        sc.covered_area::geometry, 
                        sa.geom
                    )::geography
                ) as covered_sqm
            FROM search_area sa, service_coverage sc
        )
        SELECT 
            area_sqm / 1000000.0 as total_area_km2,
            covered_sqm / 1000000.0 as covered_area_km2,
            (covered_sqm / area_sqm * 100.0) as coverage_percentage,
            COUNT(DISTINCT s.stop_id) as stops_count,
            COUNT(DISTINCT r.route_id) as routes_count
        FROM coverage_metrics cm
        CROSS JOIN (
            SELECT s.stop_id, t.route_id
            FROM gtfs_stops s, search_area sa
            JOIN gtfs_stop_times st ON s.stop_id = st.stop_id
            JOIN gtfs_trips t ON st.trip_id = t.trip_id
            JOIN gtfs_routes r ON t.route_id = r.route_id
            WHERE ST_Intersects(s.geom, sa.geom)
        ) AS service_summary
        GROUP BY cm.area_sqm, cm.covered_sqm
        """
        
        try:
            result = execute_query(
                query, 
                params={
                    'area_wkt': area_wkt,
                    'buffer_meters': service_buffer_meters
                },
                fetch='one'
            )
            
            if result:
                return {
                    'total_area_km2': float(result.total_area_km2 or 0),
                    'covered_area_km2': float(result.covered_area_km2 or 0),
                    'coverage_percentage': float(result.coverage_percentage or 0),
                    'stops_count': result.stops_count or 0,
                    'routes_count': result.routes_count or 0,
                    'service_buffer_meters': service_buffer_meters
                }
            else:
                return {
                    'total_area_km2': 0, 'covered_area_km2': 0,
                    'coverage_percentage': 0, 'stops_count': 0,
                    'routes_count': 0, 'service_buffer_meters': service_buffer_meters
                }
            
        except Exception as e:
            logger.error("Service coverage calculation failed", error=str(e))
            return {}
    
    def find_optimal_stop_locations(self,
                                   demand_points: List[SpatialPoint],
                                   existing_stops: List[str] = None,
                                   max_new_stops: int = 5,
                                   min_stop_distance: int = 500) -> List[Dict[str, Any]]:
        """
        Find optimal locations for new transit stops based on demand points
        Uses spatial clustering and coverage optimization
        """
        if not demand_points:
            return []
        
        # Convert demand points to DataFrame for analysis
        demand_data = pd.DataFrame([
            {'latitude': p.latitude, 'longitude': p.longitude}
            for p in demand_points
        ])
        
        # Use k-means clustering to identify demand centers
        from sklearn.cluster import KMeans
        
        n_clusters = min(max_new_stops, len(demand_points))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        
        # Fit clustering model
        demand_coords = demand_data[['latitude', 'longitude']].values
        cluster_labels = kmeans.fit_predict(demand_coords)
        cluster_centers = kmeans.cluster_centers_
        
        optimal_locations = []
        
        for i, center in enumerate(cluster_centers):
            center_point = SpatialPoint(
                latitude=center[0],
                longitude=center[1]
            )
            
            # Check if location conflicts with existing stops
            if existing_stops:
                conflict = False
                nearby_existing = self.find_nearby_stops(
                    center_point,
                    radius_meters=min_stop_distance,
                    limit=5,
                    include_routes=False,
                    include_ridership=False
                )
                
                if any(stop.stop_id in existing_stops for stop in nearby_existing):
                    conflict = True
            
            # Calculate demand served by this location
            cluster_demand_points = [
                demand_points[j] for j, label in enumerate(cluster_labels) if label == i
            ]
            
            coverage_area = self.calculate_service_coverage(
                Polygon([
                    (center[1] - 0.01, center[0] - 0.01),
                    (center[1] + 0.01, center[0] - 0.01),
                    (center[1] + 0.01, center[0] + 0.01),
                    (center[1] - 0.01, center[0] + 0.01),
                    (center[1] - 0.01, center[0] - 0.01)
                ])
            )
            
            optimal_locations.append({
                'cluster_id': i,
                'latitude': center[0],
                'longitude': center[1],
                'demand_points_served': len(cluster_demand_points),
                'has_conflict': conflict if existing_stops else False,
                'estimated_coverage_km2': coverage_area.get('covered_area_km2', 0),
                'priority_score': len(cluster_demand_points) * (0.5 if conflict else 1.0)
            })
        
        # Sort by priority score
        optimal_locations.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return optimal_locations
    
    def analyze_route_efficiency(self, route_id: str) -> Dict[str, Any]:
        """
        Analyze route efficiency using spatial metrics
        """
        route_geometry = self.get_route_geometry(route_id)
        
        if not route_geometry:
            return {'error': 'Route not found'}
        
        # Calculate route efficiency metrics
        query = """
        WITH route_analysis AS (
            SELECT 
                r.route_id,
                COUNT(DISTINCT st.stop_id) as total_stops,
                AVG(utd.passenger_count) as avg_ridership,
                AVG(utd.dwell_time_seconds) as avg_dwell_time,
                AVG(utd.arrival_delay_seconds) as avg_delay,
                COUNT(DISTINCT DATE(utd.timestamp)) as service_days
            FROM gtfs_routes r
            JOIN gtfs_trips t ON r.route_id = t.route_id
            JOIN gtfs_stop_times st ON t.trip_id = st.trip_id
            LEFT JOIN unified_transit_data utd ON (
                st.stop_id = utd.stop_id 
                AND t.route_id = utd.route_id
                AND utd.timestamp >= CURRENT_DATE - INTERVAL '30 days'
            )
            WHERE r.route_id = %(route_id)s
            GROUP BY r.route_id
        )
        SELECT * FROM route_analysis
        """
        
        try:
            result = execute_query(query, params={'route_id': route_id}, fetch='one')
            
            if result:
                # Calculate spatial efficiency metrics
                efficiency_metrics = {
                    'route_id': route_id,
                    'route_name': route_geometry.route_name,
                    'total_length_km': route_geometry.total_length_km,
                    'total_stops': result.total_stops,
                    'avg_stop_spacing_m': route_geometry.avg_stop_spacing_m,
                    'avg_ridership': float(result.avg_ridership or 0),
                    'avg_dwell_time_seconds': float(result.avg_dwell_time or 0),
                    'avg_delay_seconds': float(result.avg_delay or 0),
                    'service_days': result.service_days or 0,
                    
                    # Calculated efficiency metrics
                    'ridership_per_km': (result.avg_ridership or 0) / max(route_geometry.total_length_km, 0.1),
                    'stops_per_km': result.total_stops / max(route_geometry.total_length_km, 0.1),
                    'efficiency_score': self._calculate_route_efficiency_score(
                        result.avg_ridership or 0,
                        route_geometry.total_length_km,
                        result.avg_delay or 0
                    )
                }
                
                return efficiency_metrics
            else:
                return {'error': 'No data available for route'}
                
        except Exception as e:
            logger.error("Route efficiency analysis failed", 
                        error=str(e), route_id=route_id)
            return {'error': str(e)}
    
    def _calculate_route_efficiency_score(self, 
                                        avg_ridership: float,
                                        route_length_km: float,
                                        avg_delay: float) -> float:
        """
        Calculate normalized efficiency score (0-100)
        """
        if route_length_km == 0:
            return 0
        
        # Base efficiency: ridership per km
        base_efficiency = avg_ridership / route_length_km
        
        # Penalty for delays (max 50% reduction)
        delay_penalty = min(0.5, abs(avg_delay) / 600)  # 10-minute delay = 50% penalty
        
        # Normalize to 0-100 scale (assuming max efficiency of 100 riders/km)
        efficiency_score = (base_efficiency / 100) * 100 * (1 - delay_penalty)
        
        return min(100, max(0, efficiency_score))

# Global spatial query optimizer
_spatial_optimizer: Optional[SpatialQueryOptimizer] = None

def get_spatial_optimizer() -> SpatialQueryOptimizer:
    """Get or create global spatial query optimizer"""
    global _spatial_optimizer
    if _spatial_optimizer is None:
        _spatial_optimizer = SpatialQueryOptimizer()
    return _spatial_optimizer

# Convenience functions
def find_nearby_stops(location: SpatialPoint, **kwargs) -> List[StopSearchResult]:
    """Find nearby transit stops"""
    return get_spatial_optimizer().find_nearby_stops(location, **kwargs)

def get_route_geometry(route_id: str) -> Optional[RouteGeometry]:
    """Get route geometry"""
    return get_spatial_optimizer().get_route_geometry(route_id)

def calculate_service_coverage(area_polygon: Polygon, **kwargs) -> Dict[str, Any]:
    """Calculate transit service coverage"""
    return get_spatial_optimizer().calculate_service_coverage(area_polygon, **kwargs)

def analyze_route_efficiency(route_id: str) -> Dict[str, Any]:
    """Analyze route efficiency"""
    return get_spatial_optimizer().analyze_route_efficiency(route_id)