import { useEffect, useState, useCallback } from 'react';
import { toast } from '@/components/ui/use-toast';

interface SubscriptionOptions {
  channel: 'arrivals' | 'delays' | 'alerts';
  stationId?: string;
  lineColor?: string;
  onMessage?: (data: any) => void;
}

interface RealtimeMessage {
  type: 'connected' | 'arrival_update' | 'delay_update' | 'alert' | 'heartbeat' | 'initial_data';
  data?: any;
  timestamp: string;
}

export const useRealtimeSubscription = ({
  channel,
  stationId,
  lineColor,
  onMessage
}: SubscriptionOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  const connect = useCallback(() => {
    const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://vglychbweuowsovboxyf.supabase.co';
    const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

    // Create SSE connection
    const params = new URLSearchParams();
    if (stationId) params.append('stationId', stationId);
    if (lineColor) params.append('lineColor', lineColor);

    const es = new EventSource(
      `${SUPABASE_URL}/functions/v1/realtime-subscribe?${params.toString()}`,
      {
        withCredentials: false
      }
    );

    es.onopen = () => {
      setIsConnected(true);
      console.log(`Connected to ${channel} channel`);
    };

    es.onmessage = (event) => {
      try {
        const message: RealtimeMessage = JSON.parse(event.data);
        setLastUpdate(new Date());

        switch (message.type) {
          case 'connected':
            toast({
              title: 'Real-time updates enabled',
              description: `Connected to ${channel} updates`,
            });
            break;

          case 'arrival_update':
          case 'delay_update':
          case 'alert':
          case 'initial_data':
            if (onMessage) {
              onMessage(message.data);
            }
            break;

          case 'heartbeat':
            // Keep connection alive
            console.log('Heartbeat received');
            break;
        }
      } catch (error) {
        console.error('Failed to parse message:', error);
      }
    };

    es.onerror = (error) => {
      console.error('SSE error:', error);
      setIsConnected(false);
      
      // Attempt reconnect after 5 seconds
      setTimeout(() => {
        if (es.readyState === EventSource.CLOSED) {
          connect();
        }
      }, 5000);
    };

    setEventSource(es);

    return es;
  }, [channel, stationId, lineColor, onMessage]);

  useEffect(() => {
    const es = connect();

    return () => {
      if (es) {
        es.close();
        setIsConnected(false);
      }
    };
  }, [connect]);

  const disconnect = useCallback(() => {
    if (eventSource) {
      eventSource.close();
      setEventSource(null);
      setIsConnected(false);
    }
  }, [eventSource]);

  return {
    isConnected,
    lastUpdate,
    disconnect,
    reconnect: connect
  };
};