import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Play, BarChart3, Route, Clock, Users, Target } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const optimizationResults = [
  { route: 'Red Line', before: 8.5, after: 6.2, improvement: 27 },
  { route: 'Blue Line', before: 7.3, after: 5.8, improvement: 21 },
  { route: 'Gold Line', before: 9.1, after: 6.9, improvement: 24 },
  { route: 'Green Line', before: 6.8, after: 5.1, improvement: 25 },
];

export const OptimizationTab: React.FC = () => {
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationComplete, setOptimizationComplete] = useState(false);

  const handleOptimize = async () => {
    setIsOptimizing(true);
    // Simulate optimization process
    setTimeout(() => {
      setIsOptimizing(false);
      setOptimizationComplete(true);
    }, 3000);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Target className="w-5 h-5 text-marta-blue" />
          Route Optimization
        </h2>
        <Button
          onClick={handleOptimize}
          disabled={isOptimizing}
          className="bg-marta-blue hover:bg-marta-blue/90"
        >
          {isOptimizing ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
            />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {isOptimizing ? 'Optimizing...' : 'Run Optimization'}
        </Button>
      </div>

      {/* Optimization Parameters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="transit-card p-4"
      >
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Optimization Parameters
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground">Bus Capacity</label>
            <div className="mt-1 p-2 bg-secondary rounded border">40 passengers</div>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Max Wait Time</label>
            <div className="mt-1 p-2 bg-secondary rounded border">12 minutes</div>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Min Coverage</label>
            <div className="mt-1 p-2 bg-secondary rounded border">85%</div>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Target Routes</label>
            <div className="mt-1 p-2 bg-secondary rounded border">All Lines</div>
          </div>
        </div>
      </motion.div>

      {/* Current Status */}
      <div className="grid grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-orange">7.4m</div>
          <div className="text-sm text-muted-foreground">Current Avg Wait</div>
        </motion.div>
        
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-blue">89%</div>
          <div className="text-sm text-muted-foreground">Route Efficiency</div>
        </motion.div>
        
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="transit-card p-4 text-center"
        >
          <div className="text-2xl font-bold text-marta-green">92%</div>
          <div className="text-sm text-muted-foreground">Coverage Area</div>
        </motion.div>
      </div>

      {isOptimizing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="transit-card p-6 text-center"
        >
          <motion.div
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-16 h-16 mx-auto mb-4 bg-gradient-primary rounded-full flex items-center justify-center"
          >
            <Route className="w-8 h-8 text-white" />
          </motion.div>
          <div className="text-lg font-semibold">Optimizing Routes...</div>
          <div className="text-sm text-muted-foreground mt-2">
            Analyzing passenger flow patterns and adjusting schedules
          </div>
          <div className="w-full bg-secondary rounded-full h-2 mt-4">
            <motion.div
              className="bg-marta-blue h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: '100%' }}
              transition={{ duration: 3, ease: 'easeInOut' }}
            />
          </div>
        </motion.div>
      )}

      {optimizationComplete && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* Results Summary */}
          <div className="transit-card p-4 border-l-4 border-l-marta-green">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-marta-green rounded-full"></div>
              <span className="font-semibold text-marta-green">Optimization Complete</span>
            </div>
            <div className="text-sm text-muted-foreground">
              Route efficiency improved by 24% average across all lines
            </div>
          </div>

          {/* Impact Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <div className="transit-card p-4 text-center">
              <div className="text-2xl font-bold text-marta-green">5.8m</div>
              <div className="text-sm text-muted-foreground">New Avg Wait</div>
              <div className="text-xs text-marta-green">↓ 22% improvement</div>
            </div>
            <div className="transit-card p-4 text-center">
              <div className="text-2xl font-bold text-marta-blue">94%</div>
              <div className="text-sm text-muted-foreground">New Efficiency</div>
              <div className="text-xs text-marta-green">↑ 5% improvement</div>
            </div>
            <div className="transit-card p-4 text-center">
              <div className="text-2xl font-bold text-marta-orange">$12.3K</div>
              <div className="text-sm text-muted-foreground">Daily Savings</div>
              <div className="text-xs text-marta-green">Estimated</div>
            </div>
          </div>

          {/* Before/After Comparison */}
          <div className="transit-card p-4">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Wait Time Improvements
            </h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={optimizationResults}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis 
                    dataKey="route" 
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
                  <Bar dataKey="before" fill="hsl(var(--marta-red))" name="Before (min)" />
                  <Bar dataKey="after" fill="hsl(var(--marta-green))" name="After (min)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Detailed Results */}
          <div className="space-y-2">
            {optimizationResults.map((result, index) => (
              <motion.div
                key={result.route}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <Route className="w-4 h-4 text-marta-blue" />
                  <span className="font-medium">{result.route}</span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <div className="text-muted-foreground">
                    {result.before}m → {result.after}m
                  </div>
                  <div className="text-marta-green font-medium">
                    -{result.improvement}%
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
};