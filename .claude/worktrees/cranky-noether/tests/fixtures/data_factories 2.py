"""
Data factories for generating realistic test data for the MARTA platform.
"""
import random
import string
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class RouteType(Enum):
    """GTFS route types."""
    RAIL = 1
    BUS = 3
    SUBWAY = 1


class WeatherCondition(Enum):
    """Weather conditions."""
    CLEAR = "Clear"
    PARTLY_CLOUDY = "Partly Cloudy"
    CLOUDY = "Cloudy"
    RAIN = "Rain"
    SNOW = "Snow"
    FOG = "Fog"


@dataclass
class DataFactoryConfig:
    """Configuration for data factories."""
    start_date: date = field(default_factory=lambda: date(2024, 1, 1))
    end_date: date = field(default_factory=lambda: date(2024, 12, 31))
    num_routes: int = 10
    num_stops: int = 50
    num_vehicles: int = 25
    seed: Optional[int] = 42


class GTFSDataFactory:
    """Factory for generating GTFS test data."""
    
    def __init__(self, config: DataFactoryConfig):
        self.config = config
        if config.seed:
            random.seed(config.seed)
            np.random.seed(config.seed)
    
    def generate_stops(self) -> pd.DataFrame:
        """Generate realistic MARTA stops data."""
        # Atlanta metro area coordinates
        atlanta_lat_range = (33.4, 34.0)
        atlanta_lon_range = (-84.8, -84.0)
        
        stops = []
        stop_names = [
            "Airport", "College Park", "East Point", "Lakewood", "Oakland City",
            "West End", "Garnett", "Five Points", "Peachtree Center", "Civic Center",
            "North Avenue", "Midtown", "Arts Center", "Lindbergh", "Buckhead",
            "Medical Center", "Dunwoody", "Sandy Springs", "North Springs",
            "Doraville", "Chamblee", "Brookhaven", "Lenox", "East Lake",
            "Decatur", "Avondale", "Kensington", "Indian Creek", "Hamilton Holmes",
            "West Lake", "Ashby", "Vine City", "Omni Dome", "Georgia State",
            "King Memorial", "Inman Park", "Reynoldstown", "East Point",
            "College Park", "Airport", "Bankhead", "Western", "H.E. Holmes",
            "MLK Jr", "Ashby", "Vine City", "GWCC", "CNN Center", "Philips Arena"
        ]
        
        for i in range(self.config.num_stops):
            stop_name = random.choice(stop_names) + f" Station {i+1}" if i >= len(stop_names) else stop_names[i]
            
            stops.append({
                'stop_id': f'stop_{i+1:03d}',
                'stop_code': f'MARTA_{i+1:03d}',
                'stop_name': stop_name,
                'stop_desc': f'MARTA {stop_name}',
                'stop_lat': round(random.uniform(*atlanta_lat_range), 6),
                'stop_lon': round(random.uniform(*atlanta_lon_range), 6),
                'zone_id': random.randint(1, 5),
                'stop_url': f'https://marta.com/stops/stop_{i+1:03d}',
                'location_type': 0,  # Stop/platform
                'parent_station': '',
                'stop_timezone': 'America/New_York',
                'wheelchair_boarding': random.choice([0, 1, 2])
            })
        
        return pd.DataFrame(stops)
    
    def generate_routes(self) -> pd.DataFrame:
        """Generate realistic MARTA routes data."""
        route_data = [
            {'short_name': 'RED', 'long_name': 'Red Line', 'color': 'FF0000', 'type': RouteType.RAIL.value},
            {'short_name': 'GOLD', 'long_name': 'Gold Line', 'color': 'FFD700', 'type': RouteType.RAIL.value},
            {'short_name': 'BLUE', 'long_name': 'Blue Line', 'color': '0000FF', 'type': RouteType.RAIL.value},
            {'short_name': 'GREEN', 'long_name': 'Green Line', 'color': '008000', 'type': RouteType.RAIL.value},
        ]
        
        # Add bus routes
        for i in range(5, self.config.num_routes + 1):
            route_data.append({
                'short_name': str(i),
                'long_name': f'Route {i}',
                'color': f'{random.randint(0, 255):02X}{random.randint(0, 255):02X}{random.randint(0, 255):02X}',
                'type': RouteType.BUS.value
            })
        
        routes = []
        for i, route_info in enumerate(route_data):
            if i >= self.config.num_routes:
                break
                
            routes.append({
                'route_id': f'route_{i+1:03d}',
                'agency_id': 'MARTA',
                'route_short_name': route_info['short_name'],
                'route_long_name': route_info['long_name'],
                'route_desc': f'MARTA {route_info["long_name"]}',
                'route_type': route_info['type'],
                'route_url': f'https://marta.com/routes/{route_info["short_name"].lower()}',
                'route_color': route_info['color'],
                'route_text_color': 'FFFFFF' if route_info['color'] != 'FFD700' else '000000'
            })
        
        return pd.DataFrame(routes)
    
    def generate_calendar(self) -> pd.DataFrame:
        """Generate calendar data for service periods."""
        calendars = [
            {
                'service_id': 'weekday',
                'monday': 1, 'tuesday': 1, 'wednesday': 1, 'thursday': 1, 'friday': 1,
                'saturday': 0, 'sunday': 0,
                'start_date': self.config.start_date.strftime('%Y%m%d'),
                'end_date': self.config.end_date.strftime('%Y%m%d')
            },
            {
                'service_id': 'weekend',
                'monday': 0, 'tuesday': 0, 'wednesday': 0, 'thursday': 0, 'friday': 0,
                'saturday': 1, 'sunday': 1,
                'start_date': self.config.start_date.strftime('%Y%m%d'),
                'end_date': self.config.end_date.strftime('%Y%m%d')
            },
            {
                'service_id': 'daily',
                'monday': 1, 'tuesday': 1, 'wednesday': 1, 'thursday': 1, 'friday': 1,
                'saturday': 1, 'sunday': 1,
                'start_date': self.config.start_date.strftime('%Y%m%d'),
                'end_date': self.config.end_date.strftime('%Y%m%d')
            }
        ]
        
        return pd.DataFrame(calendars)
    
    def generate_trips(self, routes_df: pd.DataFrame) -> pd.DataFrame:
        """Generate trips data based on routes."""
        trips = []
        trip_id_counter = 1
        
        for _, route in routes_df.iterrows():
            route_id = route['route_id']
            
            # Generate trips for each service type
            service_types = ['weekday', 'weekend'] if route['route_type'] == RouteType.RAIL.value else ['daily']
            
            for service_id in service_types:
                # Generate trips for both directions
                for direction in [0, 1]:
                    # Number of trips varies by route type and service
                    if route['route_type'] == RouteType.RAIL.value:
                        num_trips = random.randint(20, 40) if service_id == 'weekday' else random.randint(15, 25)
                    else:
                        num_trips = random.randint(10, 20)
                    
                    for trip_num in range(num_trips):
                        trip_id = f'trip_{trip_id_counter:06d}'
                        trips.append({
                            'route_id': route_id,
                            'service_id': service_id,
                            'trip_id': trip_id,
                            'trip_headsign': f'{route["route_long_name"]} {"Northbound" if direction == 0 else "Southbound"}',
                            'direction_id': direction,
                            'block_id': f'block_{random.randint(1, 50)}',
                            'shape_id': f'shape_{route_id}_{direction}',
                            'wheelchair_accessible': random.choice([0, 1, 2]),
                            'bikes_allowed': random.choice([0, 1, 2])
                        })
                        trip_id_counter += 1
        
        return pd.DataFrame(trips)
    
    def generate_stop_times(self, trips_df: pd.DataFrame, stops_df: pd.DataFrame) -> pd.DataFrame:
        """Generate stop times for trips."""
        stop_times = []
        
        for _, trip in trips_df.iterrows():
            trip_id = trip['trip_id']
            
            # Select random stops for this trip (3-8 stops)
            num_stops = random.randint(3, min(8, len(stops_df)))
            trip_stops = stops_df.sample(n=num_stops).sort_values('stop_id')
            
            # Generate start time for trip
            start_hour = random.randint(5, 22)  # 5 AM to 10 PM
            start_minute = random.randint(0, 59)
            current_time = datetime.combine(date.today(), datetime.min.time().replace(hour=start_hour, minute=start_minute))
            
            for seq, (_, stop) in enumerate(trip_stops.iterrows(), 1):
                # Travel time between stops (2-8 minutes)
                if seq > 1:
                    travel_time = random.randint(2, 8)
                    current_time += timedelta(minutes=travel_time)
                
                # Dwell time at stop (30 seconds - 2 minutes)
                dwell_time = random.randint(30, 120)  # seconds
                
                arrival_time = current_time
                departure_time = current_time + timedelta(seconds=dwell_time)
                
                stop_times.append({
                    'trip_id': trip_id,
                    'arrival_time': arrival_time.strftime('%H:%M:%S'),
                    'departure_time': departure_time.strftime('%H:%M:%S'),
                    'stop_id': stop['stop_id'],
                    'stop_sequence': seq,
                    'pickup_type': 0,  # Regular pickup
                    'drop_off_type': 0,  # Regular drop off
                    'shape_dist_traveled': seq * random.uniform(0.5, 2.0)  # Rough distance
                })
                
                current_time = departure_time
        
        return pd.DataFrame(stop_times)


class RidershipDataFactory:
    """Factory for generating ridership test data."""
    
    def __init__(self, config: DataFactoryConfig):
        self.config = config
        if config.seed:
            random.seed(config.seed)
            np.random.seed(config.seed)
    
    def generate_historical_ridership(self) -> pd.DataFrame:
        """Generate historical ridership data with realistic patterns."""
        data = []
        current_date = self.config.start_date
        
        while current_date <= self.config.end_date:
            # Generate hourly data for each day
            for hour in range(24):
                for route_id in range(1, self.config.num_routes + 1):
                    route_name = f'route_{route_id:03d}'
                    
                    # Base ridership with patterns
                    base_ridership = self._get_base_ridership(hour, current_date.weekday(), route_id)
                    
                    # Add seasonal variations
                    seasonal_factor = self._get_seasonal_factor(current_date)
                    
                    # Add random noise
                    noise = np.random.normal(0, base_ridership * 0.1)
                    
                    ridership = max(0, int(base_ridership * seasonal_factor + noise))
                    
                    data.append({
                        'date': current_date,
                        'hour': hour,
                        'route_id': route_name,
                        'ridership': ridership,
                        'day_of_week': current_date.weekday(),
                        'is_weekend': current_date.weekday() >= 5,
                        'is_holiday': self._is_holiday(current_date),
                        'month': current_date.month,
                        'quarter': (current_date.month - 1) // 3 + 1
                    })
            
            current_date += timedelta(days=1)
        
        return pd.DataFrame(data)
    
    def _get_base_ridership(self, hour: int, day_of_week: int, route_id: int) -> float:
        """Get base ridership based on hour, day, and route."""
        # Peak hours: 7-9 AM, 5-7 PM
        hour_factors = {
            range(0, 5): 5,    # Late night
            range(5, 7): 15,   # Early morning
            range(7, 9): 100,  # Morning rush
            range(9, 11): 40,  # Mid morning
            range(11, 14): 60, # Lunch
            range(14, 17): 45, # Afternoon
            range(17, 19): 95, # Evening rush
            range(19, 22): 35, # Evening
            range(22, 24): 15  # Night
        }
        
        hour_factor = 30  # default
        for time_range, factor in hour_factors.items():
            if hour in time_range:
                hour_factor = factor
                break
        
        # Weekend factor
        weekend_factor = 0.6 if day_of_week >= 5 else 1.0
        
        # Route popularity (rail lines more popular)
        route_factor = 1.2 if route_id <= 4 else random.uniform(0.5, 1.0)
        
        return hour_factor * weekend_factor * route_factor
    
    def _get_seasonal_factor(self, date: date) -> float:
        """Get seasonal adjustment factor."""
        month = date.month
        
        # Lower ridership in summer (students), higher in fall/winter
        seasonal_factors = {
            1: 1.0, 2: 1.0, 3: 1.1, 4: 1.1,
            5: 1.0, 6: 0.8, 7: 0.7, 8: 0.8,
            9: 1.2, 10: 1.1, 11: 1.0, 12: 0.9
        }
        
        return seasonal_factors.get(month, 1.0)
    
    def _is_holiday(self, date: date) -> bool:
        """Check if date is a major holiday (simplified)."""
        holidays = [
            (1, 1),   # New Year
            (1, 15),  # MLK Day (approx)
            (7, 4),   # Independence Day
            (11, 22), # Thanksgiving (approx)
            (12, 25)  # Christmas
        ]
        
        return (date.month, date.day) in holidays


class WeatherDataFactory:
    """Factory for generating weather test data."""
    
    def __init__(self, config: DataFactoryConfig):
        self.config = config
        if config.seed:
            random.seed(config.seed)
            np.random.seed(config.seed)
    
    def generate_weather_data(self) -> pd.DataFrame:
        """Generate realistic weather data for Atlanta."""
        data = []
        current_date = self.config.start_date
        
        while current_date <= self.config.end_date:
            # Atlanta climate patterns
            temp_base = self._get_seasonal_temperature(current_date)
            
            data.append({
                'date': current_date,
                'temperature_f': round(temp_base + np.random.normal(0, 5), 1),
                'temperature_c': round((temp_base - 32) * 5/9, 1),
                'humidity': round(random.uniform(30, 95), 1),
                'precipitation_inches': max(0, round(np.random.exponential(0.1), 2)),
                'wind_speed_mph': round(random.uniform(0, 25), 1),
                'visibility_miles': round(random.uniform(5, 15), 1),
                'weather_condition': random.choice(list(WeatherCondition)).value,
                'is_severe_weather': random.random() < 0.05  # 5% chance
            })
            
            current_date += timedelta(days=1)
        
        return pd.DataFrame(data)
    
    def _get_seasonal_temperature(self, date: date) -> float:
        """Get seasonal base temperature for Atlanta."""
        month = date.month
        
        # Atlanta average temperatures by month (Fahrenheit)
        monthly_temps = {
            1: 43, 2: 48, 3: 56, 4: 64, 5: 72, 6: 79,
            7: 82, 8: 81, 9: 76, 10: 66, 11: 56, 12: 46
        }
        
        return monthly_temps.get(month, 65)


class RealtimeDataFactory:
    """Factory for generating real-time transit data."""
    
    def __init__(self, config: DataFactoryConfig):
        self.config = config
        if config.seed:
            random.seed(config.seed)
            np.random.seed(config.seed)
    
    def generate_vehicle_positions(self) -> List[Dict[str, Any]]:
        """Generate current vehicle positions."""
        positions = []
        
        for vehicle_id in range(1, self.config.num_vehicles + 1):
            route_id = random.randint(1, self.config.num_routes)
            
            # Atlanta metro area coordinates
            lat = random.uniform(33.4, 34.0)
            lon = random.uniform(-84.8, -84.0)
            
            positions.append({
                'vehicle_id': f'vehicle_{vehicle_id:03d}',
                'route_id': f'route_{route_id:03d}',
                'trip_id': f'trip_{random.randint(1, 1000):06d}',
                'latitude': round(lat, 6),
                'longitude': round(lon, 6),
                'bearing': random.randint(0, 359),
                'speed_mph': round(random.uniform(0, 45), 1),
                'timestamp': datetime.now().timestamp(),
                'occupancy_status': random.choice(['EMPTY', 'MANY_SEATS_AVAILABLE', 'FEW_SEATS_AVAILABLE', 'STANDING_ROOM_ONLY', 'CRUSHED_STANDING_ROOM_ONLY', 'FULL'])
            })
        
        return positions
    
    def generate_trip_updates(self) -> List[Dict[str, Any]]:
        """Generate trip delay/update information."""
        updates = []
        
        for _ in range(random.randint(10, 50)):
            trip_id = f'trip_{random.randint(1, 1000):06d}'
            route_id = f'route_{random.randint(1, self.config.num_routes):03d}'
            
            # Generate delays (-300 to +900 seconds, more likely to be late)
            delay = int(np.random.gamma(2, 60))  # Gamma distribution for realistic delays
            if random.random() < 0.3:  # 30% chance of being early
                delay = -delay
            
            updates.append({
                'trip_id': trip_id,
                'route_id': route_id,
                'delay_seconds': delay,
                'schedule_relationship': random.choice(['SCHEDULED', 'CANCELED', 'ADDED']),
                'timestamp': datetime.now().timestamp(),
                'stop_time_updates': self._generate_stop_time_updates(trip_id, delay)
            })
        
        return updates
    
    def _generate_stop_time_updates(self, trip_id: str, base_delay: int) -> List[Dict[str, Any]]:
        """Generate stop time updates for a trip."""
        updates = []
        num_stops = random.randint(3, 8)
        
        for stop_seq in range(1, num_stops + 1):
            # Delays can vary slightly at each stop
            stop_delay = base_delay + random.randint(-30, 30)
            
            updates.append({
                'stop_sequence': stop_seq,
                'stop_id': f'stop_{random.randint(1, self.config.num_stops):03d}',
                'arrival_delay': stop_delay,
                'departure_delay': stop_delay + random.randint(0, 60),  # Slightly longer departure delay
                'schedule_relationship': 'SCHEDULED'
            })
        
        return updates


def create_complete_test_dataset(config: DataFactoryConfig = None) -> Dict[str, pd.DataFrame]:
    """Create a complete test dataset with all data types."""
    if config is None:
        config = DataFactoryConfig()
    
    gtfs_factory = GTFSDataFactory(config)
    ridership_factory = RidershipDataFactory(config)
    weather_factory = WeatherDataFactory(config)
    
    # Generate GTFS data
    stops = gtfs_factory.generate_stops()
    routes = gtfs_factory.generate_routes()
    calendar = gtfs_factory.generate_calendar()
    trips = gtfs_factory.generate_trips(routes)
    stop_times = gtfs_factory.generate_stop_times(trips, stops)
    
    # Generate other data
    ridership = ridership_factory.generate_historical_ridership()
    weather = weather_factory.generate_weather_data()
    
    return {
        'gtfs_stops': stops,
        'gtfs_routes': routes,
        'gtfs_calendar': calendar,
        'gtfs_trips': trips,
        'gtfs_stop_times': stop_times,
        'ridership_data': ridership,
        'weather_data': weather
    }