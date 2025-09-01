"""
MARTA Data Collector for Supabase with Service Role Key
Uses service role key for write operations (more secure)
"""
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv('.env.supabase')

MARTA_API_KEY = os.environ.get('MARTA_API_KEY', '')
MARTA_API_URL = "https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata"

# For secure writes, we need the service role key
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')  # More privileged key

# If service key not available, fall back to anon key
if not SUPABASE_SERVICE_KEY:
    print("⚠️ Service role key not found, using anon key (may have limited write access)")
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_ANON_KEY', '')

def parse_delay(delay_str):
    """Parse delay string which might contain non-numeric values"""
    if not delay_str:
        return 0
    # Try to extract numeric value from string
    try:
        # Handle values like "T345S" by extracting just numbers
        import re
        numbers = re.findall(r'-?\d+', str(delay_str))
        if numbers:
            return int(numbers[0])
        return 0
    except:
        return 0

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

def collect_and_store():
    """Main collection function for Supabase with secure access"""
    print(f"\n🚇 MARTA Data Collection (Secure) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Initialize Supabase client with service role key
    try:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            print("\nTo get your service role key:")
            print("1. Go to: https://vglychbweuowsovboxyf.supabase.co/project/vglychbweuowsovboxyf/settings/api")
            print("2. Copy the 'service_role' key (not the anon key)")
            print("3. Add to .env.supabase as SUPABASE_SERVICE_KEY=your_key_here")
            return False
            
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Connected to Supabase with service role")
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False
    
    # Fetch current data
    print("🔄 Fetching real-time data from MARTA...")
    data = fetch_marta_data()
    
    if not data:
        print("❌ Failed to fetch data")
        return False
    
    print(f"✅ Received {len(data)} arrival records")
    
    # Store arrivals
    print("💾 Storing arrivals...")
    try:
        # Transform data for storage
        records = []
        for arrival in data:
            records.append({
                'station_id': arrival.get('STATION'),
                'line': arrival.get('LINE'),
                'destination': arrival.get('DESTINATION'),
                'direction': arrival.get('DIRECTION'),
                'arrival_time': arrival.get('NEXT_ARR'),
                'waiting_seconds': int(arrival.get('WAITING_SECONDS', 0)),
                'delay_seconds': parse_delay(arrival.get('DELAY', '0')),
                'train_id': arrival.get('TRAIN_ID'),
                'event_time': arrival.get('EVENT_TIME')
            })
        
        # Insert arrivals
        result = supabase.table('arrivals').insert(records).execute()
        print(f"✅ Stored {len(records)} arrivals in Supabase")
        
    except Exception as e:
        print(f"❌ Error storing arrivals: {e}")
        return False
    
    # Update stations
    print("📍 Updating stations...")
    try:
        stations = {}
        for arrival in data:
            station_id = arrival.get('STATION')
            if station_id not in stations:
                stations[station_id] = set()
            stations[station_id].add(arrival.get('LINE'))
        
        for station_id, lines in stations.items():
            try:
                supabase.table('stations').upsert({
                    'station_id': station_id,
                    'name': station_id,
                    'lines': list(lines)
                }, on_conflict='station_id').execute()
            except Exception as e:
                print(f"Error updating station {station_id}: {e}")
        
        print(f"✅ Updated {len(stations)} stations")
        
    except Exception as e:
        print(f"❌ Error updating stations: {e}")
    
    # Get current metrics
    try:
        result = supabase.from_('current_system_status').select('*').execute()
        if result.data and len(result.data) > 0:
            metrics = result.data[0]
            print(f"\n📊 System Metrics:")
            print(f"   Active stations: {metrics.get('active_stations', 0)}")
            print(f"   Active trains: {metrics.get('active_trains', 0)}")
            print(f"   Recent arrivals: {metrics.get('recent_arrivals', 0)}")
            avg_delay = metrics.get('avg_delay', 0)
            if avg_delay is not None:
                print(f"   Average delay: {float(avg_delay):.1f} seconds")
    except Exception as e:
        print(f"⚠️ Could not fetch metrics: {e}")
    
    return True

if __name__ == '__main__':
    # Can be run directly or via cron/GitHub Actions
    success = collect_and_store()
    exit(0 if success else 1)