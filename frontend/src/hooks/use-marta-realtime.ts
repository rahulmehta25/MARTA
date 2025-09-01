import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { buildApiUrl } from '@/config/api';

interface MartaArrival {
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

interface MartaStation {
  name: string;
  code: string;
  lines: string[];
  upcoming_trains: {
    line: string;
    destination: string;
    direction: string;
    waiting_time: string;
    next_arrival: string;
  }[];
}

interface MartaSystemStatus {
  status: string;
  active_trains: number;
  stations_with_service: number;
  total_arrivals: number;
  delayed_arrivals: number;
  last_updated: string;
  lines_status: {
    RED: boolean;
    GOLD: boolean;
    GREEN: boolean;
    BLUE: boolean;
  };
}

export const useMartaRailArrivals = (station?: string, line?: string, direction?: string) => {
  return useQuery<MartaArrival[]>({
    queryKey: ['marta', 'rail', 'arrivals', station, line, direction],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (station) params.append('station', station);
      if (line) params.append('line', line);
      if (direction) params.append('direction', direction);
      
      const url = buildApiUrl('/api/v1/marta/rail/arrivals');
      const queryString = params.toString();
      const response = await fetch(queryString ? `${url}?${queryString}` : url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch rail arrivals');
      }
      
      return response.json();
    },
    refetchInterval: 15000, // Refresh every 15 seconds for real-time data
    staleTime: 5000, // Data is stale after 5 seconds
  });
};

export const useMartaStations = () => {
  return useQuery<MartaStation[]>({
    queryKey: ['marta', 'rail', 'stations'],
    queryFn: async () => {
      const response = await fetch(buildApiUrl('/api/v1/marta/rail/stations'));
      
      if (!response.ok) {
        throw new Error('Failed to fetch stations');
      }
      
      return response.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000, // Data is stale after 10 seconds
  });
};

export const useMartaSystemStatus = () => {
  return useQuery<MartaSystemStatus>({
    queryKey: ['marta', 'rail', 'status'],
    queryFn: async () => {
      const response = await fetch(buildApiUrl('/api/v1/marta/rail/status'));
      
      if (!response.ok) {
        throw new Error('Failed to fetch system status');
      }
      
      return response.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000, // Data is stale after 10 seconds
  });
};

export const useNextTrain = (station: string, line?: string) => {
  return useQuery({
    queryKey: ['marta', 'rail', 'next-train', station, line],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (line) params.append('line', line);
      
      const url = buildApiUrl(`/marta/rail/next-train/${encodeURIComponent(station)}`);
      const queryString = params.toString();
      const response = await fetch(queryString ? `${url}?${queryString}` : url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch next train');
      }
      
      return response.json();
    },
    refetchInterval: 10000, // Refresh every 10 seconds for next train
    staleTime: 3000, // Data is stale after 3 seconds
    enabled: !!station,
  });
};