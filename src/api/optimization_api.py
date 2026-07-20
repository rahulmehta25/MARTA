#!/usr/bin/env python3
"""
MARTA Optimization API
Minimal FastAPI app with health and stub endpoints to unblock frontend.
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import json
import time
import random
import psycopg2
from fastapi import Query
import asyncio
from concurrent.futures import ThreadPoolExecutor


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")


class OptimizationRequest(BaseModel):
    route_ids: Optional[List[str]] = None
    timestamp: Optional[str] = None
    optimization_type: str = Field("all", pattern=r"^(short_turn|headway|all)$")
    simulation_hours: int = Field(24, ge=1, le=72)
    max_short_turns: int = Field(3, ge=0, le=10)
    bus_capacity: int = Field(50, ge=10, le=120)


class SimulationRequest(BaseModel):
    optimization_proposals: List[Dict]
    simulation_hours: int = Field(24, ge=1, le=72)
    bus_capacity: int = Field(50, ge=10, le=120)
    passenger_demand_multiplier: float = Field(1.0, ge=0.1, le=5.0)


class DynamicStopRequest(BaseModel):
    lat: float
    lon: float
    demand_threshold: int = 40
    duration_minutes: int = 180
    routes: Optional[List[str]] = None


app = FastAPI(
    title="MARTA Optimization API",
    description="API for MARTA route optimization and simulation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXECUTOR = ThreadPoolExecutor(max_workers=4)
OPT_TIMEOUT_SEC = int(os.getenv("OPT_TIMEOUT_SEC", "30"))
SIM_TIMEOUT_SEC = int(os.getenv("SIM_TIMEOUT_SEC", "30"))

@app.on_event("startup")
def on_startup() -> None:
    missing = [v for v in ("DB_HOST","DB_NAME","DB_USER","DB_PASSWORD") if not os.getenv(v)]
    if missing:
        logging.warning("Missing env vars: %s", ", ".join(missing))
    if _create_db_connection():
        logging.info("Database connectivity OK")
    else:
        logging.info("Database not reachable; using in-memory fallbacks where applicable")

# ---------------------------------------------------------------------------
# Demo datasets for stops and routes (replace with DB-backed queries later)
# ---------------------------------------------------------------------------
DEMO_STOPS = [
    {
        "id": "stop_1",
        "name": "Five Points",
        "lat": 33.7530,
        "lng": -84.3920,
        "demandLevel": "high",
        "currentPassengers": 65,
        "predictedDemand": 80,
        "routes": ["Red", "Gold", "Blue", "Green"],
    },
    {
        "id": "stop_2",
        "name": "Midtown",
        "lat": 33.7804,
        "lng": -84.3867,
        "demandLevel": "medium",
        "currentPassengers": 35,
        "predictedDemand": 50,
        "routes": ["Red", "Gold"],
    },
]

DEMO_ROUTES = [
    {
        "id": "Red",
        "name": "Red Line",
        "color": "#C62828",
        "stops": ["stop_1", "stop_2"],
        "coordinates": [[-84.3920, 33.7530], [-84.3867, 33.7804]],
        "capacity": 50,
        "currentLoad": 42,
        "optimization": {"efficiency": 0.94, "waitTime": 6, "coverage": 0.88},
    }
]


# ---------------------------------------------------------------------------
# Simple DB helpers for dynamic stops (best-effort, with graceful fallback)
# ---------------------------------------------------------------------------
def _create_db_connection():
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
    except Exception:
        return None


def ensure_dynamic_stops_table() -> bool:
    conn = _create_db_connection()
    if not conn:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dynamic_stops (
                        id SERIAL PRIMARY KEY,
                        lat DOUBLE PRECISION NOT NULL,
                        lon DOUBLE PRECISION NOT NULL,
                        demand_threshold INTEGER NOT NULL,
                        duration_minutes INTEGER NOT NULL,
                        routes TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        expires_at TIMESTAMP GENERATED ALWAYS AS (created_at + (duration_minutes || ' minutes')::interval) STORED,
                        status VARCHAR(20) DEFAULT 'active'
                    );
                    """
                )
        return True
    finally:
        conn.close()


IN_MEMORY_DYNAMIC_STOPS: List[Dict] = []


@app.get("/health")
def health() -> Dict[str, object]:
    return {
        "status": "ok",
        "database_connected": bool(_create_db_connection()),
        "ml_models_loaded": False,    # TODO: wire real check
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/stops")
def get_stops() -> List[Dict]:
    return DEMO_STOPS


@app.get("/routes")
def get_routes() -> List[Dict]:
    return DEMO_ROUTES


@app.get("/heatmap")
def get_heatmap(
    time_scope: str = Query("current", alias="time"),
    zoom: int = Query(12, ge=0, le=22),
    bounds: Optional[str] = Query(None),
) -> Dict[str, object]:
    # Generate simple synthetic heat points
    num_points = max(10, min(100, 5 * zoom))
    data = []
    for _ in range(num_points):
        intensity = round(random.random(), 3)
        data.append({
            "intensity": intensity
        })
    return {
        "status": "ok",
        "time": time_scope,
        "zoom": zoom,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/optimize")
def optimize(req: OptimizationRequest) -> Dict[str, object]:
    try:
        # Lazy import to avoid heavy startup
        from src.optimization.route_optimizer import RouteOptimizer
        def _work():
            optimizer = RouteOptimizer()
            optimizer.load_route_data()
            optimizer.load_ml_models()
            return optimizer.run_optimization(
                route_ids=req.route_ids,
                optimization_type=req.optimization_type,
                simulation_hours=req.simulation_hours,
                bus_capacity=req.bus_capacity,
                max_short_turns=req.max_short_turns,
            )
        future = EXECUTOR.submit(_work)
        results = future.result(timeout=OPT_TIMEOUT_SEC)
        return {
            "status": "ok",
            "message": "Optimization completed",
            "optimization_results": results,
            "execution_time": results.get("execution_time", 0.0),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logging.exception("Optimization failed; returning stub")
        return {
            "status": "ok",
            "message": f"Optimization fallback (stub): {e}",
            "optimization_results": {"proposals": []},
            "execution_time": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.post("/simulate")
def simulate(req: SimulationRequest) -> Dict[str, object]:
    try:
        from src.optimization.route_simulator import RouteSimulator
        def _work():
            simulator = RouteSimulator()
            return simulator.simulate(
                optimization_proposals=req.optimization_proposals,
                simulation_hours=req.simulation_hours,
                bus_capacity=req.bus_capacity,
                passenger_demand_multiplier=req.passenger_demand_multiplier,
            )
        future = EXECUTOR.submit(_work)
        results = future.result(timeout=SIM_TIMEOUT_SEC)
        return {
            "status": "ok",
            "message": "Simulation completed",
            "simulation_results": results,
            "execution_time": results.get("execution_time", 0.0),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logging.exception("Simulation failed; returning stub")
        return {
            "status": "ok",
            "message": f"Simulation fallback (stub): {e}",
            "simulation_results": {"impacts": {}},
            "execution_time": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.post("/dynamic-stops")
def create_dynamic_stop(req: DynamicStopRequest) -> Dict[str, object]:
    if ensure_dynamic_stops_table():
        conn = _create_db_connection()
        if conn:
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO dynamic_stops (lat, lon, demand_threshold, duration_minutes, routes)
                            VALUES (%s, %s, %s, %s, %s)
                            RETURNING id, created_at, expires_at
                            """,
                            (req.lat, req.lon, req.demand_threshold, req.duration_minutes, json.dumps(req.routes or [])),
                        )
                        row = cur.fetchone()
                        return {
                            "status": "ok",
                            "message": "Dynamic stop created",
                            "stop": {
                                "id": row[0],
                                "lat": req.lat,
                                "lon": req.lon,
                                "demand_threshold": req.demand_threshold,
                                "duration_minutes": req.duration_minutes,
                                "routes": req.routes or [],
                                "created_at": row[1].isoformat(),
                                "expires_at": row[2].isoformat(),
                            },
                            "timestamp": datetime.utcnow().isoformat(),
                        }
            finally:
                conn.close()
    # Fallback to in-memory storage
    item = req.dict()
    item.update({"id": len(IN_MEMORY_DYNAMIC_STOPS) + 1})
    IN_MEMORY_DYNAMIC_STOPS.append(item)
    return {
        "status": "ok",
        "message": "Dynamic stop created (memory)",
        "stop": item,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/dynamic-stops")
def list_dynamic_stops() -> Dict[str, object]:
    conn = _create_db_connection()
    if conn and ensure_dynamic_stops_table():
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, lat, lon, demand_threshold, duration_minutes, routes, created_at, expires_at, status FROM dynamic_stops WHERE status='active'"
                    )
                    rows = cur.fetchall()
                    data = []
                    for r in rows:
                        data.append(
                            {
                                "id": r[0],
                                "lat": r[1],
                                "lon": r[2],
                                "demand_threshold": r[3],
                                "duration_minutes": r[4],
                                "routes": json.loads(r[5]) if r[5] else [],
                                "created_at": r[6].isoformat() if r[6] else None,
                                "expires_at": r[7].isoformat() if r[7] else None,
                                "status": r[8],
                            }
                        )
                    return {"stops": data}
        finally:
            conn.close()
    return {"stops": IN_MEMORY_DYNAMIC_STOPS}


@app.delete("/dynamic-stops/{stop_id}")
def delete_dynamic_stop(stop_id: int) -> Dict[str, object]:
    conn = _create_db_connection()
    if conn and ensure_dynamic_stops_table():
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE dynamic_stops SET status='expired' WHERE id=%s RETURNING id",
                        (stop_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise HTTPException(status_code=404, detail="Dynamic stop not found")
                    return {"status": "ok", "message": "Dynamic stop expired", "id": stop_id}
        finally:
            conn.close()
    # Memory fallback
    for s in IN_MEMORY_DYNAMIC_STOPS:
        if s.get("id") == stop_id:
            s["status"] = "expired"
            return {"status": "ok", "message": "Dynamic stop expired (memory)", "id": stop_id}
    raise HTTPException(status_code=404, detail="Dynamic stop not found")


# ---------------------------------------------------------------------------
# WebSocket endpoint for live vehicle updates (demo positions)
# ---------------------------------------------------------------------------
@app.websocket("/ws/vehicles")
async def vehicles_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        # Start from demo route coordinates; jitter positions
        base_coords = DEMO_ROUTES[0]["coordinates"] if DEMO_ROUTES else [[-84.3920, 33.7530]]
        lon, lat = base_coords[0]
        while True:
            # Random walk
            lat += (random.random() - 0.5) * 0.001
            lon += (random.random() - 0.5) * 0.001
            payload = {
                "vehicles": [
                    {"id": "veh_1", "lat": lat, "lon": lon, "route": "Red"}
                ],
                "timestamp": datetime.utcnow().isoformat(),
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
    except Exception:
        logging.exception("Vehicle WS error")
        try:
            await websocket.close()
        except Exception:
            pass



def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    main()


