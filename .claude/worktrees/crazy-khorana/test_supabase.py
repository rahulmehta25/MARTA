"""
Quick test script to verify Supabase connection
"""
import os
import sys

# Prompt for credentials
print("🔐 Enter your Supabase credentials:")
print("(You can find these in Settings → API in your Supabase dashboard)\n")

url = input("Project URL (https://xxxxx.supabase.co): ").strip()
key = input("Anon/Public key (eyJ...): ").strip()

# Set environment variables
os.environ['SUPABASE_URL'] = url
os.environ['SUPABASE_ANON_KEY'] = key
os.environ['MARTA_API_KEY'] = 'ff98ada7-0436-42c5-b9bf-1071245ad1a0'

print("\n📡 Testing Supabase connection...")

try:
    from supabase_client import SupabaseClient
    
    # Initialize client
    client = SupabaseClient()
    print("✅ Connected to Supabase!")
    
    # Test getting metrics (will be empty initially)
    metrics = client.get_system_metrics()
    print(f"📊 System metrics: {metrics if metrics else 'No data yet'}")
    
    # Test getting recent arrivals (will be empty initially)
    arrivals = client.get_recent_arrivals(limit=5)
    print(f"🚇 Recent arrivals: {len(arrivals)} records")
    
    print("\n✨ Supabase is ready! Now let's collect some data...")
    
    # Ask if user wants to run data collection
    collect = input("\nRun data collection now? (y/n): ").strip().lower()
    
    if collect == 'y':
        print("\n🔄 Collecting MARTA data...")
        from collect_data_supabase import collect_and_store
        success = collect_and_store()
        
        if success:
            print("✅ Data collection successful!")
            
            # Check metrics again
            metrics = client.get_system_metrics()
            if metrics:
                print(f"\n📈 Updated metrics:")
                print(f"   Active stations: {metrics.get('active_stations', 0)}")
                print(f"   Active trains: {metrics.get('active_trains', 0)}")
                print(f"   Recent arrivals: {metrics.get('recent_arrivals', 0)}")
        else:
            print("❌ Data collection failed")
    
    print("\n🎉 Everything is working! Your credentials are:")
    print(f"SUPABASE_URL={url}")
    print(f"SUPABASE_ANON_KEY={key}")
    print("\nSave these for Railway and GitHub Actions!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease check your credentials and try again.")