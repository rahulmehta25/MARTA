/**
 * ML Service for MARTA Transit Analytics Platform
 * Handles all ML-related API calls to Supabase Edge Functions
 */

import { SUPABASE_ANON_KEY, DEMAND_FORECAST_URL, SURGE_DETECTION_URL } from '../config/api';

export interface DemandPrediction {
  timestamp: string;
  predicted_demand: number;
  confidence_lower: number;
  confidence_upper: number;
  surge_probability: number;
  overcrowding_risk: number;
}

export interface DemandForecastResponse {
  stop_id: string;
  predictions: DemandPrediction[];
  model_confidence: number;
  last_updated: string;
}

export interface SurgeDetectionResponse {
  surge_detected: boolean;
  location_id: string;
  surge_magnitude: number;
  surge_start_time: string;
  confidence: number;
  contributing_factors: string[];
  affected_areas: string[];
  recommended_actions: string[];
  external_factors: {
    weather_severity: number;
    traffic_index: number;
  };
}

export interface DemandForecastRequest {
  stop_id: string;
  horizon_hours?: number;
}

export interface SurgeDetectionRequest {
  location_id: string;
  current_demand: number;
  historical_baseline: number;
  external_factors?: {
    weather_severity?: number;
    traffic_index?: number;
  };
}

class MLService {
  private async makeRequest<T>(
    url: string,
    data: any,
    method: 'GET' | 'POST' = 'POST'
  ): Promise<T> {
    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
          'Content-Type': 'application/json',
        },
        body: method === 'POST' ? JSON.stringify(data) : undefined,
      });

      if (!response.ok) {
        throw new Error(`ML API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('ML Service Error:', error);
      throw error;
    }
  }

  /**
   * Get demand forecast for a specific stop
   */
  async getDemandForecast(request: DemandForecastRequest): Promise<DemandForecastResponse> {
    return this.makeRequest<DemandForecastResponse>(
      DEMAND_FORECAST_URL,
      {
        stop_id: request.stop_id,
        horizon_hours: request.horizon_hours || 24,
      }
    );
  }

  /**
   * Detect surge conditions at a location
   */
  async detectSurge(request: SurgeDetectionRequest): Promise<SurgeDetectionResponse> {
    return this.makeRequest<SurgeDetectionResponse>(
      SURGE_DETECTION_URL,
      {
        location_id: request.location_id,
        current_demand: request.current_demand,
        historical_baseline: request.historical_baseline,
        external_factors: request.external_factors || {
          weather_severity: 0,
          traffic_index: 1.0,
        },
      }
    );
  }

  /**
   * Get demand forecast for multiple stops
   */
  async getBulkDemandForecast(stopIds: string[], horizonHours: number = 24): Promise<DemandForecastResponse[]> {
    const promises = stopIds.map(stopId => 
      this.getDemandForecast({ stop_id: stopId, horizon_hours: horizonHours })
    );
    
    return Promise.all(promises);
  }

  /**
   * Monitor surge conditions for multiple locations
   */
  async monitorSurgeConditions(
    locations: Array<{
      location_id: string;
      current_demand: number;
      historical_baseline: number;
    }>
  ): Promise<SurgeDetectionResponse[]> {
    const promises = locations.map(location =>
      this.detectSurge(location)
    );
    
    return Promise.all(promises);
  }
}

export const mlService = new MLService();
export default mlService;


