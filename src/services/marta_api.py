"""
MARTA API Service for fetching real-time rail data.
"""
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.config.settings import settings

logger = logging.getLogger(__name__)


class MARTAAPIService:
    """Service for interacting with MARTA's real-time rail API."""
    
    def __init__(self):
        self.api_key = settings.marta_api_key
        self.base_url = "https://developerservices.itsmarta.com:18096"
        self.rail_endpoint = f"{self.base_url}/itsmarta/railrealtimearrivals/developerservices/traindata"
        
    async def get_real_time_rail_arrivals(self) -> List[Dict[str, Any]]:
        """
        Fetch real-time rail arrival data from MARTA API.
        
        Returns:
            List of train arrival data dictionaries
        """
        if not self.api_key:
            logger.error("MARTA API key not configured")
            return []
        
        url = f"{self.rail_endpoint}?apiKey={self.api_key}"
        
        try:
            async with httpx.AsyncClient(verify=False) as client:  # verify=False for MARTA's self-signed cert
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                
                data = response.json()
                
                # MARTA API returns data in a specific format
                # We need to parse and transform it
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
                    arrivals.append(arrival)
                
                logger.info(f"Fetched {len(arrivals)} real-time arrivals from MARTA API")
                return arrivals
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching MARTA data: {e}")
            return []
        except httpx.ConnectError as e:
            logger.error(f"Connection error to MARTA API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching MARTA data: {e}")
            return []
    
    def parse_arrival_time(self, time_str: str) -> Optional[datetime]:
        """
        Parse MARTA's time format to datetime.
        
        Args:
            time_str: Time string from MARTA API (e.g., "12:34:56 PM")
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        try:
            # MARTA uses format like "12:34:56 PM"
            return datetime.strptime(time_str, "%I:%M:%S %p")
        except (ValueError, TypeError):
            logger.warning(f"Could not parse time: {time_str}")
            return None
    
    def get_station_code(self, station_name: str) -> str:
        """
        Convert station name to station code.
        
        Args:
            station_name: Full station name
            
        Returns:
            Station code or original name if not found
        """
        # MARTA station mapping
        station_codes = {
            "AIRPORT STATION": "AIRPORT",
            "ARTS CENTER STATION": "ARTS_CENTER",
            "ASHBY STATION": "ASHBY",
            "AVONDALE STATION": "AVONDALE",
            "BANKHEAD STATION": "BANKHEAD",
            "BROOKHAVEN STATION": "BROOKHAVEN",
            "BUCKHEAD STATION": "BUCKHEAD",
            "CHAMBLEE STATION": "CHAMBLEE",
            "CIVIC CENTER STATION": "CIVIC_CENTER",
            "COLLEGE PARK STATION": "COLLEGE_PARK",
            "DECATUR STATION": "DECATUR",
            "DORAVILLE STATION": "DORAVILLE",
            "DUNWOODY STATION": "DUNWOODY",
            "EAST LAKE STATION": "EAST_LAKE",
            "EAST POINT STATION": "EAST_POINT",
            "EDGEWOOD CANDLER PARK STATION": "EDGEWOOD",
            "FIVE POINTS STATION": "FIVE_POINTS",
            "GARNETT STATION": "GARNETT",
            "GEORGIA STATE STATION": "GEORGIA_STATE",
            "HAMILTON E HOLMES STATION": "HE_HOLMES",
            "INDIAN CREEK STATION": "INDIAN_CREEK",
            "INMAN PARK STATION": "INMAN_PARK",
            "KENSINGTON STATION": "KENSINGTON",
            "KING MEMORIAL STATION": "KING_MEMORIAL",
            "LAKEWOOD STATION": "LAKEWOOD",
            "LENOX STATION": "LENOX",
            "LINDBERGH STATION": "LINDBERGH",
            "MEDICAL CENTER STATION": "MEDICAL_CENTER",
            "MIDTOWN STATION": "MIDTOWN",
            "NORTH AVE STATION": "NORTH_AVE",
            "NORTH SPRINGS STATION": "NORTH_SPRINGS",
            "OAKLAND CITY STATION": "OAKLAND_CITY",
            "OMNI DOME STATION": "OMNI",
            "PEACHTREE CENTER STATION": "PEACHTREE_CENTER",
            "SANDY SPRINGS STATION": "SANDY_SPRINGS",
            "VINE CITY STATION": "VINE_CITY",
            "WEST END STATION": "WEST_END",
            "WEST LAKE STATION": "WEST_LAKE"
        }
        
        return station_codes.get(station_name.upper(), station_name)
    
    def get_line_color(self, line: str) -> str:
        """
        Get the color associated with a MARTA line.
        
        Args:
            line: Line identifier (RED, GOLD, GREEN, BLUE)
            
        Returns:
            Hex color code for the line
        """
        colors = {
            "RED": "#EF3E42",
            "GOLD": "#F9A51A",
            "GREEN": "#00B251",
            "BLUE": "#0075C9"
        }
        return colors.get(line.upper(), "#808080")  # Default to gray


# Singleton instance
marta_service = MARTAAPIService()