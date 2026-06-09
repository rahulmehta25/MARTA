// Core transit types
export interface Station {
  id: string;
  name: string;
  lat: number;
  lng: number;
  routes: string[];
  type: 'rail' | 'bus';
  accessibility: boolean;
  parking: boolean;
}

export interface Route {
  id: string;
  name: string;
  color: string;
  type: 'rail' | 'bus';
  stops: string[];
  coordinates: [number, number][];
}

export interface Vehicle {
  id: string;
  routeId: string;
  lat: number;
  lng: number;
  bearing: number;
  speed: number;
  nextStop: string;
  delay: number;
  lastUpdated: string;
}

// Demand forecasting types
export type DemandLevel = 'low' | 'medium' | 'high' | 'critical';

export interface DemandForecast {
  stationId: string;
  timestamp: string;
  predictedRidership: number;
  actualRidership?: number;
  demandLevel: DemandLevel;
  confidence: number;
}

export interface ForecastTimeSeries {
  stationId: string;
  stationName: string;
  data: {
    timestamp: string;
    predicted: number;
    actual?: number;
    lowerBound: number;
    upperBound: number;
  }[];
}

export interface DemandHeatmapPoint {
  lat: number;
  lng: number;
  intensity: number;
}

// Route optimization types
export interface OptimizationRequest {
  date: string;
  timeRange: { start: string; end: string };
  targetMetrics: ('efficiency' | 'coverage' | 'wait_time')[];
  constraints: {
    maxFrequencyIncrease: number;
    maxCapacityIncrease: number;
    budget?: number;
  };
}

export interface OptimizationResult {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
  improvements: {
    efficiencyGain: number;
    waitTimeReduction: number;
    coverageIncrease: number;
    costImpact: number;
  };
  recommendations: RouteRecommendation[];
}

export interface RouteRecommendation {
  routeId: string;
  routeName: string;
  type: 'frequency' | 'capacity' | 'schedule' | 'reroute';
  description: string;
  impact: {
    ridershipChange: number;
    waitTimeChange: number;
    costChange: number;
  };
  priority: 'low' | 'medium' | 'high';
}

// Analytics types
export interface KPIMetric {
  id: string;
  label: string;
  value: number;
  previousValue?: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  trendValue?: number;
}

export interface RidershipData {
  date: string;
  total: number;
  byLine: Record<string, number>;
  byHour: number[];
}

export interface StationRanking {
  stationId: string;
  stationName: string;
  metric: string;
  value: number;
  rank: number;
  change: number;
}

export interface PerformanceMetric {
  timestamp: string;
  onTimePerformance: number;
  averageDelay: number;
  serviceReliability: number;
  passengerSatisfaction?: number;
}

// System health types
export interface ServiceStatus {
  service: string;
  status: 'operational' | 'degraded' | 'outage';
  lastCheck: string;
  responseTime?: number;
  message?: string;
}

export interface DataFreshness {
  dataSource: string;
  lastUpdated: string;
  staleness: 'fresh' | 'stale' | 'critical';
  recordCount: number;
}

export interface ModelHealth {
  modelName: string;
  version: string;
  lastTrained: string;
  accuracy: number;
  drift: number;
  status: 'healthy' | 'warning' | 'critical';
}

export interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  apiLatency: number;
  errorRate: number;
  requestsPerMinute: number;
}

// Trip planning types
export interface TripRequest {
  origin: { lat: number; lng: number; name?: string };
  destination: { lat: number; lng: number; name?: string };
  departureTime: string;
  preferences?: {
    fewerTransfers?: boolean;
    wheelchair?: boolean;
    avoidStairs?: boolean;
  };
}

export interface TripSegment {
  type: 'walk' | 'rail' | 'bus' | 'transfer';
  from: string;
  to: string;
  line?: string;
  lineColor?: string;
  departureTime: string;
  arrivalTime: string;
  duration: number;
  distance?: number;
  stops?: number;
  instructions?: string;
}

export interface TripOption {
  id: string;
  departureTime: string;
  arrivalTime: string;
  duration: number;
  transfers: number;
  walkingDistance: number;
  fare: number;
  segments: TripSegment[];
}

// Real-time arrival types
export interface Arrival {
  vehicleId: string;
  routeId: string;
  routeName: string;
  routeColor: string;
  destination: string;
  eta: string;
  etaMinutes: number;
  delay: number;
  status: 'on_time' | 'delayed' | 'arriving';
  platform?: string;
}

// Date range and filter types
export interface DateRange {
  start: Date;
  end: Date;
}

export interface FilterState {
  routes: string[];
  stations: string[];
  demandLevels: DemandLevel[];
  dateRange: DateRange | null;
  timeOfDay: 'all' | 'morning' | 'midday' | 'evening' | 'night';
}

// API response wrappers
export interface ApiResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// Export utility types
export type ExportFormat = 'csv' | 'json' | 'xlsx';

export interface ExportOptions {
  format: ExportFormat;
  filename?: string;
  columns?: string[];
  dateRange?: DateRange;
}
