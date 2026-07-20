/**
 * Service for fetching real-time MARTA arrival data
 */
import { api } from './api-client';

export interface RealTimeArrival {
  id: number;
  stop_id: string;
  stop_name: string;
  stop_lat: number;
  stop_lon: number;
  route_id: string | null;
  trip_id: string | null;
  arrival_time: string;
  predicted_time: string | null;
  delay_seconds: number;
  vehicle_id: string | null;
  last_updated: string | null;
}

export interface NextArrival {
  stop_id: string;
  stop_name: string;
  route_id: string | null;
  arrival_time: string | null;
  wait_minutes: number | null;
  vehicle_id: string | null;
  last_updated: string | null;
  message?: string;
}

export interface StationArrivals {
  station_query: string;
  stations_found: Array<{ id: string; name: string }>;
  arrivals: RealTimeArrival[];
}

export interface RealtimeStatus {
  status: 'active' | 'stale';
  last_updated: string | null;
  current_arrivals: number;
  arrivals_by_route: Record<string, number>;
  data_age_seconds: number | null;
}

// MARTA Rail API Types
export interface MartaRailArrival {
  destination: string;
  direction: string;
  event_time: string;
  line: string;
  next_arrival: string;
  station: string;
  train_id: string;
  waiting_seconds: string;
  waiting_time: string;
  delay: string;
}

export class RealtimeService {
  /**
   * Get all real-time arrivals
   */
  static async getArrivals(params?: {
    stop_id?: string;
    route_id?: string;
    limit?: number;
  }): Promise<RealTimeArrival[]> {
    return api.get<RealTimeArrival[]>('/realtime/arrivals', { params });
  }

  /**
   * Get arrivals by station name
   */
  static async getArrivalsByStation(
    stationName: string,
    limit = 10
  ): Promise<StationArrivals> {
    return api.get<StationArrivals>(
      `/realtime/arrivals/by-station/${encodeURIComponent(stationName)}`,
      { params: { limit } }
    );
  }

  /**
   * Get next arrival at a specific stop
   */
  static async getNextArrival(
    stopId: string,
    routeId?: string
  ): Promise<NextArrival> {
    return api.get<NextArrival>(`/realtime/arrivals/next/${stopId}`, {
      params: routeId ? { route_id: routeId } : undefined,
    });
  }

  /**
   * Get real-time data status
   */
  static async getStatus(): Promise<RealtimeStatus> {
    return api.get<RealtimeStatus>('/realtime/status');
  }

  /**
   * Refresh real-time data
   */
  static async refresh(): Promise<{
    status: string;
    message: string;
    timestamp: string;
  }> {
    return api.post('/realtime/refresh');
  }

  /**
   * Get MARTA rail arrivals from live API
   */
  static async getMartaRailArrivals(params?: {
    station?: string;
    line?: string;
    direction?: string;
  }): Promise<MartaRailArrival[]> {
    return api.get<MartaRailArrival[]>('/api/v1/marta/rail/arrivals', { params });
  }

  /**
   * Get MARTA rail stations with current arrivals
   */
  static async getMartaStations(): Promise<any[]> {
    return api.get('/api/v1/marta/rail/stations');
  }

  /**
   * Get MARTA system status
   */
  static async getMartaSystemStatus(): Promise<any> {
    return api.get('/api/v1/marta/rail/status');
  }

  /**
   * Get next train at a MARTA station
   */
  static async getNextMartaTrain(station: string, line?: string): Promise<any> {
    const params = line ? { line } : undefined;
    return api.get(`/marta/rail/next-train/${encodeURIComponent(station)}`, { params });
  }

  /**
   * Format arrival time for display
   */
  static formatArrivalTime(arrivalTime: string): string {
    const arrival = new Date(arrivalTime);
    const now = new Date();
    const diffMs = arrival.getTime() - now.getTime();
    const diffMins = Math.round(diffMs / 60000);

    if (diffMins <= 0) {
      return 'Arriving';
    } else if (diffMins === 1) {
      return '1 min';
    } else if (diffMins < 60) {
      return `${diffMins} mins`;
    } else {
      return arrival.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
      });
    }
  }

  /**
   * Get route color based on line
   */
  static getRouteColor(routeId: string | null): string {
    if (!routeId) return '#666';
    
    const colors: Record<string, string> = {
      RED: '#CE242B',
      GOLD: '#D4A723',
      GREEN: '#009D4B',
      BLUE: '#0075B2',
    };

    return colors[routeId.toUpperCase()] || '#666';
  }

  /**
   * Group arrivals by stop
   */
  static groupByStop(arrivals: RealTimeArrival[]): Map<string, RealTimeArrival[]> {
    const grouped = new Map<string, RealTimeArrival[]>();
    
    arrivals.forEach(arrival => {
      const stopId = arrival.stop_id;
      if (!grouped.has(stopId)) {
        grouped.set(stopId, []);
      }
      grouped.get(stopId)!.push(arrival);
    });

    // Sort arrivals within each stop by arrival time
    grouped.forEach(stopArrivals => {
      stopArrivals.sort((a, b) => 
        new Date(a.arrival_time).getTime() - new Date(b.arrival_time).getTime()
      );
    });

    return grouped;
  }

  /**
   * Filter arrivals within time window
   */
  static filterByTimeWindow(
    arrivals: RealTimeArrival[],
    minutesAhead = 120
  ): RealTimeArrival[] {
    const now = new Date();
    const futureTime = new Date(now.getTime() + minutesAhead * 60000);

    return arrivals.filter(arrival => {
      const arrivalTime = new Date(arrival.arrival_time);
      return arrivalTime >= now && arrivalTime <= futureTime;
    });
  }
}