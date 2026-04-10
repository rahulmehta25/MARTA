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
    <div id="main-layout" className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Header */}
      <header id="main-header" className="flex-shrink-0 bg-card/95 backdrop-blur-sm border-b border-border/50 shadow-sm z-20" role="banner">
        <div className="flex items-center justify-between px-3 sm:px-6 py-3 sm:py-4 gap-2">
          <div className="flex items-center gap-3 sm:gap-6 min-w-0">
            <a href="/" className="flex items-center gap-2 sm:gap-3 min-w-0" aria-label="MARTA Analytics home">
              <div className="w-9 h-9 sm:w-10 sm:h-10 bg-gradient-primary rounded-xl flex items-center justify-center shadow-md flex-shrink-0">
                <span className="text-white font-bold text-base sm:text-lg" aria-hidden="true">M</span>
              </div>
              <div className="min-w-0 hidden xs:block">
                <h1 className="text-lg sm:text-xl font-bold text-foreground truncate">
                  MARTA Analytics
                </h1>
                <p className="text-xs text-muted-foreground hidden sm:block">Demand Forecasting & Route Optimization</p>
              </div>
            </a>

            {/* Quick Stats - hidden on small screens */}
            <div id="header-quick-stats" className="hidden lg:flex items-center gap-3 ml-4">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-marta-green/10 border border-marta-green/20 rounded-lg">
                <div className="w-2 h-2 bg-marta-green rounded-full animate-pulse" aria-hidden="true"></div>
                <span className="text-sm font-medium text-marta-green">System Active</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-marta-orange/10 border border-marta-orange/20 rounded-lg">
                <span className="text-sm font-medium text-marta-orange">Real-time Data</span>
              </div>
            </div>
          </div>

          <nav id="header-controls" className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0" aria-label="Map controls">
            {/* Connection Status */}
            <div
              id="connection-status"
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-secondary/50 rounded-lg border border-border/50"
              role="status"
              aria-live="polite"
              aria-label={isConnected ? 'Connected - receiving live data' : 'Disconnected - reconnecting'}
            >
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isConnected ? 'bg-marta-green' : 'bg-marta-red'} animate-pulse`} aria-hidden="true" />
              <span className="text-sm font-medium">
                {isConnected ? 'Live' : 'Offline'}
              </span>
            </div>

            {/* Map Style Controls */}
            <div id="map-style-controls" className="hidden sm:flex items-center gap-0.5 bg-secondary/50 rounded-lg p-0.5 border border-border/50" role="radiogroup" aria-label="Map style">
              {[
                { style: 'light', icon: Sun, label: 'Light map' },
                { style: 'dark', icon: Moon, label: 'Dark map' },
                { style: 'satellite', icon: Satellite, label: 'Satellite map' }
              ].map(({ style, icon: Icon, label }) => (
                <Button
                  key={style}
                  variant={mapStyle === style ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setMapStyle(style as any)}
                  className={`h-8 w-8 p-0 transition-colors ${
                    mapStyle === style
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'hover:bg-secondary/80'
                  }`}
                  aria-label={label}
                  aria-pressed={mapStyle === style}
                  role="radio"
                  aria-checked={mapStyle === style}
                >
                  <Icon className="w-4 h-4" aria-hidden="true" />
                </Button>
              ))}
            </div>

            {/* Heatmap Toggle */}
            <Button
              id="heatmap-toggle"
              variant={showDemandHeatmap ? 'default' : 'outline'}
              size="sm"
              onClick={toggleDemandHeatmap}
              className={`h-8 transition-colors ${
                showDemandHeatmap
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-secondary/80'
              }`}
              aria-label={showDemandHeatmap ? 'Hide demand heatmap' : 'Show demand heatmap'}
              aria-pressed={showDemandHeatmap}
            >
              <Layers className="w-4 h-4" aria-hidden="true" />
              <span className="hidden sm:inline ml-1.5">Heatmap</span>
            </Button>

            {/* Settings */}
            <Button
              id="settings-button"
              variant="outline"
              size="sm"
              className="h-8 w-8 p-0 hover:bg-secondary/80 transition-colors"
              onClick={() => {
                const store = useAppStore.getState();
                store.setActiveTab('optimization');
                store.toggleDrawer();
              }}
              aria-label="Open settings"
            >
              <Settings className="w-4 h-4" aria-hidden="true" />
            </Button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main id="main-content" className="flex-1 relative overflow-hidden" role="main">
        {/* Map */}
        <TransitMap className="absolute inset-0" />

        {/* Search Overlay */}
        <div id="search-overlay" className="absolute top-4 left-4 right-4 sm:right-auto sm:top-6 sm:left-6 z-10">
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
      </main>
    </div>
  );
};

export default MainLayout;