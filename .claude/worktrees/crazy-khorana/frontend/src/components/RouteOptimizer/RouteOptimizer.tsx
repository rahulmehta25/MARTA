import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { Navigation, Clock, Users, ArrowRight, Zap, Route } from 'lucide-react';
import {
  stationPositions,
  stationAnalyticsMap,
  findRoute,
  getLineForSegment,
  LINE_COLORS,
  LINES,
} from '@/data/stationAnalytics';

const stationList = Object.entries(stationAnalyticsMap)
  .map(([id, a]) => ({ id, name: a.name }))
  .sort((a, b) => a.name.localeCompare(b.name));

function buildPathD(ids: string[]): string {
  return ids
    .map((id, i) => {
      const p = stationPositions[id];
      return p ? `${i === 0 ? 'M' : 'L'}${p.x},${p.y}` : '';
    })
    .filter(Boolean)
    .join(' ');
}

function getCrowdingForSegment(a: string, b: string): 'low' | 'moderate' | 'high' {
  const aLevel = stationAnalyticsMap[a]?.crowdingLevel || 'low';
  const bLevel = stationAnalyticsMap[b]?.crowdingLevel || 'low';
  const levels = { low: 0, moderate: 1, high: 2 };
  const avg = (levels[aLevel] + levels[bLevel]) / 2;
  return avg >= 1.5 ? 'high' : avg >= 0.5 ? 'moderate' : 'low';
}

function RouteMapPreview({ routeStops, animProgress }: { routeStops: string[]; animProgress: number }) {
  const activeDot = Math.min(Math.floor(animProgress * routeStops.length), routeStops.length - 1);
  const activePos = stationPositions[routeStops[activeDot]];

  return (
    <svg viewBox="0 0 1080 790" className="w-full rounded-lg border border-border/50" style={{ minHeight: 220 }}>
      <rect width="1080" height="790" fill="hsl(var(--background))" />

      {Object.entries(LINES).map(([id, stops]) => (
        <path
          key={id}
          d={buildPathD(stops)}
          fill="none"
          stroke={LINE_COLORS[id]}
          strokeWidth={2}
          opacity={0.15}
          strokeLinecap="round"
        />
      ))}

      {Object.entries(stationPositions).map(([id, pos]) => (
        <circle
          key={id}
          cx={pos.x}
          cy={pos.y}
          r={3}
          fill="hsl(var(--muted-foreground))"
          opacity={0.2}
        />
      ))}

      <path
        d={buildPathD(routeStops)}
        fill="none"
        stroke="#1E88E5"
        strokeWidth={5}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.3}
      />
      <motion.path
        d={buildPathD(routeStops)}
        fill="none"
        stroke="#1E88E5"
        strokeWidth={4}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: animProgress }}
        transition={{ duration: 0.05 }}
      />

      {routeStops.map((id, i) => {
        const pos = stationPositions[id];
        if (!pos) return null;
        const isEnd = i === 0 || i === routeStops.length - 1;
        return (
          <g key={id}>
            <circle
              cx={pos.x}
              cy={pos.y}
              r={isEnd ? 8 : 5}
              fill={isEnd ? '#1E88E5' : 'hsl(var(--background))'}
              stroke="#1E88E5"
              strokeWidth={2}
            />
            {isEnd && (
              <text
                x={pos.x}
                y={pos.y - 14}
                textAnchor="middle"
                fontSize={11}
                fontWeight={700}
                fill="hsl(var(--foreground))"
              >
                {stationAnalyticsMap[id]?.name || id}
              </text>
            )}
          </g>
        );
      })}

      {activePos && (
        <g>
          <circle cx={activePos.x} cy={activePos.y} r={10} fill="#1E88E5" opacity={0.2} />
          <circle cx={activePos.x} cy={activePos.y} r={6} fill="#1E88E5" />
          <circle cx={activePos.x} cy={activePos.y} r={3} fill="white" />
        </g>
      )}
    </svg>
  );
}

export function RouteOptimizerPanel() {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [route, setRoute] = useState<string[] | null>(null);
  const [animProgress, setAnimProgress] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const routeDetails = useMemo(() => {
    if (!route || route.length < 2) return null;
    const segments = [];
    let totalTime = 0;
    for (let i = 0; i < route.length - 1; i++) {
      const line = getLineForSegment(route[i], route[i + 1]);
      const crowding = getCrowdingForSegment(route[i], route[i + 1]);
      const time = 2 + Math.random() * 1.5;
      totalTime += time;
      segments.push({
        from: route[i],
        to: route[i + 1],
        line,
        crowding,
        time: Math.round(time * 10) / 10,
      });
    }
    return { segments, totalTime: Math.round(totalTime), stops: route.length };
  }, [route]);

  const handleFindRoute = () => {
    if (!origin || !destination || origin === destination) return;
    const found = findRoute(origin, destination);
    setRoute(found);
    if (found) {
      setAnimProgress(0);
      setIsAnimating(true);
    }
  };

  useEffect(() => {
    if (!isAnimating) return;
    let progress = 0;
    const interval = setInterval(() => {
      progress += 0.02;
      if (progress >= 1) {
        progress = 1;
        setIsAnimating(false);
        clearInterval(interval);
      }
      setAnimProgress(progress);
    }, 30);
    return () => clearInterval(interval);
  }, [isAnimating]);

  const altTime = routeDetails ? routeDetails.totalTime + Math.floor(Math.random() * 8) + 3 : 0;

  return (
    <div className="space-y-5">
      <Card className="border-0 shadow-md">
        <CardContent className="p-5">
          <div className="flex items-center gap-3 mb-5">
            <div className="p-2 bg-primary/10 rounded-xl">
              <Navigation className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold">Route Optimizer</h3>
              <p className="text-xs text-muted-foreground">Find the fastest route with crowding analysis</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-[1fr,auto,1fr,auto] gap-3 items-end">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Origin</label>
              <Select value={origin} onValueChange={setOrigin}>
                <SelectTrigger>
                  <SelectValue placeholder="Select station" />
                </SelectTrigger>
                <SelectContent>
                  {stationList.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-center pb-1">
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Destination</label>
              <Select value={destination} onValueChange={setDestination}>
                <SelectTrigger>
                  <SelectValue placeholder="Select station" />
                </SelectTrigger>
                <SelectContent>
                  {stationList.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleFindRoute} disabled={!origin || !destination || origin === destination}>
              <Route className="h-4 w-4 mr-2" />
              Find Route
            </Button>
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>
        {route && routeDetails && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
          >
            <RouteMapPreview routeStops={route} animProgress={animProgress} />

            <div className="grid grid-cols-3 gap-3">
              <Card className="border-0 shadow-sm">
                <CardContent className="p-4 text-center">
                  <Clock className="h-5 w-5 mx-auto mb-1 text-primary" />
                  <p className="text-2xl font-bold tabular-nums">{routeDetails.totalTime}</p>
                  <p className="text-[10px] text-muted-foreground">Minutes</p>
                </CardContent>
              </Card>
              <Card className="border-0 shadow-sm">
                <CardContent className="p-4 text-center">
                  <Zap className="h-5 w-5 mx-auto mb-1 text-amber-500" />
                  <p className="text-2xl font-bold tabular-nums">{routeDetails.stops}</p>
                  <p className="text-[10px] text-muted-foreground">Stops</p>
                </CardContent>
              </Card>
              <Card className="border-0 shadow-sm">
                <CardContent className="p-4 text-center">
                  <Users className="h-5 w-5 mx-auto mb-1 text-emerald-500" />
                  <p className="text-2xl font-bold capitalize">
                    {routeDetails.segments.filter((s) => s.crowding === 'high').length > routeDetails.segments.length / 2
                      ? 'High'
                      : routeDetails.segments.filter((s) => s.crowding === 'low').length > routeDetails.segments.length / 2
                      ? 'Low'
                      : 'Mod'}
                  </p>
                  <p className="text-[10px] text-muted-foreground">Crowding</p>
                </CardContent>
              </Card>
            </div>

            <Card className="border-0 shadow-md">
              <CardContent className="p-4">
                <p className="text-xs font-medium text-muted-foreground mb-3">
                  Route Segments
                </p>
                <div className="space-y-1.5 max-h-64 overflow-y-auto">
                  {routeDetails.segments.map((seg, i) => {
                    const crowdColor =
                      seg.crowding === 'high'
                        ? 'bg-red-500'
                        : seg.crowding === 'moderate'
                        ? 'bg-amber-500'
                        : 'bg-green-500';
                    return (
                      <div key={i} className="flex items-center gap-2 text-xs py-1.5 px-2 rounded-md hover:bg-secondary/50 transition-colors duration-150">
                        <div
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: LINE_COLORS[seg.line] }}
                        />
                        <span className="font-medium truncate">{stationAnalyticsMap[seg.from]?.name}</span>
                        <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                        <span className="font-medium truncate">{stationAnalyticsMap[seg.to]?.name}</span>
                        <span className="ml-auto text-muted-foreground shrink-0 tabular-nums">{seg.time}m</span>
                        <div className={`w-2 h-2 rounded-full shrink-0 ${crowdColor}`} title={seg.crowding} />
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            <Card className="border border-dashed border-muted-foreground/20 shadow-none rounded-lg">
              <CardContent className="p-4">
                <p className="text-xs font-semibold text-muted-foreground mb-2">Alternative Route</p>
                <div className="flex items-center justify-between">
                  <p className="text-sm">
                    Via{' '}
                    {route.length > 4
                      ? stationAnalyticsMap[route[Math.floor(route.length / 2)]]?.name
                      : 'Five Points'}{' '}
                    (different line)
                  </p>
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-semibold">{altTime} min</span>
                    <span className="text-xs text-red-500">+{altTime - routeDetails.totalTime} min</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
