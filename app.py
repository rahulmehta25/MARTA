"""
Minimal Flask application for Railway deployment.
"""
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def root():
    return jsonify({
        "name": "MARTA Transit Analytics",
        "version": "0.1.0",
        "status": "running",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "message": "Backend is running successfully!"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "MARTA Transit Analytics"})

@app.route('/api/v1/routes')
def routes():
    return jsonify({
        "routes": [
            {"id": "red", "name": "Red Line", "status": "operational"},
            {"id": "gold", "name": "Gold Line", "status": "operational"},
            {"id": "blue", "name": "Blue Line", "status": "operational"},
            {"id": "green", "name": "Green Line", "status": "operational"}
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8000)))
