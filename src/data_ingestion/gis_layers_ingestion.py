import os
import logging
import requests
import fiona
import psycopg2
from shapely.geometry import shape, mapping
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# GIS Data Sources
GIS_SOURCES = {
    'marta_rail_stations': {
        'url': 'https://opendata.atlantaregional.com/datasets/marta-rail-stations/geoservice',
        'format': 'geojson',
        'table_name': 'marta_rail_stations'
    },
    'marta_bus_stops': {
        'url': 'https://opendata.atlantaregional.com/datasets/marta-bus-stops/geoservice',
        'format': 'geojson', 
        'table_name': 'marta_bus_stops'
    }
}

OUTPUT_DIR = "data/gis"
GIS_TABLE = "marta_gis_layers"

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

CREATE_GIS_TABLE = f'''
CREATE TABLE IF NOT EXISTS {GIS_TABLE} (
    id SERIAL PRIMARY KEY,
    layer_name TEXT,
    feature_id TEXT,
    feature_name TEXT,
    feature_type TEXT,
    properties JSONB,
    geom GEOMETRY(GEOMETRY, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

def create_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

def setup_gis_table(conn):
    with conn.cursor() as cursor:
        cursor.execute(CREATE_GIS_TABLE)
        conn.commit()
        logging.info(f"Ensured GIS table {GIS_TABLE} exists.")

def download_geojson(url, layer_name):
    logging.info(f"Downloading GeoJSON for {layer_name} from {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    # Save raw GeoJSON
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"{layer_name}.geojson")
    with open(output_file, 'w') as f:
        f.write(response.text)
    
    logging.info(f"Saved GeoJSON to {output_file}")
    return response.json()

def process_geojson_features(geojson_data, layer_name):
    features = []
    for feature in geojson_data.get('features', []):
        geom = shape(feature['geometry'])
        props = feature.get('properties', {})
        
        # Extract common properties
        feature_id = props.get('OBJECTID') or props.get('id') or props.get('station_id')
        feature_name = props.get('STATION_NAME') or props.get('name') or props.get('stop_name')
        feature_type = props.get('TYPE') or props.get('feature_type') or layer_name
        
        features.append({
            'layer_name': layer_name,
            'feature_id': str(feature_id),
            'feature_name': feature_name,
            'feature_type': feature_type,
            'properties': json.dumps(props),
            'geom': geom.wkt
        })
    
    return features

def store_gis_features(conn, features):
    if not features:
        return
    
    with conn.cursor() as cursor:
        for feature in features:
            cursor.execute(f'''
                INSERT INTO {GIS_TABLE} (layer_name, feature_id, feature_name, feature_type, properties, geom)
                VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))
                ON CONFLICT (layer_name, feature_id) DO UPDATE SET
                    feature_name = EXCLUDED.feature_name,
                    feature_type = EXCLUDED.feature_type,
                    properties = EXCLUDED.properties,
                    geom = EXCLUDED.geom,
                    created_at = CURRENT_TIMESTAMP;
            ''', (
                feature['layer_name'],
                feature['feature_id'],
                feature['feature_name'],
                feature['feature_type'],
                feature['properties'],
                feature['geom']
            ))
        conn.commit()
        logging.info(f"Inserted/updated {len(features)} GIS features.")

def ingest_gis_layer(source_name, source_config):
    logging.info(f"Starting GIS ingestion for {source_name}")
    
    try:
        # Download GeoJSON
        geojson_data = download_geojson(source_config['url'], source_name)
        
        # Process features
        features = process_geojson_features(geojson_data, source_name)
        
        # Store in database
        conn = create_db_connection()
        setup_gis_table(conn)
        store_gis_features(conn, features)
        conn.close()
        
        logging.info(f"Successfully ingested {len(features)} features for {source_name}")
        return len(features)
        
    except Exception as e:
        logging.error(f"Error ingesting GIS layer {source_name}: {e}")
        return 0

def main():
    logging.info("Starting GIS layers ingestion")
    
    total_features = 0
    for source_name, source_config in GIS_SOURCES.items():
        features_count = ingest_gis_layer(source_name, source_config)
        total_features += features_count
    
    logging.info(f"GIS ingestion complete. Total features processed: {total_features}")

if __name__ == "__main__":
    main() 