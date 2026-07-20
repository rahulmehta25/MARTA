"""
SQLite Database Setup for MARTA Analytics
Free, local, and works on Railway's free tier
"""
import os
import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager
import json

# Database path - persists on Railway
DB_PATH = os.environ.get('DB_PATH', 'marta_data.db')

def init_database():
    """Initialize database with all required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Stations table - static data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stations (
            station_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lat REAL,
            lon REAL,
            lines TEXT,  -- JSON array of lines
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Real-time arrivals - historical data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arrivals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            line TEXT NOT NULL,
            destination TEXT NOT NULL,
            direction TEXT,
            arrival_time TIMESTAMP,
            waiting_seconds INTEGER,
            delay_seconds INTEGER,
            train_id TEXT,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (station_id) REFERENCES stations(station_id)
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_arrivals_station ON arrivals(station_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_arrivals_time ON arrivals(collected_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_arrivals_line ON arrivals(line)')
    
    # Daily statistics table - pre-calculated metrics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            station_id TEXT NOT NULL,
            line TEXT,
            total_arrivals INTEGER,
            avg_delay_seconds REAL,
            max_delay_seconds INTEGER,
            on_time_percentage REAL,
            peak_hour INTEGER,
            peak_hour_arrivals INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, station_id, line)
        )
    ''')
    
    # Hourly patterns table - for predictions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hourly_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            line TEXT,
            hour INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            avg_arrivals REAL,
            avg_delay REAL,
            sample_count INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(station_id, line, hour, day_of_week)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {DB_PATH}")

@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()

def cleanup_old_data(days_to_keep=7):
    """Remove data older than specified days to stay within free tier limits"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Delete old arrivals
        cursor.execute('''
            DELETE FROM arrivals 
            WHERE collected_at < ?
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        
        # Delete old daily stats (keep 30 days)
        cursor.execute('''
            DELETE FROM daily_stats 
            WHERE date < date('now', '-30 days')
        ''')
        
        conn.commit()
        
    if deleted_count > 0:
        print(f"🧹 Cleaned up {deleted_count} old arrival records")
        
    # Vacuum to reclaim space
    conn = sqlite3.connect(DB_PATH)
    conn.execute('VACUUM')
    conn.close()

def get_database_size():
    """Check database size to ensure we stay under limits"""
    if os.path.exists(DB_PATH):
        size_bytes = os.path.getsize(DB_PATH)
        size_mb = size_bytes / (1024 * 1024)
        return {
            'size_mb': round(size_mb, 2),
            'size_bytes': size_bytes,
            'warning': size_mb > 900  # Warn if approaching 1GB limit
        }
    return {'size_mb': 0, 'size_bytes': 0, 'warning': False}

def insert_arrival(arrival_data):
    """Insert a single arrival record"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO arrivals (
                station_id, line, destination, direction,
                arrival_time, waiting_seconds, delay_seconds, train_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            arrival_data['station'],
            arrival_data['line'],
            arrival_data['destination'],
            arrival_data['direction'],
            arrival_data.get('next_arrival'),
            int(arrival_data.get('waiting_seconds', 0)),
            parse_delay(arrival_data.get('delay', '0')),
            arrival_data.get('train_id')
        ))
        conn.commit()

def parse_delay(delay_str):
    """Parse delay string like 'T78S' or '0 Seconds' to integer seconds"""
    if not delay_str:
        return 0
    if delay_str == '0 Seconds':
        return 0
    if delay_str.startswith('T') and delay_str.endswith('S'):
        return int(delay_str[1:-1])
    return 0

def get_station_stats(station_id, days=7):
    """Get statistics for a specific station"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get average delays by line
        cursor.execute('''
            SELECT 
                line,
                AVG(delay_seconds) as avg_delay,
                COUNT(*) as total_arrivals,
                SUM(CASE WHEN delay_seconds <= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as on_time_pct
            FROM arrivals
            WHERE station_id = ?
                AND collected_at >= datetime('now', '-' || ? || ' days')
            GROUP BY line
        ''', (station_id, days))
        
        return [dict(row) for row in cursor.fetchall()]

def get_system_metrics():
    """Get overall system metrics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get current day stats
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT station_id) as active_stations,
                COUNT(DISTINCT train_id) as active_trains,
                COUNT(*) as total_arrivals,
                AVG(delay_seconds) as avg_delay,
                SUM(CASE WHEN delay_seconds > 300 THEN 1 ELSE 0 END) as significant_delays
            FROM arrivals
            WHERE collected_at >= datetime('now', '-1 hour')
        ''')
        
        metrics = dict(cursor.fetchone())
        
        # Add database size
        metrics['database'] = get_database_size()
        
        return metrics

if __name__ == '__main__':
    # Initialize database when run directly
    init_database()
    print(f"📊 Database size: {get_database_size()}")