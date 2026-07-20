import React from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, DollarSign, Clock, Users, Target } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const performanceData = [
  { month: 'Jan', efficiency: 85, satisfaction: 78, cost: 95000 },
  { month: 'Feb', efficiency: 87, satisfaction: 81, cost: 92000 },
  { month: 'Mar', efficiency: 89, satisfaction: 85, cost: 88000 },
  { month: 'Apr', efficiency: 91, satisfaction: 87, cost: 85000 },
  { month: 'May', efficiency: 94, satisfaction: 92, cost: 81000 },
  { month: 'Jun', efficiency: 94, satisfaction: 94, cost: 79000 },
];

const routeDistribution = [
  { name: 'Red Line', value: 35, color: 'hsl(var(--marta-red))' },
  { name: 'Blue Line', value: 28, color: 'hsl(var(--marta-blue))' },
  { name: 'Gold Line', value: 22, color: 'hsl(var(--marta-orange))' },
  { name: 'Green Line', value: 15, color: 'hsl(var(--marta-green))' },
];

export const AnalyticsTab: React.FC = () => {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-marta-blue" />
          Performance Analytics
        </h2>
        <div className="text-sm text-muted-foreground">
          Last 6 months
        </div>
      </div>

      {/* KPI Dashboard */}
      <div className="grid grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="transit-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-marta-green" />
            <span className="text-sm font-medium">System Efficiency</span>
          </div>
          <div className="text-2xl font-bold text-marta-green">94%</div>
          <div className="text-xs text-muted-foreground">↑ 12% from last month</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="transit-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-marta-blue" />
            <span className="text-sm font-medium">Passenger Satisfaction</span>
          </div>
          <div className="text-2xl font-bold text-marta-blue">94%</div>
          <div className="text-xs text-muted-foreground">↑ 8% from last month</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="transit-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-4 h-4 text-marta-orange" />
            <span className="text-sm font-medium">Monthly Cost</span>
          </div>
          <div className="text-2xl font-bold text-marta-orange">$79K</div>
          <div className="text-xs text-muted-foreground">↓ 17% from last month</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="transit-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-marta-red" />
            <span className="text-sm font-medium">Avg Wait Time</span>
          </div>
          <div className="text-2xl font-bold text-marta-red">5.8m</div>
          <div className="text-xs text-muted-foreground">↓ 22% from last month</div>
        </motion.div>
      </div>

      {/* Performance Trends */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="transit-card p-4"
      >
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          6-Month Performance Trends
        </h3>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="month" 
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
                dataKey="efficiency" 
                stroke="hsl(var(--marta-green))" 
                strokeWidth={2}
                name="Efficiency %"
              />
              <Line 
                type="monotone" 
                dataKey="satisfaction" 
                stroke="hsl(var(--marta-blue))" 
                strokeWidth={2}
                name="Satisfaction %"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-6 mt-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-marta-green"></div>
            <span>System Efficiency</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-marta-blue"></div>
            <span>Passenger Satisfaction</span>
          </div>
        </div>
      </motion.div>

      {/* Route Usage Distribution */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="transit-card p-4"
      >
        <h3 className="font-semibold mb-4">Route Usage Distribution</h3>
        <div className="flex items-center justify-between">
          <div className="h-32 w-32">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={routeDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={20}
                  outerRadius={40}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {routeDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 ml-6 space-y-2">
            {routeDistribution.map((route, index) => (
              <motion.div
                key={route.name}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 + index * 0.1 }}
                className="flex items-center justify-between text-sm"
              >
                <div className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: route.color }}
                  />
                  <span>{route.name}</span>
                </div>
                <span className="font-medium">{route.value}%</span>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Cost Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="grid grid-cols-2 gap-4"
      >
        <div className="transit-card p-4">
          <h4 className="font-semibold mb-2 text-sm">Cost Reduction</h4>
          <div className="text-xl font-bold text-marta-green">$16K</div>
          <div className="text-xs text-muted-foreground">Monthly savings from optimization</div>
        </div>
        
        <div className="transit-card p-4">
          <h4 className="font-semibold mb-2 text-sm">ROI</h4>
          <div className="text-xl font-bold text-marta-blue">342%</div>
          <div className="text-xs text-muted-foreground">Return on ML investment</div>
        </div>
      </motion.div>

      {/* Insights */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className="transit-card p-4"
      >
        <h3 className="font-semibold mb-3">Key Insights</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 bg-marta-green rounded-full mt-1.5"></div>
            <span>Red Line optimization reduced wait times by 27% during peak hours</span>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 bg-marta-blue rounded-full mt-1.5"></div>
            <span>Demand forecasting accuracy improved to 94.2% with latest model</span>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 bg-marta-orange rounded-full mt-1.5"></div>
            <span>Cost savings of $16K/month achieved through route optimization</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
};