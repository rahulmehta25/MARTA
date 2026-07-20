"""
MARTA Data Collector - Fetches and stores real-time data
Designed to run as a scheduled job (cron or GitHub Actions)
"""
import os
import httpx
import json
from datetime import datetime
from database import (
    init_database, 
    insert_arrival, 
    cleanup_old_data,
    get_database_size,
    get_db
)

MARTA_API_KEY = os.environ.get('MARTA_API_KEY', '')
MARTA_API_URL = "https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata"

def fetch_marta_data():
    """Fetch current data from MARTA API"""
    if not MARTA_API_KEY:
        print("❌ No MARTA API key configured")
        return None
    
    try:
        url = f"{MARTA_API_URL}?apiKey={MARTA_API_KEY}"
        
        with httpx.Client(verify=False, timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"❌ Error fetching MARTA data: {e}")
        return None

def store_stations(arrivals_data):
    """Extract and store unique stations"""
    stations = {}
    
    for arrival in arrivals_data:
        station = arrival.get('STATION')
        if station and station not in stations:
            stations[station] = {
                'name': station,
                'lines': set()
            }
        if station:
            line = arrival.get('LINE')
            if line:
                stations[station]['lines'].add(line)
    
    # Store in database
    with get_db() as conn:
        cursor = conn.cursor()
        for station_id, data in stations.items():
            cursor.execute('''
                INSERT OR REPLACE INTO stations (station_id, name, lines)
                VALUES (?, ?, ?)
            ''', (
                station_id,
                data['name'],
                json.dumps(list(data['lines']))
            ))
        conn.commit()
    
    return len(stations)

def collect_and_store():
    """Main collection function"""
    print(f"\n🚇 MARTA Data Collection - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Initialize database if needed
    init_database()
    
    # Check database size
    db_size = get_database_size()
    print(f"📊 Database size: {db_size['size_mb']} MB")
    
    if db_size['warning']:
        print("⚠️ Database approaching 1GB limit, cleaning old data...")
        cleanup_old_data(days_to_keep=5)  # Keep less data if approaching limit
    
    # Fetch current data
    print("🔄 Fetching real-time data from MARTA...")
    data = fetch_marta_data()
    
    if not data:
        print("❌ Failed to fetch data")
        return False
    
    print(f"✅ Received {len(data)} arrival records")
    
    # Store stations
    station_count = store_stations(data)
    print(f"📍 Updated {station_count} stations")
    
    # Store arrivals
    stored_count = 0
    error_count = 0
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for arrival in data:
            try:
                # Transform MARTA format to our format
                cursor.execute('''
                    INSERT INTO arrivals (
                        station_id, line, destination, direction,
                        arrival_time, waiting_seconds, delay_seconds, train_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    arrival.get('STATION'),
                    arrival.get('LINE'),
                    arrival.get('DESTINATION'),
                    arrival.get('DIRECTION'),
                    arrival.get('NEXT_ARR'),
                    int(arrival.get('WAITING_SECONDS', 0)),
                    parse_delay(arrival.get('DELAY', '0')),
                    arrival.get('TRAIN_ID')
                ))
                stored_count += 1
            except Exception as e:
                error_count += 1
                if error_count <= 3:  # Only show first 3 errors
                    print(f"⚠️ Error storing arrival: {e}")
        
        conn.commit()
    
    print(f"💾 Stored {stored_count} arrivals ({error_count} errors)")
    
    # Clean old data periodically
    if datetime.now().hour == 3:  # Run cleanup at 3 AM
        print("🧹 Running daily cleanup...")
        cleanup_old_data()
    
    # Show current database stats
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM arrivals')
        total_records = cursor.fetchone()['count']
        
        cursor.execute('''
            SELECT COUNT(DISTINCT DATE(collected_at)) as days 
            FROM arrivals
        ''')
        days_of_data = cursor.fetchone()['days']
    
    print(f"\n📈 Database Stats:")
    print(f"   Total records: {total_records:,}")
    print(f"   Days of data: {days_of_data}")
    print(f"   Database size: {get_database_size()['size_mb']} MB")
    
    return True

def parse_delay(delay_str):
    """Parse delay string to integer seconds"""
    if not delay_str:
        return 0
    if delay_str == '0 Seconds':
        return 0
    if delay_str.startswith('T') and delay_str.endswith('S'):
        try:
            return int(delay_str[1:-1])
        except:
            return 0
    return 0

if __name__ == '__main__':
    # Can be run directly or via cron/GitHub Actions
    success = collect_and_store()
    exit(0 if success else 1)