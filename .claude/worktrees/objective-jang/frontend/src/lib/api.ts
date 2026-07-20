import { createClient } from '@supabase/supabase-js';

// Supabase configuration
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://vglychbweuowsovboxyf.supabase.co';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY';

// Create Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// MARTA API configuration
const MARTA_API_KEY = 'ff98ada7-0436-42c5-b9bf-1071245ad1a0';
const MARTA_BASE_URL = 'https://developerservices.itsmarta.com:18096';

interface Stop {
  STOPID: string;
  TIMEPOINT: string;
  STOPNAME: string;
  LATITUDE: number;
  LONGITUDE: number;
}

interface Route {
  ROUTE: string;
  ROUTE_SHORT: string;
  COLOR: string;
}

interface Train {
  DESTINATION: string;
  DIRECTION: string;
  EVENT_TIME: string;
  LINE: string;
  NEXT_ARR: string;
  STATION: string;
  TRAIN_ID: string;
  WAITING_TIME: string;
  WAITING_SECONDS: string;
  DELAY: string;
}

class ApiService {
  private cache: Map<string, { data: any; timestamp: number }> = new Map();
  private cacheTimeout = 30000; // 30 seconds

  private getCached<T>(key: string): T | null {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data as T;
    }
    return null;
  }

  private setCache(key: string, data: any): void {
    this.cache.set(key, { data, timestamp: Date.now() });
  }

  async getStops(): Promise<Stop[]> {
    const cacheKey = 'stops';
    const cached = this.getCached<Stop[]>(cacheKey);
    if (cached) return cached;

    try {
      // First try Supabase edge function
      const response = await fetch(`${SUPABASE_URL}/functions/v1/marta-arrivals`, {
        headers: {
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        // Extract unique stations from arrivals data
        const stopsMap = new Map<string, Stop>();
        data.forEach((arrival: any) => {
          if (!stopsMap.has(arrival.station)) {
            stopsMap.set(arrival.station, {
              STOPID: arrival.station,
              TIMEPOINT: 'Y',
              STOPNAME: arrival.station,
              LATITUDE: 33.7490 + (Math.random() - 0.5) * 0.1, // Mock coordinates
              LONGITUDE: -84.3880 + (Math.random() - 0.5) * 0.1
            });
          }
        });
        const stops = Array.from(stopsMap.values());
        this.setCache(cacheKey, stops);
        return stops;
      }
    } catch (error) {
      console.error('Failed to fetch from Supabase:', error);
    }

    // Fallback to mock data
    const mockStops: Stop[] = [
      { STOPID: 'FIVE POINTS STATION', TIMEPOINT: 'Y', STOPNAME: 'Five Points Station', LATITUDE: 33.7540, LONGITUDE: -84.3916 },
      { STOPID: 'AIRPORT STATION', TIMEPOINT: 'Y', STOPNAME: 'Airport Station', LATITUDE: 33.6407, LONGITUDE: -84.4467 },
      { STOPID: 'MIDTOWN STATION', TIMEPOINT: 'Y', STOPNAME: 'Midtown Station', LATITUDE: 33.7808, LONGITUDE: -84.3865 },
      { STOPID: 'BUCKHEAD STATION', TIMEPOINT: 'Y', STOPNAME: 'Buckhead Station', LATITUDE: 33.8498, LONGITUDE: -84.3678 },
      { STOPID: 'DECATUR STATION', TIMEPOINT: 'Y', STOPNAME: 'Decatur Station', LATITUDE: 33.7747, LONGITUDE: -84.2963 }
    ];
    
    this.setCache(cacheKey, mockStops);
    return mockStops;
  }

  async getRoutes(): Promise<Route[]> {
    const cacheKey = 'routes';
    const cached = this.getCached<Route[]>(cacheKey);
    if (cached) return cached;

    // MARTA rail lines
    const routes: Route[] = [
      { ROUTE: 'RED', ROUTE_SHORT: 'Red Line', COLOR: '#EF3E42' },
      { ROUTE: 'GOLD', ROUTE_SHORT: 'Gold Line', COLOR: '#F9B418' },
      { ROUTE: 'BLUE', ROUTE_SHORT: 'Blue Line', COLOR: '#0075C9' },
      { ROUTE: 'GREEN', ROUTE_SHORT: 'Green Line', COLOR: '#00AA4F' }
    ];
    
    this.setCache(cacheKey, routes);
    return routes;
  }

  async getArrivals(stationId?: string): Promise<Train[]> {
    const cacheKey = `arrivals-${stationId || 'all'}`;
    const cached = this.getCached<Train[]>(cacheKey);
    if (cached) return cached;

    try {
      const url = stationId 
        ? `${SUPABASE_URL}/functions/v1/marta-arrivals?station=${encodeURIComponent(stationId)}`
        : `${SUPABASE_URL}/functions/v1/marta-arrivals`;

      const response = await fetch(url, {
        headers: {
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        this.setCache(cacheKey, data);
        return data;
      }
    } catch (error) {
      console.error('Failed to fetch arrivals:', error);
    }

    // Return empty array if fetch fails
    return [];
  }

  async getPerformanceMetrics(): Promise<any> {
    try {
      const response = await fetch(`${SUPABASE_URL}/functions/v1/analytics-performance`, {
        headers: {
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
        }
      });

      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Failed to fetch performance metrics:', error);
    }

    // Return mock metrics if fetch fails
    return {
      systemHealth: 95,
      avgDelay: 2.3,
      onTimePerformance: 87,
      passengerSatisfaction: 4.2
    };
  }

  async getDelayPatterns(stationId?: string): Promise<any> {
    try {
      const url = stationId
        ? `${SUPABASE_URL}/functions/v1/delay-patterns?station=${encodeURIComponent(stationId)}`
        : `${SUPABASE_URL}/functions/v1/delay-patterns`;

      const response = await fetch(url, {
        headers: {
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
        }
      });

      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Failed to fetch delay patterns:', error);
    }

    return [];
  }

  async getDemandForecast(stationId?: string): Promise<any> {
    try {
      const url = stationId
        ? `${SUPABASE_URL}/functions/v1/demand-forecast?station=${encodeURIComponent(stationId)}`
        : `${SUPABASE_URL}/functions/v1/demand-forecast`;

      const response = await fetch(url, {
        headers: {
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
        }
      });

      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Failed to fetch demand forecast:', error);
    }

    return {
      currentDemand: 'moderate',
      predictedDemand: 'high',
      peakHours: ['7:00 AM - 9:00 AM', '5:00 PM - 7:00 PM']
    };
  }

  async predictArrival(stationId: string, line: string, direction: string): Promise<any> {
    try {
      const response = await fetch(
        `${SUPABASE_URL}/functions/v1/predict-arrival?station=${encodeURIComponent(stationId)}&line=${line}&direction=${direction}`,
        {
          headers: {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
          }
        }
      );

      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Failed to predict arrival:', error);
    }

    return {
      predicted_seconds: 300,
      confidence: 0.75,
      factors: ['historical_average', 'current_delays']
    };
  }

  // Supabase database methods
  async getFromSupabase(table: string, filters?: any) {
    let query = supabase.from(table).select('*');
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        query = query.eq(key, value);
      });
    }

    const { data, error } = await query;
    if (error) throw error;
    return data;
  }

  async insertToSupabase(table: string, data: any) {
    const { data: result, error } = await supabase
      .from(table)
      .insert(data)
      .select();
    
    if (error) throw error;
    return result;
  }

  async updateSupabase(table: string, id: string, updates: any) {
    const { data, error } = await supabase
      .from(table)
      .update(updates)
      .eq('id', id)
      .select();
    
    if (error) throw error;
    return data;
  }
}

export const apiService = new ApiService();