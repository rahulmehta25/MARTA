import React, { useEffect, useState } from 'react';
import { TransitMap } from '@/components/Map/TransitMap';
import { SearchBar } from '@/components/Search/SearchBar';
import { useAppStore } from '@/store';
import { Layers, Info, ChevronDown, ChevronUp, Train, MapPin, Clock, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';

export const MainLayout: React.FC = () => {
  const {
    showDemandHeatmap,
    toggleDemandHeatmap,
    isConnected,
    fetchStops,
    fetchRoutes,
    setConnected,
    selectedStop,
    setSelectedStop,
  } = useAppStore();

  const [showMapControls, setShowMapControls] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        await Promise.all([fetchStops(), fetchRoutes()]);
        setConnected(true);
      } catch {
        setConnected(false);
      }
    };
    init();
  }, [fetchStops, fetchRoutes, setConnected]);

  return (
    <div
      id="map-page"
      className="relative w-full overflow-hidden"
      style={{ height: 'calc(100vh - var(--header-height, 96px))' }}
    >
      {/* Full-screen map */}
      <TransitMap className="absolute inset-0" />

      {/* Search overlay — top left */}
      <div
        id="map-search-overlay"
        className="absolute top-4 left-4 right-4 sm:right-auto sm:max-w-sm z-10"
      >
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.3 }}
        >
          <SearchBar />
        </motion.div>
      </div>

      {/* Map controls — top right */}
      <div
        id="map-controls-overlay"
        className="absolute top-4 right-4 z-10 flex flex-col gap-2"
      >
        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col gap-1.5"
        >
          {/* Heatmap toggle */}
          <button
            id="heatmap-toggle-btn"
            onClick={toggleDemandHeatmap}
            className={`flex items-center gap-2 pl-3 pr-3.5 py-2.5 rounded-xl text-sm font-semibold shadow-md transition-all ${
              showDemandHeatmap
                ? 'bg-blue-600 text-white shadow-blue-200'
                : 'bg-white text-gray-700 border border-gray-200 hover:border-gray-300'
            }`}
            aria-pressed={showDemandHeatmap}
            aria-label="Toggle demand heatmap"
          >
            <Layers className="w-4 h-4" />
            <span className="hidden sm:inline">Heatmap</span>
            {showDemandHeatmap && (
              <span className="w-2 h-2 rounded-full bg-white/70" />
            )}
          </button>
        </motion.div>
      </div>

      {/* Live status pill — bottom left (above bottom nav on mobile) */}
      <motion.div
        id="map-live-status"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="absolute bottom-24 md:bottom-6 left-4 z-10"
      >
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold shadow-md backdrop-blur-sm ${
            isConnected
              ? 'bg-white/95 text-green-700 border border-green-200'
              : 'bg-white/95 text-gray-500 border border-gray-200'
          }`}
        >
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 arrival-pulse' : 'bg-gray-400'}`} />
          {isConnected ? 'Live data' : 'Reconnecting...'}
        </div>
      </motion.div>

      {/* Quick action FAB — bottom right */}
      <motion.div
        id="map-fab-area"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45 }}
        className="absolute bottom-24 md:bottom-6 right-4 z-10 flex flex-col gap-2 items-end"
      >
        <button
          id="map-fab-info"
          onClick={() => setShowMapControls((v) => !v)}
          className="w-12 h-12 bg-white border border-gray-200 rounded-2xl shadow-lg flex items-center justify-center text-gray-600 hover:bg-gray-50 transition-all hover:shadow-xl active:scale-95"
          aria-label="Map legend"
        >
          <Info className="w-5 h-5" />
        </button>
      </motion.div>

      {/* Map legend / key */}
      <AnimatePresence>
        {showMapControls && (
          <motion.div
            id="map-legend"
            initial={{ opacity: 0, scale: 0.95, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 8 }}
            transition={{ duration: 0.18 }}
            className="absolute bottom-40 md:bottom-20 right-4 z-10 bg-white rounded-2xl border border-gray-200 shadow-xl p-4 w-52"
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-gray-900">Map Legend</h3>
              <button
                id="close-legend-btn"
                onClick={() => setShowMapControls(false)}
                className="p-0.5 rounded hover:bg-gray-100 text-gray-400"
                aria-label="Close legend"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div id="legend-lines" className="space-y-2">
              {[
                { color: '#EF4444', label: 'Red Line' },
                { color: '#F59E0B', label: 'Gold Line' },
                { color: '#0075BF', label: 'Blue Line' },
                { color: '#16A34A', label: 'Green Line' },
              ].map(({ color, label }) => (
                <div key={label} className="flex items-center gap-2">
                  <div className="w-4 h-2 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-xs text-gray-600">{label}</span>
                </div>
              ))}
              <div className="border-t border-gray-100 pt-2 mt-2 space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-green-400 border-2 border-white shadow-sm" />
                  <span className="text-xs text-gray-600">Station (Normal)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-amber-400 border-2 border-white shadow-sm" />
                  <span className="text-xs text-gray-600">Station (Busy)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white shadow-sm" />
                  <span className="text-xs text-gray-600">Station (High demand)</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Station detail panel — slides up from bottom when a stop is selected */}
      <AnimatePresence>
        {selectedStop && (
          <motion.div
            id="station-detail-panel"
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
            className="absolute bottom-0 left-0 right-0 z-20 bg-white rounded-t-3xl shadow-2xl border-t border-gray-200 pb-safe"
            style={{ maxHeight: '55vh', overflowY: 'auto' }}
          >
            {/* Handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-10 h-1 rounded-full bg-gray-300" />
            </div>

            <div id="station-panel-header" className="flex items-start justify-between px-5 pt-2 pb-3">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-sm">
                  <Train className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-gray-900 leading-tight">
                    {selectedStop.name}
                  </h2>
                  <div className="flex items-center gap-2 mt-0.5">
                    {selectedStop.routes.map((route) => (
                      <span
                        key={route}
                        id={`panel-route-chip-${route}`}
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full text-white ${
                          route === 'RED' ? 'bg-red-500' :
                          route === 'GOLD' ? 'bg-amber-500' :
                          route === 'BLUE' ? 'bg-blue-600' : 'bg-green-600'
                        }`}
                      >
                        {route}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <button
                id="close-station-panel"
                onClick={() => setSelectedStop(null)}
                className="p-1.5 rounded-xl hover:bg-gray-100 text-gray-400 transition-colors"
                aria-label="Close station panel"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Quick stats */}
            <div id="station-panel-stats" className="grid grid-cols-3 gap-3 px-5 pb-4">
              <div className="bg-gray-50 rounded-xl p-3 text-center">
                <div
                  id="station-demand-stat"
                  className={`text-sm font-bold capitalize ${
                    selectedStop.demandLevel === 'high' ? 'text-red-600' :
                    selectedStop.demandLevel === 'medium' ? 'text-amber-600' : 'text-green-600'
                  }`}
                >
                  {selectedStop.demandLevel}
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">Demand</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-3 text-center">
                <div id="station-passengers-stat" className="text-sm font-bold text-gray-800">
                  {selectedStop.currentPassengers}
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">On platform</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-3 text-center">
                <div id="station-predicted-stat" className="text-sm font-bold text-blue-700">
                  {selectedStop.predictedDemand}%
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">Predicted load</div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default MainLayout;
