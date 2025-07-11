import os
import logging
import requests
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import time
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# OpenWeatherMap API Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "YOUR_OPENWEATHER_API_KEY")
ATLANTA_LAT = 33.7490
ATLANTA_LON = -84.3880

# API Endpoints
CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
HISTORICAL_WEATHER_URL = "https://api.openweathermap.org/data/2.5/onecall/timemachine"

OUTPUT_CSV = "data/external/atlanta_weather_data.csv"
WEATHER_TABLE = "atlanta_weather_data"

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

CREATE_WEATHER_TABLE = f'''
CREATE TABLE IF NOT EXISTS {WEATHER_TABLE} (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    temperature_celsius NUMERIC,
    feels_like_celsius NUMERIC,
    humidity INTEGER,
    pressure_hpa NUMERIC,
    wind_speed_mps NUMERIC,
    wind_direction_degrees INTEGER,
    weather_condition TEXT,
    weather_description TEXT,
    precipitation_mm NUMERIC,
    visibility_meters INTEGER,
    cloudiness_percent INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

def create_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

def setup_weather_table(conn):
    with conn.cursor() as cursor:
        cursor.execute(CREATE_WEATHER_TABLE)
        conn.commit()
        logging.info(f"Ensured weather table {WEATHER_TABLE} exists.")

def fetch_current_weather():
    logging.info("Fetching current weather data")
    
    params = {
        'lat': ATLANTA_LAT,
        'lon': ATLANTA_LON,
        'appid': OPENWEATHER_API_KEY,
        'units': 'metric'
    }
    
    try:
        response = requests.get(CURRENT_WEATHER_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather_data = {
            'timestamp': datetime.fromtimestamp(data['dt']),
            'temperature_celsius': data['main']['temp'],
            'feels_like_celsius': data['main']['feels_like'],
            'humidity': data['main']['humidity'],
            'pressure_hpa': data['main']['pressure'],
            'wind_speed_mps': data['wind']['speed'],
            'wind_direction_degrees': data['wind'].get('deg'),
            'weather_condition': data['weather'][0]['main'],
            'weather_description': data['weather'][0]['description'],
            'precipitation_mm': data.get('rain', {}).get('1h', 0),
            'visibility_meters': data.get('visibility'),
            'cloudiness_percent': data['clouds']['all']
        }
        
        logging.info(f"Current weather: {weather_data['temperature_celsius']}°C, {weather_data['weather_condition']}")
        return weather_data
        
    except Exception as e:
        logging.error(f"Error fetching current weather: {e}")
        return None

def fetch_historical_weather(days_back=5):
    logging.info(f"Fetching historical weather data for last {days_back} days")
    
    historical_data = []
    
    for i in range(days_back):
        target_date = datetime.now() - timedelta(days=i+1)
        timestamp = int(target_date.timestamp())
        
        params = {
            'lat': ATLANTA_LAT,
            'lon': ATLANTA_LON,
            'dt': timestamp,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        
        try:
            response = requests.get(HISTORICAL_WEATHER_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process hourly data
            for hour_data in data.get('hourly', []):
                weather_data = {
                    'timestamp': datetime.fromtimestamp(hour_data['dt']),
                    'temperature_celsius': hour_data['temp'],
                    'feels_like_celsius': hour_data['feels_like'],
                    'humidity': hour_data['humidity'],
                    'pressure_hpa': hour_data['pressure'],
                    'wind_speed_mps': hour_data['wind_speed'],
                    'wind_direction_degrees': hour_data.get('wind_deg'),
                    'weather_condition': hour_data['weather'][0]['main'],
                    'weather_description': hour_data['weather'][0]['description'],
                    'precipitation_mm': hour_data.get('rain', {}).get('1h', 0),
                    'visibility_meters': hour_data.get('visibility'),
                    'cloudiness_percent': hour_data['clouds']
                }
                historical_data.append(weather_data)
            
            # Rate limiting
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error fetching historical weather for {target_date.date()}: {e}")
    
    logging.info(f"Fetched {len(historical_data)} historical weather records")
    return historical_data

def store_weather_data(conn, weather_data_list):
    if not weather_data_list:
        return
    
    with conn.cursor() as cursor:
        for weather_data in weather_data_list:
            cursor.execute(f'''
                INSERT INTO {WEATHER_TABLE} (
                    timestamp, temperature_celsius, feels_like_celsius, humidity, 
                    pressure_hpa, wind_speed_mps, wind_direction_degrees, 
                    weather_condition, weather_description, precipitation_mm, 
                    visibility_meters, cloudiness_percent
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp) DO UPDATE SET
                    temperature_celsius = EXCLUDED.temperature_celsius,
                    feels_like_celsius = EXCLUDED.feels_like_celsius,
                    humidity = EXCLUDED.humidity,
                    pressure_hpa = EXCLUDED.pressure_hpa,
                    wind_speed_mps = EXCLUDED.wind_speed_mps,
                    wind_direction_degrees = EXCLUDED.wind_direction_degrees,
                    weather_condition = EXCLUDED.weather_condition,
                    weather_description = EXCLUDED.weather_description,
                    precipitation_mm = EXCLUDED.precipitation_mm,
                    visibility_meters = EXCLUDED.visibility_meters,
                    cloudiness_percent = EXCLUDED.cloudiness_percent,
                    created_at = CURRENT_TIMESTAMP;
            ''', (
                weather_data['timestamp'],
                weather_data['temperature_celsius'],
                weather_data['feels_like_celsius'],
                weather_data['humidity'],
                weather_data['pressure_hpa'],
                weather_data['wind_speed_mps'],
                weather_data['wind_direction_degrees'],
                weather_data['weather_condition'],
                weather_data['weather_description'],
                weather_data['precipitation_mm'],
                weather_data['visibility_meters'],
                weather_data['cloudiness_percent']
            ))
        conn.commit()
        logging.info(f"Inserted/updated {len(weather_data_list)} weather records.")

def save_to_csv(weather_data_list):
    if not weather_data_list:
        return
    
    df = pd.DataFrame(weather_data_list)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    logging.info(f"Saved weather data to {OUTPUT_CSV}")

def main():
    logging.info("Starting weather data ingestion")
    
    # Fetch current weather
    current_weather = fetch_current_weather()
    
    # Fetch historical weather
    historical_weather = fetch_historical_weather(days_back=5)
    
    # Combine data
    all_weather_data = []
    if current_weather:
        all_weather_data.append(current_weather)
    all_weather_data.extend(historical_weather)
    
    if all_weather_data:
        # Store in database
        conn = create_db_connection()
        setup_weather_table(conn)
        store_weather_data(conn, all_weather_data)
        conn.close()
        
        # Save to CSV
        save_to_csv(all_weather_data)
        
        logging.info(f"Weather ingestion complete. Total records: {len(all_weather_data)}")
    else:
        logging.error("No weather data retrieved")

if __name__ == "__main__":
    main() 