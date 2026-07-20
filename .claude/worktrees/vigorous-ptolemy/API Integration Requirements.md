# API Integration Requirements

## Backend API Endpoints

Based on the technical implementation guide, the frontend will need to integrate with the following APIs:

### 1. Prediction API
**Endpoint**: `/predict/demand`
**Method**: `POST`
**Purpose**: Get real-time demand forecasts for specific stops and times

**Request Format**:
```json
{
  "stop_id": "string",
  "timestamp": "datetime_string"
}
```

**Response Format**:
```json
{
  "stop_id": "string",
  "timestamp": "datetime_string",
  "predicted_riders": "integer",
  "demand_level": "string"  // "Underloaded", "Normal", "Overloaded"
}
```

### 2. Route Optimization API
**Endpoint**: `/optimize/routes`
**Method**: `POST`
**Purpose**: Get route optimization suggestions based on demand forecasts

**Request Format**:
```json
{
  "forecasted_demand_heatmap": "array_of_objects",
  "current_route_topology": "array_of_objects",
  "bus_capacity_assumptions": "integer",
  "optimization_constraints": "object"
}
```

**Response Format**:
```json
{
  "proposed_routes": "array_of_objects",
  "load_balancing_simulation": "object",
  "impact_metrics": "object"
}
```

### 3. Data Access API
**Endpoints**: `/data/historical_trips`, `/data/features`
**Method**: `GET`
**Purpose**: Access historical trip data and engineered features

### 4. Heatmap Data API
**Endpoint**: `/data/heatmap`
**Method**: `GET`
**Purpose**: Get demand heatmap data for visualization
**Parameters**: `time_window`, `zoom_level`, `bounds`

## Frontend Data Requirements

### Map Data
- **GTFS Static Data**: Stops, routes, shapes for base map layers
- **Real-time Vehicle Positions**: Current bus locations
- **Stop Information**: Names, coordinates, accessibility info

### Demand Forecasting Data
- **Historical Demand**: Past ridership patterns
- **Predicted Demand**: Forecasted ridership by stop and time
- **Demand Levels**: Categorized load levels (Underloaded, Normal, Overloaded)
- **Time Series Data**: Demand trends over time

### Route Optimization Data
- **Current Routes**: Existing route configurations
- **Proposed Routes**: Optimization suggestions
- **Simulation Results**: Impact metrics and performance data
- **Optimization Constraints**: User-defined parameters

### Real-time Data
- **Vehicle Positions**: Live bus locations and status
- **Trip Updates**: Delays, cancellations, schedule changes
- **System Alerts**: Service disruptions, maintenance notices

## Data Formats

### GeoJSON for Spatial Data
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-84.3880, 33.7490]
      },
      "properties": {
        "stop_id": "STOP_001",
        "stop_name": "Five Points Station",
        "predicted_riders": 45,
        "demand_level": "Normal"
      }
    }
  ]
}
```

### Time Series Data
```json
{
  "stop_id": "STOP_001",
  "time_series": [
    {
      "timestamp": "2025-01-01T08:00:00Z",
      "predicted_riders": 25,
      "actual_riders": 23,
      "demand_level": "Normal"
    }
  ]
}
```

### Heatmap Data
```json
{
  "bounds": {
    "north": 33.8,
    "south": 33.7,
    "east": -84.3,
    "west": -84.4
  },
  "data": [
    {
      "lat": 33.7490,
      "lng": -84.3880,
      "intensity": 0.8,
      "demand_level": "High"
    }
  ]
}
```

## WebSocket/SSE Requirements

For real-time updates, the frontend should support:

### WebSocket Endpoints
- **Vehicle Positions**: `ws://api/vehicles/live`
- **Demand Updates**: `ws://api/demand/live`
- **System Alerts**: `ws://api/alerts/live`

### Event Types
```json
{
  "type": "vehicle_position_update",
  "data": {
    "vehicle_id": "BUS_001",
    "lat": 33.7490,
    "lng": -84.3880,
    "route_id": "ROUTE_1",
    "timestamp": "2025-01-01T08:00:00Z"
  }
}
```

## Error Handling

### HTTP Status Codes
- **200**: Success
- **400**: Bad Request (invalid parameters)
- **401**: Unauthorized
- **404**: Not Found
- **429**: Rate Limited
- **500**: Internal Server Error

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_STOP_ID",
    "message": "The provided stop_id does not exist",
    "details": {
      "stop_id": "INVALID_STOP"
    }
  }
}
```

## Caching Strategy

### Client-Side Caching
- **Static Data**: Cache GTFS static data for 24 hours
- **Predictions**: Cache demand predictions for 5 minutes
- **Historical Data**: Cache historical trends for 1 hour

### Cache Keys
- `gtfs_static_${version}`
- `demand_prediction_${stop_id}_${timestamp}`
- `route_optimization_${hash}`

## Rate Limiting

### API Limits
- **Prediction API**: 100 requests per minute
- **Optimization API**: 10 requests per minute
- **Data Access API**: 1000 requests per hour

### Frontend Strategies
- **Debouncing**: Delay API calls for user input
- **Batching**: Combine multiple requests when possible
- **Caching**: Reduce redundant API calls

## Authentication

### API Key Authentication
```javascript
headers: {
  'Authorization': 'Bearer YOUR_API_KEY',
  'Content-Type': 'application/json'
}
```

### Environment Variables
```
REACT_APP_API_BASE_URL=https://api.marta-platform.com
REACT_APP_API_KEY=your_api_key_here
REACT_APP_MAPBOX_TOKEN=your_mapbox_token_here
```

This document provides the foundation for integrating the frontend with the MARTA backend APIs, ensuring proper data flow and real-time functionality.

