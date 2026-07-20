import React, { useState, useEffect } from 'react';
import { Train, Clock, RefreshCw, AlertCircle, MapPin } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RealtimeService, type MartaRailArrival } from '@/lib/realtime-service';

interface SystemStatus {
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

export const RealTimePanel: React.FC = () => {
  const [arrivals, setArrivals] = useState<MartaRailArrival[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const formatTime = (waitingTime: string) => {
    // MARTA API already provides formatted waiting time
    return waitingTime || 'Unknown';
  };

  const getLineColor = (line: string): string => {
    const colors: Record<string, string> = {
      RED: '#EF3E42',
      GOLD: '#F9A51A',
      GREEN: '#00B251',
      BLUE: '#0075C9',
    };
    return colors[line?.toUpperCase()] || '#666';
  };

  const fetchData = async () => {
    try {
      setError(null);
      
      // Fetch both MARTA status and arrivals
      const [statusData, arrivalsData] = await Promise.all([
        RealtimeService.getMartaSystemStatus(),
        RealtimeService.getMartaRailArrivals()
      ]);

      setStatus(statusData);
      
      // Sort by waiting seconds
      const sortedArrivals = [...arrivalsData].sort((a, b) => {
        const aSeconds = parseInt(a.waiting_seconds) || 999999;
        const bSeconds = parseInt(b.waiting_seconds) || 999999;
        return aSeconds - bSeconds;
      });
      
      // Group by station and take first 10 unique stations
      const seenStations = new Set<string>();
      const uniqueArrivals = sortedArrivals.filter(arrival => {
        if (seenStations.has(arrival.station)) {
          return false;
        }
        seenStations.add(arrival.station);
        return true;
      });
      
      setArrivals(uniqueArrivals.slice(0, 10));
    } catch (err) {
      console.error('Error fetching MARTA real-time data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load real-time data');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchData();
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading && !isRefreshing) {
    return (
      <Card className="w-full">
        <CardContent className="py-8">
          <div className="flex items-center justify-center">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
            <span className="text-muted-foreground">Loading real-time data...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Train className="h-5 w-5" />
            Live Arrivals
          </CardTitle>
          <div className="flex items-center gap-3">
            {status && (
              <div className="flex items-center gap-2 text-xs">
                <div className={`w-2 h-2 rounded-full ${
                  status.status === 'normal' ? 'bg-green-500' : 
                  status.status === 'minor_delays' ? 'bg-yellow-500' : 'bg-red-500'
                }`} />
                <span className="text-muted-foreground">
                  {status.active_trains} trains
                </span>
              </div>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="h-8 w-8"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {error ? (
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">{error}</span>
          </div>
        ) : arrivals.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Train className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No upcoming arrivals</p>
          </div>
        ) : (
          <div className="space-y-2">
            {arrivals.map((arrival, idx) => (
              <div
                key={`${arrival.train_id}-${arrival.station}-${idx}`}
                className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Badge
                    style={{ backgroundColor: getLineColor(arrival.line) }}
                    className="text-white font-bold min-w-[50px] justify-center"
                  >
                    {arrival.line || 'N/A'}
                  </Badge>
                  <div>
                    <div className="font-medium text-sm flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {arrival.station.replace(' STATION', '')}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      To {arrival.destination} • {arrival.direction}
                    </div>
                  </div>
                </div>
                <div className="flex flex-col items-end">
                  <span className="font-semibold text-sm">
                    {formatTime(arrival.waiting_time)}
                  </span>
                  {arrival.delay !== '0 Seconds' && arrival.delay !== 'T0S' && (
                    <span className="text-xs text-orange-600">Delayed</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {status && status.last_updated && (
          <div className="text-center text-xs text-muted-foreground mt-4">
            Data updated {new Date(status.last_updated).toLocaleTimeString()}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RealTimePanel;