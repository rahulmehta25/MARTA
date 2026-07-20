"""
MARTA Analytics Engine - Analyzes stored data to provide insights
No complex ML, just smart statistics that actually work
"""
import sqlite3
from datetime import datetime, timedelta
from database import get_db, DB_PATH
import json
import statistics

class MartaAnalytics:
    """Simple but effective analytics on collected MARTA data"""
    
    @staticmethod
    def get_station_delays(station_id, hours=24):
        """Get delay patterns for a station"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get delays by hour of day
            cursor.execute('''
                SELECT 
                    strftime('%H', collected_at) as hour,
                    line,
                    AVG(delay_seconds) as avg_delay,
                    MAX(delay_seconds) as max_delay,
                    COUNT(*) as sample_size
                FROM arrivals
                WHERE station_id = ?
                    AND collected_at >= datetime('now', '-' || ? || ' hours')
                GROUP BY hour, line
                ORDER BY hour
            ''', (station_id, hours))
            
            delays_by_hour = {}
            for row in cursor.fetchall():
                hour = int(row['hour'])
                if hour not in delays_by_hour:
                    delays_by_hour[hour] = {}
                delays_by_hour[hour][row['line']] = {
                    'avg_delay': round(row['avg_delay'], 1),
                    'max_delay': row['max_delay'],
                    'samples': row['sample_size']
                }
            
            return delays_by_hour
    
    @staticmethod
    def predict_next_arrival(station_id, line=None):
        """Predict next arrival based on historical patterns"""
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        day_of_week = datetime.now().weekday()
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get historical arrivals for this time
            query = '''
                SELECT 
                    AVG(CAST(strftime('%M', arrival_time) as INTEGER)) as avg_minute,
                    AVG(delay_seconds) as avg_delay,
                    COUNT(*) as samples
                FROM arrivals
                WHERE station_id = ?
                    AND strftime('%H', collected_at) = ?
                    AND strftime('%w', collected_at) = ?
            '''
            params = [station_id, f'{current_hour:02d}', str(day_of_week)]
            
            if line:
                query += ' AND line = ?'
                params.append(line)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if result and result['samples'] > 5:  # Need enough data
                avg_minute = result['avg_minute'] or current_minute
                avg_delay = result['avg_delay'] or 0
                
                # Simple prediction
                if avg_minute > current_minute:
                    minutes_until = avg_minute - current_minute
                else:
                    minutes_until = (60 - current_minute) + avg_minute
                
                return {
                    'predicted_minutes': round(minutes_until),
                    'expected_delay': round(avg_delay),
                    'confidence': min(result['samples'] / 20, 1.0),  # Max confidence at 20 samples
                    'based_on_samples': result['samples']
                }
            
            return None
    
    @staticmethod
    def get_busy_times(station_id, line=None):
        """Get busy times like Google Maps popular times"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    strftime('%H', collected_at) as hour,
                    strftime('%w', collected_at) as day_of_week,
                    COUNT(*) as arrivals,
                    AVG(waiting_seconds) as avg_wait
                FROM arrivals
                WHERE station_id = ?
                    AND collected_at >= datetime('now', '-7 days')
            '''
            params = [station_id]
            
            if line:
                query += ' AND line = ?'
                params.append(line)
            
            query += ' GROUP BY hour, day_of_week'
            
            cursor.execute(query, params)
            
            # Organize by day and hour
            busy_times = {}
            for row in cursor.fetchall():
                day = int(row['day_of_week'])
                hour = int(row['hour'])
                
                if day not in busy_times:
                    busy_times[day] = {}
                
                busy_times[day][hour] = {
                    'arrivals': row['arrivals'],
                    'avg_wait_seconds': round(row['avg_wait'])
                }
            
            # Calculate relative busyness
            all_counts = []
            for day_data in busy_times.values():
                for hour_data in day_data.values():
                    all_counts.append(hour_data['arrivals'])
            
            if all_counts:
                max_count = max(all_counts)
                for day_data in busy_times.values():
                    for hour_data in day_data.values():
                        hour_data['busyness'] = round(
                            (hour_data['arrivals'] / max_count) * 100
                        )
            
            return busy_times
    
    @staticmethod
    def get_line_performance():
        """Compare performance across all lines"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    line,
                    COUNT(*) as total_arrivals,
                    AVG(delay_seconds) as avg_delay,
                    STDDEV(delay_seconds) as delay_stddev,
                    SUM(CASE WHEN delay_seconds > 300 THEN 1 ELSE 0 END) as major_delays,
                    SUM(CASE WHEN delay_seconds <= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as on_time_pct
                FROM arrivals
                WHERE collected_at >= datetime('now', '-24 hours')
                GROUP BY line
            ''')
            
            performance = {}
            for row in cursor.fetchall():
                performance[row['line']] = {
                    'total_arrivals': row['total_arrivals'],
                    'avg_delay_seconds': round(row['avg_delay'], 1),
                    'delay_variability': round(row['delay_stddev'] or 0, 1),
                    'major_delays': row['major_delays'],
                    'on_time_percentage': round(row['on_time_pct'], 1),
                    'reliability_score': round(
                        row['on_time_pct'] * (1 - (row['delay_stddev'] or 0) / 1000),
                        1
                    )
                }
            
            return performance
    
    @staticmethod
    def get_travel_time_estimate(from_station, to_station, line=None):
        """Estimate travel time between stations based on historical data"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # This is simplified - in reality would need station order
            # For now, return average time between consecutive observations
            query = '''
                SELECT 
                    AVG(waiting_seconds) as avg_wait,
                    COUNT(*) as samples
                FROM arrivals a1
                WHERE EXISTS (
                    SELECT 1 FROM arrivals a2
                    WHERE a2.station_id = ?
                    AND a2.train_id = a1.train_id
                    AND a2.collected_at > a1.collected_at
                )
                AND a1.station_id = ?
            '''
            params = [to_station, from_station]
            
            if line:
                query += ' AND a1.line = ?'
                params.append(line)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if result and result['samples'] > 0:
                return {
                    'estimated_minutes': round(result['avg_wait'] / 60),
                    'samples': result['samples']
                }
            
            return None
    
    @staticmethod
    def get_system_health():
        """Overall system health metrics"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Current status
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT station_id) as active_stations,
                    COUNT(DISTINCT train_id) as active_trains,
                    COUNT(*) as recent_arrivals,
                    AVG(delay_seconds) as current_avg_delay
                FROM arrivals
                WHERE collected_at >= datetime('now', '-30 minutes')
            ''')
            current = dict(cursor.fetchone())
            
            # Historical comparison
            cursor.execute('''
                SELECT 
                    AVG(delay_seconds) as historical_avg_delay,
                    STDDEV(delay_seconds) as delay_stddev
                FROM arrivals
                WHERE collected_at >= datetime('now', '-7 days')
            ''')
            historical = dict(cursor.fetchone())
            
            # Calculate health score
            delay_diff = current['current_avg_delay'] - historical['historical_avg_delay']
            
            if delay_diff < -30:
                status = 'excellent'
                score = 95
            elif delay_diff < 30:
                status = 'normal'
                score = 85
            elif delay_diff < 120:
                status = 'delays'
                score = 60
            else:
                status = 'major_delays'
                score = 30
            
            return {
                'status': status,
                'health_score': score,
                'active_stations': current['active_stations'],
                'active_trains': current['active_trains'],
                'current_avg_delay': round(current['current_avg_delay'], 1),
                'historical_avg_delay': round(historical['historical_avg_delay'], 1),
                'delay_trend': 'increasing' if delay_diff > 0 else 'decreasing'
            }

def STDDEV(values):
    """SQLite doesn't have STDDEV built-in, so we add it"""
    if not values or len(values) < 2:
        return 0
    return statistics.stdev(values)

# Register the STDDEV function with SQLite
conn = sqlite3.connect(DB_PATH)
conn.create_aggregate("STDDEV", 1, STDDEV)
conn.close()

if __name__ == '__main__':
    # Test analytics
    analytics = MartaAnalytics()
    
    print("🚇 MARTA Analytics Test")
    print("=" * 50)
    
    # Test system health
    health = analytics.get_system_health()
    print(f"\n📊 System Health: {health}")
    
    # Test line performance
    performance = analytics.get_line_performance()
    print(f"\n🚂 Line Performance: {json.dumps(performance, indent=2)}")