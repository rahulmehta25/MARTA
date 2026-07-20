"""
MARTA Real-time rail arrivals API endpoints using live data.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import logging

from src.services.marta_api import marta_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/rail/arrivals")
async def get_rail_arrivals(
    station: Optional[str] = Query(None, description="Filter by station name"),
    line: Optional[str] = Query(None, description="Filter by line (RED, GOLD, GREEN, BLUE)"),
    direction: Optional[str] = Query(None, description="Filter by direction (N, S, E, W)")
) -> List[Dict[str, Any]]:
    """
    Get real-time rail arrival predictions from MARTA API.
    
    Returns upcoming train arrivals with real-time data.
    """
    try:
        # Fetch real-time data from MARTA
        arrivals = await marta_service.get_real_time_rail_arrivals()
        
        if not arrivals:
            logger.warning("No arrivals data received from MARTA API")
            return []
        
        # Apply filters if provided
        filtered_arrivals = arrivals
        
        if station:
            station_upper = station.upper()
            filtered_arrivals = [
                a for a in filtered_arrivals 
                if station_upper in a.get("station", "").upper()
            ]
        
        if line:
            line_upper = line.upper()
            filtered_arrivals = [
                a for a in filtered_arrivals 
                if a.get("line", "").upper() == line_upper
            ]
        
        if direction:
            direction_upper = direction.upper()
            filtered_arrivals = [
                a for a in filtered_arrivals 
                if a.get("direction", "").upper() == direction_upper
            ]
        
        # Sort by waiting time
        filtered_arrivals.sort(
            key=lambda x: int(x.get("waiting_seconds", "999999"))
        )
        
        return filtered_arrivals
        
    except Exception as e:
        logger.error(f"Error fetching rail arrivals: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch real-time data")


@router.get("/rail/stations")
async def get_stations() -> List[Dict[str, Any]]:
    """
    Get list of all MARTA rail stations with current arrival information.
    """
    try:
        # Fetch real-time data
        arrivals = await marta_service.get_real_time_rail_arrivals()
        
        # Group by station
        stations_data = {}
        for arrival in arrivals:
            station = arrival.get("station", "Unknown")
            if station not in stations_data:
                stations_data[station] = {
                    "name": station,
                    "code": marta_service.get_station_code(station),
                    "trains": [],
                    "lines": set()
                }
            
            stations_data[station]["trains"].append({
                "line": arrival.get("line"),
                "destination": arrival.get("destination"),
                "direction": arrival.get("direction"),
                "waiting_time": arrival.get("waiting_time"),
                "next_arrival": arrival.get("next_arrival")
            })
            
            if arrival.get("line"):
                stations_data[station]["lines"].add(arrival.get("line"))
        
        # Convert to list and clean up
        stations = []
        for station_name, data in stations_data.items():
            stations.append({
                "name": data["name"],
                "code": data["code"],
                "lines": list(data["lines"]),
                "upcoming_trains": data["trains"][:5]  # Limit to next 5 trains
            })
        
        # Sort by station name
        stations.sort(key=lambda x: x["name"])
        
        return stations
        
    except Exception as e:
        logger.error(f"Error fetching stations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch station data")


@router.get("/rail/lines")
async def get_lines() -> Dict[str, Any]:
    """
    Get information about MARTA rail lines and their current status.
    """
    try:
        # Fetch real-time data
        arrivals = await marta_service.get_real_time_rail_arrivals()
        
        # Group by line
        lines_data = {
            "RED": {"name": "Red Line", "color": "#EF3E42", "stations": set(), "trains": 0},
            "GOLD": {"name": "Gold Line", "color": "#F9A51A", "stations": set(), "trains": 0},
            "GREEN": {"name": "Green Line", "color": "#00B251", "stations": set(), "trains": 0},
            "BLUE": {"name": "Blue Line", "color": "#0075C9", "stations": set(), "trains": 0}
        }
        
        for arrival in arrivals:
            line = arrival.get("line", "").upper()
            if line in lines_data:
                lines_data[line]["stations"].add(arrival.get("station"))
                if arrival.get("train_id"):
                    lines_data[line]["trains"] += 1
        
        # Convert sets to lists
        for line in lines_data:
            lines_data[line]["stations"] = sorted(list(lines_data[line]["stations"]))
            lines_data[line]["active"] = lines_data[line]["trains"] > 0
        
        return {
            "lines": lines_data,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching lines data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch lines data")


@router.get("/rail/next-train/{station}")
async def get_next_train(
    station: str,
    line: Optional[str] = Query(None, description="Filter by specific line")
) -> Dict[str, Any]:
    """
    Get the next train arriving at a specific station.
    """
    try:
        # Fetch real-time data
        arrivals = await marta_service.get_real_time_rail_arrivals()
        
        # Filter by station
        station_upper = station.upper()
        station_arrivals = [
            a for a in arrivals 
            if station_upper in a.get("station", "").upper()
        ]
        
        if not station_arrivals:
            raise HTTPException(status_code=404, detail=f"No data found for station: {station}")
        
        # Filter by line if specified
        if line:
            line_upper = line.upper()
            station_arrivals = [
                a for a in station_arrivals 
                if a.get("line", "").upper() == line_upper
            ]
        
        if not station_arrivals:
            return {
                "station": station,
                "message": "No upcoming trains found",
                "line_filter": line
            }
        
        # Sort by waiting time and get the next one
        station_arrivals.sort(
            key=lambda x: int(x.get("waiting_seconds", "999999"))
        )
        next_train = station_arrivals[0]
        
        return {
            "station": next_train.get("station"),
            "line": next_train.get("line"),
            "destination": next_train.get("destination"),
            "direction": next_train.get("direction"),
            "waiting_time": next_train.get("waiting_time"),
            "next_arrival": next_train.get("next_arrival"),
            "train_id": next_train.get("train_id"),
            "delay": next_train.get("delay")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching next train: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch next train data")


@router.get("/rail/status")
async def get_system_status() -> Dict[str, Any]:
    """
    Get overall MARTA rail system status.
    """
    try:
        # Fetch real-time data
        arrivals = await marta_service.get_real_time_rail_arrivals()
        
        if not arrivals:
            return {
                "status": "unknown",
                "message": "No data available",
                "last_updated": datetime.now().isoformat()
            }
        
        # Calculate statistics
        total_trains = len(set(a.get("train_id") for a in arrivals if a.get("train_id")))
        total_stations = len(set(a.get("station") for a in arrivals))
        
        # Check for delays
        delays = [a for a in arrivals if "delay" in a.get("delay", "").lower()]
        
        status = "normal"
        if len(delays) > len(arrivals) * 0.3:  # More than 30% delayed
            status = "delays"
        elif len(delays) > len(arrivals) * 0.1:  # More than 10% delayed
            status = "minor_delays"
        
        return {
            "status": status,
            "active_trains": total_trains,
            "stations_with_service": total_stations,
            "total_arrivals": len(arrivals),
            "delayed_arrivals": len(delays),
            "last_updated": datetime.now().isoformat(),
            "lines_status": {
                "RED": len([a for a in arrivals if a.get("line") == "RED"]) > 0,
                "GOLD": len([a for a in arrivals if a.get("line") == "GOLD"]) > 0,
                "GREEN": len([a for a in arrivals if a.get("line") == "GREEN"]) > 0,
                "BLUE": len([a for a in arrivals if a.get("line") == "BLUE"]) > 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system status")