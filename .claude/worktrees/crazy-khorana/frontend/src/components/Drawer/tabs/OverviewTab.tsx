import React from 'react';
import { useAppStore } from '@/store';
import { MapPin, Route, TrendingUp, Users, Clock, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export const OverviewTab: React.FC = () => {
  const { selectedStop, selectedRoute, stops, isConnected, lastUpdate } = useAppStore();

  const stats = [
    { 
      label: 'Active Stops', 
      value: '38', 
      change: '+2', 
      trend: 'up',
      icon: <MapPin className="w-5 h-5 text-marta-blue" />
    },
    { 
      label: 'Routes Operating', 
      value: '4', 
      change: '100%', 
      trend: 'stable',
      icon: <Route className="w-5 h-5 text-marta-green" />
    },
    { 
      label: 'Total Passengers', 
      value: '1,247', 
      change: '+12%', 
      trend: 'up',
      icon: <Users className="w-5 h-5 text-marta-orange" />
    },
    { 
      label: 'Avg Wait Time', 
      value: '6.2m', 
      change: '-18%', 
      trend: 'down',
      icon: <Clock className="w-5 h-5 text-marta-red" />
    },
  ];

  const alerts = [
    { id: 1, type: 'high-demand', message: 'High demand detected at Five Points Station', time: '2 min ago' },
    { id: 2, type: 'optimization', message: 'Route optimization completed for Red Line', time: '5 min ago' },
    { id: 3, type: 'system', message: 'Real-time data sync successful', time: '8 min ago' },
  ];

  const getAlertColor = (type: string) => {
    switch (type) {
      case 'high-demand': return 'text-marta-red';
      case 'optimization': return 'text-marta-green';
      default: return 'text-marta-blue';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Connection Status */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">System Overview</h2>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-marta-green' : 'bg-marta-red'}`} />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="transit-card p-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              {stat.icon}
              <div className={`text-xs px-2 py-1 rounded-full ${
                stat.trend === 'up' ? 'bg-marta-green/10 text-marta-green' :
                stat.trend === 'down' ? 'bg-marta-red/10 text-marta-red' :
                'bg-marta-blue/10 text-marta-blue'
              }`}>
                {stat.change}
              </div>
            </div>
            <div>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Selected Stop/Route Info */}
      {(selectedStop || selectedRoute) && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="transit-card p-4"
        >
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            {selectedStop ? <MapPin className="w-4 h-4" /> : <Route className="w-4 h-4" />}
            {selectedStop ? 'Selected Stop' : 'Selected Route'}
          </h3>
          {selectedStop && (
            <div className="space-y-2">
              <div className="font-medium">{selectedStop.name}</div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Current: </span>
                  <span className="font-medium">{selectedStop.currentPassengers}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Predicted: </span>
                  <span className="font-medium">{selectedStop.predictedDemand}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Demand: </span>
                  <span className={`font-medium ${
                    selectedStop.demandLevel === 'high' ? 'text-marta-red' :
                    selectedStop.demandLevel === 'medium' ? 'text-marta-orange' :
                    'text-marta-green'
                  }`}>
                    {selectedStop.demandLevel}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Routes: </span>
                  <span className="font-medium">{selectedStop.routes.join(', ')}</span>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Recent Alerts */}
      <div className="space-y-3">
        <h3 className="font-semibold flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          Recent Activity
        </h3>
        <div className="space-y-2">
          {alerts.map((alert, index) => (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-start gap-3 p-3 bg-secondary/30 rounded-lg"
            >
              <div className={`w-2 h-2 rounded-full mt-2 ${getAlertColor(alert.type)}`} />
              <div className="flex-1 min-w-0">
                <div className="text-sm">{alert.message}</div>
                <div className="text-xs text-muted-foreground mt-1">{alert.time}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Last Update */}
      {lastUpdate && (
        <div className="text-center text-xs text-muted-foreground">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};