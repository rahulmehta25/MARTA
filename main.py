"""
Simplified FastAPI application for MARTA Transit Analytics Platform.
This is a minimal version for Railway deployment.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Create FastAPI application
app = FastAPI(
    title="MARTA Transit Analytics",
    version="0.1.0",
    description="Real-time transit analytics and optimization for MARTA"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MARTA Transit Analytics",
        "version": "0.1.0",
        "status": "running",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "message": "Backend is running successfully!"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MARTA Transit Analytics"}

@app.get("/api/v1/routes")
async def get_routes():
    """Get available routes."""
    return {
        "routes": [
            {"id": "red", "name": "Red Line", "status": "operational"},
            {"id": "gold", "name": "Gold Line", "status": "operational"},
            {"id": "blue", "name": "Blue Line", "status": "operational"},
            {"id": "green", "name": "Green Line", "status": "operational"}
        ]
    }

@app.get("/api/v1/stops")
async def get_stops():
    """Get available stops."""
    return {
        "stops": [
            {"id": "n5", "name": "North Springs", "line": "red"},
            {"id": "s1", "name": "Airport", "line": "red"},
            {"id": "e1", "name": "Indian Creek", "line": "blue"},
            {"id": "w1", "name": "Hamilton E Holmes", "line": "blue"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
