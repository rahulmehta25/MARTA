import React, { useEffect } from 'react';
import { TransitMap } from '@/components/Map/TransitMap';
import { SearchBar } from '@/components/Search/SearchBar';
import { BottomDrawer } from '@/components/Drawer/BottomDrawer';
import { useAppStore } from '@/store';
import { Settings, Layers, Satellite, Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';

export const MainLayout: React.FC = () => {
  const { 
    mapStyle, 
    setMapStyle, 
    showDemandHeatmap, 
    toggleDemandHeatmap,
    isConnected,
    fetchStops,
    fetchRoutes,
    setConnected
  } = useAppStore();

  // Fetch data on mount
  useEffect(() => {
    const initializeData = async () => {
      try {
        await Promise.all([fetchStops(), fetchRoutes()]);
        setConnected(true);
      } catch (error) {
        console.error('Failed to initialize data:', error);
        setConnected(false);
      }
    };

    initializeData();
  }, [fetchStops, fetchRoutes, setConnected]);

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Enhanced Header */}
      <header className="flex-shrink-0 bg-gradient-to-r from-card via-card to-card/95 backdrop-blur-sm border-b border-border/50 shadow-lg z-20">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <motion.div 
                className="w-10 h-10 bg-gradient-primary rounded-xl flex items-center justify-center shadow-lg"
                whileHover={{ scale: 1.05, rotate: 5 }}
                whileTap={{ scale: 0.95 }}
              >
                <span className="text-white font-bold text-lg">M</span>
              </motion.div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                  MARTA Analytics
                </h1>
                <p className="text-xs text-muted-foreground">Demand Forecasting & Route Optimization</p>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="hidden md:flex items-center gap-4 ml-8">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-marta-green/10 border border-marta-green/20 rounded-lg">
                <div className="w-2 h-2 bg-marta-green rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-marta-green">847 Active</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-marta-orange/10 border border-marta-orange/20 rounded-lg">
                <span className="text-sm font-medium text-marta-orange">3 High Demand</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-marta-blue/10 border border-marta-blue/20 rounded-lg">
                <span className="text-sm font-medium text-marta-blue">94% Efficiency</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Connection Status with Animation */}
            <motion.div 
              className="flex items-center gap-2 px-4 py-2 bg-secondary/50 backdrop-blur-sm rounded-xl border border-border/50"
              animate={{ 
                borderColor: isConnected ? 'hsl(var(--marta-green) / 0.3)' : 'hsl(var(--marta-red) / 0.3)'
              }}
              transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
            >
              <motion.div 
                className={`w-2 h-2 rounded-full ${isConnected ? 'bg-marta-green' : 'bg-marta-red'}`}
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
              <span className="text-sm font-medium">
                {isConnected ? 'Live Data' : 'Reconnecting...'}
              </span>
            </motion.div>

            {/* Enhanced Map Controls */}
            <div className="flex items-center gap-1 bg-secondary/50 backdrop-blur-sm rounded-xl p-1 border border-border/50">
              {[
                { style: 'light', icon: Sun, label: 'Light' },
                { style: 'dark', icon: Moon, label: 'Dark' },
                { style: 'satellite', icon: Satellite, label: 'Satellite' }
              ].map(({ style, icon: Icon, label }) => (
                <Button
                  key={style}
                  variant={mapStyle === style ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setMapStyle(style as any)}
                  className={`h-8 px-3 transition-all duration-300 ${
                    mapStyle === style 
                      ? 'bg-primary text-primary-foreground shadow-md' 
                      : 'hover:bg-secondary/80'
                  }`}
                  title={label}
                >
                  <Icon className="w-4 h-4" />
                </Button>
              ))}
            </div>

            {/* Enhanced Heatmap Toggle */}
            <Button
              variant={showDemandHeatmap ? 'default' : 'outline'}
              size="sm"
              onClick={toggleDemandHeatmap}
              className={`flex items-center gap-2 transition-all duration-300 ${
                showDemandHeatmap 
                  ? 'bg-gradient-demand shadow-lg hover:shadow-xl' 
                  : 'hover:bg-secondary/80'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span className="hidden sm:inline">Heatmap</span>
              {showDemandHeatmap && (
                <motion.div
                  className="w-1 h-1 bg-white rounded-full"
                  animate={{ scale: [1, 1.5, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              )}
            </Button>

            {/* Settings with Badge */}
            <div className="relative">
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Button 
                  variant="outline" 
                  size="sm"
                  className="hover:bg-secondary/80 transition-all duration-300"
                >
                  <Settings className="w-4 h-4" />
                </Button>
              </motion.div>
              <motion.div
                className="absolute -top-1 -right-1 w-2 h-2 bg-marta-red rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 relative overflow-hidden">
        {/* Map */}
        <TransitMap className="absolute inset-0" />

        {/* Search Overlay */}
        <div className="absolute top-6 left-6 z-10">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <SearchBar />
          </motion.div>
        </div>

        {/* Bottom Drawer */}
        <BottomDrawer />
      </div>
    </div>
  );
};