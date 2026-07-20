import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, TrendingUp, Users, Clock } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import {
  stationPositions,
  stationAnalyticsMap,
  getStationAnalytics,
  LINE_COLORS,
  LINES,
} from '@/data/stationAnalytics';
import { martaStops } from '@/data/martaData';

function buildPathD(stationIds: string[]): string {
  const parts: string[] = [];
  stationIds.forEach((id, i) => {
    const pos = stationPositions[id];
    if (!pos) return;
    parts.push(i === 0 ? `M${pos.x},${pos.y}` : `L${pos.x},${pos.y}`);
  });
  return parts.join(' ');
}

interface TrainState {
  line: string;
  segmentIndex: number;
  progress: number;
  direction: 1 | -1;
}

function interpolate(a: { x: number; y: number }, b: { x: number; y: number }, t: number) {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

function getTrainPos(train: TrainState): { x: number; y: number } | null {
  const stops = LINES[train.line as keyof typeof LINES];
  if (!stops) return null;
  const i = train.segmentIndex;
  const a = stationPositions[stops[i]];
  const b = stationPositions[stops[i + 1]];
  if (!a || !b) return a || null;
  return interpolate(a, b, train.progress);
}

// Compute optimal label placement per station to avoid overlaps
function getLabelPlacement(id: string, pos: { x: number; y: number }): {
  x: number;
  y: number;
  anchor: string;
} {
  // East-west line stations (y=460) — alternate above/below
  const eastWestStations = [
    'HAMILTON_HOLMES', 'WEST_LAKE', 'ASHBY', 'VINE_CITY',
    'GEORGIA_STATE', 'KING_MEMORIAL', 'INMAN_PARK', 'EDGEWOOD',
    'EAST_LAKE', 'DECATUR', 'AVONDALE', 'KENSINGTON', 'INDIAN_CREEK',
  ];
  const ewIndex = eastWestStations.indexOf(id);
  if (ewIndex !== -1) {
    const above = ewIndex % 2 === 0;
    return {
      x: pos.x,
      y: above ? pos.y - 12 : pos.y + 16,
      anchor: 'middle',
    };
  }

  // BANKHEAD — special position (below-right of its dot)
  if (id === 'BANKHEAD') {
    return { x: pos.x + 12, y: pos.y + 4, anchor: 'start' };
  }

  // GOLD branch (northeast diagonal) — labels below
  const goldBranch = ['LENOX', 'BROOKHAVEN', 'CHAMBLEE', 'DORAVILLE'];
  if (goldBranch.includes(id)) {
    return { x: pos.x, y: pos.y + 18, anchor: 'middle' };
  }

  // North-south spine (x=480) — alternate left/right
  const northSouth = [
    'NORTH_SPRINGS', 'SANDY_SPRINGS', 'DUNWOODY', 'MEDICAL_CENTER',
    'BUCKHEAD', 'LINDBERGH', 'ARTS_CENTER', 'MIDTOWN',
    'NORTH_AVE', 'CIVIC_CENTER', 'PEACHTREE_CENTER', 'FIVE_POINTS',
    'GARNETT', 'WEST_END', 'OAKLAND_CITY', 'LAKEWOOD',
    'EAST_POINT', 'COLLEGE_PARK', 'AIRPORT',
  ];
  const nsIndex = northSouth.indexOf(id);
  if (nsIndex !== -1) {
    // FIVE_POINTS is a major hub — put label to the right
    if (id === 'FIVE_POINTS') {
      return { x: pos.x - 14, y: pos.y + 4, anchor: 'end' };
    }
    const left = nsIndex % 2 === 0;
    return {
      x: left ? pos.x - 14 : pos.x + 14,
      y: pos.y + 3.5,
      anchor: left ? 'end' : 'start',
    };
  }

  // Fallback
  return { x: pos.x + 14, y: pos.y + 3.5, anchor: 'start' };
}

interface StationPopupProps {
  stationId: string;
  onClose: () => void;
}

function StationPopup({ stationId, onClose }: StationPopupProps) {
  const analytics = getStationAnalytics(stationId);
  const stop = martaStops.find((s) => s.id === stationId);
  if (!analytics || !stop) return null;

  const chartData = analytics.hourlyPattern.map((v, i) => ({
    hour: `${i}`,
    riders: v,
  }));

  const crowdColor =
    analytics.crowdingLevel === 'high'
      ? 'text-red-500'
      : analytics.crowdingLevel === 'moderate'
      ? 'text-amber-500'
      : 'text-green-500';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border/60 rounded-lg shadow-2xl w-full max-w-md mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-gradient-to-r from-primary/15 to-primary/5 px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold">{analytics.name}</h3>
            <div className="flex gap-1.5 mt-1">
              {stop.routes.map((r) => (
                <span
                  key={r}
                  className="text-[10px] font-bold text-white px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: LINE_COLORS[r] }}
                >
                  {r}
                </span>
              ))}
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-secondary transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center p-3 bg-secondary/50 rounded-lg">
              <Users className="h-4 w-4 mx-auto mb-1 text-blue-500" />
              <p className="text-lg font-bold tabular-nums">{(analytics.dailyRidership / 1000).toFixed(1)}K</p>
              <p className="text-[10px] text-muted-foreground">Daily Riders</p>
            </div>
            <div className="text-center p-3 bg-secondary/50 rounded-lg">
              <Clock className="h-4 w-4 mx-auto mb-1 text-amber-500" />
              <p className="text-lg font-bold tabular-nums">{analytics.peakHours.length > 0 ? analytics.peakHours[0] : 'N/A'}</p>
              <p className="text-[10px] text-muted-foreground">Peak Start</p>
            </div>
            <div className="text-center p-3 bg-secondary/50 rounded-lg">
              <TrendingUp className={`h-4 w-4 mx-auto mb-1 ${crowdColor}`} />
              <p className="text-lg font-bold capitalize">{analytics.crowdingLevel}</p>
              <p className="text-[10px] text-muted-foreground">Crowding</p>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Hourly Ridership
            </p>
            <div className="h-36 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} barSize={8}>
                  <XAxis
                    dataKey="hour"
                    tick={{ fontSize: 9 }}
                    tickLine={false}
                    axisLine={false}
                    interval={2}
                  />
                  <YAxis hide />
                  <Tooltip
                    contentStyle={{
                      background: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                    formatter={(v: number) => [`${v} riders`, 'Passengers']}
                    labelFormatter={(l) => `${l}:00`}
                  />
                  <Bar dataKey="riders" fill="hsl(var(--primary))" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-primary/5 rounded-lg border border-primary/10">
            <div>
              <p className="text-xs text-muted-foreground">Predicted Demand</p>
              <p className="text-xl font-bold tabular-nums">{(analytics.predictedDemand / 1000).toFixed(1)}K</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">On-Time Rate</p>
              <p className="text-xl font-bold text-emerald-600 tabular-nums">{(analytics.onTimeRate * 100).toFixed(1)}%</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function MartaRailMap() {
  const [selectedStation, setSelectedStation] = useState<string | null>(null);
  const [hoveredStation, setHoveredStation] = useState<string | null>(null);
  const [trains, setTrains] = useState<TrainState[]>([]);
  const animRef = useRef<number>();

  useEffect(() => {
    const initial: TrainState[] = [];
    Object.keys(LINES).forEach((line) => {
      const stops = LINES[line as keyof typeof LINES];
      initial.push({ line, segmentIndex: 2, progress: 0, direction: 1 });
      initial.push({ line, segmentIndex: stops.length - 4, progress: 0, direction: -1 });
    });
    setTrains(initial);
  }, []);

  const animate = useCallback(() => {
    setTrains((prev) =>
      prev.map((t) => {
        const stops = LINES[t.line as keyof typeof LINES];
        let { segmentIndex, progress, direction } = t;
        progress += 0.008;
        if (progress >= 1) {
          progress = 0;
          segmentIndex += direction;
          if (segmentIndex >= stops.length - 1) {
            direction = -1 as const;
            segmentIndex = stops.length - 2;
          } else if (segmentIndex < 0) {
            direction = 1 as const;
            segmentIndex = 0;
          }
        }
        return { ...t, segmentIndex, progress, direction };
      })
    );
    animRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    animRef.current = requestAnimationFrame(animate);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [animate]);

  const allStationIds = Object.keys(stationPositions);

  const lineConfigs = [
    { id: 'RED', stops: LINES.RED, color: LINE_COLORS.RED, width: 4 },
    { id: 'GOLD', stops: LINES.GOLD, color: LINE_COLORS.GOLD, width: 4 },
    { id: 'BLUE', stops: LINES.BLUE, color: LINE_COLORS.BLUE, width: 4 },
    { id: 'GREEN', stops: LINES.GREEN, color: LINE_COLORS.GREEN, width: 4 },
  ];

  return (
    <div className="relative w-full bg-card border border-border/50 rounded-lg overflow-hidden shadow-md">
      <div className="flex items-center gap-6 px-5 py-3 border-b border-border/40 bg-secondary/30">
        <h3 className="font-semibold text-sm">MARTA Rail System Map</h3>
        <div className="flex items-center gap-4 ml-auto">
          {Object.entries(LINE_COLORS).map(([name, color]) => (
            <div key={name} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-xs text-muted-foreground">{name}</span>
            </div>
          ))}
        </div>
      </div>

      <svg viewBox="0 0 1080 790" className="w-full" style={{ minHeight: 420 }}>
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <rect width="1080" height="790" fill="hsl(var(--background))" />

        {lineConfigs.map((lc) => (
          <g key={lc.id}>
            <path
              d={buildPathD(lc.stops)}
              fill="none"
              stroke={lc.color}
              strokeWidth={lc.width}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.25}
            />
            <path
              d={buildPathD(lc.stops)}
              fill="none"
              stroke={lc.color}
              strokeWidth={lc.width - 1}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.9}
            />
          </g>
        ))}

        {/* Station dots */}
        {allStationIds.map((id) => {
          const pos = stationPositions[id];
          const stop = martaStops.find((s) => s.id === id);
          const isHub = stop && stop.routes.length > 2;
          const isHovered = hoveredStation === id;
          const isSelected = selectedStation === id;
          const analytics = stationAnalyticsMap[id];
          const crowdFill =
            analytics?.crowdingLevel === 'high'
              ? '#EF4444'
              : analytics?.crowdingLevel === 'moderate'
              ? '#F59E0B'
              : '#22C55E';

          return (
            <g
              key={id}
              className="cursor-pointer"
              onClick={() => setSelectedStation(id)}
              onMouseEnter={() => setHoveredStation(id)}
              onMouseLeave={() => setHoveredStation(null)}
            >
              {(isHovered || isSelected) && (
                <circle cx={pos.x} cy={pos.y} r={isHub ? 14 : 11} fill={crowdFill} opacity={0.2} />
              )}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={isHub ? 7 : 5}
                fill="hsl(var(--background))"
                stroke={isHovered || isSelected ? crowdFill : isHub ? '#1E88E5' : 'hsl(var(--muted-foreground))'}
                strokeWidth={isHub ? 2.5 : 1.5}
                style={{ transition: 'stroke 0.15s ease' }}
              />
              {isHub && <circle cx={pos.x} cy={pos.y} r={3} fill="#1E88E5" />}
            </g>
          );
        })}

        {/* Labels rendered after dots for proper layering */}
        {allStationIds.map((id) => {
          const pos = stationPositions[id];
          const stop = martaStops.find((s) => s.id === id);
          const isHub = stop && stop.routes.length > 2;
          const isHovered = hoveredStation === id;
          const analytics = stationAnalyticsMap[id];
          const label = getLabelPlacement(id, pos);

          return (
            <text
              key={`label-${id}`}
              x={label.x}
              y={label.y}
              fontSize={isHovered ? 11 : 9}
              fill="hsl(var(--foreground))"
              textAnchor={label.anchor}
              fontWeight={isHovered || isHub ? 600 : 400}
              opacity={isHovered ? 1 : 0.7}
              className="select-none pointer-events-none"
              style={{
                fontFamily: 'Inter, system-ui, sans-serif',
                transition: 'font-size 0.15s ease, opacity 0.15s ease',
              }}
            >
              {analytics?.name || id}
            </text>
          );
        })}

        {trains.map((t, i) => {
          const pos = getTrainPos(t);
          if (!pos) return null;
          return (
            <g key={i} filter="url(#glow)">
              <circle cx={pos.x} cy={pos.y} r={6} fill={LINE_COLORS[t.line]} opacity={0.9} />
              <circle cx={pos.x} cy={pos.y} r={3} fill="white" />
            </g>
          );
        })}
      </svg>

      <AnimatePresence>
        {selectedStation && (
          <StationPopup stationId={selectedStation} onClose={() => setSelectedStation(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}
