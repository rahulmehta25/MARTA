import os
import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import psycopg2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

KPI_URL = "https://itsmarta.com/KPIRidership.aspx"
OUTPUT_CSV = "data/external/marta_ridership_kpi.csv"
RIDERSHIP_TABLE = "marta_ridership_kpi"

# Database connection details (set as environment variables)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

CREATE_RIDERSHIP_TABLE = f'''
CREATE TABLE IF NOT EXISTS {RIDERSHIP_TABLE} (
    report_month TEXT,
    bus_ridership BIGINT,
    rail_ridership BIGINT,
    mobility_ridership BIGINT,
    total_ridership BIGINT
);
'''

def create_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

def setup_table(conn):
    with conn.cursor() as cursor:
        cursor.execute(CREATE_RIDERSHIP_TABLE)
        conn.commit()
        logging.info("Ensured ridership KPI table exists.")

def scrape_kpi_table():
    logging.info(f"Fetching KPI page: {KPI_URL}")
    response = requests.get(KPI_URL, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    # Find all tables on the page
    tables = pd.read_html(response.text)
    # Heuristic: Find the table with 'Bus', 'Rail', 'Mobility', 'Total' columns
    for table in tables:
        cols = [c.lower() for c in table.columns.astype(str)]
        if any('bus' in c for c in cols) and any('rail' in c for c in cols) and any('total' in c for c in cols):
            df = table
            break
    else:
        raise ValueError("Could not find ridership table on KPI page.")
    # Clean up column names
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    # Standardize column names
    rename_map = {
        'month': 'report_month',
        'bus': 'bus_ridership',
        'rail': 'rail_ridership',
        'mobility': 'mobility_ridership',
        'total': 'total_ridership'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    # Keep only relevant columns
    keep_cols = ['report_month', 'bus_ridership', 'rail_ridership', 'mobility_ridership', 'total_ridership']
    df = df[[c for c in keep_cols if c in df.columns]]
    # Drop rows with missing month or total
    df = df.dropna(subset=['report_month', 'total_ridership'])
    # Save to CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    logging.info(f"Saved ridership KPI data to {OUTPUT_CSV}")
    return df

def store_to_db(df):
    conn = create_db_connection()
    setup_table(conn)
    with conn.cursor() as cursor:
        for _, row in df.iterrows():
            cursor.execute(f'''
                INSERT INTO {RIDERSHIP_TABLE} (report_month, bus_ridership, rail_ridership, mobility_ridership, total_ridership)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (report_month) DO UPDATE SET
                    bus_ridership=EXCLUDED.bus_ridership,
                    rail_ridership=EXCLUDED.rail_ridership,
                    mobility_ridership=EXCLUDED.mobility_ridership,
                    total_ridership=EXCLUDED.total_ridership;
            ''', (
                row.get('report_month'),
                int(row.get('bus_ridership', 0) or 0),
                int(row.get('rail_ridership', 0) or 0),
                int(row.get('mobility_ridership', 0) or 0),
                int(row.get('total_ridership', 0) or 0)
            ))
        conn.commit()
        logging.info(f"Inserted/updated {len(df)} rows in {RIDERSHIP_TABLE}.")
    conn.close()

def main():
    try:
        df = scrape_kpi_table()
        store_to_db(df)
        logging.info("Ridership KPI ingestion complete.")
    except Exception as e:
        logging.error(f"Error in ridership KPI ingestion: {e}")

if __name__ == "__main__":
    main() 