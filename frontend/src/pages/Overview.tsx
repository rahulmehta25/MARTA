import React from 'react';
import { InteractiveMap } from '@/components/Map/InteractiveMap';
import { useAppStore } from '@/store';
import { martaStops, martaRoutes } from '@/data/martaData';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Train,
  MapPin,
  Users,
  Clock,
  Layers,
  Radio,
  X,
  Accessibility,
  Car,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCountUp } from '@/hooks/useCountUp';

function AnimatedKPI({
  icon: Icon,
  label,
  rawValue,
  suffix,
  decimals,
  trend,
  trendValue,
  className,
}: {
  icon: React.ElementType;
  label: string;
  rawValue: number;
  suffix?: string;
  decimals?: number;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  className?: string;
}) {
  const animated = useCountUp(rawValue, 1200, decimals);
  return (
    <div className={className}>
      <Card className="hover-lift h-full">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-muted-foreground">{label}</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {animated}{suffix || ''}
              </p>
              {trend && trendValue && (
                <p
                  className={cn(
                    'mt-1 text-xs font-medium',
                    trend === 'up' && 'text-green-600',
                    trend === 'down' && 'text-red-600',
                    trend === 'stable' && 'text-muted-foreground'
                  )}
                >
                  {trend === 'up' && '+'}
                  {trendValue}
                </p>
              )}
            </div>
            <div className="rounded-lg bg-secondary p-2">
              <Icon className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function OverviewPage() {
  const {
    selectedStation,
    selectedRoute,
    showHeatmap,
    showStations,
    showVehicles,
    toggleHeatmap,
    toggleStations,
    toggleVehicles,
    setSelectedStation,
    setSelectedRoute,
  } = useAppStore();

  return (
    <div className="flex h-full">
      {/* Map area */}
      <div className="flex-1 relative">
        <div className="h-full animate-fade-in-scale">
          <InteractiveMap className="h-full" />
        </div>

        {/* Map controls */}
        <div className="absolute top-4 right-4 z-10 animate-fade-in-up stagger-3">
          <Card className="w-48">
            <CardHeader className="p-3 pb-2">
              <CardTitle className="text-sm font-medium">Map Layers</CardTitle>
            </CardHeader>
            <CardContent className="p-3 pt-0 space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="heatmap" className="text-xs">
                  Demand Heatmap
                </Label>
                <Switch
                  id="heatmap"
                  checked={showHeatmap}
                  onCheckedChange={toggleHeatmap}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="stations" className="text-xs">
                  Stations
                </Label>
                <Switch
                  id="stations"
                  checked={showStations}
                  onCheckedChange={toggleStations}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="vehicles" className="text-xs">
                  Live Vehicles
                </Label>
                <Switch
                  id="vehicles"
                  checked={showVehicles}
                  onCheckedChange={toggleVehicles}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Side panel */}
      <aside className="w-80 border-l border-border bg-card overflow-y-auto">
        <div className="p-4 space-y-4">
          {/* KPIs */}
          <div className="grid grid-cols-2 gap-3">
            <AnimatedKPI
              className="animate-fade-in-up stagger-1"
              icon={MapPin}
              label="Stations"
              rawValue={martaStops.length}
            />
            <AnimatedKPI
              className="animate-fade-in-up stagger-2"
              icon={Train}
              label="Lines"
              rawValue={martaRoutes.length}
            />
            <AnimatedKPI
              className="animate-fade-in-up stagger-3"
              icon={Users}
              label="Daily Riders"
              rawValue={142}
              suffix="K"
              trend="up"
              trendValue="3.2%"
            />
            <AnimatedKPI
              className="animate-fade-in-up stagger-4"
              icon={Clock}
              label="On-Time"
              rawValue={94.2}
              suffix="%"
              decimals={1}
              trend="up"
              trendValue="1.1%"
            />
          </div>

          {/* Selected station/route details */}
          {selectedStation ? (
            <div className="animate-fade-in-scale">
              <Card>
                <CardHeader className="p-4 pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base">
                        {selectedStation.name}
                      </CardTitle>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Rail Station
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => setSelectedStation(null)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-0 space-y-3">
                  {/* Lines */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-1.5">Lines</p>
                    <div className="flex gap-1.5 flex-wrap">
                      {selectedStation.routes.map((routeId) => {
                        const route = martaRoutes.find((r) => r.id === routeId);
                        return (
                          <span
                            key={routeId}
                            className="px-2 py-0.5 rounded text-xs font-medium text-white"
                            style={{ backgroundColor: route?.color || '#6b7280' }}
                          >
                            {route?.name || routeId}
                          </span>
                        );
                      })}
                    </div>
                  </div>

                  {/* Features */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-1.5">
                      Features
                    </p>
                    <div className="flex gap-2">
                      {selectedStation.accessibility && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Accessibility className="h-3.5 w-3.5" />
                          <span>Accessible</span>
                        </div>
                      )}
                      {selectedStation.parking && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Car className="h-3.5 w-3.5" />
                          <span>Parking</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Current status */}
                  <div className="pt-2 border-t border-border">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Current wait</span>
                      <span className="font-medium">4 min</span>
                    </div>
                    <div className="flex justify-between text-xs mt-1">
                      <span className="text-muted-foreground">Passengers</span>
                      <span className="font-medium">~45</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : selectedRoute ? (
            <div className="animate-fade-in-scale">
              <Card>
                <CardHeader className="p-4 pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: selectedRoute.color }}
                      />
                      <CardTitle className="text-base">
                        {selectedRoute.name}
                      </CardTitle>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => setSelectedRoute(null)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-0 space-y-3">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Stations</span>
                    <span className="font-medium">{selectedRoute.stops.length}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Status</span>
                    <span className="font-medium text-green-600">On Schedule</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Frequency</span>
                    <span className="font-medium">Every 10 min</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="p-6 text-center">
                <Layers className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
                <p className="text-sm text-muted-foreground">
                  Select a station or route on the map to view details
                </p>
              </CardContent>
            </Card>
          )}

          {/* Quick stats */}
          <div className="animate-fade-in-up stagger-5">
            <Card>
              <CardHeader className="p-4 pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Radio className="h-4 w-4" />
                  System Status
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="space-y-2">
                  {martaRoutes.map((route) => (
                    <div
                      key={route.id}
                      className="flex items-center justify-between text-xs rounded-md pl-3 py-1"
                      style={{ borderLeft: `4px solid ${route.color}` }}
                    >
                      <div className="flex items-center gap-2">
                        <span>{route.name}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="relative flex h-1.5 w-1.5">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-green-500" />
                        </span>
                        <span className="text-green-600 font-medium">Normal</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </aside>
    </div>
  );
}
