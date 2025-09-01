"""
Flask application for MARTA Transit Analytics with Supabase
Real database, real analytics, all free tier!
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import httpx
from datetime import datetime, timedelta
import logging
from supabase_client import SupabaseClient
from collect_data_supabase import collect_and_store

# Import analytics and ML modules
try:
    from analytics_engine import MARTAAnalyticsEngine
    from ml_models import ArrivalPredictionModel, DemandForecastModel
    analytics_available = True
except ImportError as e:
    logger.warning(f"Analytics modules not available: {e}")
    analytics_available = False

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

# Initialize analytics engine and ML models
analytics_engine = None
arrival_model = None
demand_model = None

if analytics_available and supabase:
    try:
        analytics_engine = MARTAAnalyticsEngine()
        arrival_model = ArrivalPredictionModel()
        demand_model = DemandForecastModel()
        logger.info("✅ Analytics and ML models initialized")
    except Exception as e:
        logger.warning(f"Analytics initialization failed: {e}")

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
                "performance": "/api/v1/analytics/performance",
                "delay_patterns": "/api/v1/analytics/delay-patterns",
                "demand_forecast": "/api/v1/analytics/demand/<station_id>",
                "insights": "/api/v1/analytics/insights"
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
    """Get ML-based arrival predictions for a station"""
    if not supabase:
        return jsonify({"error": "Database not configured"}), 503
    
    try:
        line = request.args.get('line')
        direction = request.args.get('direction', 'N')
        
        # Try ML model first if available
        if arrival_model and line:
            try:
                ml_prediction = arrival_model.predict(
                    station_id=station_id,
                    line=line.upper(),
                    direction=direction.upper()
                )
                
                if ml_prediction.get('predicted_seconds'):
                    return jsonify({
                        'station_id': station_id,
                        'line': line,
                        'direction': direction,
                        'predicted_seconds': ml_prediction['predicted_seconds'],
                        'predicted_arrival': ml_prediction.get('predicted_arrival'),
                        'confidence': ml_prediction.get('confidence', 0.5),
                        'method': 'machine_learning',
                        'model_version': ml_prediction.get('model_version', '1.0.0')
                    })
            except Exception as e:
                logger.warning(f"ML prediction failed, falling back: {e}")
        
        # Fallback to simple predictions
        recent = supabase.get_recent_arrivals(station_id=station_id, line=line, limit=20)
        
        if recent:
            waits = [a.get('waiting_seconds', 0) for a in recent if a.get('waiting_seconds')]
            avg_wait = sum(waits) / len(waits) if waits else 600
            
            prediction = {
                'station_id': station_id,
                'line': line,
                'direction': direction,
                'predicted_seconds': int(avg_wait),
                'predicted_arrival': (datetime.now() + timedelta(seconds=avg_wait)).isoformat(),
                'confidence': min(len(recent) / 20, 1.0),
                'based_on_samples': len(recent),
                'method': 'statistical_average'
            }
        else:
            prediction = {
                'station_id': station_id,
                'line': line,
                'direction': direction,
                'predicted_seconds': None,
                'confidence': 0,
                'message': 'Insufficient data for prediction'
            }
        
        return jsonify(prediction)
        
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/analytics/performance')
def get_performance():
    """Get comprehensive system performance metrics"""
    if not supabase:
        return jsonify({
            'status': 'database_unavailable',
            'message': 'Using live data only',
            'timestamp': datetime.now().isoformat()
        })
    
    try:
        # Try analytics engine first if available
        if analytics_engine:
            try:
                # Calculate real performance metrics
                performance_metrics = analytics_engine.calculate_performance_metrics(hours_back=24)
                
                # Aggregate metrics by line
                line_performance = {}
                for key, metrics in performance_metrics.items():
                    line = metrics.get('line')
                    if line not in line_performance:
                        line_performance[line] = {
                            'stations': 0,
                            'total_on_time_pct': 0,
                            'total_reliability': 0,
                            'avg_delay': 0
                        }
                    line_performance[line]['stations'] += 1
                    line_performance[line]['total_on_time_pct'] += metrics.get('on_time_percentage', 0)
                    line_performance[line]['total_reliability'] += metrics.get('reliability_score', 0)
                    line_performance[line]['avg_delay'] += metrics.get('avg_delay_seconds', 0)
                
                # Calculate averages
                for line, stats in line_performance.items():
                    if stats['stations'] > 0:
                        stats['on_time_percentage'] = round(stats['total_on_time_pct'] / stats['stations'], 1)
                        stats['reliability_score'] = round(stats['total_reliability'] / stats['stations'], 1)
                        stats['avg_delay_seconds'] = round(stats['avg_delay'] / stats['stations'], 1)
                        del stats['total_on_time_pct']
                        del stats['total_reliability']
                
                # Calculate system health
                system_on_time = sum(m.get('on_time_percentage', 0) for m in performance_metrics.values()) / max(len(performance_metrics), 1)
                
                if system_on_time >= 90:
                    health_status = 'excellent'
                elif system_on_time >= 75:
                    health_status = 'good'
                elif system_on_time >= 60:
                    health_status = 'fair'
                else:
                    health_status = 'poor'
                
                return jsonify({
                    'health_status': health_status,
                    'health_score': round(system_on_time, 1),
                    'line_performance': line_performance,
                    'total_stations_analyzed': len(performance_metrics),
                    'method': 'analytics_engine',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"Analytics engine failed, using fallback: {e}")
        
        # Fallback to basic metrics
        metrics = supabase.get_system_metrics()
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
            'method': 'basic_metrics',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/analytics/delay-patterns')
def get_delay_patterns():
    """Get identified delay patterns in the system"""
    if not analytics_engine:
        return jsonify({
            'status': 'analytics_unavailable',
            'message': 'Analytics engine not initialized',
            'patterns': []
        })
    
    try:
        # Get delay patterns
        patterns = analytics_engine.identify_delay_patterns()
        
        # Format for API response
        formatted_patterns = []
        for pattern in patterns:
            formatted_patterns.append({
                'type': pattern.get('type', 'unknown'),
                'line': pattern.get('line'),
                'stations': pattern.get('stations', []),
                'frequency': pattern.get('frequency', 0),
                'average_delay': pattern.get('avg_delay', 0),
                'time_of_day': pattern.get('common_times', []),
                'description': pattern.get('description', '')
            })
        
        return jsonify({
            'patterns_count': len(formatted_patterns),
            'patterns': formatted_patterns,
            'analysis_period': '24_hours',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting delay patterns: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/analytics/demand/<station_id>')
def get_demand_forecast(station_id):
    """Get demand forecast for a specific station"""
    if not demand_model:
        return jsonify({
            'status': 'forecast_unavailable',
            'message': 'Demand forecasting not initialized'
        })
    
    try:
        # Get parameters
        date_str = request.args.get('date', datetime.now().date().isoformat())
        hour = request.args.get('hour', datetime.now().hour)
        
        # Parse date
        forecast_date = datetime.fromisoformat(date_str) if date_str else datetime.now()
        forecast_hour = int(hour) if hour else datetime.now().hour
        
        # Get forecast
        forecast = demand_model.forecast(
            station_id=station_id,
            date=forecast_date,
            hour=forecast_hour
        )
        
        return jsonify(forecast)
        
    except Exception as e:
        logger.error(f"Error getting demand forecast: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/analytics/insights')
def get_insights():
    """Get system insights and recommendations"""
    if not analytics_engine:
        return jsonify({
            'status': 'insights_unavailable',
            'message': 'Analytics engine not initialized',
            'insights': []
        })
    
    try:
        # Generate insights
        insights = analytics_engine.generate_insights()
        
        # Calculate performance metrics for context
        metrics = analytics_engine.calculate_performance_metrics(hours_back=24)
        
        # Get worst performing stations
        worst_stations = sorted(
            metrics.items(),
            key=lambda x: x[1].get('on_time_percentage', 100)
        )[:5]
        
        # Get best performing stations
        best_stations = sorted(
            metrics.items(),
            key=lambda x: x[1].get('on_time_percentage', 0),
            reverse=True
        )[:5]
        
        # Format insights
        formatted_insights = []
        for insight in insights:
            formatted_insights.append({
                'type': 'system',
                'message': insight,
                'severity': 'info'
            })
        
        # Add performance insights
        if worst_stations:
            station_id = worst_stations[0][1].get('station_id', 'Unknown')
            on_time = worst_stations[0][1].get('on_time_percentage', 0)
            formatted_insights.append({
                'type': 'performance',
                'message': f"Worst performing: {station_id} with {on_time:.1f}% on-time",
                'severity': 'warning'
            })
        
        if best_stations:
            station_id = best_stations[0][1].get('station_id', 'Unknown')
            on_time = best_stations[0][1].get('on_time_percentage', 0)
            formatted_insights.append({
                'type': 'performance',
                'message': f"Best performing: {station_id} with {on_time:.1f}% on-time",
                'severity': 'success'
            })
        
        # Add system health insight
        system_on_time = sum(m.get('on_time_percentage', 0) for m in metrics.values()) / max(len(metrics), 1)
        formatted_insights.append({
            'type': 'health',
            'message': f"System-wide on-time performance: {system_on_time:.1f}%",
            'severity': 'info' if system_on_time > 75 else 'warning'
        })
        
        return jsonify({
            'insights_count': len(formatted_insights),
            'insights': formatted_insights,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
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