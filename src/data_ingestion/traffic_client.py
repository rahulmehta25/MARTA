import os
import time
from typing import Any, Dict, Optional

import requests

from src.config.settings import settings


class TomTomTrafficAPIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.tomtom.com/traffic/flow/4/json/",
    ) -> None:
        self.api_key = api_key or settings.traffic_api_key or os.getenv("TRAFFIC_API_KEY")
        if not self.api_key:
            raise ValueError("TRAFFIC_API_KEY is not set")
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
        params["key"] = self.api_key

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
        raise RuntimeError("Unknown error performing traffic API request")

    def get_traffic_flow(self, point: str) -> Dict[str, Any]:
        # point example: "33.64,-84.55,33.88,-84.28" or lat,lon depending on endpoint
        return self._make_request(
            "flowSegmentData",
            {
                "point": point,
                "unit": "KMPH",
                "openLr": "false",
                "jsonp": "false",
            },
        )



