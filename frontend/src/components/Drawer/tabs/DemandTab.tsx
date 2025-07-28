import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, BarChart3, MapPin, Clock } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

// Demo data for demand visualization
const hourlyDemand = [
  { hour: '6 AM', demand: 12, predicted: 15 },
  { hour: '7 AM', demand: 28, predicted: 32 },
  { hour: '8 AM', demand: 45, predicted: 48 },
  { hour: '9 AM', demand: 32, predicted: 35 },
  { hour: '10 AM', demand: 22, predicted: 25 },
  { hour: '11 AM', demand: 18, predicted: 20 },
  { hour: '12 PM', demand: 35, predicted: 38 },
  { hour: '1 PM', demand: 42, predicted: 45 },
];

const topStops = [
  { name: 'Five Points', current: 45, predicted: 52, change: '+15%' },
  { name: 'Midtown', current: 41, predicted: 47, change: '+12%' },
  { name: 'Peachtree Center', current: 32, predicted: 38, change: '+18%' },
  { name: 'Buckhead', current: 28, predicted: 33, change: '+17%' },
];

export const DemandTab: React.FC = () => {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-marta-blue" />
          Demand Forecasting
        </h2>
        <div className="text-sm text-muted-foreground flex items-center gap-1">
          <Clock className="w-4 h-4" />
          Live updates every 30s
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-red">847</div>
          <div className="text-sm text-muted-foreground">Current Passengers</div>
          <div className="text-xs text-marta-green mt-1">↑ 12% vs last hour</div>
        </motion.div>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-orange">963</div>
          <div className="text-sm text-muted-foreground">Next Hour Prediction</div>
          <div className="text-xs text-marta-green mt-1">93% confidence</div>
        </motion.div>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-blue">6.2m</div>
          <div className="text-sm text-muted-foreground">Avg Wait Time</div>
          <div className="text-xs text-marta-red mt-1">↓ 18% improvement</div>
        </motion.div>
      </div>

      {/* Demand Trend Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="transit-card p-4"
      >
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4" />
          Hourly Demand Trend
        </h3>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={hourlyDemand}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="hour" 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
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
                stroke="hsl(var(--marta-blue))" 
                strokeWidth={2}
                name="Current"
              />
              <Line 
                type="monotone" 
                dataKey="predicted" 
                stroke="hsl(var(--marta-orange))" 
                strokeWidth={2}
                strokeDasharray="5 5"
                name="Predicted"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-6 mt-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-marta-blue"></div>
            <span>Current Demand</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-marta-orange border-dashed"></div>
            <span>Predicted Demand</span>
          </div>
        </div>
      </motion.div>

      {/* Top Demand Stops */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="transit-card p-4"
      >
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <MapPin className="w-4 h-4" />
          High Demand Stops
        </h3>
        <div className="space-y-3">
          {topStops.map((stop, index) => (
            <motion.div
              key={stop.name}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <div className="w-2 h-8 bg-gradient-demand rounded-full"></div>
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
        className="grid grid-cols-2 gap-4"
      >
        <div className="transit-card p-4 text-center">
          <div className="text-lg font-bold text-marta-green">94.2%</div>
          <div className="text-sm text-muted-foreground">Model Accuracy</div>
        </div>
        <div className="transit-card p-4 text-center">
          <div className="text-lg font-bold text-marta-blue">±3.1</div>
          <div className="text-sm text-muted-foreground">Avg Error Rate</div>
        </div>
      </motion.div>
    </div>
  );
};