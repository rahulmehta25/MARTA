/**
 * Flexible API configuration that supports both Railway and Supabase backends
 */

// Backend options
const BACKENDS = {
  RAILWAY: 'https://marta-production.up.railway.app',
  SUPABASE: 'https://vglychbweuowsovboxyf.supabase.co/functions/v1/marta-api',
  LOCAL: 'http://localhost:8000'
};

// Get API URL with fallback chain
const getApiUrl = () => {
  // 1. Check for explicit environment variable
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) {
    return envUrl;
  }
  
  // 2. Check for backend type preference
  const backendType = import.meta.env.VITE_BACKEND_TYPE;
  if (backendType && BACKENDS[backendType as keyof typeof BACKENDS]) {
    return BACKENDS[backendType as keyof typeof BACKENDS];
  }
  
  // 3. Use Supabase in production (recommended)
  if (import.meta.env.PROD) {
    return BACKENDS.SUPABASE;
  }
  
  // 4. Use local in development
  return BACKENDS.LOCAL;
};

export const apiConfig = {
  baseUrl: getApiUrl(),
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * Build a full API URL from an endpoint
 */
export function buildApiUrl(endpoint: string): string {
  const base = apiConfig.baseUrl.replace(/\/$/, ''); // Remove trailing slash
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${base}${path}`;
}

// Simplified endpoints for both backends
export const MARTA_ENDPOINTS = {
  // Core endpoints that work with both backends
  arrivals: '/arrivals',
  stations: '/stations',
  metrics: '/metrics',
  collect: '/collect',
  
  // Legacy Railway endpoints (for compatibility)
  rail: {
    arrivals: '/api/v1/marta/rail/arrivals',
    stations: '/api/v1/marta/rail/stations',
    status: '/api/v1/marta/rail/status',
  },
  bus: {
    arrivals: '/api/v1/marta/bus/arrivals',
    routes: '/api/v1/marta/bus/routes',
    stops: '/api/v1/marta/bus/stops',
  },
};

// Auto-detect and use appropriate endpoints
export function getEndpoint(type: 'arrivals' | 'stations' | 'metrics') {
  const isSupabase = apiConfig.baseUrl.includes('supabase');
  
  if (isSupabase) {
    // Use simple endpoints for Supabase
    return MARTA_ENDPOINTS[type];
  } else {
    // Use legacy endpoints for Railway
    switch(type) {
      case 'arrivals':
        return MARTA_ENDPOINTS.rail.arrivals;
      case 'stations':
        return MARTA_ENDPOINTS.rail.stations;
      case 'metrics':
        return MARTA_ENDPOINTS.rail.status;
      default:
        return `/${type}`;
    }
  }
}

// Export typed endpoint paths
export type MartaRailEndpoint = keyof typeof MARTA_ENDPOINTS.rail;
export type MartaBusEndpoint = keyof typeof MARTA_ENDPOINTS.bus;