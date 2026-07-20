import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { motion } from 'framer-motion';
import { Map, BarChart3, Navigation, Sun, Moon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { MartaRailMap } from '@/components/InteractiveMap/MartaRailMap';
import { ForecastDashboard } from '@/components/DemandForecast/ForecastDashboard';
import { RouteOptimizerPanel } from '@/components/RouteOptimizer/RouteOptimizer';
import { HealthMetrics } from '@/components/SystemHealth/HealthMetrics';

function useTheme() {
  const [isDark, setIsDark] = useState(() => {
    return document.documentElement.classList.contains('dark');
  });

  const toggle = () => {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('marta-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('marta-theme', 'light');
    }
  };

  return { isDark, toggle };
}

const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('map');
  const { isDark, toggle } = useTheme();

  return (
    <div className="min-h-screen bg-background transition-colors duration-300">
      <div className="bg-gradient-to-r from-primary/10 via-primary/5 to-background border-b border-border/50">
        <div className="container mx-auto px-4 py-5">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center text-white font-bold text-lg">
                M
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                  MARTA Intelligence
                </h1>
                <p className="text-sm text-muted-foreground">
                  Interactive map, demand forecasting & route optimization
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Link
                to="/"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors hidden sm:block"
              >
                Home
              </Link>
              <Link
                to="/analytics"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors hidden sm:block"
              >
                Analytics
              </Link>
              <button
                onClick={toggle}
                className="p-2 rounded-lg border border-border/50 hover:bg-secondary/80 transition-colors"
                title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {isDark ? (
                  <Sun className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Moon className="h-4 w-4 text-muted-foreground" />
                )}
              </button>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-lg">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs font-medium text-green-600 dark:text-green-400">System Online</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6 space-y-6">
        <HealthMetrics />

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full max-w-lg mx-auto grid-cols-3">
            <TabsTrigger value="map" className="flex items-center gap-2">
              <Map className="h-4 w-4" />
              <span className="hidden sm:inline">Rail Map</span>
              <span className="sm:hidden">Map</span>
            </TabsTrigger>
            <TabsTrigger value="forecast" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Demand Forecast</span>
              <span className="sm:hidden">Forecast</span>
            </TabsTrigger>
            <TabsTrigger value="route" className="flex items-center gap-2">
              <Navigation className="h-4 w-4" />
              <span className="hidden sm:inline">Route Optimizer</span>
              <span className="sm:hidden">Routes</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="map" className="mt-5">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <MartaRailMap />
            </motion.div>
          </TabsContent>

          <TabsContent value="forecast" className="mt-5">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <ForecastDashboard />
            </motion.div>
          </TabsContent>

          <TabsContent value="route" className="mt-5">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <RouteOptimizerPanel />
            </motion.div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Dashboard;
