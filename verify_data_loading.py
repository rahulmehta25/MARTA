#!/usr/bin/env python3
"""
Data Loading Verification Script
Checks if GTFS static data was successfully loaded into the database
"""
import os
import sys
import psycopg2
import pandas as pd
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from config.settings import settings
except ImportError:
    # Fallback for direct execution
    import os
    settings = type('Settings', (), {
        'DB_HOST': os.getenv('DB_HOST', 'localhost'),
        'DB_NAME': os.getenv('DB_NAME', 'marta_db'),
        'DB_USER': os.getenv('DB_USER', 'marta_user'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD', 'marta_password'),
        'DB_PORT': os.getenv('DB_PORT', 5432),
    })()

def create_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            port=settings.DB_PORT
        )
        print("✅ Database connection established successfully")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None

def check_table_exists(conn, table_name):
    """Check if a table exists in the database"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table_name,))
            exists = cursor.fetchone()[0]
            return exists
    except Exception as e:
        print(f"❌ Error checking if table {table_name} exists: {e}")
        return False

def get_table_row_count(conn, table_name):
    """Get the number of rows in a table"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            return count
    except Exception as e:
        print(f"❌ Error getting row count for {table_name}: {e}")
        return 0

def get_table_sample(conn, table_name, limit=5):
    """Get a sample of rows from a table"""
    try:
        query = f"SELECT * FROM {table_name} LIMIT {limit};"
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        print(f"❌ Error getting sample from {table_name}: {e}")
        return None

def verify_gtfs_tables():
    """Verify that all GTFS tables exist and have data"""
    print("🔍 Verifying GTFS data loading...")
    print("=" * 50)
    
    conn = create_db_connection()
    if not conn:
        return False
    
    # GTFS tables to check
    gtfs_tables = [
        "gtfs_stops",
        "gtfs_routes", 
        "gtfs_trips",
        "gtfs_stop_times",
        "gtfs_calendar",
        "gtfs_shapes"
    ]
    
    verification_results = {}
    
    for table_name in gtfs_tables:
        print(f"\n📊 Checking table: {table_name}")
        
        # Check if table exists
        exists = check_table_exists(conn, table_name)
        if not exists:
            print(f"   ❌ Table {table_name} does not exist")
            verification_results[table_name] = {"exists": False, "row_count": 0}
            continue
        
        print(f"   ✅ Table {table_name} exists")
        
        # Get row count
        row_count = get_table_row_count(conn, table_name)
        print(f"   📈 Row count: {row_count:,}")
        
        # Get sample data
        sample_df = get_table_sample(conn, table_name, limit=3)
        if sample_df is not None and not sample_df.empty:
            print(f"   📋 Sample columns: {list(sample_df.columns)}")
            print(f"   📋 Sample data:")
            for idx, row in sample_df.iterrows():
                # Show first few columns to avoid overwhelming output
                sample_data = dict(row.head(3))
                print(f"      Row {idx}: {sample_data}")
        else:
            print(f"   ⚠️  No sample data available")
        
        verification_results[table_name] = {"exists": True, "row_count": row_count}
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 50)
    
    total_tables = len(gtfs_tables)
    existing_tables = sum(1 for result in verification_results.values() if result["exists"])
    total_rows = sum(result["row_count"] for result in verification_results.values())
    
    print(f"✅ Tables existing: {existing_tables}/{total_tables}")
    print(f"📊 Total rows loaded: {total_rows:,}")
    
    if existing_tables == total_tables:
        print("🎉 All GTFS tables are present!")
        
        # Check if we have reasonable data volumes
        if verification_results["gtfs_stops"]["row_count"] > 0:
            print("✅ Stops data loaded")
        if verification_results["gtfs_routes"]["row_count"] > 0:
            print("✅ Routes data loaded")
        if verification_results["gtfs_trips"]["row_count"] > 0:
            print("✅ Trips data loaded")
        if verification_results["gtfs_stop_times"]["row_count"] > 0:
            print("✅ Stop times data loaded")
        if verification_results["gtfs_calendar"]["row_count"] > 0:
            print("✅ Calendar data loaded")
        if verification_results["gtfs_shapes"]["row_count"] > 0:
            print("✅ Shapes data loaded")
            
        print(f"\n🎯 Data loading appears to be successful!")
        return True
    else:
        print("❌ Some tables are missing or empty")
        return False
    
    conn.close()

def check_data_quality():
    """Perform basic data quality checks"""
    print("\n🔍 Performing data quality checks...")
    print("=" * 50)
    
    conn = create_db_connection()
    if not conn:
        return
    
    try:
        # Check for null values in critical columns
        quality_checks = [
            ("gtfs_stops", "stop_id", "Missing stop IDs"),
            ("gtfs_stops", "stop_lat", "Missing stop latitudes"),
            ("gtfs_stops", "stop_lon", "Missing stop longitudes"),
            ("gtfs_routes", "route_id", "Missing route IDs"),
            ("gtfs_trips", "trip_id", "Missing trip IDs"),
            ("gtfs_stop_times", "trip_id", "Missing trip IDs in stop times"),
            ("gtfs_stop_times", "stop_id", "Missing stop IDs in stop times"),
        ]
        
        for table, column, description in quality_checks:
            if check_table_exists(conn, table):
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL;")
                    null_count = cursor.fetchone()[0]
                    total_count = get_table_row_count(conn, table)
                    if total_count > 0:
                        null_percentage = (null_count / total_count) * 100
                        print(f"📊 {description}: {null_count:,} nulls ({null_percentage:.1f}%)")
                    else:
                        print(f"📊 {description}: Table is empty")
        
        # Check for duplicate primary keys
        duplicate_checks = [
            ("gtfs_stops", "stop_id"),
            ("gtfs_routes", "route_id"),
            ("gtfs_trips", "trip_id"),
        ]
        
        for table, column in duplicate_checks:
            if check_table_exists(conn, table):
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM (
                            SELECT {column}, COUNT(*) 
                            FROM {table} 
                            GROUP BY {column} 
                            HAVING COUNT(*) > 1
                        ) AS duplicates;
                    """)
                    duplicate_count = cursor.fetchone()[0]
                    print(f"📊 Duplicate {column}s in {table}: {duplicate_count}")
        
    except Exception as e:
        print(f"❌ Error during data quality checks: {e}")
    
    conn.close()

if __name__ == "__main__":
    print("🚀 MARTA GTFS Data Loading Verification")
    print("=" * 50)
    print(f"⏰ Verification started at: {datetime.now()}")
    
    # Verify tables and data
    success = verify_gtfs_tables()
    
    # Perform quality checks if data exists
    if success:
        check_data_quality()
    
    print(f"\n⏰ Verification completed at: {datetime.now()}")
    
    if success:
        print("\n🎉 Data loading verification completed successfully!")
        print("You can now proceed with the next steps in your MARTA platform.")
    else:
        print("\n❌ Data loading verification failed.")
        print("Please check the GTFS ingestion process and try again.") 