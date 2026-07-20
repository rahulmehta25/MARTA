/**
 * Component for displaying real-time MARTA arrivals
 */
import React, { useState, useEffect } from 'react';
import { Clock, Train, RefreshCw, AlertCircle } from 'lucide-react';
import { RealtimeService, type RealTimeArrival } from '@/lib/realtime-service';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface RealTimeArrivalsProps {
  stopId?: string;
  stationName?: string;
  limit?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const RealTimeArrivals: React.FC<RealTimeArrivalsProps> = ({
  stopId,
  stationName,
  limit = 10,
  autoRefresh = true,
  refreshInterval = 30000, // 30 seconds
}) => {
  const [arrivals, setArrivals] = useState<RealTimeArrival[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchArrivals = async () => {
    try {
      setError(null);
      let data: RealTimeArrival[] = [];

      if (stationName) {
        const response = await RealtimeService.getArrivalsByStation(stationName, limit);
        data = response.arrivals;
      } else if (stopId) {
        data = await RealtimeService.getArrivals({ stop_id: stopId, limit });
      } else {
        data = await RealtimeService.getArrivals({ limit });
      }

      // Filter for future arrivals only
      const filtered = RealtimeService.filterByTimeWindow(data, 120);
      setArrivals(filtered);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error fetching arrivals:', err);
      setError(err instanceof Error ? err.message : 'Failed to load arrivals');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchArrivals();
  };

  useEffect(() => {
    fetchArrivals();

    if (autoRefresh) {
      const interval = setInterval(fetchArrivals, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [stopId, stationName, limit, autoRefresh, refreshInterval]);

  // Group arrivals by stop
  const groupedArrivals = RealtimeService.groupByStop(arrivals);

  if (loading && !isRefreshing) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="flex items-center justify-center">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading arrivals...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {error}
          <Button
            variant="link"
            size="sm"
            onClick={handleRefresh}
            className="ml-2"
          >
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (arrivals.length === 0) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-muted-foreground">
            <Train className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No upcoming arrivals</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Train className="h-5 w-5" />
            Real-Time Arrivals
          </CardTitle>
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-muted-foreground">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="h-8 w-8"
            >
              <RefreshCw
                className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`}
              />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Array.from(groupedArrivals.entries()).map(([stopId, stopArrivals]) => (
            <div key={stopId} className="space-y-2">
              <h3 className="font-medium text-sm">
                {stopArrivals[0].stop_name}
              </h3>
              <div className="space-y-1">
                {stopArrivals.slice(0, 3).map((arrival) => (
                  <ArrivalItem key={arrival.id} arrival={arrival} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

interface ArrivalItemProps {
  arrival: RealTimeArrival;
}

const ArrivalItem: React.FC<ArrivalItemProps> = ({ arrival }) => {
  const arrivalTime = RealtimeService.formatArrivalTime(arrival.arrival_time);
  const routeColor = RealtimeService.getRouteColor(arrival.route_id);

  return (
    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-3">
        <Badge
          style={{ backgroundColor: routeColor }}
          className="text-white font-bold min-w-[60px] justify-center"
        >
          {arrival.route_id || 'N/A'}
        </Badge>
        <div className="flex flex-col">
          <span className="text-sm font-medium">
            Train {arrival.vehicle_id || 'Unknown'}
          </span>
          {arrival.trip_id && (
            <span className="text-xs text-muted-foreground">
              Trip {arrival.trip_id}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <span className="font-semibold">
          {arrivalTime}
        </span>
        {arrival.delay_seconds > 0 && (
          <Badge variant="outline" className="text-xs">
            +{Math.round(arrival.delay_seconds / 60)}m
          </Badge>
        )}
      </div>
    </div>
  );
};

export default RealTimeArrivals;