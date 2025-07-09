import React, { useRef, useEffect, useState, useCallback } from 'react';
import { config } from '../../utils/config';
import { api } from '../../utils/api';
import { colors, geo } from '../../utils/helpers';
import { MapPin, Bus, AlertTriangle, Map as MapIcon } from 'lucide-react';

export const MapContainer = ({ onStopSelect, selectedStop, layers }) => {
  const [stops, setStops] = useState([]);
  const [heatmapData, setHeatmapData] = useState(null);
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load initial data
  useEffect(() => {
    const loadMapData = async () => {
      try {
        setLoading(true);
        
        // Load stops data
        const stopsData = await api.getStops();
        setStops(stopsData);
        
        // Load initial heatmap data
        if (layers.demand) {
          const heatmap = await api.getHeatmapData(
            'current',
            config.DEFAULT_MAP_ZOOM,
            config.ATLANTA_BOUNDS
          );
          setHeatmapData(heatmap);
        }
        
      } catch (error) {
        console.error('Error loading map data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadMapData();
  }, [layers.demand]);

  // Handle stop click
  const handleStopClick = useCallback((stop) => {
    onStopSelect?.(stop);
  }, [onStopSelect]);

  return (
    <div className="relative w-full h-full bg-gray-900">
      {/* Placeholder Map Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-800 via-gray-900 to-black">
        {/* Grid pattern overlay */}
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }}
        />
        
        {/* Atlanta area representation */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative">
            {/* Central area (Downtown Atlanta) */}
            <div className="w-32 h-32 bg-blue-600 bg-opacity-30 rounded-full blur-xl"></div>
            
            {/* Surrounding areas */}
            <div className="absolute -top-16 -left-8 w-20 h-20 bg-green-500 bg-opacity-20 rounded-full blur-lg"></div>
            <div className="absolute -bottom-12 right-4 w-24 h-24 bg-purple-500 bg-opacity-20 rounded-full blur-lg"></div>
            <div className="absolute top-8 -right-16 w-16 h-16 bg-orange-500 bg-opacity-20 rounded-full blur-lg"></div>
          </div>
        </div>
      </div>

      {/* Stop Markers */}
      {layers.routes && stops.map((stop, index) => (
        <button
          key={stop.stop_id}
          onClick={() => handleStopClick(stop)}
          className={`
            absolute p-2 rounded-full transition-all duration-200 hover:scale-110 z-20
            ${selectedStop?.stop_id === stop.stop_id 
              ? 'bg-blue-500 text-white shadow-lg' 
              : 'bg-white text-gray-700 hover:bg-blue-50'
            }
          `}
          style={{
            left: `${20 + (index % 5) * 15}%`,
            top: `${30 + Math.floor(index / 5) * 20}%`,
          }}
          title={stop.stop_name}
        >
          <MapPin size={16} />
        </button>
      ))}

      {/* Demand Heatmap Visualization */}
      {layers.demand && heatmapData?.data && (
        <div className="absolute inset-0 pointer-events-none z-10">
          {heatmapData.data.slice(0, 20).map((point, index) => (
            <div
              key={index}
              className="absolute rounded-full blur-sm"
              style={{
                left: `${Math.random() * 80 + 10}%`,
                top: `${Math.random() * 80 + 10}%`,
                width: `${20 + point.intensity * 40}px`,
                height: `${20 + point.intensity * 40}px`,
                backgroundColor: colors.getIntensityColor(point.intensity),
                opacity: 0.6
              }}
            />
          ))}
        </div>
      )}

      {/* Vehicle Markers */}
      {layers.vehicles && vehicles.map((vehicle, index) => (
        <div
          key={vehicle.vehicle_id || index}
          className="absolute p-1 bg-green-500 text-white rounded-full z-20"
          style={{
            left: `${Math.random() * 70 + 15}%`,
            top: `${Math.random() * 70 + 15}%`,
          }}
        >
          <Bus size={12} />
        </div>
      ))}

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
            <span className="text-gray-700">Loading map data...</span>
          </div>
        </div>
      )}

      {/* Map placeholder notice */}
      <div className="absolute top-4 left-4 bg-black bg-opacity-60 text-white rounded-lg p-3 text-sm z-30">
        <div className="flex items-center space-x-2">
          <MapIcon className="h-4 w-4" />
          <span>Map Preview Mode</span>
        </div>
        <p className="text-xs text-gray-300 mt-1">
          Add Mapbox token to enable full map functionality
        </p>
      </div>

      {/* Map controls info */}
      <div className="absolute bottom-4 left-4 bg-white bg-opacity-90 rounded-lg p-3 text-xs text-gray-600 z-30">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span>Transit Stops ({stops.length})</span>
          </div>
          {layers.demand && (
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-gradient-to-r from-green-400 to-red-500 rounded-full"></div>
              <span>Demand Heatmap</span>
            </div>
          )}
          {layers.vehicles && (
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span>Live Vehicles</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MapContainer;

