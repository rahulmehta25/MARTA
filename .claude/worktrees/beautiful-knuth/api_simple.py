"""
Simple Flask API for MARTA that works with Supabase
Optimized for serverless deployment
"""
import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import httpx
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# Configuration
MARTA_API_KEY = os.environ.get('MARTA_API_KEY', 'ff98ada7-0436-42c5-b9bf-1071245ad1a0')
MARTA_API_URL = "https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata"
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://vglychbweuowsovboxyf.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', '')

# Initialize Supabase client
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        pass

def fetch_marta_data():
    """Fetch real-time data from MARTA API"""
    try:
        url = f"{MARTA_API_URL}?apiKey={MARTA_API_KEY}"
        with httpx.Client(verify=False, timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching MARTA data: {e}")
        return None

def store_to_supabase(data):
    """Store data in Supabase if connected"""
    if not supabase or not data:
        return False
    
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
                'delay_seconds': int(arrival.get('DELAY', '0') if arrival.get('DELAY') else 0),
                'train_id': arrival.get('TRAIN_ID'),
                'event_time': arrival.get('EVENT_TIME')
            })
        
        # Insert to Supabase
        result = supabase.table('arrivals').insert(records).execute()
        return True
    except Exception as e:
        print(f"Error storing to Supabase: {e}")
        return False

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'active',
        'service': 'MARTA Real-time API',
        'database': 'Supabase' if supabase else 'Not connected',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/arrivals')
def get_arrivals():
    """Get real-time arrivals"""
    data = fetch_marta_data()
    
    if data:
        # Store in background if Supabase is connected
        if supabase:
            store_to_supabase(data)
        return jsonify(data)
    else:
        # Try to get recent data from Supabase
        if supabase:
            try:
                result = supabase.table('arrivals')\
                    .select('*')\
                    .order('collected_at', desc=True)\
                    .limit(300)\
                    .execute()
                
                # Transform back to MARTA format
                if result.data:
                    transformed = []
                    for a in result.data:
                        transformed.append({
                            'STATION': a['station_id'],
                            'LINE': a['line'],
                            'DESTINATION': a['destination'],
                            'DIRECTION': a['direction'],
                            'NEXT_ARR': a['arrival_time'],
                            'WAITING_SECONDS': str(a['waiting_seconds']),
                            'TRAIN_ID': a['train_id'],
                            'EVENT_TIME': a['event_time'],
                            'DELAY': str(a.get('delay_seconds', 0))
                        })
                    return jsonify(transformed)
            except:
                pass
        
        return jsonify({'error': 'Unable to fetch data'}), 503

@app.route('/stations')
def get_stations():
    """Get station list from Supabase"""
    if not supabase:
        return jsonify({'error': 'Database not connected'}), 503
    
    try:
        result = supabase.table('stations').select('*').execute()
        return jsonify(result.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metrics')
def get_metrics():
    """Get system metrics from Supabase view"""
    if not supabase:
        return jsonify({'error': 'Database not connected'}), 503
    
    try:
        result = supabase.from_('current_system_status').select('*').execute()
        if result.data:
            return jsonify(result.data[0])
        return jsonify({})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/collect', methods=['POST'])
def trigger_collection():
    """Manually trigger data collection"""
    data = fetch_marta_data()
    if data:
        stored = store_to_supabase(data) if supabase else False
        return jsonify({
            'success': True,
            'count': len(data),
            'stored': stored,
            'timestamp': datetime.now().isoformat()
        })
    return jsonify({'success': False, 'error': 'Failed to fetch data'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)