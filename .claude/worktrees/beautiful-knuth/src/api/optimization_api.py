#!/usr/bin/env python3
"""
MARTA Optimization API
REST API for route optimization and simulation services
"""
import os
import sys
import logging
import joblib
from datetime import datetime
from typing import Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import optimization modules
from src.optimization.route_optimizer import RouteOptimizer
from src.optimization.route_simulator import RouteSimulator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

# API configuration
API_CONFIG = {
    'host': '0.0.0.0',
    'port': 8001,
    'debug': True,
    'reload': True
}

# Pydantic models for API requests/responses
class OptimizationRequest(BaseModel):
    route_ids: Optional[List[str]] = None
    timestamp: Optional[str] = None
    optimization_type: str = "all"  # "short_turn", "headway", "all"
    simulation_hours: int = 24
    max_short_turns: int = 3
    bus_capacity: int = 50

class SimulationRequest(BaseModel):
    optimization_proposals: List[Dict]
    simulation_hours: int = 24
    bus_capacity: int = 50
    passenger_demand_multiplier: float = 1.0

class OptimizationResponse(BaseModel):
    status: str
    message: str
    optimization_results: Optional[Dict] = None
    simulation_results: Optional[Dict] = None
    execution_time: float
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    database_connected: bool
    ml_models_loaded: bool
    timestamp: str

# Initialize FastAPI app
app = FastAPI(
    title="MARTA Optimization API",
    description="API for MARTA route optimization and simulation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for optimization components
route_optimizer = None
route_simulator = None

def create_db_connection():
    """Create database connection"""
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return None

def initialize_optimization_components():
    """Initialize optimization components"""
    global route_optimizer, route_simulator
    
    try:
        # Initialize route optimizer
        route_optimizer = RouteOptimizer()
        route_optimizer.load_route_data()
        route_optimizer.load_ml_models()
        
        # Initialize route simulator
        route_simulator = RouteSimulator()
        route_simulator.load_route_data()
        
        logging.info("✅ Optimization components initialized successfully")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to initialize optimization components: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logging.info("🚀 Starting MARTA Optimization API")
    initialize_optimization_components()

@app.get("/", response_model=Dict)
async def root():
    """Root endpoint"""
    return {
        "message": "MARTA Optimization API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "optimize": "/optimize",
            "simulate": "/simulate",
            "optimize_and_simulate": "/optimize-and-simulate"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    # Check database connection
    db_connected = create_db_connection() is not None
    
    # Check ML models
    ml_models_loaded = (
        route_optimizer is not None and 
        route_optimizer.demand_model is not None
    )
    
    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        database_connected=db_connected,
        ml_models_loaded=ml_models_loaded,
        timestamp=datetime.now().isoformat()
    )

@app.post("/optimize", response_model=OptimizationResponse)
async def optimize_routes(request: OptimizationRequest):
    """Optimize routes based on ML predictions"""
    start_time = datetime.now()
    
    try:
        if route_optimizer is None:
            raise HTTPException(status_code=500, detail="Optimization components not initialized")
        
        # Parse timestamp
        timestamp = datetime.now()
        if request.timestamp:
            try:
                timestamp = datetime.fromisoformat(request.timestamp)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid timestamp format")
        
        # Run optimization
        logging.info(f"Starting route optimization for {len(request.route_ids) if request.route_ids else 'all'} routes")
        
        # Update optimizer config based on request
        route_optimizer.config['max_short_turns'] = request.max_short_turns
        route_optimizer.config['bus_capacity'] = request.bus_capacity
        
        # Run optimization
        results = route_optimizer.optimize_route_network(timestamp)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return OptimizationResponse(
            status="success",
            message="Route optimization completed successfully",
            optimization_results=results,
            execution_time=execution_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logging.error(f"Optimization failed: {e}")
        execution_time = (datetime.now() - start_time).total_seconds()
        
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {str(e)}"
        )

@app.post("/simulate", response_model=OptimizationResponse)
async def simulate_routes(request: SimulationRequest):
    """Simulate route performance with optimization proposals"""
    start_time = datetime.now()
    
    try:
        if route_simulator is None:
            raise HTTPException(status_code=500, detail="Simulation components not initialized")
        
        # Update simulator config
        route_simulator.config['simulation_hours'] = request.simulation_hours
        route_simulator.config['bus_capacity'] = request.bus_capacity
        
        # Create simulation entities
        route_simulator.create_simulation_entities()
        
        # Generate passenger demand
        route_simulator.generate_passenger_demand()
        
        # Run baseline simulation
        logging.info("Running baseline simulation...")
        route_simulator.run_simulation()
        baseline_results = route_simulator.get_simulation_results()
        
        # Run optimized simulation
        logging.info("Running optimized simulation...")
        optimized_simulator = RouteSimulator()
        optimized_simulator.load_route_data()
        optimized_simulator.create_simulation_entities()
        optimized_simulator.generate_passenger_demand()
        optimized_simulator.run_simulation(request.optimization_proposals)
        optimized_results = optimized_simulator.get_simulation_results()
        
        # Compare scenarios
        comparison = route_simulator.compare_scenarios(baseline_results, optimized_results)
        
        simulation_results = {
            'baseline': baseline_results,
            'optimized': optimized_results,
            'comparison': comparison
        }
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return OptimizationResponse(
            status="success",
            message="Route simulation completed successfully",
            simulation_results=simulation_results,
            execution_time=execution_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logging.error(f"Simulation failed: {e}")
        execution_time = (datetime.now() - start_time).total_seconds()
        
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {str(e)}"
        )

@app.post("/optimize-and-simulate", response_model=OptimizationResponse)
async def optimize_and_simulate(request: OptimizationRequest):
    """Run complete optimization and simulation workflow"""
    start_time = datetime.now()
    
    try:
        # Step 1: Run optimization
        logging.info("Step 1: Running route optimization...")
        optimization_response = await optimize_routes(request)
        
        if optimization_response.status != "success":
            raise HTTPException(status_code=500, detail="Optimization step failed")
        
        # Step 2: Run simulation with optimization proposals
        logging.info("Step 2: Running simulation...")
        
        # Extract optimization proposals
        optimization_results = optimization_response.optimization_results
        short_turn_proposals = optimization_results.get('short_turn_proposals', [])
        headway_optimizations = optimization_results.get('headway_optimizations', [])
        
        # Convert to simulation format
        simulation_proposals = []
        
        for proposal in short_turn_proposals:
            simulation_proposals.append({
                'type': 'short_turn',
                'route_id': proposal['route_id'],
                'turnaround_stop_id': proposal['turnaround_stop_id']
            })
        
        for optimization in headway_optimizations:
            simulation_proposals.append({
                'type': 'headway_optimization',
                'route_id': optimization['route_id'],
                'optimal_headway': optimization.get('optimal_headway', 15)
            })
        
        # Create simulation request
        simulation_request = SimulationRequest(
            optimization_proposals=simulation_proposals,
            simulation_hours=request.simulation_hours,
            bus_capacity=request.bus_capacity
        )
        
        # Run simulation
        simulation_response = await simulate_routes(simulation_request)
        
        if simulation_response.status != "success":
            raise HTTPException(status_code=500, detail="Simulation step failed")
        
        # Combine results
        combined_results = {
            'optimization': optimization_results,
            'simulation': simulation_response.simulation_results,
            'summary': {
                'total_execution_time': (datetime.now() - start_time).total_seconds(),
                'optimization_time': optimization_response.execution_time,
                'simulation_time': simulation_response.execution_time,
                'routes_analyzed': optimization_results.get('routes_analyzed', 0),
                'short_turn_proposals': len(short_turn_proposals),
                'headway_optimizations': len(headway_optimizations),
                'baseline_satisfaction': simulation_response.simulation_results['baseline']['metrics'].get('passenger_satisfaction', 0),
                'optimized_satisfaction': simulation_response.simulation_results['optimized']['metrics'].get('passenger_satisfaction', 0)
            }
        }
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return OptimizationResponse(
            status="success",
            message="Complete optimization and simulation workflow completed successfully",
            optimization_results=combined_results,
            execution_time=execution_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logging.error(f"Optimize and simulate failed: {e}")
        execution_time = (datetime.now() - start_time).total_seconds()
        
        raise HTTPException(
            status_code=500,
            detail=f"Optimize and simulate failed: {str(e)}"
        )

@app.get("/routes")
async def get_routes():
    """Get available routes"""
    try:
        conn = create_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT route_id, route_short_name, route_long_name FROM gtfs_routes LIMIT 100")
            routes = cursor.fetchall()
        
        conn.close()
        
        return {
            "routes": [
                {
                    "route_id": route[0],
                    "short_name": route[1],
                    "long_name": route[2]
                }
                for route in routes
            ]
        }
        
    except Exception as e:
        logging.error(f"Failed to get routes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get routes: {str(e)}")

@app.get("/stops")
async def get_stops():
    """Get available stops"""
    try:
        conn = create_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT stop_id, stop_name, stop_lat, stop_lon FROM gtfs_stops LIMIT 100")
            stops = cursor.fetchall()
        
        conn.close()
        
        return {
            "stops": [
                {
                    "stop_id": stop[0],
                    "name": stop[1],
                    "latitude": float(stop[2]),
                    "longitude": float(stop[3])
                }
                for stop in stops
            ]
        }
        
    except Exception as e:
        logging.error(f"Failed to get stops: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stops: {str(e)}")

@app.get("/optimization-history")
async def get_optimization_history():
    """Get recent optimization results"""
    try:
        # Look for recent optimization result files
        import glob
        result_files = glob.glob("optimization_results_*.pkl")
        
        history = []
        for filename in sorted(result_files, reverse=True)[:10]:  # Last 10 results
            try:
                data = joblib.load(filename)
                history.append({
                    "filename": filename,
                    "timestamp": data.get('timestamp', 'Unknown'),
                    "routes_analyzed": data.get('routes_analyzed', 0),
                    "short_turn_proposals": len(data.get('short_turn_proposals', [])),
                    "headway_optimizations": len(data.get('headway_optimizations', []))
                })
            except Exception as e:
                logging.warning(f"Could not load {filename}: {e}")
        
        return {"optimization_history": history}
        
    except Exception as e:
        logging.error(f"Failed to get optimization history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get optimization history: {str(e)}")

def main():
    """Run the API server"""
    logging.info("🚀 Starting MARTA Optimization API Server")
    
    uvicorn.run(
        "src.api.optimization_api:app",
        host=API_CONFIG['host'],
        port=API_CONFIG['port'],
        reload=API_CONFIG['reload'],
        log_level="info"
    )

if __name__ == "__main__":
    main() 