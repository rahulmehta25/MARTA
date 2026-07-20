import axios from 'axios';
import { config } from '../utils/config.js';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: config.API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    ...(config.API_KEY && { 'Authorization': `Bearer ${config.API_KEY}` })
  }
});

// Request interceptor for logging and authentication
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    
    // Handle specific error cases
    if (error.response?.status === 401) {
      console.error('Unauthorized access - check API key');
    } else if (error.response?.status === 429) {
      console.error('Rate limit exceeded');
    } else if (error.response?.status >= 500) {
      console.error('Server error - please try again later');
    }
    
    return Promise.reject(error);
  }
);

// API service functions
export const apiService = {
  // Demand Forecasting API
  async predictDemand(stopId, timestamp) {
    try {
      const response = await apiClient.post('/predict/demand', {
        stop_id: stopId,
        timestamp: timestamp
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to predict demand: ${error.message}`);
    }
  },

  // Route Optimization API
  async optimizeRoutes(demandHeatmap, routeTopology, busCapacity, constraints = {}) {
    try {
      const response = await apiClient.post('/optimize/routes', {
        forecasted_demand_heatmap: demandHeatmap,
        current_route_topology: routeTopology,
        bus_capacity_assumptions: busCapacity,
        optimization_constraints: constraints
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to optimize routes: ${error.message}`);
    }
  },

  // Historical Data API
  async getHistoricalTrips(params = {}) {
    try {
      const response = await apiClient.get('/data/historical_trips', { params });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch historical trips: ${error.message}`);
    }
  },

  // Features Data API
  async getFeatures(params = {}) {
    try {
      const response = await apiClient.get('/data/features', { params });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch features: ${error.message}`);
    }
  },

  // Heatmap Data API
  async getHeatmapData(timeWindow, zoomLevel, bounds) {
    try {
      const response = await apiClient.get('/data/heatmap', {
        params: {
          time_window: timeWindow,
          zoom_level: zoomLevel,
          bounds: JSON.stringify(bounds)
        }
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch heatmap data: ${error.message}`);
    }
  },

  // GTFS Static Data
  async getStops() {
    try {
      const response = await apiClient.get('/data/stops');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch stops: ${error.message}`);
    }
  },

  async getRoutes() {
    try {
      const response = await apiClient.get('/data/routes');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch routes: ${error.message}`);
    }
  },

  // Real-time Data
  async getVehiclePositions() {
    try {
      const response = await apiClient.get('/data/vehicles/live');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch vehicle positions: ${error.message}`);
    }
  },

  async getTripUpdates() {
    try {
      const response = await apiClient.get('/data/trips/updates');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch trip updates: ${error.message}`);
    }
  },

  // Search API
  async searchStops(query) {
    try {
      const response = await apiClient.get('/search/stops', {
        params: { q: query }
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to search stops: ${error.message}`);
    }
  }
};

// Mock data service for development/testing
export const mockApiService = {
  async predictDemand(stopId, timestamp) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return {
      stop_id: stopId,
      timestamp: timestamp,
      predicted_riders: Math.floor(Math.random() * 100) + 10,
      demand_level: ['Underloaded', 'Normal', 'Overloaded'][Math.floor(Math.random() * 3)]
    };
  },

  async getHeatmapData(timeWindow, zoomLevel, bounds) {
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Generate mock heatmap data
    const data = [];
    for (let i = 0; i < 50; i++) {
      data.push({
        lat: bounds.south + Math.random() * (bounds.north - bounds.south),
        lng: bounds.west + Math.random() * (bounds.east - bounds.west),
        intensity: Math.random(),
        demand_level: ['Low', 'Medium', 'High', 'Overloaded'][Math.floor(Math.random() * 4)]
      });
    }
    
    return { bounds, data };
  },

  async getStops() {
    await new Promise(resolve => setTimeout(resolve, 200));
    
    return [
      {
        stop_id: 'STOP_001',
        stop_name: 'Five Points Station',
        stop_lat: 33.7537,
        stop_lon: -84.3918,
        zone_id: 'downtown'
      },
      {
        stop_id: 'STOP_002',
        stop_name: 'Peachtree Center Station',
        stop_lat: 33.7594,
        stop_lon: -84.3875,
        zone_id: 'downtown'
      },
      {
        stop_id: 'STOP_003',
        stop_name: 'Midtown Station',
        stop_lat: 33.7806,
        stop_lon: -84.3868,
        zone_id: 'midtown'
      }
    ];
  },

  async searchStops(query) {
    await new Promise(resolve => setTimeout(resolve, 200));
    
    const allStops = await this.getStops();
    return allStops.filter(stop => 
      stop.stop_name.toLowerCase().includes(query.toLowerCase())
    );
  }
};

// Use mock service in development if no API key is provided
export const api = config.API_KEY ? apiService : mockApiService;

export default api;

