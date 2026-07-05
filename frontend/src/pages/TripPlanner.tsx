import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  MapPin,
  Clock,
  ArrowRightLeft,
  Navigation,
  Train,
  Footprints,
  ChevronRight,
} from 'lucide-react';
import { martaStops, martaRoutes } from '@/data/martaData';
import { useAppStore } from '@/store';
import { cn } from '@/lib/utils';

interface TripSegment {
  type: 'walk' | 'rail';
  from: string;
  to: string;
  line?: string;
  lineColor?: string;
  duration: number;
  stops?: number;
}

interface TripResult {
  id: string;
  departure: string;
  arrival: string;
  duration: number;
  transfers: number;
  segments: TripSegment[];
}

// Generate sample trip results
function generateTripResults(origin: string, destination: string): TripResult[] {
  const now = new Date();
  const results: TripResult[] = [];

  for (let i = 0; i < 3; i++) {
    const depTime = new Date(now.getTime() + (5 + i * 15) * 60000);
    const duration = Math.floor(Math.random() * 20 + 20);
    const arrTime = new Date(depTime.getTime() + duration * 60000);

    const segments: TripSegment[] = [
      { type: 'walk', from: 'Your location', to: origin, duration: 5 },
      {
        type: 'rail',
        from: origin,
        to: destination,
        line: i % 2 === 0 ? 'Red Line' : 'Gold Line',
        lineColor: i % 2 === 0 ? '#dc2626' : '#f59e0b',
        duration: duration - 10,
        stops: Math.floor(Math.random() * 8 + 3),
      },
      { type: 'walk', from: destination, to: 'Destination', duration: 5 },
    ];

    results.push({
      id: `trip-${i}`,
      departure: depTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
      arrival: arrTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }),
      duration,
      transfers: i === 2 ? 1 : 0,
      segments,
    });
  }

  return results;
}

export default function TripPlannerPage() {
  const { trip, setTripOrigin, setTripDestination, swapOriginDestination } = useAppStore();
  const [originStation, setOriginStation] = useState('');
  const [destinationStation, setDestinationStation] = useState('');
  const [results, setResults] = useState<TripResult[]>([]);
  const [selectedTrip, setSelectedTrip] = useState<TripResult | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!originStation || !destinationStation) return;

    setIsSearching(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 500));

    const origin = martaStops.find((s) => s.id === originStation);
    const destination = martaStops.find((s) => s.id === destinationStation);

    if (origin && destination) {
      setResults(generateTripResults(origin.name, destination.name));
    }
    setIsSearching(false);
  };

  const handleSwap = () => {
    const temp = originStation;
    setOriginStation(destinationStation);
    setDestinationStation(temp);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-semibold">Trip Planner</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Plan your journey across the MARTA system
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Search panel */}
        <div className="col-span-1 space-y-4 animate-slide-in-left">
          <Card className="hover-lift">
            <CardHeader className="pb-4">
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <Navigation className="h-4 w-4" />
                Plan Your Trip
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Origin */}
              <div className="space-y-2">
                <Label className="text-sm">From</Label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-green-600" />
                  <Select value={originStation} onValueChange={setOriginStation}>
                    <SelectTrigger className="pl-9">
                      <SelectValue placeholder="Select origin station" />
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
              </div>

              {/* Swap button */}
              <div className="flex justify-center">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleSwap}
                  className="rounded-full hover:rotate-180 transition-transform duration-300"
                >
                  <ArrowRightLeft className="h-4 w-4 rotate-90" />
                </Button>
              </div>

              {/* Destination */}
              <div className="space-y-2">
                <Label className="text-sm">To</Label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-red-600" />
                  <Select value={destinationStation} onValueChange={setDestinationStation}>
                    <SelectTrigger className="pl-9">
                      <SelectValue placeholder="Select destination" />
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
              </div>

              {/* Time */}
              <div className="space-y-2">
                <Label className="text-sm">Depart</Label>
                <Select defaultValue="now">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="now">Leave now</SelectItem>
                    <SelectItem value="15min">In 15 minutes</SelectItem>
                    <SelectItem value="30min">In 30 minutes</SelectItem>
                    <SelectItem value="1hr">In 1 hour</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                className="w-full"
                onClick={handleSearch}
                disabled={!originStation || !destinationStation || isSearching}
              >
                {isSearching ? 'Searching...' : 'Find Routes'}
              </Button>
            </CardContent>
          </Card>

          {/* Quick tips */}
          <div className="animate-fade-in-up stagger-3">
            <Card className="hover-lift">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">
                  <strong>Tip:</strong> Five Points is the central transfer point for all
                  MARTA rail lines.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Results */}
        <div className="col-span-2 space-y-4">
          {results.length > 0 ? (
            <div className="space-y-4 animate-fade-in-up">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {results.length} routes found
                </p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="h-3.5 w-3.5" />
                  Departing soon
                </div>
              </div>

              <div className="space-y-3">
                {results.map((trip, i) => (
                  <div
                    key={trip.id}
                    className={cn(
                      'animate-fade-in-up',
                      i < 6 ? `stagger-${i + 1}` : 'stagger-6'
                    )}
                  >
                    <Card
                      className={cn(
                        'cursor-pointer hover-lift transition-all',
                        selectedTrip?.id === trip.id && 'ring-2 ring-primary'
                      )}
                      onClick={() => setSelectedTrip(trip)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-4">
                            <div className="text-center">
                              <p className="text-lg font-semibold">{trip.departure}</p>
                              <p className="text-2xs text-muted-foreground">Depart</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="h-px w-8 bg-border" />
                              <span className="text-xs text-muted-foreground">
                                {trip.duration} min
                              </span>
                              <div className="h-px w-8 bg-border" />
                            </div>
                            <div className="text-center">
                              <p className="text-lg font-semibold">{trip.arrival}</p>
                              <p className="text-2xs text-muted-foreground">Arrive</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium">
                              {trip.transfers === 0 ? 'Direct' : `${trip.transfers} transfer`}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {trip.segments.find((s) => s.type === 'rail')?.stops} stops
                            </p>
                          </div>
                        </div>

                        {/* Segments preview */}
                        <div className="flex items-center gap-2">
                          {trip.segments.map((segment, j) => (
                            <React.Fragment key={j}>
                              {segment.type === 'walk' ? (
                                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                  <Footprints className="h-3.5 w-3.5" />
                                  <span>{segment.duration}m</span>
                                </div>
                              ) : (
                                <div
                                  className="flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium text-white"
                                  style={{ backgroundColor: segment.lineColor }}
                                >
                                  <Train className="h-3.5 w-3.5" />
                                  <span>{segment.line}</span>
                                </div>
                              )}
                              {j < trip.segments.length - 1 && (
                                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                ))}
              </div>

              {/* Selected trip details */}
              {selectedTrip && (
                <div className="animate-fade-in-up">
                  <Card className="hover-lift">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base font-medium">
                        Route Details
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {selectedTrip.segments.map((segment, i) => (
                          <div
                            key={i}
                            className={cn(
                              'flex gap-4 animate-slide-in-left',
                              i < 6 ? `stagger-${i + 1}` : 'stagger-6'
                            )}
                          >
                            <div className="flex flex-col items-center">
                              <div
                                className={cn(
                                  'h-3 w-3 rounded-full',
                                  segment.type === 'walk' ? 'bg-gray-400' : 'bg-current'
                                )}
                                style={
                                  segment.type === 'rail'
                                    ? { backgroundColor: segment.lineColor }
                                    : undefined
                                }
                              />
                              {i < selectedTrip.segments.length - 1 && (
                                <div
                                  className={cn(
                                    'w-0.5 flex-1 my-1',
                                    segment.type === 'walk' ? 'bg-gray-300' : 'bg-current'
                                  )}
                                  style={
                                    segment.type === 'rail'
                                      ? { backgroundColor: segment.lineColor }
                                      : undefined
                                  }
                                />
                              )}
                            </div>
                            <div className="flex-1 pb-4">
                              <div className="flex items-center justify-between">
                                <p className="text-sm font-medium">{segment.from}</p>
                                <p className="text-xs text-muted-foreground">
                                  {segment.duration} min
                                </p>
                              </div>
                              {segment.type === 'rail' && (
                                <p className="text-xs text-muted-foreground mt-0.5">
                                  Take {segment.line} for {segment.stops} stops
                                </p>
                              )}
                              {segment.type === 'walk' && (
                                <p className="text-xs text-muted-foreground mt-0.5">
                                  Walk to station
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                        <div className="flex gap-4">
                          <div className="h-3 w-3 rounded-full bg-red-500" />
                          <p className="text-sm font-medium">
                            {selectedTrip.segments[selectedTrip.segments.length - 1].to}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          ) : (
            <div className="animate-fade-in-scale stagger-2">
              <Card className="h-96">
                <CardContent className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <Navigation className="h-12 w-12 mx-auto text-muted-foreground/30 mb-4" />
                    <p className="text-lg font-medium mb-1">Plan Your Journey</p>
                    <p className="text-sm text-muted-foreground max-w-sm">
                      Select your origin and destination stations to find the best routes.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
