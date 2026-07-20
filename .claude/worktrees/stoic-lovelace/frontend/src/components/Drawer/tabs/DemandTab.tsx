import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, BarChart3, MapPin, Clock, RefreshCw } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

// Supabase config - anon key is safe in frontend bundles
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://vglychbweuowsovboxyf.supabase.co';
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY';

interface HourlyPoint {
  hour: string;
  demand: number;
  predicted: number;
}

interface StopDemand {
  name: string;
  current: number;
  predicted: number;
  change: string;
}

interface ForecastMetrics {
  currentPassengers: number;
  nextHourPrediction: number;
  avgWaitTime: string;
  modelAccuracy: string;
  avgError: string;
  isLive: boolean;
}

// Static demo data used as fallback when API is unavailable
const DEMO_HOURLY: HourlyPoint[] = [
  { hour: '6 AM', demand: 12, predicted: 15 },
  { hour: '7 AM', demand: 28, predicted: 32 },
  { hour: '8 AM', demand: 45, predicted: 48 },
  { hour: '9 AM', demand: 32, predicted: 35 },
  { hour: '10 AM', demand: 22, predicted: 25 },
  { hour: '11 AM', demand: 18, predicted: 20 },
  { hour: '12 PM', demand: 35, predicted: 38 },
  { hour: '1 PM', demand: 42, predicted: 45 },
];

const DEMO_STOPS: StopDemand[] = [
  { name: 'Five Points', current: 45, predicted: 52, change: '+15%' },
  { name: 'Midtown', current: 41, predicted: 47, change: '+12%' },
  { name: 'Peachtree Center', current: 32, predicted: 38, change: '+18%' },
  { name: 'Buckhead', current: 28, predicted: 33, change: '+17%' },
];

const DEMO_METRICS: ForecastMetrics = {
  currentPassengers: 847,
  nextHourPrediction: 963,
  avgWaitTime: '6.2m',
  modelAccuracy: '94.2%',
  avgError: '±3.1',
  isLive: false,
};

export const DemandTab: React.FC = () => {
  const [hourlyData, setHourlyData] = useState<HourlyPoint[]>(DEMO_HOURLY);
  const [topStops, setTopStops] = useState<StopDemand[]>(DEMO_STOPS);
  const [metrics, setMetrics] = useState<ForecastMetrics>(DEMO_METRICS);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);

  const fetchDemandData = useCallback(async () => {
    try {
      setLoading(true);

      const response = await fetch(`${SUPABASE_URL}/functions/v1/demand-forecast`, {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) throw new Error('Forecast API unavailable');

      const data = await response.json();

      // Map API response to chart format
      if (data.hourly && Array.isArray(data.hourly)) {
        const mapped: HourlyPoint[] = data.hourly.map((point: Record<string, unknown>) => ({
          hour: String(point.hour ?? point.time ?? ''),
          demand: Number(point.demand ?? point.actual ?? 0),
          predicted: Number(point.predicted ?? point.forecast ?? 0),
        }));
        if (mapped.length > 0) setHourlyData(mapped);
      }

      if (data.top_stops && Array.isArray(data.top_stops)) {
        const mapped: StopDemand[] = data.top_stops.map((s: Record<string, unknown>) => {
          const current = Number(s.current ?? s.current_passengers ?? 0);
          const predicted = Number(s.predicted ?? s.predicted_demand ?? 0);
          const pct = current > 0 ? Math.round(((predicted - current) / current) * 100) : 0;
          return {
            name: String(s.name ?? s.station ?? ''),
            current,
            predicted,
            change: `${pct >= 0 ? '+' : ''}${pct}%`,
          };
        });
        if (mapped.length > 0) setTopStops(mapped);
      }

      setMetrics({
        currentPassengers: Number(data.current_passengers ?? DEMO_METRICS.currentPassengers),
        nextHourPrediction: Number(data.next_hour_prediction ?? DEMO_METRICS.nextHourPrediction),
        avgWaitTime: String(data.avg_wait_time ?? DEMO_METRICS.avgWaitTime),
        modelAccuracy: String(data.model_accuracy ?? DEMO_METRICS.modelAccuracy),
        avgError: String(data.avg_error ?? DEMO_METRICS.avgError),
        isLive: true,
      });

      setIsLive(true);
    } catch {
      // Keep demo data on failure — chart still shows something meaningful
      setIsLive(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDemandData();
    const interval = setInterval(fetchDemandData, 30000);
    return () => clearInterval(interval);
  }, [fetchDemandData]);

  return (
    <div id="demand-tab-container" className="p-6 space-y-6">
      <div id="demand-tab-header" className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-marta-blue" />
          Demand Forecasting
        </h2>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchDemandData}
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh forecast data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <div className="text-sm text-muted-foreground flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {isLive ? (
              <span className="text-marta-green">Live — updates every 30s</span>
            ) : (
              <span>Demo data</span>
            )}
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div id="demand-metrics-grid" className="grid grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-red">
            {metrics.currentPassengers.toLocaleString()}
          </div>
          <div className="text-sm text-muted-foreground">Current Passengers</div>
          <div className="text-xs text-marta-green mt-1">
            {isLive ? 'live data' : 'demo'}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-orange">
            {metrics.nextHourPrediction.toLocaleString()}
          </div>
          <div className="text-sm text-muted-foreground">Next Hour Prediction</div>
          <div className="text-xs text-marta-green mt-1">{metrics.modelAccuracy} confidence</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-blue">{metrics.avgWaitTime}</div>
          <div className="text-sm text-muted-foreground">Avg Wait Time</div>
          <div className="text-xs text-marta-red mt-1">avg error {metrics.avgError}</div>
        </motion.div>
      </div>

      {/* Demand Trend Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        id="demand-chart-card"
        className="transit-card p-4"
      >
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4" />
          Hourly Demand Trend
          {!isLive && (
            <span className="text-xs text-muted-foreground font-normal ml-auto">demo data</span>
          )}
        </h3>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="hour" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
              <Line
                type="monotone"
                dataKey="demand"
                stroke="#0ea5e9"
                strokeWidth={2}
                name="Actual"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="predicted"
                stroke="#f97316"
                strokeWidth={2}
                strokeDasharray="5 5"
                name="Predicted"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div id="demand-chart-legend" className="flex justify-center gap-6 mt-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-sky-500"></div>
            <span>Actual Demand</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-orange-500 border-dashed"></div>
            <span>Predicted</span>
          </div>
        </div>
      </motion.div>

      {/* Top Demand Stops */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        id="demand-top-stops-card"
        className="transit-card p-4"
      >
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <MapPin className="w-4 h-4" />
          High Demand Stops
        </h3>
        <div id="demand-stops-list" className="space-y-3">
          {topStops.map((stop, index) => (
            <motion.div
              key={stop.name}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <div className="w-2 h-8 bg-gradient-demand rounded-full flex-shrink-0"></div>
                <div>
                  <div className="font-medium text-sm">{stop.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {stop.current} current → {stop.predicted} predicted
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-marta-green">{stop.change}</div>
                <div className="text-xs text-muted-foreground">next hour</div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Model Performance */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        id="demand-model-performance"
        className="grid grid-cols-2 gap-4"
      >
        <div className="transit-card p-4 text-center">
          <div className="text-lg font-bold text-marta-green">{metrics.modelAccuracy}</div>
          <div className="text-sm text-muted-foreground">Model Accuracy</div>
        </div>
        <div className="transit-card p-4 text-center">
          <div className="text-lg font-bold text-marta-blue">{metrics.avgError}</div>
          <div className="text-sm text-muted-foreground">Avg Error Rate</div>
        </div>
      </motion.div>
    </div>
  );
};
