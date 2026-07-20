import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { endpoints } from '@/config/api';

interface Route {
  route_id: string;
  route_short_name: string;
  route_long_name: string;
  route_color: string;
  route_type: number;
}

interface Stop {
  stop_id: string;
  stop_name: string;
  stop_lat: number;
  stop_lon: number;
  stop_code?: string;
  wheelchair_boarding?: number;
}

interface Arrival {
  stop_id: string;
  route_id: string;
  destination: string;
  arrival_time: string;
  predicted_time: string;
  is_delayed: boolean;
  delay_seconds: number;
}

export const useMartaRoutes = () => {
  return useQuery<Route[]>({
    queryKey: ['marta', 'routes'],
    queryFn: () => api.get(endpoints.routes),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useMartaStops = (lat?: number, lon?: number, radius?: number) => {
  return useQuery<Stop[]>({
    queryKey: ['marta', 'stops', lat, lon, radius],
    queryFn: () => api.get(endpoints.stops, {
      params: lat && lon ? { lat, lon, radius: radius || 1.0 } : undefined
    }),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};

export const useStopArrivals = (stopId: string) => {
  return useQuery<{
    stop_id: string;
    stop_name: string;
    arrivals: Arrival[];
    last_updated: string | null;
  }>({
    queryKey: ['marta', 'arrivals', stopId],
    queryFn: () => api.get(endpoints.stopArrivals(stopId)),
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: !!stopId,
  });
};

export const useSystemHealth = () => {
  return useQuery({
    queryKey: ['system', 'health'],
    queryFn: () => api.get(endpoints.healthDetailed),
    refetchInterval: 60000, // Refresh every minute
  });
};