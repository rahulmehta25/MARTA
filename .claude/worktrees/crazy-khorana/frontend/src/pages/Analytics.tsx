import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrivalBoard } from '@/components/RealTime/ArrivalBoard';
import { TripPlanner } from '@/components/TripPlanning/TripPlanner';
import { PerformanceDashboard } from '@/components/Analytics/PerformanceDashboard';
import {
  Train,
  Navigation,
  BarChart3,
  Activity,
  Map,
  Clock,
  ArrowLeft
} from 'lucide-react';
import { motion } from 'framer-motion';

const Analytics: React.FC = () => {
  const [activeTab, setActiveTab] = useState('realtime');

  // Popular stations for quick access
  const popularStations = [
    'FIVE POINTS STATION',
    'AIRPORT STATION',
    'LINDBERGH STATION',
    'PEACHTREE CENTER STATION',
    'NORTH SPRINGS STATION'
  ];

  return (
    <div id="analytics-page" className="min-h-screen bg-background">
      {/* Header */}
      <header id="analytics-header" className="bg-gradient-to-r from-primary/10 via-primary/5 to-background border-b" role="banner">
        <div className="container mx-auto px-4 py-4 sm:py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <div className="flex items-center gap-3">
                <a href="/" className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Back to map">
                  <ArrowLeft className="h-5 w-5" aria-hidden="true" />
                </a>
                <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
                  MARTA Analytics
                </h1>
              </div>
              <p className="text-sm text-muted-foreground mt-1 ml-8">
                Real-time tracking, ML predictions, and performance insights
              </p>
            </div>
            <div className="flex items-center gap-2 ml-8 sm:ml-0">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-lg" role="status">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" aria-hidden="true" />
                <span className="text-sm font-medium text-green-600">Live Data</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/10 border border-purple-500/20 rounded-lg" role="status">
                <Activity className="h-4 w-4 text-purple-600" aria-hidden="true" />
                <span className="text-sm font-medium text-purple-600">ML Active</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main id="analytics-content" className="container mx-auto px-4 py-6 sm:py-8" role="main">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full max-w-2xl mx-auto grid-cols-3">
            <TabsTrigger value="realtime" className="flex items-center gap-2">
              <Train className="h-4 w-4" />
              <span className="hidden sm:inline">Real-Time</span>
              <span className="sm:hidden">Live</span>
            </TabsTrigger>
            <TabsTrigger value="planning" className="flex items-center gap-2">
              <Navigation className="h-4 w-4" />
              <span className="hidden sm:inline">Trip Planner</span>
              <span className="sm:hidden">Plan</span>
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Performance</span>
              <span className="sm:hidden">Stats</span>
            </TabsTrigger>
          </TabsList>

          {/* Real-Time Arrivals Tab */}
          <TabsContent value="realtime" className="space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              {/* Quick Station Selection */}
              <div id="popular-stations" className="mb-6">
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Map className="h-5 w-5" aria-hidden="true" />
                  Popular Stations
                </h2>
                <div className="flex flex-wrap gap-2" role="group" aria-label="Quick station selection">
                  {popularStations.map((station) => (
                    <button
                      key={station}
                      className="px-4 py-2 text-sm bg-secondary hover:bg-secondary/80 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 touch-target"
                      onClick={() => {
                        console.log('Selected station:', station);
                      }}
                      aria-label={`View arrivals at ${station.replace(' STATION', '')}`}
                    >
                      {station.replace(' STATION', '')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Arrival Boards Grid */}
              <div className="grid gap-6 lg:grid-cols-2">
                <ArrivalBoard stationId="FIVE POINTS STATION" limit={8} />
                <ArrivalBoard stationId="AIRPORT STATION" limit={8} />
              </div>

              {/* System Status */}
              <div className="mt-6 p-4 bg-secondary/30 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="h-5 w-5 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      Updates every 30 seconds • Predictions powered by ML with 77% confidence
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          </TabsContent>

          {/* Trip Planning Tab */}
          <TabsContent value="planning" className="space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <TripPlanner />
              
              {/* Additional Info */}
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                  <h3 className="font-medium text-blue-600 mb-1">Smart Routing</h3>
                  <p className="text-sm text-muted-foreground">
                    AI-optimized routes considering real-time delays and crowding
                  </p>
                </div>
                <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
                  <h3 className="font-medium text-green-600 mb-1">Live Updates</h3>
                  <p className="text-sm text-muted-foreground">
                    Real-time arrival predictions with ML confidence scores
                  </p>
                </div>
                <div className="p-4 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                  <h3 className="font-medium text-purple-600 mb-1">Multi-Modal</h3>
                  <p className="text-sm text-muted-foreground">
                    Combines walking and train options for optimal routes
                  </p>
                </div>
              </div>
            </motion.div>
          </TabsContent>

          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <PerformanceDashboard />
              
              {/* Analytics Footer */}
              <div className="mt-6 p-4 bg-secondary/30 rounded-lg">
                <div className="text-sm text-muted-foreground">
                  <p>
                    Analytics powered by real-time data from {' '}
                    <span className="font-medium text-foreground">802+ arrivals</span>,
                    processed by ML models with {' '}
                    <span className="font-medium text-foreground">77% confidence</span>.
                    Performance metrics calculated for {' '}
                    <span className="font-medium text-foreground">55 station/line combinations</span>.
                  </p>
                </div>
              </div>
            </motion.div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default Analytics;