"""
MARTA Data Collector for Supabase
Fetches real-time data and stores in Supabase
"""
import os
import httpx
from datetime import datetime
from supabase_client import SupabaseClient

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

def collect_and_store():
    """Main collection function for Supabase"""
    print(f"\n🚇 MARTA Data Collection (Supabase) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Initialize Supabase client
    try:
        supabase = SupabaseClient()
        print("✅ Connected to Supabase")
    except ValueError as e:
        print(f"❌ Supabase connection failed: {e}")
        return False
    
    # Fetch current data
    print("🔄 Fetching real-time data from MARTA...")
    data = fetch_marta_data()
    
    if not data:
        print("❌ Failed to fetch data")
        return False
    
    print(f"✅ Received {len(data)} arrival records")
    
    # Update stations
    print("📍 Updating stations...")
    stations_updated = supabase.update_stations(data)
    if stations_updated:
        print("✅ Stations updated")
    
    # Store arrivals
    print("💾 Storing arrivals...")
    arrivals_stored = supabase.insert_arrivals(data)
    
    if arrivals_stored:
        print(f"✅ Stored {len(data)} arrivals in Supabase")
    else:
        print("⚠️ Some arrivals may not have been stored")
    
    # Get current metrics
    metrics = supabase.get_system_metrics()
    if metrics:
        print(f"\n📊 System Metrics:")
        print(f"   Active stations: {metrics.get('active_stations', 0)}")
        print(f"   Active trains: {metrics.get('active_trains', 0)}")
        print(f"   Recent arrivals: {metrics.get('recent_arrivals', 0)}")
        avg_delay = metrics.get('avg_delay', 0)
        if avg_delay is not None:
            print(f"   Average delay: {avg_delay:.1f} seconds")
        else:
            print(f"   Average delay: 0.0 seconds")
    
    # Clean old data periodically (once per day)
    if datetime.now().hour == 3:
        print("🧹 Running daily cleanup...")
        supabase.cleanup_old_data(days_to_keep=30)
    
    return True

if __name__ == '__main__':
    # Can be run directly or via cron/GitHub Actions
    success = collect_and_store()
    exit(0 if success else 1)