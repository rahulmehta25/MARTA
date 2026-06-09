#!/usr/bin/env python3
"""
Weather Integration - Enhanced weather data for ML feature correlation with transit usage
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import requests
import json
import psycopg2
from psycopg2 import pool

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)

# Atlanta coordinates
ATLANTA_LAT = 33.7490
ATLANTA_LON = -84.3880


class WeatherIntegration:
    """
    Enhanced weather data integration for ML features
    Fetches current and forecast weather, correlates with transit patterns
    """

    def __init__(self, db_pool: Optional[pool.ThreadedConnectionPool] = None):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.db_pool = db_pool or self._create_db_pool()
        self._init_tables()

        logger.info("WeatherIntegration initialized")

    def _create_db_pool(self) -> pool.ThreadedConnectionPool:
        return pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=5,
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            port=settings.DB_PORT
        )

    def _init_tables(self):
        """Initialize weather tables with ML-ready schema"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    -- Enhanced weather data table
                    CREATE TABLE IF NOT EXISTS weather_data (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        location_lat NUMERIC,
                        location_lon NUMERIC,

                        -- Temperature
                        temperature_c NUMERIC,
                        feels_like_c NUMERIC,
                        temp_min_c NUMERIC,
                        temp_max_c NUMERIC,

                        -- Precipitation
                        precipitation_mm NUMERIC DEFAULT 0,
                        precipitation_probability NUMERIC,
                        snow_mm NUMERIC DEFAULT 0,

                        -- Humidity and pressure
                        humidity_percent INTEGER,
                        pressure_hpa NUMERIC,
                        dew_point_c NUMERIC,

                        -- Wind
                        wind_speed_mps NUMERIC,
                        wind_gust_mps NUMERIC,
                        wind_direction_deg INTEGER,

                        -- Visibility and clouds
                        visibility_m INTEGER,
                        cloudiness_percent INTEGER,
                        uv_index NUMERIC,

                        -- Conditions
                        weather_main VARCHAR(50),
                        weather_description VARCHAR(255),
                        weather_icon VARCHAR(10),
                        weather_code INTEGER,

                        -- ML Features (pre-computed)
                        is_precipitation BOOLEAN,
                        is_severe_weather BOOLEAN,
                        temperature_category VARCHAR(20),
                        comfort_index NUMERIC,

                        -- Metadata
                        source VARCHAR(50) DEFAULT 'openweathermap',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                        UNIQUE(timestamp, location_lat, location_lon)
                    );

                    CREATE INDEX IF NOT EXISTS idx_weather_timestamp
                        ON weather_data(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_weather_main
                        ON weather_data(weather_main);

                    -- Weather forecast table
                    CREATE TABLE IF NOT EXISTS weather_forecast (
                        id SERIAL PRIMARY KEY,
                        forecast_timestamp TIMESTAMP NOT NULL,
                        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        temperature_c NUMERIC,
                        feels_like_c NUMERIC,
                        precipitation_probability NUMERIC,
                        precipitation_mm NUMERIC,
                        weather_main VARCHAR(50),
                        weather_description VARCHAR(255),
                        wind_speed_mps NUMERIC,
                        humidity_percent INTEGER,
                        cloudiness_percent INTEGER,
                        is_precipitation BOOLEAN,
                        UNIQUE(forecast_timestamp)
                    );

                    CREATE INDEX IF NOT EXISTS idx_forecast_timestamp
                        ON weather_forecast(forecast_timestamp);

                    -- Weather-transit correlation table
                    CREATE TABLE IF NOT EXISTS weather_transit_correlation (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        hour INTEGER,
                        avg_temperature NUMERIC,
                        precipitation_mm NUMERIC,
                        weather_main VARCHAR(50),
                        avg_ridership NUMERIC,
                        avg_delay_seconds NUMERIC,
                        correlation_score NUMERIC,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date, hour)
                    );
                """)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def _compute_comfort_index(
        self,
        temp_c: float,
        humidity: int,
        wind_speed: float
    ) -> float:
        """Compute comfort index for transit waiting"""
        # Simple thermal comfort index
        # Higher is more comfortable (0-100 scale)
        temp_comfort = 100 - abs(temp_c - 20) * 3  # Optimal at 20C
        humidity_comfort = 100 - abs(humidity - 50) * 0.5  # Optimal at 50%
        wind_penalty = min(wind_speed * 5, 30)  # Wind reduces comfort

        comfort = (temp_comfort + humidity_comfort) / 2 - wind_penalty
        return max(0, min(100, comfort))

    def _categorize_temperature(self, temp_c: float) -> str:
        """Categorize temperature for ML features"""
        if temp_c < 0:
            return 'freezing'
        elif temp_c < 10:
            return 'cold'
        elif temp_c < 20:
            return 'cool'
        elif temp_c < 30:
            return 'warm'
        else:
            return 'hot'

    def _is_severe_weather(
        self,
        weather_code: int,
        wind_speed: float,
        visibility: int
    ) -> bool:
        """Determine if weather is severe (affects transit)"""
        severe_codes = [
            200, 201, 202,  # Thunderstorm
            502, 503, 504,  # Heavy rain
            602, 622,  # Heavy snow
            711, 731, 751, 761, 762,  # Dust/sand/ash
            771, 781  # Squall/tornado
        ]

        if weather_code in severe_codes:
            return True
        if wind_speed > 15:  # Strong wind
            return True
        if visibility < 500:  # Very low visibility
            return True

        return False

    def fetch_current_weather(self) -> Optional[Dict]:
        """Fetch current weather from OpenWeatherMap"""
        if not self.api_key:
            logger.warning("No OpenWeatherMap API key configured")
            return None

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': ATLANTA_LAT,
                'lon': ATLANTA_LON,
                'appid': self.api_key,
                'units': 'metric'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract and compute features
            weather_data = {
                'timestamp': datetime.fromtimestamp(data['dt']),
                'location_lat': ATLANTA_LAT,
                'location_lon': ATLANTA_LON,
                'temperature_c': data['main']['temp'],
                'feels_like_c': data['main']['feels_like'],
                'temp_min_c': data['main']['temp_min'],
                'temp_max_c': data['main']['temp_max'],
                'humidity_percent': data['main']['humidity'],
                'pressure_hpa': data['main']['pressure'],
                'wind_speed_mps': data['wind']['speed'],
                'wind_gust_mps': data['wind'].get('gust'),
                'wind_direction_deg': data['wind'].get('deg'),
                'visibility_m': data.get('visibility', 10000),
                'cloudiness_percent': data['clouds']['all'],
                'weather_main': data['weather'][0]['main'],
                'weather_description': data['weather'][0]['description'],
                'weather_icon': data['weather'][0]['icon'],
                'weather_code': data['weather'][0]['id'],
                'precipitation_mm': data.get('rain', {}).get('1h', 0) or 0,
                'snow_mm': data.get('snow', {}).get('1h', 0) or 0,
            }

            # Compute ML features
            weather_data['is_precipitation'] = weather_data['precipitation_mm'] > 0 or weather_data['snow_mm'] > 0
            weather_data['is_severe_weather'] = self._is_severe_weather(
                weather_data['weather_code'],
                weather_data['wind_speed_mps'],
                weather_data['visibility_m']
            )
            weather_data['temperature_category'] = self._categorize_temperature(
                weather_data['temperature_c']
            )
            weather_data['comfort_index'] = self._compute_comfort_index(
                weather_data['temperature_c'],
                weather_data['humidity_percent'],
                weather_data['wind_speed_mps']
            )

            logger.info(f"Fetched weather: {weather_data['temperature_c']}C, {weather_data['weather_main']}")
            return weather_data

        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return None

    def fetch_weather_forecast(self, hours: int = 48) -> List[Dict]:
        """Fetch weather forecast"""
        if not self.api_key:
            return []

        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                'lat': ATLANTA_LAT,
                'lon': ATLANTA_LON,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': min(hours // 3, 40)  # API returns 3-hour intervals
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            forecasts = []
            for item in data.get('list', []):
                forecast = {
                    'forecast_timestamp': datetime.fromtimestamp(item['dt']),
                    'temperature_c': item['main']['temp'],
                    'feels_like_c': item['main']['feels_like'],
                    'precipitation_probability': item.get('pop', 0) * 100,
                    'precipitation_mm': item.get('rain', {}).get('3h', 0) or 0,
                    'weather_main': item['weather'][0]['main'],
                    'weather_description': item['weather'][0]['description'],
                    'wind_speed_mps': item['wind']['speed'],
                    'humidity_percent': item['main']['humidity'],
                    'cloudiness_percent': item['clouds']['all'],
                    'is_precipitation': item.get('rain', {}).get('3h', 0) > 0
                }
                forecasts.append(forecast)

            logger.info(f"Fetched {len(forecasts)} forecast entries")
            return forecasts

        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            return []

    def store_weather(self, weather_data: Dict) -> bool:
        """Store weather data in database"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO weather_data (
                        timestamp, location_lat, location_lon,
                        temperature_c, feels_like_c, temp_min_c, temp_max_c,
                        precipitation_mm, snow_mm,
                        humidity_percent, pressure_hpa,
                        wind_speed_mps, wind_gust_mps, wind_direction_deg,
                        visibility_m, cloudiness_percent,
                        weather_main, weather_description, weather_icon, weather_code,
                        is_precipitation, is_severe_weather, temperature_category, comfort_index
                    )
                    VALUES (
                        %(timestamp)s, %(location_lat)s, %(location_lon)s,
                        %(temperature_c)s, %(feels_like_c)s, %(temp_min_c)s, %(temp_max_c)s,
                        %(precipitation_mm)s, %(snow_mm)s,
                        %(humidity_percent)s, %(pressure_hpa)s,
                        %(wind_speed_mps)s, %(wind_gust_mps)s, %(wind_direction_deg)s,
                        %(visibility_m)s, %(cloudiness_percent)s,
                        %(weather_main)s, %(weather_description)s, %(weather_icon)s, %(weather_code)s,
                        %(is_precipitation)s, %(is_severe_weather)s, %(temperature_category)s, %(comfort_index)s
                    )
                    ON CONFLICT (timestamp, location_lat, location_lon) DO UPDATE SET
                        temperature_c = EXCLUDED.temperature_c,
                        weather_main = EXCLUDED.weather_main,
                        precipitation_mm = EXCLUDED.precipitation_mm
                """, weather_data)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error storing weather: {e}")
            conn.rollback()
            return False
        finally:
            self.db_pool.putconn(conn)

    def store_forecast(self, forecasts: List[Dict]) -> int:
        """Store forecast data"""
        if not forecasts:
            return 0

        conn = self.db_pool.getconn()
        stored = 0
        try:
            with conn.cursor() as cursor:
                for forecast in forecasts:
                    cursor.execute("""
                        INSERT INTO weather_forecast (
                            forecast_timestamp, temperature_c, feels_like_c,
                            precipitation_probability, precipitation_mm,
                            weather_main, weather_description,
                            wind_speed_mps, humidity_percent, cloudiness_percent,
                            is_precipitation
                        )
                        VALUES (
                            %(forecast_timestamp)s, %(temperature_c)s, %(feels_like_c)s,
                            %(precipitation_probability)s, %(precipitation_mm)s,
                            %(weather_main)s, %(weather_description)s,
                            %(wind_speed_mps)s, %(humidity_percent)s, %(cloudiness_percent)s,
                            %(is_precipitation)s
                        )
                        ON CONFLICT (forecast_timestamp) DO UPDATE SET
                            temperature_c = EXCLUDED.temperature_c,
                            weather_main = EXCLUDED.weather_main,
                            fetched_at = CURRENT_TIMESTAMP
                    """, forecast)
                    stored += 1
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing forecast: {e}")
            conn.rollback()
        finally:
            self.db_pool.putconn(conn)

        return stored

    def compute_transit_correlation(self, date: datetime = None) -> Dict:
        """Compute correlation between weather and transit patterns"""
        target_date = date or datetime.now().date()

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get weather-transit data correlation
                cursor.execute("""
                    WITH hourly_weather AS (
                        SELECT
                            DATE_TRUNC('hour', timestamp) as hour,
                            AVG(temperature_c) as avg_temp,
                            SUM(precipitation_mm) as total_precip,
                            MODE() WITHIN GROUP (ORDER BY weather_main) as main_weather
                        FROM weather_data
                        WHERE DATE(timestamp) = %s
                        GROUP BY DATE_TRUNC('hour', timestamp)
                    ),
                    hourly_transit AS (
                        SELECT
                            DATE_TRUNC('hour', timestamp) as hour,
                            COUNT(*) as trip_count,
                            AVG(arrival_delay) as avg_delay
                        FROM gtfs_trip_updates
                        WHERE DATE(timestamp) = %s
                        GROUP BY DATE_TRUNC('hour', timestamp)
                    )
                    SELECT
                        w.hour,
                        w.avg_temp,
                        w.total_precip,
                        w.main_weather,
                        t.trip_count,
                        t.avg_delay
                    FROM hourly_weather w
                    LEFT JOIN hourly_transit t ON w.hour = t.hour
                    ORDER BY w.hour
                """, (target_date, target_date))

                rows = cursor.fetchall()

                # Store correlations
                for row in rows:
                    if row[4] is not None:  # Has transit data
                        cursor.execute("""
                            INSERT INTO weather_transit_correlation
                            (date, hour, avg_temperature, precipitation_mm,
                             weather_main, avg_ridership, avg_delay_seconds)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (date, hour) DO UPDATE SET
                                avg_temperature = EXCLUDED.avg_temperature,
                                precipitation_mm = EXCLUDED.precipitation_mm,
                                avg_ridership = EXCLUDED.avg_ridership,
                                avg_delay_seconds = EXCLUDED.avg_delay_seconds
                        """, (
                            target_date,
                            row[0].hour if row[0] else None,
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            row[5]
                        ))

                conn.commit()

                return {
                    'date': str(target_date),
                    'hours_with_data': len([r for r in rows if r[4] is not None]),
                    'total_hours': len(rows)
                }
        finally:
            self.db_pool.putconn(conn)

    def get_weather_features_for_ml(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Get weather features formatted for ML training"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        timestamp,
                        temperature_c,
                        feels_like_c,
                        precipitation_mm,
                        humidity_percent,
                        wind_speed_mps,
                        cloudiness_percent,
                        is_precipitation::int,
                        is_severe_weather::int,
                        comfort_index,
                        CASE weather_main
                            WHEN 'Clear' THEN 0
                            WHEN 'Clouds' THEN 1
                            WHEN 'Rain' THEN 2
                            WHEN 'Snow' THEN 3
                            WHEN 'Thunderstorm' THEN 4
                            ELSE 5
                        END as weather_code_encoded
                    FROM weather_data
                    WHERE timestamp BETWEEN %s AND %s
                    ORDER BY timestamp
                """, (start_time, end_time))

                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            self.db_pool.putconn(conn)

    def run_ingestion(self) -> Dict:
        """Run complete weather ingestion"""
        results = {
            'current_weather': False,
            'forecast_count': 0,
            'correlation_computed': False
        }

        # Fetch and store current weather
        current = self.fetch_current_weather()
        if current:
            results['current_weather'] = self.store_weather(current)

        # Fetch and store forecast
        forecasts = self.fetch_weather_forecast(hours=48)
        results['forecast_count'] = self.store_forecast(forecasts)

        # Compute correlations
        try:
            self.compute_transit_correlation()
            results['correlation_computed'] = True
        except Exception as e:
            logger.error(f"Error computing correlation: {e}")

        return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    integration = WeatherIntegration()
    results = integration.run_ingestion()

    print(f"\nWeather Ingestion Results:")
    print(f"  Current weather stored: {results['current_weather']}")
    print(f"  Forecast entries stored: {results['forecast_count']}")
    print(f"  Correlation computed: {results['correlation_computed']}")
