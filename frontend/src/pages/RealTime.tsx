import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Radio,
  Train,
  Clock,
  RefreshCw,
  MapPin,
  ArrowRight,
  AlertCircle,
} from 'lucide-react';
import { martaStops, martaRoutes } from '@/data/martaData';
import { cn } from '@/lib/utils';
import { useCountUp } from '@/hooks/useCountUp';

interface Arrival {
  id: string;
  line: string;
  lineColor: string;
  destination: string;
  etaMinutes: number;
  status: 'on_time' | 'delayed' | 'arriving';
  delay?: number;
  platform?: string;
}

interface Vehicle {
  id: string;
  routeId: string;
  routeName: string;
  routeColor: string;
  currentStation: string;
  nextStation: string;
  speed: number;
  passengers: number;
}

// Generate sample arrivals
function generateArrivals(stationId: string): Arrival[] {
  const station = martaStops.find((s) => s.id === stationId);
  if (!station) return [];

  return station.routes.flatMap((routeId) => {
    const route = martaRoutes.find((r) => r.id === routeId);
    if (!route) return [];

    return Array.from({ length: 2 }, (_, i) => ({
      id: `${routeId}-${i}`,
      line: route.name,
      lineColor: route.color,
      destination: i % 2 === 0 ? 'Airport' : 'North Springs',
      etaMinutes: Math.floor(Math.random() * 15) + 1,
      status: Math.random() > 0.8 ? 'delayed' : Math.random() > 0.5 ? 'arriving' : 'on_time',
      delay: Math.random() > 0.8 ? Math.floor(Math.random() * 5) + 1 : undefined,
      platform: Math.random() > 0.5 ? 'A' : 'B',
    }));
  }).sort((a, b) => a.etaMinutes - b.etaMinutes);
}

// Generate sample vehicles
function generateVehicles(): Vehicle[] {
  return martaRoutes.flatMap((route) =>
    Array.from({ length: 3 }, (_, i) => {
      const stationIndex = Math.floor(Math.random() * (route.stops.length - 1));
      const currentStation = martaStops.find((s) => s.id === route.stops[stationIndex]);
      const nextStation = martaStops.find((s) => s.id === route.stops[stationIndex + 1]);

      return {
        id: `${route.id}-V${i + 1}`,
        routeId: route.id,
        routeName: route.name,
        routeColor: route.color,
        currentStation: currentStation?.name || 'Unknown',
        nextStation: nextStation?.name || 'Unknown',
        speed: Math.floor(Math.random() * 30) + 20,
        passengers: Math.floor(Math.random() * 150) + 50,
      };
    })
  );
}

export default function RealTimePage() {
  const [selectedStation, setSelectedStation] = useState(martaStops[0].id);
  const [arrivals, setArrivals] = useState<Arrival[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshData = async () => {
    setIsRefreshing(true);
    await new Promise((resolve) => setTimeout(resolve, 300));
    setArrivals(generateArrivals(selectedStation));
    setVehicles(generateVehicles());
    setLastUpdated(new Date());
    setIsRefreshing(false);
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 30000);
    return () => clearInterval(interval);
  }, [selectedStation]);

  const stationName = martaStops.find((s) => s.id === selectedStation)?.name || '';

  const activeTrainCount = useCountUp(vehicles.length, 800);
  const totalPassengers = Math.floor(vehicles.reduce((a, b) => a + b.passengers, 0) / 1000);
  const animatedPassengers = useCountUp(totalPassengers, 800);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-in-up">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-green-500" />
            </span>
            <h1 className="text-2xl font-semibold">Real-Time View</h1>
          </div>
          <Badge variant="secondary" className="text-green-700 bg-green-50">
            Live
          </Badge>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={refreshData}
            disabled={isRefreshing}
            className="gap-2"
          >
            <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Arrivals panel */}
        <div className="col-span-2 space-y-4">
          {/* Station selector */}
          <div className="flex items-center gap-4 animate-slide-in-left">
            <div className="w-64">
              <Select value={selectedStation} onValueChange={setSelectedStation}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {martaStops.map((station) => (
                    <SelectItem key={station.id} value={station.id}>
                      {station.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4" />
              <span>{stationName}</span>
            </div>
          </div>

          {/* Arrivals board */}
          <div className="animate-fade-in-up stagger-2">
            <Card className="hover-lift">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <Radio className="h-4 w-4" />
                  Upcoming Arrivals
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {arrivals.map((arrival, index) => (
                    <div
                      key={arrival.id}
                      className={cn(
                        'flex items-center gap-4 p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors animate-fade-in-up',
                        index < 6 ? `stagger-${index + 1}` : 'stagger-6'
                      )}
                    >
                      {/* Line indicator */}
                      <div
                        className="px-2.5 py-1 rounded text-xs font-semibold text-white min-w-[80px] text-center"
                        style={{ backgroundColor: arrival.lineColor }}
                      >
                        {arrival.line.replace(' Line', '')}
                      </div>

                      {/* Destination */}
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <ArrowRight className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{arrival.destination}</span>
                        </div>
                        {arrival.platform && (
                          <span className="text-xs text-muted-foreground">
                            Platform {arrival.platform}
                          </span>
                        )}
                      </div>

                      {/* Status */}
                      <div className="flex items-center gap-3">
                        {arrival.status === 'delayed' && arrival.delay && (
                          <div className="flex items-center gap-1 text-xs text-amber-600">
                            <AlertCircle className="h-3.5 w-3.5" />
                            <span>+{arrival.delay} min</span>
                          </div>
                        )}
                        {arrival.status === 'arriving' && (
                          <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                            Arriving
                          </Badge>
                        )}
                      </div>

                      {/* ETA */}
                      <div className="text-right min-w-[60px]">
                        <p className="text-xl font-semibold tabular-nums">
                          {arrival.etaMinutes}
                        </p>
                        <p className="text-2xs text-muted-foreground">min</p>
                      </div>
                    </div>
                  ))}

                  {arrivals.length === 0 && (
                    <div className="py-8 text-center text-muted-foreground">
                      <Train className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No upcoming arrivals</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Live vehicles panel */}
        <div className="space-y-4 animate-fade-in-up stagger-3">
          <Card className="hover-lift">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <Train className="h-4 w-4" />
                Active Vehicles
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {vehicles.slice(0, 8).map((vehicle, i) => (
                  <div
                    key={vehicle.id}
                    className={cn(
                      'p-3 rounded-lg border border-border hover:border-border/80 hover-lift animate-fade-in-up',
                      i < 6 ? `stagger-${i + 1}` : 'stagger-6'
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="relative flex h-2 w-2">
                          <span
                            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
                            style={{ backgroundColor: vehicle.routeColor }}
                          />
                          <span
                            className="relative inline-flex h-2 w-2 rounded-full"
                            style={{ backgroundColor: vehicle.routeColor }}
                          />
                        </span>
                        <span className="text-xs font-medium">{vehicle.id}</span>
                      </div>
                      <span className="text-2xs text-muted-foreground">
                        {vehicle.routeName}
                      </span>
                    </div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Location</span>
                        <span className="font-medium truncate max-w-[120px]">
                          {vehicle.currentStation}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Next stop</span>
                        <span className="truncate max-w-[120px]">
                          {vehicle.nextStation}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Speed</span>
                        <span>{vehicle.speed} mph</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Passengers</span>
                        <span>~{vehicle.passengers}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* System summary */}
          <Card className="hover-lift animate-fade-in-up stagger-4">
            <CardContent className="p-4">
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p className="text-2xl font-semibold tabular-nums">{activeTrainCount}</p>
                  <p className="text-xs text-muted-foreground">Active trains</p>
                </div>
                <div>
                  <p className="text-2xl font-semibold tabular-nums">{animatedPassengers}K</p>
                  <p className="text-xs text-muted-foreground">Passengers</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
