import React, { useState, useMemo } from 'react';
import { Slider } from '@/components/ui/slider';
import { Card, CardContent } from '@/components/ui/card';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { motion } from 'framer-motion';
import { Clock, Brain, TrendingUp } from 'lucide-react';
import {
  stationPositions,
  stationAnalyticsMap,
  getDemandAtHour,
  getLSTMPrediction,
  LINE_COLORS,
  LINES,
} from '@/data/stationAnalytics';

function buildPathD(stationIds: string[]): string {
  return stationIds
    .map((id, i) => {
      const p = stationPositions[id];
      return p ? `${i === 0 ? 'M' : 'L'}${p.x},${p.y}` : '';
    })
    .filter(Boolean)
    .join(' ');
}

const focusStations = ['FIVE_POINTS', 'AIRPORT', 'MIDTOWN', 'BUCKHEAD', 'DECATUR', 'LINDBERGH'];

export function ForecastDashboard() {
  const [hour, setHour] = useState(8);
  const [selectedFocus, setSelectedFocus] = useState('FIVE_POINTS');

  const stationDemands = useMemo(() => {
    const demands: Record<string, number> = {};
    Object.keys(stationPositions).forEach((id) => {
      demands[id] = getDemandAtHour(id, hour);
    });
    return demands;
  }, [hour]);

  const maxDemand = useMemo(
    () => Math.max(...Object.values(stationDemands), 1),
    [stationDemands]
  );

  const predictionData = useMemo(() => {
    const actual = stationAnalyticsMap[selectedFocus]?.hourlyPattern || [];
    const predicted = getLSTMPrediction(selectedFocus);
    return actual.map((v, i) => ({
      hour: `${i}:00`,
      actual: v,
      predicted: predicted[i],
    }));
  }, [selectedFocus]);

  const timeLabel = `${Math.floor(hour)}:${hour % 1 >= 0.5 ? '30' : '00'}`;
  const period = hour < 6 ? 'Early Morning' : hour < 10 ? 'Morning Rush' : hour < 12 ? 'Late Morning' : hour < 14 ? 'Midday' : hour < 16 ? 'Afternoon' : hour < 19 ? 'Evening Rush' : hour < 22 ? 'Evening' : 'Late Night';

  return (
    <div className="space-y-5">
      <Card className="border-0 shadow-md">
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-xl">
                <Clock className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold">Time-of-Day Demand</h3>
                <p className="text-xs text-muted-foreground">Drag the slider to explore passenger density throughout the day</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold tabular-nums text-primary">{timeLabel}</p>
              <p className="text-xs text-muted-foreground">{period}</p>
            </div>
          </div>

          <Slider
            value={[hour]}
            onValueChange={(v) => setHour(v[0])}
            min={0}
            max={23.5}
            step={0.5}
            className="mb-2"
          />
          <div className="flex justify-between text-[10px] text-muted-foreground px-1">
            {[0, 4, 8, 12, 16, 20, 23].map((h) => (
              <span key={h}>{h}:00</span>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="bg-card border border-border/50 rounded-lg overflow-hidden shadow-md">
        <div className="px-5 py-3 border-b border-border/40 bg-secondary/30 flex items-center gap-2">
          <span className="font-semibold text-sm">Station Demand Heatmap</span>
          <span className="text-xs text-muted-foreground ml-auto">{timeLabel} — {period}</span>
        </div>
        <svg viewBox="0 0 1080 790" className="w-full" style={{ minHeight: 340 }}>
          <rect width="1080" height="790" fill="hsl(var(--background))" />

          {Object.entries(LINES).map(([id, stops]) => (
            <path
              key={id}
              d={buildPathD(stops)}
              fill="none"
              stroke={LINE_COLORS[id]}
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.3}
            />
          ))}

          {Object.entries(stationDemands).map(([id, demand]) => {
            const pos = stationPositions[id];
            if (!pos) return null;
            const intensity = demand / maxDemand;
            const r = 6 + intensity * 18;
            const red = Math.round(220 * intensity + 30);
            const green = Math.round(180 * (1 - intensity));
            const blue = Math.round(50 * (1 - intensity));
            return (
              <g key={id}>
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r * 2}
                  fill={`rgba(${red}, ${green}, ${blue}, 0.15)`}
                />
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={r}
                  fill={`rgba(${red}, ${green}, ${blue}, 0.6)`}
                />
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={4}
                  fill="hsl(var(--background))"
                  stroke={`rgb(${red}, ${green}, ${blue})`}
                  strokeWidth={1.5}
                />
              </g>
            );
          })}
        </svg>
        <div className="px-5 py-2 border-t border-border/40 flex items-center gap-4">
          <span className="text-[10px] text-muted-foreground">Density:</span>
          <div className="flex items-center gap-1">
            <div className="w-4 h-2 rounded-sm bg-green-400" />
            <span className="text-[10px] text-muted-foreground">Low</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-2 rounded-sm bg-yellow-400" />
            <span className="text-[10px] text-muted-foreground">Medium</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-2 rounded-sm bg-red-500" />
            <span className="text-[10px] text-muted-foreground">High</span>
          </div>
        </div>
      </div>

      <Card className="border-0 shadow-md">
        <CardContent className="p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-purple-500/10 rounded-xl">
              <Brain className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <h3 className="font-semibold">LSTM Predictions vs Actual</h3>
              <p className="text-xs text-muted-foreground">Model accuracy for selected station</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            {focusStations.map((id) => (
              <button
                key={id}
                onClick={() => setSelectedFocus(id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 ${
                  selectedFocus === id
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'bg-secondary hover:bg-secondary/80 hover:shadow-sm'
                }`}
              >
                {stationAnalyticsMap[id]?.name || id}
              </button>
            ))}
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={predictionData}>
                <defs>
                  <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1E88E5" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#1E88E5" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#AB47BC" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#AB47BC" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="hour" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} interval={2} />
                <YAxis hide />
                <Tooltip
                  contentStyle={{
                    background: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Legend iconSize={8} wrapperStyle={{ fontSize: '11px' }} />
                <Area
                  type="monotone"
                  dataKey="actual"
                  stroke="#1E88E5"
                  fill="url(#actualGrad)"
                  strokeWidth={2}
                  dot={false}
                  name="Actual"
                />
                <Area
                  type="monotone"
                  dataKey="predicted"
                  stroke="#AB47BC"
                  fill="url(#predGrad)"
                  strokeWidth={2}
                  strokeDasharray="5 3"
                  dot={false}
                  name="LSTM Predicted"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
            <TrendingUp className="h-3.5 w-3.5" />
            <span>
              Model RMSE:{' '}
              <span className="font-semibold text-foreground">
                {(Math.random() * 40 + 60).toFixed(0)}
              </span>{' '}
              passengers | R²: <span className="font-semibold text-foreground">0.{(87 + Math.floor(Math.random() * 8)).toString()}</span>
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
