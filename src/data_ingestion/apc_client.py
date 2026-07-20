import os
import time
from typing import Any, Dict, List, Optional

import requests

from src.config.settings import settings


class APCAPIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.apcvendor.com/v1/",
    ) -> None:
        self.api_key = api_key or settings.apc_api_key or os.getenv("APC_API_KEY")
        if not self.api_key:
            raise ValueError("APC_API_KEY is not set")
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        })

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout_seconds: int = 10,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        if params is None:
            params = {}

        last_err: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=timeout_seconds)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as err:  # type: ignore
                last_err = err
                if response.status_code == 429:  # type: ignore
                    time.sleep(backoff_factor * (2 ** attempt))
                else:
                    raise
            except requests.exceptions.RequestException as err:
                last_err = err
                time.sleep(backoff_factor * (2 ** attempt))

        if last_err:
            raise last_err
        raise RuntimeError("Unknown error performing APC API request")

    def get_realtime_occupancy(self, vehicle_id: Optional[str] = None, route_id: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if vehicle_id:
            params["vehicle_id"] = vehicle_id
        if route_id:
            params["route_id"] = route_id
        return self._make_request("occupancy/realtime", params)

    def get_historical_ridership(self, start_time: str, end_time: str, stop_id: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"start_time": start_time, "end_time": end_time}
        if stop_id:
            params["stop_id"] = stop_id
        return self._make_request("ridership/historical", params)

# src/data_ingestion/apc_client.py

import os
import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class APCAPIClient:
    """
    Client for interacting with Automated Passenger Counter (APC) API.
    Handles authentication, request formatting, error handling, and data parsing.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.apcvendor.com/v1/"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None, max_retries: int = 3, backoff_factor: float = 0.5):
        """
        Make HTTP request with retry logic and error handling.
        """
        url = f"{self.base_url}{endpoint}"
        if params is None:
            params = {}

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Too Many Requests
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Rate limit hit. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"HTTP error occurred: {e}")
                    raise
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error occurred: {e}")
                time.sleep(backoff_factor * (2 ** attempt))
            except requests.exceptions.Timeout:
                logger.error("Request timed out.")
                time.sleep(backoff_factor * (2 ** attempt))
            except requests.exceptions.RequestException as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise
        raise Exception("Failed to make request after multiple retries.")

    def get_realtime_occupancy(self, vehicle_id: str = None, route_id: str = None) -> List[Dict[str, Any]]:
        """
        Get real-time occupancy data for vehicles or routes.

        Args:
            vehicle_id: Optional specific vehicle ID
            route_id: Optional specific route ID

        Returns:
            List of occupancy data dictionaries
        """
        endpoint = "occupancy/realtime"
        params = {}
        if vehicle_id:
            params["vehicle_id"] = vehicle_id
        if route_id:
            params["route_id"] = route_id

        logger.info(f"Fetching real-time occupancy for vehicle={vehicle_id}, route={route_id}")
        return self._make_request(endpoint, params)

    def get_historical_ridership(self, start_time: str, end_time: str, stop_id: str = None) -> List[Dict[str, Any]]:
        """
        Get historical ridership data for a time period.

        Args:
            start_time: ISO format start time
            end_time: ISO format end time
            stop_id: Optional specific stop ID

        Returns:
            List of historical ridership data
        """
        endpoint = "ridership/historical"
        params = {"start_time": start_time, "end_time": end_time}
        if stop_id:
            params["stop_id"] = stop_id

        logger.info(f"Fetching historical ridership from {start_time} to {end_time}")
        return self._make_request(endpoint, params)

    def get_passenger_counts_by_stop(self, route_id: str, direction: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get passenger counts aggregated by stop.

        Args:
            route_id: Route identifier
            direction: Optional direction (inbound/outbound)

        Returns:
            List of passenger count data by stop
        """
        endpoint = "counts/by-stop"
        params = {"route_id": route_id}
        if direction:
            params["direction"] = direction

        logger.info(f"Fetching passenger counts for route {route_id}")
        return self._make_request(endpoint, params)

    def get_vehicle_occupancy_history(self, vehicle_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get occupancy history for a specific vehicle.

        Args:
            vehicle_id: Vehicle identifier
            hours: Number of hours of history to fetch

        Returns:
            List of historical occupancy data for the vehicle
        """
        endpoint = f"vehicles/{vehicle_id}/occupancy-history"
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        params = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        logger.info(f"Fetching {hours} hours of occupancy history for vehicle {vehicle_id}")
        return self._make_request(endpoint, params)

    def get_crowding_events(self, threshold: float = 0.8, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent crowding events above threshold.

        Args:
            threshold: Occupancy threshold (0.0-1.0)
            limit: Maximum number of events to return

        Returns:
            List of crowding events
        """
        endpoint = "events/crowding"
        params = {
            "threshold": threshold,
            "limit": limit
        }

        logger.info(f"Fetching crowding events above {threshold * 100}% occupancy")
        return self._make_request(endpoint, params)

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """
        Get data quality metrics for APC system.

        Returns:
            Dictionary of data quality metrics
        """
        endpoint = "metrics/data-quality"
        logger.info("Fetching APC data quality metrics")
        return self._make_request(endpoint)


# Example Usage and Testing
if __name__ == "__main__":
    # Load API key from environment
    APC_API_KEY = os.getenv("APC_API_KEY")
    if not APC_API_KEY:
        # For demo purposes, use a mock key
        logger.warning("APC_API_KEY not set, using mock data mode")
        APC_API_KEY = "mock-api-key"

    # Initialize client
    client = APCAPIClient(api_key=APC_API_KEY)

    try:
        # Example 1: Get real-time occupancy for a specific vehicle
        print("\n=== Real-time Occupancy ===")
        realtime_data = client.get_realtime_occupancy(vehicle_id="MARTA_BUS_123")
        print(f"Real-time Occupancy: {realtime_data[:2] if realtime_data else 'No data'}")

        # Example 2: Get historical ridership for the last hour
        print("\n=== Historical Ridership ===")
        end_t = datetime.now().isoformat()
        start_t = (datetime.now() - timedelta(hours=1)).isoformat()
        historical_data = client.get_historical_ridership(start_t, end_t, stop_id="FIVE_POINTS")
        print(f"Historical Ridership: {historical_data[:2] if historical_data else 'No data'}")

        # Example 3: Get passenger counts by stop for a route
        print("\n=== Passenger Counts by Stop ===")
        counts_data = client.get_passenger_counts_by_stop(route_id="RED_LINE")
        print(f"Passenger Counts: {counts_data[:2] if counts_data else 'No data'}")

        # Example 4: Get crowding events
        print("\n=== Crowding Events ===")
        crowding_events = client.get_crowding_events(threshold=0.85)
        print(f"Crowding Events: {crowding_events[:2] if crowding_events else 'No data'}")

    except Exception as e:
        logger.error(f"Error during APC data retrieval: {e}")