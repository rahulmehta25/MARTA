# External Services and APIs Reference Guide

This document provides a detailed reference for the external services and APIs required to make the MARTA Transit Analytics Platform fully production-ready. It covers Weather APIs, Traffic Data APIs, Automated Passenger Counter (APC) systems, and Social Media Sentiment Analysis APIs, outlining their purpose, recommended providers, and key considerations for integration.

## 1. Weather APIs

**Purpose:** To provide current, forecast, and historical weather conditions, which are crucial inputs for demand forecasting models and for contextualizing operational decisions. Weather events significantly impact transit ridership and operational efficiency.

**Recommended Providers:**

*   **OpenWeatherMap:**
    *   **Key Features:** Offers a comprehensive set of APIs, including the One Call API 3.0 (current, minute, hourly, daily forecast, and historical data) and a dedicated History API for hourly historical weather data. Supports JSON and CSV formats.
    *   **Considerations:** Good for both beginners and professionals. Free tier available for limited usage, paid plans for higher request volumes and more features. Requires API key.
    *   **Documentation:** [https://openweathermap.org/api](https://openweathermap.org/api)

*   **Tomorrow.io:**
    *   **Key Features:** Positioned as a leading weather API with 80+ data layers. Offers highly accurate current conditions, short-term forecasts (nowcasting), and extensive historical weather data (hourly and daily up to twenty years back).
    *   **Considerations:** Enterprise-grade solution, often cited for accuracy and actionable insights. May have higher costs compared to basic providers. Requires API key.
    *   **Documentation:** [https://www.tomorrow.io/weather-api/](https://www.tomorrow.io/weather-api/)

*   **Visual Crossing:**
    *   **Key Features:** Provides a fast, free, and simple weather API for history and forecast data. Includes current conditions, alerts, hourly, sub-hourly, and daily data worldwide.
    *   **Considerations:** User-friendly and good for quick integration. Free tier available. Requires API key.
    *   **Documentation:** [https://www.visualcrossing.com/weather-api/](https://www.visualcrossing.com/weather-api/)

*   **Open-Meteo.com:**
    *   **Key Features:** Free and open-source weather API, ideal for non-commercial use, and does not require an API key. Offers a Historical Weather API based on reanalysis datasets, combining various observations.
    *   **Considerations:** Excellent for projects with budget constraints or for initial prototyping. Might have limitations on commercial use or advanced features compared to paid services.
    *   **Documentation:** [https://open-meteo.com/](https://open-meteo.com/)

**Integration Strategy:**

1.  **Selection:** Choose a provider based on data granularity needs, historical data requirements, budget, and ease of integration.
2.  **API Key Management:** Securely store the API key as an environment variable (e.g., `WEATHER_API_KEY`) in Supabase secrets or the deployment environment.
3.  **Python Client:** Develop a dedicated Python client (`src/data_ingestion/weather_client.py`) to handle API requests, error handling, and rate limiting.
4.  **Scheduled Ingestion:** Implement scheduled jobs (e.g., cron jobs, Airflow tasks) to fetch current weather data every 15-30 minutes, hourly/daily forecasts, and historical data as needed.
5.  **Database Storage:** Store ingested weather data in a dedicated `weather_data` table in the Supabase PostgreSQL database, with appropriate indexing on `timestamp` and `location`.

### Example Python Client for OpenWeatherMap

```python
# src/data_ingestion/weather_client.py (simplified for reference)

import os
import requests
import time
from datetime import datetime, timedelta

class WeatherAPIClient:
    def __init__(self, api_key: str, base_url: str = "https://api.openweathermap.org/data/2.5/"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _make_request(self, endpoint: str, params: dict, max_retries: int = 3, backoff_factor: float = 0.5):
        url = f"{self.base_url}{endpoint}"
        params["appid"] = self.api_key

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    time.sleep(backoff_factor * (2 ** attempt))
                else:
                    raise
            except requests.exceptions.RequestException as e:
                raise
        raise Exception("Failed to make request after multiple retries.")

    def get_current_weather(self, lat: float, lon: float):
        endpoint = "weather"
        params = {"lat": lat, "lon": lon, "units": "metric"}
        return self._make_request(endpoint, params)

    def get_hourly_forecast(self, lat: float, lon: float):
        endpoint = "onecall"
        params = {"lat": lat, "lon": lon, "exclude": "current,minutely,daily,alerts", "units": "metric"}
        return self._make_request(endpoint, params)

    def get_historical_weather(self, lat: float, lon: float, dt: datetime):
        endpoint = "onecall/timemachine"
        params = {"lat": lat, "lon": lon, "dt": int(dt.timestamp()), "units": "metric"}
        return self._make_request(endpoint, params)

# To use this client, ensure WEATHER_API_KEY is set as an environment variable.
# Example: client = WeatherAPIClient(api_key=os.getenv("WEATHER_API_KEY"))
```

## 2. Traffic Data APIs

**Purpose:** To obtain real-time and historical traffic conditions, which are vital for accurate route optimization, predicting travel times, and understanding potential delays in transit operations.

**Recommended Providers:**

*   **TomTom Traffic APIs:**
    *   **Key Features:** Integrates real-time traffic flow, incidents, and historical traffic data. Offers a specialized Traffic Stats API for in-depth analysis of historical traffic patterns.
    *   **Considerations:** Comprehensive and widely used in navigation and logistics. Provides high-quality data for various regions. Requires API key and has usage-based pricing.
    *   **Documentation:** [https://www.tomtom.com/products/traffic-apis/](https://www.tomtom.com/products/traffic-apis/)

*   **HERE Traffic APIs:**
    *   **Key Features:** Provides real-time traffic information (flow, incidents) and Traffic Analytics for historical traffic information, leveraging speed and volume data from GPS probe data.
    *   **Considerations:** Another industry leader with robust mapping and location services. Offers detailed traffic insights. Requires API key and has usage-based pricing.
    *   **Documentation:** [https://www.here.com/docs/category/maps-traffic](https://www.here.com/docs/category/maps-traffic)

*   **Google Maps Platform (Routes API):**
    *   **Key Features:** Offers traffic data as part of its routing services, with options to control the quality of response data versus latency. Known for its accurate and frequently updated road network and traffic information.
    *   **Considerations:** Part of the broader Google Maps Platform, which might be beneficial if other mapping services are also needed. Usage is metered and requires API key.
    *   **Documentation:** [https://developers.google.com/maps/documentation/routes/config_trade_offs](https://developers.google.com/maps/documentation/routes/config_trade_offs)

**Integration Strategy:**

1.  **Selection:** Choose a provider based on coverage area, data granularity (e.g., segment-level traffic), real-time update frequency, and pricing model.
2.  **API Key Management:** Securely store the API key as an environment variable (e.g., `TRAFFIC_API_KEY`).
3.  **Python Client:** Develop a dedicated Python client (`src/data_ingestion/traffic_client.py`) to handle API requests, authentication, and rate limiting.
4.  **Scheduled Ingestion:** Implement scheduled jobs to fetch real-time traffic flow data for relevant MARTA routes every 1-5 minutes and traffic incident data as frequently as possible. Historical data should be ingested for model training.
5.  **Database Storage:** Store ingested traffic data in `traffic_flow` and `traffic_incidents` tables in Supabase, with appropriate indexing on `timestamp` and `road_segment_id`.
6.  **Route Segment Mapping:** Map MARTA routes and stops to the traffic API\'s road segments to ensure accurate data correlation.

### Example Python Client for TomTom Traffic API

```python
# src/data_ingestion/traffic_client.py (simplified for reference)

import os
import requests
import time

class TomTomTrafficAPIClient:
    def __init__(self, api_key: str, base_url: str = "https://api.tomtom.com/traffic/flow/4/json/"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _make_request(self, endpoint: str, params: dict, max_retries: int = 3, backoff_factor: float = 0.5):
        url = f"{self.base_url}{endpoint}"
        params["key"] = self.api_key

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    time.sleep(backoff_factor * (2 ** attempt))
                else:
                    raise
            except requests.exceptions.RequestException as e:
                raise
        raise Exception("Failed to make request after multiple retries.")

    def get_traffic_flow(self, bounding_box: str):
        endpoint = "flowSegmentData"
        params = {
            "key": self.api_key,
            "point": bounding_box,
            "unit": "KMPH",
            "openLr": "false",
            "jsonp": "false"
        }
        return self._make_request(endpoint, params)

# To use this client, ensure TOMTOM_API_KEY is set as an environment variable.
# Example: client = TomTomTrafficAPIClient(api_key=os.getenv("TOMTOM_API_KEY"))
```
## 3. Automated Passenger Counter (APC) Systems

**Purpose:** To provide real-time and historical passenger boarding and alighting data, enabling accurate occupancy monitoring, overcrowding detection, and ridership analysis. This is a critical component for the platform's core ML features.

**Recommended Providers/Approaches:**

*   **Swiftly (APC Connector):**
    *   **Key Features:** Swiftly offers a data platform specifically for public transit, including an 


APC Connector that allows transit agencies to connect their APC units directly to the internet. This provides access to historical ridership data and real-time crowding information.
    *   **Considerations:** This is a highly relevant solution as it's designed for transit. Integration would likely involve setting up data feeds or API access through Swiftly's platform. This is a specialized service rather than a generic API.
    *   **Documentation:** [https://www.goswift.ly/](https://www.goswift.ly/)

*   **Specialized APC Vendors (e.g., V-Count, Parquery, Passio Technologies):**
    *   **Key Features:** These companies provide hardware and software solutions for automated passenger counting. Their systems typically offer dashboards, reports, and often provide mechanisms for data export or API access to the collected passenger data.
    *   **Considerations:** Integration would depend on the specific vendor MARTA uses. It might involve direct API calls, SFTP transfers of data files, or custom data connectors. Direct engagement with MARTA's IT and operations teams would be necessary to understand their existing APC infrastructure and data access capabilities.

**Integration Strategy:**

1.  **MARTA Engagement:** The first step is to collaborate with MARTA to identify their current APC system vendor and understand the available data access methods (API, data dumps, real-time streams).
2.  **Data Access Protocol:** Based on MARTA's capabilities, establish a secure data access protocol (e.g., API keys, SSH for SFTP, cloud storage access credentials).
3.  **Python Client/Ingestor:** Develop a dedicated Python client (`src/data_ingestion/apc_client.py` or `src/data_ingestion/apc_file_ingestor.py`) to retrieve and process APC data.
4.  **Real-time vs. Batch:** Determine if real-time data streams are available for immediate occupancy updates or if batch processing of historical data files is the primary method.
5.  **Data Transformation:** Implement robust data transformation logic to map raw APC data to the platform's data models, ensuring consistency with vehicle IDs, routes, stops, and timestamps.
6.  **Database Storage:** Store processed APC data in dedicated tables (e.g., `passenger_counts`, `vehicle_occupancy`) in the Supabase PostgreSQL database, with appropriate indexing and RLS policies.

### Example Python Client for APC System

```python
# src/data_ingestion/apc_client.py (simplified for reference)

import os
import requests
import time
from typing import List, Dict, Any

class APCAPIClient:
    def __init__(self, api_key: str, base_url: str = "https://api.apcvendor.com/v1/"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None, max_retries: int = 3, backoff_factor: float = 0.5):
        url = f"{self.base_url}{endpoint}"
        if params is None:
            params = {}

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    time.sleep(backoff_factor * (2 ** attempt))
                else:
                    raise
            except requests.exceptions.RequestException as e:
                raise
        raise Exception("Failed to make request after multiple retries.")

    def get_realtime_occupancy(self, vehicle_id: str = None, route_id: str = None) -> List[Dict[str, Any]]:
        endpoint = "occupancy/realtime"
        params = {}
        if vehicle_id: params["vehicle_id"] = vehicle_id
        if route_id: params["route_id"] = route_id
        return self._make_request(endpoint, params)

    def get_historical_ridership(self, start_time: str, end_time: str, stop_id: str = None) -> List[Dict[str, Any]]:
        endpoint = "ridership/historical"
        params = {"start_time": start_time, "end_time": end_time}
        if stop_id: params["stop_id"] = stop_id
        return self._make_request(endpoint, params)

# To use this client, ensure APC_API_KEY is set as an environment variable.
# Example: client = APCAPIClient(api_key=os.getenv("APC_API_KEY"))
```

## 4. Social Media Sentiment Analysis APIs

**Purpose:** To analyze public sentiment from social media data, providing insights into public perception of MARTA services, identifying emerging issues, or understanding the impact of specific events.

**Recommended Providers:**

*   **Google Cloud Natural Language API:**
    *   **Key Features:** Offers powerful sentiment analysis capabilities, inspecting text to identify the prevailing emotional opinion (positive, negative, neutral) and magnitude. Part of Google Cloud's broader AI/ML services.
    *   **Considerations:** Highly accurate and scalable. Integrates well with other Google Cloud services. Usage-based pricing. Requires Google Cloud project setup and authentication.
    *   **Documentation:** [https://cloud.google.com/natural-language/docs/analyzing-sentiment](https://cloud.google.com/natural-language/docs/analyzing-sentiment)

*   **AssemblyAI Sentiment Analysis API:**
    *   **Key Features:** Specializes in AI for audio and text. Their sentiment analysis API is designed for ease of use and accuracy. Often cited as a top choice for sentiment analysis.
    *   **Considerations:** May offer specific advantages for processing text derived from speech (if audio analysis is ever considered). Requires API key and has usage-based pricing.
    *   **Documentation:** [https://www.assemblyai.com/](https://www.assemblyai.com/)

*   **OpenAI API (GPT Models):**
    *   **Key Features:** While not a dedicated sentiment analysis API, OpenAI's large language models (LLMs) like GPT-3.5 or GPT-4 can be prompted to perform highly nuanced sentiment analysis, including aspect-based sentiment and emotion detection.
    *   **Considerations:** Offers flexibility and can handle complex contextual understanding. Requires careful prompt engineering to ensure consistent results. Usage is token-based pricing. Requires API key.
    *   **Documentation:** [https://openai.com/docs/api-reference/sentiment](https://openai.com/docs/api-reference/sentiment) (Note: Direct sentiment API might not be explicitly listed, but LLMs can perform this task).

**Integration Strategy:**

1.  **Data Collection:** First, social media data needs to be collected. This can be done via:
    *   **Social Media Platform APIs:** (e.g., Twitter API for tweets, potentially other platforms if available). Note that access to these APIs can be restricted or require specific approvals.
    *   **Web Scraping Tools:** Tools like Apify can be used to scrape public comments from platforms like Facebook, Instagram, or TikTok, though this requires adherence to terms of service and legal considerations.
2.  **API Key Management:** Securely store API keys for the chosen sentiment analysis provider and any social media data collection APIs.
3.  **Python Client:** Develop a Python client (`src/services/sentiment_analyzer.py`) to send collected text data to the sentiment analysis API and parse the results.
4.  **Scheduled Processing:** Implement scheduled jobs to periodically collect social media data and process it for sentiment. This might be less real-time than other data sources due to API limitations o5.  **Database Storage:** Store sentiment analysis results (e.g., text, sentiment score, detected entities, associated metadata like timestamp and source) in a dedicated table in Supabase, allowing for trend analysis and integration into the dashboard.

### Example Python Client for Sentiment Analysis

```python
# src/services/sentiment_analyzer.py (simplified for reference)

import os
import requests
from typing import List, Dict, Any

class SentimentAPIClient:
    def __init__(self, api_key: str, base_url: str = "https://api.sentimentprovider.com/v1/"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

    def analyze_sentiment(self, text_list: List[str]) -> List[Dict[str, Any]]:
        endpoint = "analyze"
        payload = {"documents": [{"id": str(i), "text": text} for i, text in enumerate(text_list)]}
        response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
        response.raise_for_status()
        return response.json()

# To use this client, ensure SENTIMENT_API_KEY is set as an environment variable.
# Example: client = SentimentAPIClient(api_key=os.getenv("SENTIMENT_API_KEY"))
```  [OpenWeatherMap API Documentation](https://openweathermap.org/api)
*   [Tomorrow.io Weather API](https://www.tomorrow.io/weather-api/)
*   [Visual Crossing Weather API](https://www.visualcrossing.com/weather-api/)
*   [Open-Meteo.com Free Open-Source Weather API](https://open-meteo.com/)
*   [TomTom Traffic APIs](https://www.tomtom.com/products/traffic-apis/)
*   [HERE Traffic APIs Documentation](https://www.here.com/docs/category/maps-traffic)
*   [Google Maps Platform Routes API](https://developers.google.com/maps/documentation/routes/config_trade_offs)
*   [Swiftly Data Platform for Public Transit](https://www.goswift.ly/)
*   [Google Cloud Natural Language API - Sentiment Analysis](https://cloud.google.com/natural-language/docs/analyzing-sentiment)
*   [AssemblyAI - Best APIs for Sentiment Analysis](https://assemblyai.com/blog/best-apis-for-sentiment-analysis)
*   [OpenAI API Documentation](https://openai.com/docs/api-reference/sentiment)

---

**Author:** Manus AI


