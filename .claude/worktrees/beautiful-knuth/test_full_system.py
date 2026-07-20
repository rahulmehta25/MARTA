#!/usr/bin/env python3
"""
Full system test for MARTA Analytics Platform
Tests all components: API, Database, Collection
"""

import os
import sys
import httpx
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment
load_dotenv('.env.supabase')

def test_supabase_connection():
    """Test Supabase database connection"""
    print("\n1. Testing Supabase Connection...")
    try:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            print("❌ Missing Supabase credentials")
            return False
        
        supabase: Client = create_client(url, key)
        
        # Test reading from arrivals
        result = supabase.table('arrivals').select('*').limit(5).execute()
        count = len(result.data) if result.data else 0
        print(f"✅ Supabase connected - Found {count} recent arrivals")
        return True
        
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return False

def test_railway_api():
    """Test Railway backend API"""
    print("\n2. Testing Railway Backend...")
    try:
        response = httpx.get(
            'https://marta-production.up.railway.app/',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Railway API active - {data.get('message', 'Connected')}")
            return True
        else:
            print(f"⚠️ Railway API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️ Railway API not accessible: {e}")
        return False

def test_marta_api():
    """Test MARTA API directly"""
    print("\n3. Testing MARTA API...")
    try:
        api_key = os.getenv('MARTA_API_KEY')
        if not api_key:
            print("❌ No MARTA API key")
            return False
        
        url = f"https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata?apiKey={api_key}"
        
        with httpx.Client(verify=False, timeout=30) as client:
            response = client.get(url)
            data = response.json()
            print(f"✅ MARTA API working - {len(data)} arrivals fetched")
            return True
            
    except Exception as e:
        print(f"❌ MARTA API error: {e}")
        return False

def test_data_collection():
    """Test data collection to Supabase"""
    print("\n4. Testing Data Collection...")
    try:
        # Import and run collection
        from collect_data_secure import collect_and_store
        success = collect_and_store()
        
        if success:
            print("✅ Data collection successful")
            return True
        else:
            print("❌ Data collection failed")
            return False
            
    except Exception as e:
        print(f"❌ Collection error: {e}")
        return False

def test_frontend():
    """Test frontend availability"""
    print("\n5. Testing Frontend...")
    try:
        response = httpx.get('https://marta-eta.vercel.app', timeout=10)
        if response.status_code == 200:
            print("✅ Frontend accessible on Vercel")
            return True
        else:
            print(f"⚠️ Frontend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️ Frontend check failed: {e}")
        return False

def main():
    """Run all system tests"""
    print("=" * 60)
    print("🚇 MARTA Analytics Platform - System Test")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {
        'Supabase': test_supabase_connection(),
        'Railway API': test_railway_api(),
        'MARTA API': test_marta_api(),
        'Data Collection': test_data_collection(),
        'Frontend': test_frontend()
    }
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("-" * 60)
    
    all_passed = True
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {component:20} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All systems operational!")
        print("\nNext steps:")
        print("1. Add GitHub secrets for automated collection")
        print("2. Deploy Edge Functions (optional)")
        print("3. Update frontend API endpoint (optional)")
    else:
        print("\n⚠️ Some components need attention")
        print("\nTroubleshooting:")
        print("1. Check .env.supabase has all credentials")
        print("2. Verify RLS policies allow writes")
        print("3. Ensure services are deployed")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())