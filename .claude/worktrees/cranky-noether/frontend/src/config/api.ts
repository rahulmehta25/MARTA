/**
 * API configuration for the MARTA Transit Analytics frontend
 */

// Get API URL from environment or use default
const getApiUrl = () => {
  // Check for environment variable
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) {
    return envUrl;
  }
  
  // Production URL when deployed on Vercel
  if (import.meta.env.PROD) {
    return 'https://marta-production.up.railway.app';
  }
  
  // Development URL
  return 'http://localhost:8000';
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

// MARTA-specific endpoints
export const MARTA_ENDPOINTS = {
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

// Export typed endpoint paths
export type MartaRailEndpoint = keyof typeof MARTA_ENDPOINTS.rail;
export type MartaBusEndpoint = keyof typeof MARTA_ENDPOINTS.bus;