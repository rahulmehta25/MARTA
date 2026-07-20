"""API endpoints for ML predictions and optimization."""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from src.ml.demand_forecaster import DemandForecaster, DemandPrediction
from src.ml.overcrowding_detector import OvercrowdingDetector, CrowdingAlert
from src.ml.route_optimizer import RouteOptimizer, OptimizedRoute
from src.ml.surge_predictor import SurgePredictor, SurgePrediction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])

# Initialize ML models
demand_forecaster = DemandForecaster()
overcrowding_detector = OvercrowdingDetector()
route_optimizer = RouteOptimizer()
surge_predictor = SurgePredictor()

# Pydantic models for requests/responses
class DemandForecastRequest(BaseModel):
    stop_id: str
    start_time: Optional[datetime] = Field(default_factory=datetime.now)
    horizon_hours: int = Field(default=24, ge=1, le=168)

class DemandForecastResponse(BaseModel):
    stop_id: str
    predictions: List[Dict]
    model_confidence: float
    last_updated: datetime

class CrowdingCheckRequest(BaseModel):
    stop_id: str
    route_id: str
    passenger_count: int
    vehicle_type: str = "bus_standard"

class RouteOptimizationRequest(BaseModel):
    route_id: str
    optimization_goals: List[str] = ["minimize_wait_time", "minimize_crowding"]
    constraints: Optional[Dict] = None

class SurgePredictionRequest(BaseModel):
    location_id: str
    current_demand: float
    historical_baseline: float
    external_factors: Optional[Dict] = None

@router.post("/demand/forecast", response_model=DemandForecastResponse)
async def forecast_demand(request: DemandForecastRequest):
    """Generate demand forecast for a stop."""
    try:
        # Generate predictions
        predictions = demand_forecaster.predict(
            stop_id=request.stop_id,
            start_time=request.start_time,
            horizon_hours=request.horizon_hours
        )

        # Convert to response format
        prediction_dicts = [
            {
                "timestamp": pred.timestamp.isoformat(),
                "predicted_demand": pred.predicted_demand,
                "confidence_lower": pred.confidence_lower,
                "confidence_upper": pred.confidence_upper,
                "surge_probability": pred.surge_probability,
                "overcrowding_risk": pred.overcrowding_risk
            }
            for pred in predictions
        ]

        return DemandForecastResponse(
            stop_id=request.stop_id,
            predictions=prediction_dicts,
            model_confidence=0.85,  # Would calculate actual confidence
            last_updated=datetime.now()
        )

    except Exception as e:
        logger.error(f"Demand forecast failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crowding/detect")
async def detect_crowding(request: CrowdingCheckRequest):
    """Check for overcrowding at a stop/vehicle."""
    try:
        alert = overcrowding_detector.detect_crowding(
            occupancy_data={
                "passenger_count": request.passenger_count,
                "vehicle_type": request.vehicle_type
            },
            stop_id=request.stop_id,
            route_id=request.route_id
        )

        if alert:
            return {
                "status": "alert",
                "crowding_level": alert.crowding_level.value,
                "current_occupancy": alert.current_occupancy,
                "capacity": alert.capacity,
                "occupancy_percentage": (alert.current_occupancy / alert.capacity * 100),
                "predicted_duration_minutes": alert.predicted_duration_minutes,
                "recommended_actions": alert.recommended_actions,
                "affected_stops": alert.affected_stops_downstream,
                "alternatives": alert.alternative_routes
            }
        else:
            return {
                "status": "normal",
                "message": "No overcrowding detected"
            }

    except Exception as e:
        logger.error(f"Crowding detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/crowding/propagation/{route_id}")
async def predict_crowding_propagation(
    route_id: str,
    initial_stop: str = Query(..., description="Stop where crowding starts"),
    horizon_minutes: int = Query(30, description="Prediction horizon in minutes")
):
    """Predict how crowding will propagate along a route."""
    try:
        predictions = overcrowding_detector.predict_crowding_propagation(
            initial_stop=initial_stop,
            route_id=route_id,
            time_horizon_minutes=horizon_minutes
        )

        return {
            "route_id": route_id,
            "initial_stop": initial_stop,
            "predictions": predictions,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Propagation prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/route/optimize")
async def optimize_route(
    request: RouteOptimizationRequest,
    background_tasks: BackgroundTasks
):
    """Optimize a route configuration."""
    try:
        # Run optimization (this could be async in production)
        optimized = route_optimizer.optimize_route(
            route_id=request.route_id,
            demand_forecast=[],  # Would fetch actual forecast
            constraints=request.constraints
        )

        return {
            "route_id": optimized.route_id,
            "optimized_frequency": optimized.frequency_minutes,
            "vehicle_count": len(optimized.vehicle_assignments),
            "expected_wait_time": optimized.expected_wait_time,
            "expected_travel_time": optimized.expected_travel_time,
            "improvement_percentage": optimized.improvement_percentage,
            "modifications": optimized.modifications,
            "status": "optimized"
        }

    except Exception as e:
        logger.error(f"Route optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/surge/predict")
async def predict_surge(request: SurgePredictionRequest):
    """Predict demand surge at a location."""
    try:
        prediction = surge_predictor.predict_surge(
            location_id=request.location_id,
            current_demand=request.current_demand,
            historical_baseline=request.historical_baseline,
            external_factors=request.external_factors
        )

        if prediction:
            return {
                "surge_detected": True,
                "location_id": prediction.location_id,
                "surge_start_time": prediction.surge_start_time.isoformat(),
                "surge_magnitude": prediction.surge_magnitude,
                "confidence": prediction.confidence,
                "contributing_factors": prediction.contributing_factors,
                "affected_areas": prediction.affected_areas,
                "recommended_actions": prediction.recommended_actions
            }
        else:
            return {
                "surge_detected": False,
                "location_id": request.location_id,
                "message": "No surge predicted"
            }

    except Exception as e:
        logger.error(f"Surge prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/surge/realtime")
async def detect_realtime_surges():
    """Detect emerging surges from real-time data."""
    try:
        # Would fetch actual real-time data
        mock_realtime_data = {
            "stop_1": {"demand": 150, "timestamp": datetime.now().isoformat()},
            "stop_2": {"demand": 200, "timestamp": datetime.now().isoformat()},
            "stop_3": {"demand": 75, "timestamp": datetime.now().isoformat()}
        }

        emerging_surges = surge_predictor.detect_emerging_surge(
            real_time_data=mock_realtime_data
        )

        return {
            "emerging_surges": emerging_surges,
            "scan_time": datetime.now().isoformat(),
            "locations_monitored": len(mock_realtime_data)
        }

    except Exception as e:
        logger.error(f"Real-time surge detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/surge/forecast")
async def get_surge_forecast(
    horizon_hours: int = Query(4, ge=1, le=24, description="Forecast horizon in hours")
):
    """Get surge forecast for the next N hours."""
    try:
        forecast = surge_predictor.get_surge_forecast(horizon_hours)

        return {
            "forecast": forecast,
            "generated_at": datetime.now().isoformat(),
            "horizon_hours": horizon_hours
        }

    except Exception as e:
        logger.error(f"Surge forecast failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fleet/reposition")
async def reposition_fleet(
    surge_locations: List[str],
    available_vehicles: List[str]
):
    """Generate fleet repositioning commands for surge response."""
    try:
        # Mock current positions
        current_positions = {
            vehicle: f"depot_{i % 3}"
            for i, vehicle in enumerate(available_vehicles)
        }

        # Mock surge data
        demand_surge = {
            location: {
                "surge_magnitude": 2.5 - (i * 0.3),
                "urgency": "high" if i == 0 else "normal"
            }
            for i, location in enumerate(surge_locations)
        }

        commands = route_optimizer.reposition_vehicles(
            current_positions=current_positions,
            demand_surge=demand_surge,
            available_vehicles=available_vehicles
        )

        return {
            "repositioning_commands": commands,
            "vehicles_repositioned": len(commands),
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Fleet repositioning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/ml-status")
async def get_ml_system_status():
    """Get overall ML system status."""
    try:
        crowding_status = overcrowding_detector.get_system_status()

        return {
            "status": "operational",
            "models": {
                "demand_forecaster": "ready",
                "overcrowding_detector": "ready",
                "route_optimizer": "ready",
                "surge_predictor": "ready"
            },
            "crowding_status": crowding_status,
            "last_update": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/patterns/{stop_id}")
async def analyze_stop_patterns(
    stop_id: str,
    days: int = Query(30, description="Days of historical data to analyze")
):
    """Analyze historical patterns for a stop."""
    try:
        # Would fetch actual historical data
        mock_historical = [
            {
                "timestamp": (datetime.now() - timedelta(days=i)).isoformat(),
                "occupancy_ratio": 0.7 + (0.3 * (i % 7 == 0)),
                "duration_minutes": 20 + (i % 10),
                "magnitude": 1.5 + (0.5 * (i % 5 == 0))
            }
            for i in range(days)
        ]

        patterns = overcrowding_detector.analyze_patterns(
            historical_data=mock_historical,
            stop_id=stop_id
        )

        surge_patterns = surge_predictor.analyze_surge_patterns(
            historical_data=mock_historical,
            location_id=stop_id
        )

        return {
            "stop_id": stop_id,
            "crowding_patterns": patterns,
            "surge_patterns": surge_patterns,
            "analysis_period_days": days,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Pattern analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))