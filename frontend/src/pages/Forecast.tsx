import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { format, subDays, addDays } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Download, CalendarIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { martaStops } from '@/data/martaData';
import { exportToCSV, generateExportFilename } from '@/lib/export';
import { cn } from '@/lib/utils';
import { useCountUp } from '@/hooks/useCountUp';

// Generate sample forecast data
function generateForecastData(stationId: string, days: number) {
  const data = [];
  const baseDate = new Date();
  const baseRidership = Math.floor(Math.random() * 2000) + 1000;

  for (let i = -days; i <= 7; i++) {
    const date = i < 0 ? subDays(baseDate, Math.abs(i)) : addDays(baseDate, i);
    const dayOfWeek = date.getDay();
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
    const multiplier = isWeekend ? 0.6 : 1;
    const hourlyVariation = Math.sin((i % 24) * Math.PI / 12) * 200;

    const actual = i <= 0 ? Math.floor((baseRidership + hourlyVariation) * multiplier + Math.random() * 300) : undefined;
    const predicted = Math.floor((baseRidership + hourlyVariation) * multiplier + Math.random() * 100);
    const lowerBound = Math.floor(predicted * 0.85);
    const upperBound = Math.floor(predicted * 1.15);

    data.push({
      date: format(date, 'MMM dd'),
      fullDate: date.toISOString(),
      actual,
      predicted,
      lowerBound,
      upperBound,
      isPrediction: i > 0,
    });
  }

  return data;
}

function AnimatedMetricCard({
  label,
  rawValue,
  suffix,
  decimals,
  sublabel,
  trend,
  className,
}: {
  label: string;
  rawValue: number;
  suffix?: string;
  decimals?: number;
  sublabel?: string;
  trend?: 'up' | 'down' | 'stable';
  className?: string;
}) {
  const animated = useCountUp(rawValue, 1200, decimals);
  return (
    <div className={className}>
      <Card className="hover-lift h-full">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold mt-1 tabular-nums">
            {animated}{suffix || ''}
          </p>
          {sublabel && (
            <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>
          )}
          {trend && (
            <div className="flex items-center gap-1 mt-1">
              {trend === 'up' && (
                <>
                  <TrendingUp className="h-3 w-3 text-green-600" />
                  <span className="text-xs text-green-600">Trending up</span>
                </>
              )}
              {trend === 'down' && (
                <>
                  <TrendingDown className="h-3 w-3 text-red-600" />
                  <span className="text-xs text-red-600">Trending down</span>
                </>
              )}
              {trend === 'stable' && (
                <>
                  <Minus className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Stable</span>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ForecastPage() {
  const [selectedStation, setSelectedStation] = useState(martaStops[0].id);
  const [dateRange, setDateRange] = useState<{ start: Date; end: Date }>({
    start: subDays(new Date(), 14),
    end: addDays(new Date(), 7),
  });

  const forecastData = useMemo(
    () => generateForecastData(selectedStation, 14),
    [selectedStation]
  );

  const stationName = martaStops.find((s) => s.id === selectedStation)?.name || '';

  // Calculate accuracy metrics
  const pastData = forecastData.filter((d) => d.actual !== undefined);
  const mape = useMemo(() => {
    if (pastData.length === 0) return 0;
    const errors = pastData.map((d) =>
      Math.abs((d.actual! - d.predicted) / d.actual!) * 100
    );
    return errors.reduce((a, b) => a + b, 0) / errors.length;
  }, [pastData]);

  const trend = useMemo(() => {
    if (pastData.length < 2) return 'stable' as const;
    const recent = pastData.slice(-5);
    const avg = recent.reduce((a, b) => a + (b.actual || 0), 0) / recent.length;
    const older = pastData.slice(-10, -5);
    const olderAvg = older.reduce((a, b) => a + (b.actual || 0), 0) / older.length;
    if (avg > olderAvg * 1.05) return 'up' as const;
    if (avg < olderAvg * 0.95) return 'down' as const;
    return 'stable' as const;
  }, [pastData]);

  const todayForecast = forecastData.find((d) => d.isPrediction)?.predicted || 0;
  const weekAvg = Math.floor(
    forecastData.filter((d) => d.isPrediction).reduce((a, b) => a + b.predicted, 0) / 7
  );
  const accuracy = 100 - mape;

  const handleExport = () => {
    exportToCSV(
      forecastData.map((d) => ({
        date: d.fullDate,
        actual: d.actual || '',
        predicted: d.predicted,
        lower_bound: d.lowerBound,
        upper_bound: d.upperBound,
      })),
      generateExportFilename(`forecast_${stationName.replace(/\s+/g, '_')}`)
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-semibold">Demand Forecast</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Predicted ridership based on historical patterns and ML models
          </p>
        </div>
        <Button variant="outline" onClick={handleExport} className="gap-2">
          <Download className="h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4 animate-slide-in-left">
        <div className="w-64">
          <Select value={selectedStation} onValueChange={setSelectedStation}>
            <SelectTrigger>
              <SelectValue placeholder="Select station" />
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

        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" className="gap-2">
              <CalendarIcon className="h-4 w-4" />
              {format(dateRange.start, 'MMM dd')} - {format(dateRange.end, 'MMM dd')}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="range"
              selected={{ from: dateRange.start, to: dateRange.end }}
              onSelect={(range) => {
                if (range?.from && range?.to) {
                  setDateRange({ start: range.from, end: range.to });
                }
              }}
              numberOfMonths={2}
            />
          </PopoverContent>
        </Popover>
      </div>

      {/* Metrics cards */}
      <div className="grid grid-cols-4 gap-4">
        <AnimatedMetricCard
          className="animate-fade-in-up stagger-1"
          label="Today's Forecast"
          rawValue={todayForecast}
          sublabel="passengers"
        />
        <AnimatedMetricCard
          className="animate-fade-in-up stagger-2"
          label="7-Day Avg Forecast"
          rawValue={weekAvg}
          trend={trend}
        />
        <AnimatedMetricCard
          className="animate-fade-in-up stagger-3"
          label="Model Accuracy"
          rawValue={accuracy}
          suffix="%"
          decimals={1}
          sublabel={`MAPE: ${mape.toFixed(1)}%`}
        />
        <AnimatedMetricCard
          className="animate-fade-in-up stagger-4"
          label="Peak Hour"
          rawValue={530}
          suffix=" PM"
          decimals={0}
          sublabel="Expected high demand"
        />
      </div>

      {/* Main chart */}
      <div className="animate-fade-in-scale stagger-2">
        <Card className="hover-lift">
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-medium">
              Ridership Forecast - {stationName}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={forecastData}>
                  <defs>
                    <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={{ stroke: '#e5e7eb' }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={{ stroke: '#e5e7eb' }}
                    tickFormatter={(value) => `${(value / 1000).toFixed(1)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                    }}
                    formatter={(value: number) => [value.toLocaleString(), '']}
                  />
                  <Legend />
                  {/* Confidence interval */}
                  <Area
                    type="monotone"
                    dataKey="upperBound"
                    stroke="transparent"
                    fill="#3b82f6"
                    fillOpacity={0.1}
                    name="Upper Bound"
                    animationDuration={1200}
                    animationEasing="ease-out"
                  />
                  <Area
                    type="monotone"
                    dataKey="lowerBound"
                    stroke="transparent"
                    fill="white"
                    name="Lower Bound"
                    animationDuration={1200}
                    animationEasing="ease-out"
                  />
                  {/* Actual values */}
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Actual"
                    connectNulls={false}
                    animationDuration={1200}
                    animationEasing="ease-out"
                  />
                  {/* Predicted values */}
                  <Line
                    type="monotone"
                    dataKey="predicted"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ r: 3 }}
                    name="Predicted"
                    animationDuration={1200}
                    animationEasing="ease-out"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Hourly breakdown */}
      <div className="animate-fade-in-scale stagger-3">
        <Card className="hover-lift">
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-medium">
              Hourly Demand Pattern (Today)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={Array.from({ length: 24 }, (_, i) => ({
                    hour: `${i}:00`,
                    demand: Math.floor(
                      Math.sin((i - 6) * Math.PI / 12) * 500 +
                      (i >= 7 && i <= 9 ? 800 : 0) +
                      (i >= 16 && i <= 18 ? 900 : 0) +
                      Math.random() * 100 +
                      300
                    ),
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="hour"
                    tick={{ fontSize: 10 }}
                    tickLine={false}
                    interval={2}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="demand"
                    stroke="#3b82f6"
                    fill="url(#colorPredicted)"
                    name="Passengers"
                    animationDuration={1200}
                    animationEasing="ease-out"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
