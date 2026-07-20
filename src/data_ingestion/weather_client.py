import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from src.config.settings import settings


class WeatherAPIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openweathermap.org/data/2.5/",
    ) -> None:
        self.api_key = api_key or settings.weather_api_key or os.getenv("WEATHER_API_KEY")
        if not self.api_key:
            raise ValueError("WEATHER_API_KEY is not set")
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout_seconds: int = 10,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        params["appid"] = self.api_key

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
            except requests.exceptions.RequestException as err:  # network errors
                last_err = err
                time.sleep(backoff_factor * (2 ** attempt))

        if last_err:
            raise last_err
        raise RuntimeError("Unknown error performing weather API request")

    def get_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        return self._make_request("weather", {"lat": lat, "lon": lon, "units": "metric"})

    def get_hourly_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        return self._make_request(
            "onecall",
            {"lat": lat, "lon": lon, "exclude": "current,minutely,daily,alerts", "units": "metric"},
        )

    def get_historical_weather(self, lat: float, lon: float, dt: datetime) -> Dict[str, Any]:
        return self._make_request(
            "onecall/timemachine",
            {"lat": lat, "lon": lon, "dt": int(dt.timestamp()), "units": "metric"},
        )



