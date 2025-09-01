"""
Flask application for MARTA Transit Analytics
Direct implementation for Railway deployment
"""
import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
import httpx
from datetime import datetime
import logging

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app, origins=["https://marta-eta.vercel.app", "http://localhost:3000", "http://localhost:5173"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.environ.get('PORT', 8000))
MARTA_API_KEY = os.environ.get('MARTA_API_KEY', '')
MARTA_API_URL = "https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata"

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "service": "MARTA Transit Analytics",
        "status": "healthy"
    })

@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        "name": "MARTA Transit Analytics API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "marta_rail_arrivals": "/api/v1/marta/rail/arrivals",
            "marta_rail_stations": "/api/v1/marta/rail/stations",
            "marta_rail_status": "/api/v1/marta/rail/status"
        }
    })

@app.route('/api/v1/marta/rail/arrivals')
def get_rail_arrivals():
    """Get real-time MARTA rail arrivals"""
    try:
        # Get query parameters
        station = request.args.get('station')
        line = request.args.get('line')
        direction = request.args.get('direction')
        
        # Fetch from MARTA API
        url = f"{MARTA_API_URL}?apiKey={MARTA_API_KEY}"
        
        # Use httpx for the request (handles SSL better)
        with httpx.Client(verify=False) as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Transform the data
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
                
                # Apply filters
                if station and station.upper() not in arrival["station"].upper():
                    continue
                if line and arrival["line"] != line.upper():
                    continue
                if direction and arrival["direction"] != direction.upper():
                    continue
                    
                arrivals.append(arrival)
            
            # Sort by waiting seconds
            arrivals.sort(key=lambda x: int(x.get("waiting_seconds", "999999")))
            
            logger.info(f"Fetched {len(arrivals)} arrivals from MARTA API")
            return jsonify(arrivals)
            
    except Exception as e:
        logger.error(f"Error fetching MARTA data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/marta/rail/stations')
def get_stations():
    """Get list of all MARTA rail stations with current arrivals"""
    try:
        # Fetch from MARTA API
        url = f"{MARTA_API_URL}?apiKey={MARTA_API_KEY}"
        
        with httpx.Client(verify=False) as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Group by station
            stations_data = {}
            for train in data:
                station = train.get("STATION", "Unknown")
                if station not in stations_data:
                    stations_data[station] = {
                        "name": station,
                        "trains": [],
                        "lines": set()
                    }
                
                stations_data[station]["trains"].append({
                    "line": train.get("LINE"),
                    "destination": train.get("DESTINATION"),
                    "direction": train.get("DIRECTION"),
                    "waiting_time": train.get("WAITING_TIME"),
                    "next_arrival": train.get("NEXT_ARR")
                })
                
                if train.get("LINE"):
                    stations_data[station]["lines"].add(train.get("LINE"))
            
            # Convert to list
            stations = []
            for station_name, data in stations_data.items():
                stations.append({
                    "name": data["name"],
                    "lines": list(data["lines"]),
                    "upcoming_trains": data["trains"][:5]  # Limit to 5
                })
            
            stations.sort(key=lambda x: x["name"])
            return jsonify(stations)
            
    except Exception as e:
        logger.error(f"Error fetching stations: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/marta/rail/status')
def get_system_status():
    """Get MARTA rail system status"""
    try:
        # Fetch from MARTA API
        url = f"{MARTA_API_URL}?apiKey={MARTA_API_KEY}"
        
        with httpx.Client(verify=False) as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Calculate statistics
            total_trains = len(set(t.get("TRAIN_ID") for t in data if t.get("TRAIN_ID")))
            total_stations = len(set(t.get("STATION") for t in data))
            
            # Check for delays
            delays = [t for t in data if "delay" in t.get("DELAY", "").lower()]
            
            status = "normal"
            if len(delays) > len(data) * 0.3:
                status = "delays"
            elif len(delays) > len(data) * 0.1:
                status = "minor_delays"
            
            return jsonify({
                "status": status,
                "active_trains": total_trains,
                "stations_with_service": total_stations,
                "total_arrivals": len(data),
                "delayed_arrivals": len(delays),
                "last_updated": datetime.now().isoformat(),
                "lines_status": {
                    "RED": len([t for t in data if t.get("LINE") == "RED"]) > 0,
                    "GOLD": len([t for t in data if t.get("LINE") == "GOLD"]) > 0,
                    "GREEN": len([t for t in data if t.get("LINE") == "GREEN"]) > 0,
                    "BLUE": len([t for t in data if t.get("LINE") == "BLUE"]) > 0
                }
            })
            
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)