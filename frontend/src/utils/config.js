// Configuration file for MARTA platform
export const config = {
  // API Configuration
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  API_KEY: import.meta.env.VITE_API_KEY || '',
  
  // Mapbox Configuration
  MAPBOX_TOKEN: import.meta.env.VITE_MAPBOX_TOKEN || '',
  
  // Map Configuration
  DEFAULT_MAP_CENTER: {
    lat: 33.7490,
    lng: -84.3880
  },
  DEFAULT_MAP_ZOOM: 11,
  
  // Atlanta bounds for MARTA service area
  ATLANTA_BOUNDS: {
    north: 33.9,
    south: 33.6,
    east: -84.2,
    west: -84.6
  },
  
  // Update intervals (in milliseconds)
  REAL_TIME_UPDATE_INTERVAL: 30000, // 30 seconds
  DEMAND_UPDATE_INTERVAL: 300000,   // 5 minutes
  
  // Cache durations (in milliseconds)
  CACHE_DURATION: {
    STATIC_DATA: 24 * 60 * 60 * 1000,    // 24 hours
    PREDICTIONS: 5 * 60 * 1000,           // 5 minutes
    HISTORICAL: 60 * 60 * 1000            // 1 hour
  },
  
  // Rate limiting
  RATE_LIMITS: {
    PREDICTION_API: 100,  // requests per minute
    OPTIMIZATION_API: 10, // requests per minute
    DATA_ACCESS_API: 1000 // requests per hour
  },
  
  // Demand level thresholds
  DEMAND_THRESHOLDS: {
    LOW: 0.3,
    NORMAL: 0.7,
    HIGH: 0.9
  },
  
  // Heatmap configuration
  HEATMAP: {
    RADIUS: 20,
    MAX_ZOOM: 16,
    MIN_ZOOM: 8,
    OPACITY: 0.7
  },
  
  // Animation durations
  ANIMATION: {
    FAST: 150,
    MEDIUM: 300,
    SLOW: 500
  }
};

// Validation function to check if required environment variables are set
export const validateConfig = () => {
  const requiredVars = ['VITE_MAPBOX_TOKEN'];
  const missing = requiredVars.filter(varName => !import.meta.env[varName]);
  
  if (missing.length > 0) {
    console.warn('Missing environment variables:', missing);
    console.warn('Please create a .env file with the required variables');
  }
  
  return missing.length === 0;
};

export default config;

