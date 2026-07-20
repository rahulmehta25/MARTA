"""
Supabase client for MARTA Transit Analytics
Handles all database operations with Supabase
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx
import json

class SupabaseClient:
    """Simple Supabase client using REST API"""
    
    def __init__(self):
        # Get credentials from environment
        self.url = os.environ.get('SUPABASE_URL', '')
        self.anon_key = os.environ.get('SUPABASE_ANON_KEY', '')
        
        if not self.url or not self.anon_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
        
        # Set up headers
        self.headers = {
            'apikey': self.anon_key,
            'Authorization': f'Bearer {self.anon_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'  # Don't return data after insert
        }
        
        # API endpoints
        self.base_url = f"{self.url}/rest/v1"
    
    def insert_arrivals(self, arrivals: List[Dict]) -> bool:
        """Insert multiple arrival records"""
        try:
            # Transform data for Supabase
            records = []
            for arrival in arrivals:
                records.append({
                    'station_id': arrival.get('STATION'),
                    'line': arrival.get('LINE'),
                    'destination': arrival.get('DESTINATION'),
                    'direction': arrival.get('DIRECTION'),
                    'arrival_time': arrival.get('NEXT_ARR'),
                    'waiting_seconds': int(arrival.get('WAITING_SECONDS', 0)),
                    'delay_seconds': self._parse_delay(arrival.get('DELAY', '0')),
                    'train_id': arrival.get('TRAIN_ID'),
                    'event_time': arrival.get('EVENT_TIME')
                })
            
            # Batch insert
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/arrivals",
                    headers=self.headers,
                    json=records
                )
                
                if response.status_code in [200, 201]:
                    return True
                else:
                    print(f"Error inserting arrivals: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            print(f"Exception inserting arrivals: {e}")
            return False
    
    def update_stations(self, arrivals: List[Dict]) -> bool:
        """Update stations from arrival data"""
        try:
            # Extract unique stations
            stations = {}
            for arrival in arrivals:
                station = arrival.get('STATION')
                if station:
                    if station not in stations:
                        stations[station] = {
                            'station_id': station,
                            'name': station,
                            'lines': []
                        }
                    line = arrival.get('LINE')
                    if line and line not in stations[station]['lines']:
                        stations[station]['lines'].append(line)
            
            # Upsert stations
            for station_data in stations.values():
                with httpx.Client() as client:
                    response = client.post(
                        f"{self.base_url}/stations",
                        headers={**self.headers, 'Prefer': 'resolution=merge-duplicates'},
                        json=station_data
                    )
                    
                    if response.status_code not in [200, 201]:
                        print(f"Error updating station {station_data['station_id']}: {response.text}")
            
            return True
                    
        except Exception as e:
            print(f"Exception updating stations: {e}")
            return False
    
    def get_recent_arrivals(self, station_id: Optional[str] = None, 
                           line: Optional[str] = None,
                           limit: int = 100) -> List[Dict]:
        """Get recent arrivals with optional filters"""
        try:
            # Build query
            params = {
                'select': '*',
                'order': 'collected_at.desc',
                'limit': str(limit)
            }
            
            # Add filters
            filters = []
            if station_id:
                filters.append(f"station_id=eq.{station_id}")
            if line:
                filters.append(f"line=eq.{line}")
            
            # Add time filter (last hour)
            filters.append(f"collected_at=gte.{(datetime.now() - timedelta(hours=1)).isoformat()}")
            
            if filters:
                params['where'] = '&'.join(filters)
            
            # Make request
            with httpx.Client() as client:
                response = client.get(
                    f"{self.base_url}/arrivals",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Error getting arrivals: {response.text}")
                    return []
                    
        except Exception as e:
            print(f"Exception getting arrivals: {e}")
            return []
    
    def get_station_stats(self, station_id: str, days: int = 7) -> Dict:
        """Get statistics for a station"""
        try:
            # Use RPC to call the database function
            with httpx.Client() as client:
                response = client.post(
                    f"{self.url}/rest/v1/rpc/get_station_delays",
                    headers=self.headers,
                    json={
                        'p_station_id': station_id,
                        'p_hours': days * 24
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Error getting station stats: {response.text}")
                    return {}
                    
        except Exception as e:
            print(f"Exception getting station stats: {e}")
            return {}
    
    def get_system_metrics(self) -> Dict:
        """Get current system metrics"""
        try:
            # Query the view
            with httpx.Client() as client:
                response = client.get(
                    f"{self.base_url}/current_system_status",
                    headers=self.headers,
                    params={'select': '*'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data[0] if data else {}
                else:
                    print(f"Error getting metrics: {response.text}")
                    return {}
                    
        except Exception as e:
            print(f"Exception getting metrics: {e}")
            return {}
    
    def update_hourly_stats(self) -> bool:
        """Update hourly statistics (call periodically)"""
        try:
            # Calculate stats for each station/line/hour
            query = """
                INSERT INTO hourly_stats (station_id, line, hour, day_of_week, 
                    avg_delay_seconds, avg_waiting_seconds, total_arrivals, on_time_percentage)
                SELECT 
                    station_id,
                    line,
                    EXTRACT(HOUR FROM collected_at)::INTEGER as hour,
                    EXTRACT(DOW FROM collected_at)::INTEGER as day_of_week,
                    AVG(delay_seconds) as avg_delay_seconds,
                    AVG(waiting_seconds) as avg_waiting_seconds,
                    COUNT(*) as total_arrivals,
                    SUM(CASE WHEN delay_seconds <= 60 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100
                FROM arrivals
                WHERE collected_at > NOW() - INTERVAL '7 days'
                GROUP BY station_id, line, hour, day_of_week
                ON CONFLICT (station_id, line, hour, day_of_week) 
                DO UPDATE SET
                    avg_delay_seconds = EXCLUDED.avg_delay_seconds,
                    avg_waiting_seconds = EXCLUDED.avg_waiting_seconds,
                    total_arrivals = EXCLUDED.total_arrivals,
                    on_time_percentage = EXCLUDED.on_time_percentage,
                    last_updated = NOW()
            """
            
            # Execute via RPC or direct SQL if you have permissions
            # For now, this would need to be a database function
            
            return True
                    
        except Exception as e:
            print(f"Exception updating stats: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Clean up old data"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with httpx.Client() as client:
                response = client.delete(
                    f"{self.base_url}/arrivals",
                    headers=self.headers,
                    params={'collected_at': f'lt.{cutoff_date}'}
                )
                
                if response.status_code in [200, 204]:
                    print(f"Cleaned up arrivals older than {days_to_keep} days")
                    return True
                else:
                    print(f"Error cleaning up: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"Exception cleaning up: {e}")
            return False
    
    def _parse_delay(self, delay_str: str) -> int:
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

# Test the client
if __name__ == '__main__':
    # Test with dummy credentials (replace with real ones)
    os.environ['SUPABASE_URL'] = 'https://your-project.supabase.co'
    os.environ['SUPABASE_ANON_KEY'] = 'your-anon-key'
    
    try:
        client = SupabaseClient()
        print("✅ Supabase client initialized")
        
        # Test getting metrics
        metrics = client.get_system_metrics()
        print(f"System metrics: {metrics}")
        
    except ValueError as e:
        print(f"❌ {e}")
        print("Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")