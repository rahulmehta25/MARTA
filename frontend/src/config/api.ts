/**
 * API configuration for the MARTA Transit Analytics Platform
 */

const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

// Get API URL from environment or use defaults
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (isProduction ? 'https://marta-eta.vercel.app' : 'http://localhost:8000');

const WS_BASE_URL = import.meta.env.VITE_WEBSOCKET_URL || 
  (isProduction ? 'wss://marta-eta.vercel.app/ws' : 'ws://localhost:8000/ws');

// Supabase ML System
export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://gszmaaefdekacgqtetqd.supabase.co';
export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdzem1hYWVmZGVrYWNncXRldHFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc4NzUwMDUsImV4cCI6MjA3MzQ1MTAwNX0.Gk0moC-kk9hBuDTmDwPEqUhmsFP6Q1Z_1t1pjhMNluY';
export const DEMAND_FORECAST_URL = import.meta.env.VITE_DEMAND_FORECAST_URL || 'https://gszmaaefdekacgqtetqd.supabase.co/functions/v1/demand-forecast';
export const SURGE_DETECTION_URL = import.meta.env.VITE_SURGE_DETECTION_URL || 'https://gszmaaefdekacgqtetqd.supabase.co/functions/v1/surge-detection';

export const apiConfig = {
  baseUrl: API_BASE_URL,
  wsUrl: WS_BASE_URL,
  apiPrefix: '/api/v1',
  timeout: 30000, // 30 seconds
  retries: 3,
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * Build full API endpoint URL
 */
export const buildApiUrl = (endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${apiConfig.baseUrl}${apiConfig.apiPrefix}${cleanEndpoint}`;
};

/**
 * Build WebSocket URL
 */
export const buildWsUrl = (endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${apiConfig.wsUrl}${cleanEndpoint}`;
};

// API endpoints
export const endpoints = {
  // Health
  health: '/health',
  healthDetailed: '/health/detailed',
  
  // Routes
  routes: '/routes',
  routeById: (id: string) => `/routes/${id}`,
  routePerformance: (id: string) => `/routes/${id}/performance`,
  
  // Stops
  stops: '/stops',
  stopById: (id: string) => `/stops/${id}`,
  stopArrivals: (id: string) => `/stops/${id}/arrivals`,
  
  // Real-time
  realTimeUpdates: '/real-time/updates',
  realTimeArrivals: '/realtime/arrivals',
  realTimeByStation: (station: string) => `/realtime/arrivals/by-station/${encodeURIComponent(station)}`,
  realTimeNext: (stopId: string) => `/realtime/arrivals/next/${stopId}`,
  realTimeStatus: '/realtime/status',
  realTimeRefresh: '/realtime/refresh',
  
  // Analytics
  systemMetrics: '/analytics/system',
  routeMetrics: '/analytics/routes',
  
  // WebSocket endpoints
  ws: {
    realTime: '/real-time',
    alerts: '/alerts',
  },
  
  // ML System endpoints
  ml: {
    demandForecast: DEMAND_FORECAST_URL,
    surgeDetection: SURGE_DETECTION_URL,
  },
};

export default apiConfig;