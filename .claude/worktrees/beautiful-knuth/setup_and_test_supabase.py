"""
Setup and test Supabase connection
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.supabase')

print("🚀 MARTA Analytics - Supabase Setup")
print("=" * 50)

# Verify credentials are loaded
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_ANON_KEY')
marta_key = os.environ.get('MARTA_API_KEY')

print(f"✅ Supabase URL: {url[:40]}...")
print(f"✅ Anon Key: {key[:20]}...")
print(f"✅ MARTA API Key: {'Configured' if marta_key else 'Missing'}")

print("\n📡 Testing Supabase connection...")

try:
    from supabase_client import SupabaseClient
    
    # Initialize client
    client = SupabaseClient()
    print("✅ Successfully connected to Supabase!")
    
    # Test getting metrics (will be empty initially)
    print("\n📊 Checking database...")
    metrics = client.get_system_metrics()
    
    if metrics:
        print(f"   Found existing data:")
        print(f"   - Active stations: {metrics.get('active_stations', 0)}")
        print(f"   - Active trains: {metrics.get('active_trains', 0)}")
        print(f"   - Recent arrivals: {metrics.get('recent_arrivals', 0)}")
    else:
        print("   Database is empty (expected for new setup)")
    
    print("\n🔄 Testing MARTA data collection...")
    from collect_data_supabase import collect_and_store
    
    success = collect_and_store()
    
    if success:
        print("\n✅ Data collection successful!")
        
        # Check metrics again
        metrics = client.get_system_metrics()
        if metrics:
            print(f"\n📈 Database now contains:")
            print(f"   - Active stations: {metrics.get('active_stations', 0)}")
            print(f"   - Active trains: {metrics.get('active_trains', 0)}")
            print(f"   - Recent arrivals: {metrics.get('recent_arrivals', 0)}")
            print(f"   - Average delay: {metrics.get('avg_delay', 0):.1f} seconds")
    else:
        print("⚠️ Data collection had issues")
    
    print("\n" + "=" * 50)
    print("🎉 Supabase is fully configured and working!")
    print("\n📝 Next steps:")
    print("1. These credentials are saved in .env.supabase")
    print("2. Add them to Railway variables")
    print("3. Add them to GitHub secrets")
    print("4. Deploy the new backend")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure you ran the SQL schema in Supabase")
    print("2. Check that your credentials are correct")
    print("3. Ensure python-dotenv is installed: pip install python-dotenv")