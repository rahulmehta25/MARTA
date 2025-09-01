"""
Flask application for MARTA Transit Analytics with Supabase
Real database, real analytics, all free tier!
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import httpx
from datetime import datetime
import logging
from supabase_client import SupabaseClient
from collect_data_supabase import collect_and_store

app = Flask(__name__)
CORS(app, origins=["https://marta-eta.vercel.app", "http://localhost:3000", "http://localhost:5173"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MARTA_API_KEY = os.environ.get('MARTA_API_KEY', '')
MARTA_API_URL = "https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata"

# Initialize Supabase client
try:
    supabase = SupabaseClient()
    logger.info("✅ Supabase client initialized")
except Exception as e:
    logger.error(f"❌ Supabase initialization failed: {e}")
    supabase = None

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "service": "MARTA Transit Analytics",
        "status": "healthy",
        "database": "supabase" if supabase else "unavailable"
    })

@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        "name": "MARTA Transit Analytics API",
        "version": "2.0.0",
        "database": "Supabase PostgreSQL",
        "api_key_configured": bool(MARTA_API_KEY),
        "supabase_configured": supabase is not None,
        "endpoints": {
            "health": "/health",
            "real_time": {
                "marta_rail_arrivals": "/api/v1/marta/rail/arrivals",
                "marta_rail_stations": "/api/v1/marta/rail/stations",
                "marta_rail_status": "/api/v1/marta/rail/status"
            },
            "analytics": {
                "station_analytics": "/api/v1/analytics/station/<station_id>",
                "system_analytics": "/api/v1/analytics/system",
                "predictions": "/api/v1/analytics/predictions/<station_id>",
                "performance": "/api/v1/analytics/performance"
            },
            "data": {
                "collect": "/api/v1/data/collect",
                "metrics": "/api/v1/data/metrics"
            }
        }
    })

# ============= REAL-TIME MARTA ENDPOINTS (Direct from MARTA) =============

@app.route('/api/v1/marta/rail/arrivals')
def get_rail_arrivals():
    """Get real-time MARTA rail arrivals"""
    try:
        if not MARTA_API_KEY:
            return jsonify({"error": "MARTA API key not configured"}), 500
        
        station = request.args.get('station')
        line = request.args.get('line')
        direction = request.args.get('direction')
        
        url = f"{MARTA_API_URL}?apiKey={MARTA_API_KEY}"
        
        with httpx.Client(verify=False) as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            # Store in Supabase if available
            if supabase and len(data) > 0:
                try:
                    supabase.insert_arrivals(data[:50])  # Store first 50 to avoid overload
                    supabase.update_stations(data)
                except Exception as e:
                    logger.warning(f"Failed to store in Supabase: {e}")
            
            # Transform and filter
            arrivals = []
            for train in data:
                arrival = {
                    "destination": train.get("DESTINATION"),
                    "direction": train.get("DIRECTION"),
                    "event_time": train.get("EVENT_TIME"),
                    "line": train.get("LINE"),
                    "next_arrival": train.get("NEXT_ARR"),
                    "station": train.get("STATION"),
                    "train_id": train.get("TRAIN_ID"),
                    "waiting_seconds": train.get("WAITING_SECONDS"),
                    "waiting_time": train.get("WAITING_TIME"),
                    "delay": train.get("DELAY", "0 Seconds")
                }
                
                if station and station.upper() not in arrival["station"].upper():
                    continue
                if line and arrival["line"] != line.upper():
                    continue
                if direction and arrival["direction"] != direction.upper():
                    continue
                    
                arrivals.append(arrival)
            
            arrivals.sort(key=lambda x: int(x.get("waiting_seconds", "999999")))
            
            return jsonify(arrivals)
            
    except Exception as e:
        logger.error(f"Error fetching MARTA data: {e}")
        return jsonify({"error": str(e)}), 500

# ============= ANALYTICS ENDPOINTS (From Supabase) =============

@app.route('/api/v1/analytics/station/<station_id>')
def get_station_analytics(station_id):
    """Get analytics for a specific station from Supabase"""
    if not supabase:
        return jsonify({"error": "Database not configured"}), 503
    
    try:
        # Get recent arrivals for this station
        recent_arrivals = supabase.get_recent_arrivals(station_id=station_id, limit=50)
        
        # Get station statistics
        stats = supabase.get_station_stats(station_id)
        
        # Calculate simple analytics
        if recent_arrivals:
            delays = [a.get('delay_seconds', 0) for a in recent_arrivals]
            avg_delay = sum(delays) / len(delays) if delays else 0
            
            lines = {}
            for arrival in recent_arrivals:
                line = arrival.get('line')
                if line:
                    if line not in lines:
                        lines[line] = []
                    lines[line].append(arrival.get('delay_seconds', 0))
            
            line_stats = {}
            for line, line_delays in lines.items():
                line_stats[line] = {
                    'avg_delay': sum(line_delays) / len(line_delays) if line_delays else 0,
                    'max_delay': max(line_delays) if line_delays else 0,
                    'arrival_count': len(line_delays)
                }
        else:
            avg_delay = 0
            line_stats = {}
        
        return jsonify({
            'station_id': station_id,
            'recent_arrivals_count': len(recent_arrivals),
            'average_delay_seconds': round(avg_delay, 1),
            'line_statistics': line_stats,
            'detailed_stats': stats,
            'data_source': 'supabase',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting station analytics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/analytics/system')
def get_system_analytics():
    """Get system-wide analytics from Supabase"""
    if not supabase:
        return jsonify({"error": "Database not configured"}), 503
    
    try:
        # Get system metrics
        metrics = supabase.get_system_metrics()
        
        # Get recent arrivals for analysis
        recent_arrivals = supabase.get_recent_arrivals(limit=200)
        
        # Calculate line performance
        line_performance = {}
        for arrival in recent_arrivals:
            line = arrival.get('line')
            if line:
                if line not in line_performance:
                    line_performance[line] = {
                        'total_arrivals': 0,
                        'total_delay': 0,
                        'on_time': 0
                    }
                line_performance[line]['total_arrivals'] += 1
                delay = arrival.get('delay_seconds', 0)
                line_performance[line]['total_delay'] += delay
                if delay <= 60:
                    line_performance[line]['on_time'] += 1
        
        # Calculate percentages
        for line, stats in line_performance.items():
            if stats['total_arrivals'] > 0:
                stats['avg_delay'] = round(stats['total_delay'] / stats['total_arrivals'], 1)
                stats['on_time_percentage'] = round(
                    (stats['on_time'] / stats['total_arrivals']) * 100, 1
                )
        
        return jsonify({
            'system_metrics': metrics,
            'line_performance': line_performance,
            'total_records_analyzed': len(recent_arrivals),
            'data_source': 'supabase',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system analytics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/analytics/predictions/<station_id>')
def get_predictions(station_id):
    """Get arrival predictions for a station"""
    if not supabase:
        return jsonify({"error": "Database not configured"}), 503
    
    try:
        line = request.args.get('line')
        
        # For now, return simple predictions based on recent patterns
        recent = supabase.get_recent_arrivals(station_id=station_id, line=line, limit=20)
        
        if recent:
            # Simple average-based prediction
            waits = [a.get('waiting_seconds', 0) for a in recent if a.get('waiting_seconds')]
            avg_wait = sum(waits) / len(waits) if waits else 600  # Default 10 minutes
            
            prediction = {
                'station_id': station_id,
                'line': line,
                'predicted_next_arrival_minutes': round(avg_wait / 60, 1),
                'confidence': min(len(recent) / 20, 1.0),
                'based_on_samples': len(recent),
                'method': 'simple_average'
            }
        else:
            prediction = {
                'station_id': station_id,
                'line': line,
                'predicted_next_arrival_minutes': None,
                'confidence': 0,
                'message': 'Insufficient data for prediction'
            }
        
        return jsonify(prediction)
        
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/analytics/performance')
def get_performance():
    """Get system performance metrics"""
    if not supabase:
        # Return live metrics if no database
        return jsonify({
            'status': 'database_unavailable',
            'message': 'Using live data only',
            'timestamp': datetime.now().isoformat()
        })
    
    try:
        metrics = supabase.get_system_metrics()
        
        # Determine health status
        avg_delay = metrics.get('avg_delay', 0) if metrics else 0
        if avg_delay < 60:
            health_status = 'excellent'
            health_score = 95
        elif avg_delay < 180:
            health_status = 'good'
            health_score = 80
        elif avg_delay < 300:
            health_status = 'fair'
            health_score = 60
        else:
            health_status = 'poor'
            health_score = 40
        
        return jsonify({
            'health_status': health_status,
            'health_score': health_score,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return jsonify({"error": str(e)}), 500

# ============= DATA MANAGEMENT ENDPOINTS =============

@app.route('/api/v1/data/collect', methods=['POST'])
def trigger_data_collection():
    """Manually trigger data collection"""
    try:
        if not MARTA_API_KEY:
            return jsonify({"error": "No API key configured"}), 400
        
        if not supabase:
            return jsonify({"error": "Database not configured"}), 503
        
        # Run collection
        success = collect_and_store()
        
        if success:
            # Get updated metrics
            metrics = supabase.get_system_metrics()
            
            return jsonify({
                "status": "success",
                "message": "Data collection completed",
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Collection failed"}), 500
            
    except Exception as e:
        logger.error(f"Error in data collection: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/data/metrics')
def get_data_metrics():
    """Get database metrics"""
    if not supabase:
        return jsonify({"error": "Database not configured"}), 503
    
    try:
        metrics = supabase.get_system_metrics()
        
        return jsonify({
            'database': 'supabase',
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)