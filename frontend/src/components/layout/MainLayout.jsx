import React, { useState } from 'react';
import { MapContainer } from '../map/MapContainer';
import { SearchBar } from '../search/SearchBar';
import { BottomDrawer } from '../drawer/BottomDrawer';
import { FloatingButtons } from '../floating-buttons/FloatingButtons';

export const MainLayout = () => {
  const [selectedStop, setSelectedStop] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [mapLayers, setMapLayers] = useState({
    demand: true,
    routes: true,
    vehicles: false,
    optimization: false
  });

  const handleStopSelect = (stop) => {
    setSelectedStop(stop);
    setDrawerOpen(true);
  };

  const handleSearchSelect = (result) => {
    setSearchQuery(result.stop_name);
    setSelectedStop(result);
    setDrawerOpen(true);
  };

  const toggleLayer = (layerName) => {
    setMapLayers(prev => ({
      ...prev,
      [layerName]: !prev[layerName]
    }));
  };

  return (
    <div className="relative h-screen w-full overflow-hidden bg-gray-900">
      {/* Search Bar - Fixed at top */}
      <div className="absolute top-0 left-0 right-0 z-30 p-4">
        <SearchBar
          value={searchQuery}
          onChange={setSearchQuery}
          onSelect={handleSearchSelect}
          placeholder="Search for stops, routes, or destinations..."
        />
      </div>

      {/* Map Container - Full screen background */}
      <div className="absolute inset-0 z-10">
        <MapContainer
          onStopSelect={handleStopSelect}
          selectedStop={selectedStop}
          layers={mapLayers}
        />
      </div>

      {/* Floating Action Buttons - Right side */}
      <div className="absolute right-4 top-20 z-20">
        <FloatingButtons
          layers={mapLayers}
          onToggleLayer={toggleLayer}
          onResetView={() => setSelectedStop(null)}
        />
      </div>

      {/* Bottom Drawer - Expandable panel */}
      <BottomDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        selectedStop={selectedStop}
        onStopSelect={setSelectedStop}
      />
    </div>
  );
};

export default MainLayout;

