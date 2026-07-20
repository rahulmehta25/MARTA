#!/usr/bin/env python3
"""Test Supabase connection using credentials from .env.supabase"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

# Load environment variables
load_dotenv('.env.supabase')

def test_connection():
    """Test Supabase connection and table existence"""
    
    # Get credentials from environment
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("❌ Missing Supabase credentials in .env.supabase")
        return False
    
    print(f"🔍 Testing connection to: {url}")
    
    try:
        # Create Supabase client
        supabase: Client = create_client(url, key)
        print("✅ Successfully connected to Supabase!")
        
        # Test tables
        tables = ['stations', 'arrivals', 'hourly_stats', 'system_metrics', 'predictions']
        
        for table in tables:
            try:
                # Try to query each table (limit 1 to be fast)
                result = supabase.table(table).select("*").limit(1).execute()
                print(f"✅ Table '{table}' exists and is accessible")
            except Exception as e:
                error_msg = str(e)
                if 'relation' in error_msg and 'does not exist' in error_msg:
                    print(f"❌ Table '{table}' does not exist - need to run SQL schema")
                else:
                    print(f"⚠️ Table '{table}' error: {error_msg}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)