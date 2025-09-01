import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Train, Clock, AlertCircle, TrendingUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Arrival {
  station: string;
  line: string;
  destination: string;
  waiting_seconds: number;
  waiting_time: string;
  direction: string;
  delay: string;
  predicted_seconds?: number;
  confidence?: number;
}

interface ArrivalBoardProps {
  stationId?: string;
  limit?: number;
}

export const ArrivalBoard: React.FC<ArrivalBoardProps> = ({ 
  stationId = 'FIVE POINTS STATION', 
  limit = 10 
}) => {
  const [arrivals, setArrivals] = useState<Arrival[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Supabase Edge Functions endpoint
  const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://vglychbweuowsovboxyf.supabase.co';
  const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY';

  const fetchArrivals = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch real-time arrivals from Supabase Edge Function
      const response = await fetch(
        `${SUPABASE_URL}/functions/v1/marta-arrivals?station=${encodeURIComponent(stationId)}`,
        {
          headers: {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
          }
        }
      );
      
      if (!response.ok) throw new Error('Failed to fetch arrivals');
      
      const data = await response.json();
      
      // Sort by waiting time and limit
      const sortedArrivals = data
        .sort((a: Arrival, b: Arrival) => a.waiting_seconds - b.waiting_seconds)
        .slice(0, limit);
      
      // Fetch predictions for each arrival
      const arrivalsWithPredictions = await Promise.all(
        sortedArrivals.map(async (arrival: Arrival) => {
          try {
            const predResponse = await fetch(
              `${API_BASE}/api/v1/analytics/predictions/${encodeURIComponent(arrival.station)}?line=${arrival.line}&direction=${arrival.direction}`
            );
            if (predResponse.ok) {
              const prediction = await predResponse.json();
              return {
                ...arrival,
                predicted_seconds: prediction.predicted_seconds,
                confidence: prediction.confidence
              };
            }
          } catch (e) {
            console.warn('Prediction fetch failed:', e);
          }
          return arrival;
        })
      );
      
      setArrivals(arrivalsWithPredictions);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load arrivals');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchArrivals();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchArrivals, 30000);
    
    return () => clearInterval(interval);
  }, [stationId]);

  const getLineColor = (line: string) => {
    switch (line?.toUpperCase()) {
      case 'RED': return 'bg-red-500';
      case 'GOLD': return 'bg-yellow-500';
      case 'BLUE': return 'bg-blue-500';
      case 'GREEN': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return 'Arriving';
    const minutes = Math.floor(seconds / 60);
    return `${minutes} min`;
  };

  const getDelayStatus = (delayStr: string) => {
    const delay = parseInt(delayStr) || 0;
    if (delay <= 60) return { text: 'On Time', color: 'text-green-500' };
    if (delay <= 300) return { text: 'Minor Delay', color: 'text-yellow-500' };
    return { text: 'Delayed', color: 'text-red-500' };
  };

  if (loading && arrivals.length === 0) {
    return (
      <Card className="w-full">
        <CardContent className="p-6">
          <div className="flex items-center justify-center space-x-2">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
            <span>Loading arrivals...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full border-red-200">
        <CardContent className="p-6">
          <div className="flex items-center space-x-2 text-red-500">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Train className="h-5 w-5" />
            {stationId}
          </CardTitle>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            {lastUpdate.toLocaleTimeString()}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border">
          <AnimatePresence mode="popLayout">
            {arrivals.map((arrival, index) => (
              <motion.div
                key={`${arrival.train_id}-${index}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: index * 0.05 }}
                className="p-4 hover:bg-secondary/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {/* Line indicator */}
                    <div className={`w-3 h-12 rounded-full ${getLineColor(arrival.line)}`} />
                    
                    {/* Arrival info */}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{arrival.destination}</span>
                        <Badge variant="outline" className="text-xs">
                          {arrival.direction}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-sm text-muted-foreground">
                          {arrival.line} Line
                        </span>
                        <span className={`text-xs ${getDelayStatus(arrival.delay).color}`}>
                          {getDelayStatus(arrival.delay).text}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Timing */}
                  <div className="text-right">
                    <div className="text-2xl font-bold">
                      {formatTime(arrival.waiting_seconds)}
                    </div>
                    {arrival.predicted_seconds && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <TrendingUp className="h-3 w-3" />
                        <span>ML: {formatTime(arrival.predicted_seconds)}</span>
                        {arrival.confidence && (
                          <span className="text-xs">
                            ({Math.round(arrival.confidence * 100)}%)
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {arrivals.length === 0 && (
            <div className="p-8 text-center text-muted-foreground">
              No arrivals scheduled for this station
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ArrivalBoard;