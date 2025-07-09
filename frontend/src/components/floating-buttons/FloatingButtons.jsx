import React, { useState } from 'react';
import { 
  Layers, 
  RotateCcw, 
  Settings, 
  Eye, 
  EyeOff, 
  MapPin, 
  Bus, 
  TrendingUp,
  Route
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../ui/Button';

export const FloatingButtons = ({ layers, onToggleLayer, onResetView }) => {
  const [showLayerMenu, setShowLayerMenu] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const layerControls = [
    {
      key: 'demand',
      label: 'Demand Heatmap',
      icon: TrendingUp,
      color: 'text-red-600',
      description: 'Show ridership demand intensity'
    },
    {
      key: 'routes',
      label: 'Transit Stops',
      icon: MapPin,
      color: 'text-blue-600',
      description: 'Show MARTA stops and stations'
    },
    {
      key: 'vehicles',
      label: 'Live Vehicles',
      icon: Bus,
      color: 'text-green-600',
      description: 'Show real-time bus positions'
    },
    {
      key: 'optimization',
      label: 'Route Optimization',
      icon: Route,
      color: 'text-purple-600',
      description: 'Show proposed route changes'
    }
  ];

  const handleLayerToggle = (layerKey) => {
    onToggleLayer(layerKey);
  };

  return (
    <div className="flex flex-col space-y-3">
      {/* Layer Control Button */}
      <div className="relative">
        <Button
          onClick={() => setShowLayerMenu(!showLayerMenu)}
          className={`
            w-12 h-12 rounded-full shadow-lg transition-all duration-200
            ${showLayerMenu 
              ? 'bg-blue-600 hover:bg-blue-700 text-white' 
              : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200'
            }
          `}
        >
          <Layers className="h-5 w-5" />
        </Button>

        {/* Layer Menu */}
        <AnimatePresence>
          {showLayerMenu && (
            <motion.div
              initial={{ opacity: 0, x: 20, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.9 }}
              className="absolute right-full top-0 mr-3 w-72 bg-white rounded-xl shadow-xl border border-gray-200 p-4 z-50"
            >
              <div className="mb-3">
                <h3 className="font-semibold text-gray-900 mb-1">Map Layers</h3>
                <p className="text-sm text-gray-600">Toggle data visualizations</p>
              </div>

              <div className="space-y-3">
                {layerControls.map((layer) => {
                  const Icon = layer.icon;
                  const isActive = layers[layer.key];
                  
                  return (
                    <div
                      key={layer.key}
                      className={`
                        flex items-center justify-between p-3 rounded-lg border transition-all cursor-pointer
                        ${isActive 
                          ? 'bg-blue-50 border-blue-200' 
                          : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                        }
                      `}
                      onClick={() => handleLayerToggle(layer.key)}
                    >
                      <div className="flex items-center space-x-3">
                        <div className={`
                          p-2 rounded-lg
                          ${isActive ? 'bg-blue-100' : 'bg-white'}
                        `}>
                          <Icon className={`h-4 w-4 ${isActive ? layer.color : 'text-gray-500'}`} />
                        </div>
                        <div>
                          <p className={`font-medium ${isActive ? 'text-blue-900' : 'text-gray-900'}`}>
                            {layer.label}
                          </p>
                          <p className="text-xs text-gray-600">
                            {layer.description}
                          </p>
                        </div>
                      </div>
                      
                      <div className={`
                        w-5 h-5 rounded border-2 flex items-center justify-center
                        ${isActive 
                          ? 'bg-blue-600 border-blue-600' 
                          : 'border-gray-300'
                        }
                      `}>
                        {isActive && (
                          <Eye className="h-3 w-3 text-white" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 pt-3 border-t border-gray-200">
                <Button
                  onClick={() => {
                    // Toggle all layers off
                    Object.keys(layers).forEach(key => {
                      if (layers[key]) {
                        onToggleLayer(key);
                      }
                    });
                  }}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  <EyeOff className="h-4 w-4 mr-2" />
                  Hide All Layers
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Reset View Button */}
      <Button
        onClick={onResetView}
        className="w-12 h-12 rounded-full bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 shadow-lg transition-all duration-200"
        title="Reset map view"
      >
        <RotateCcw className="h-5 w-5" />
      </Button>

      {/* Settings Button */}
      <div className="relative">
        <Button
          onClick={() => setShowSettings(!showSettings)}
          className={`
            w-12 h-12 rounded-full shadow-lg transition-all duration-200
            ${showSettings 
              ? 'bg-gray-600 hover:bg-gray-700 text-white' 
              : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200'
            }
          `}
        >
          <Settings className="h-5 w-5" />
        </Button>

        {/* Settings Menu */}
        <AnimatePresence>
          {showSettings && (
            <motion.div
              initial={{ opacity: 0, x: 20, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.9 }}
              className="absolute right-full top-0 mr-3 w-64 bg-white rounded-xl shadow-xl border border-gray-200 p-4 z-50"
            >
              <div className="mb-3">
                <h3 className="font-semibold text-gray-900 mb-1">Settings</h3>
                <p className="text-sm text-gray-600">Customize your experience</p>
              </div>

              <div className="space-y-3">
                <SettingItem
                  label="Auto-refresh data"
                  description="Update data automatically"
                  defaultChecked={true}
                />
                
                <SettingItem
                  label="Show notifications"
                  description="Alert for service disruptions"
                  defaultChecked={true}
                />
                
                <SettingItem
                  label="High contrast mode"
                  description="Improve visibility"
                  defaultChecked={false}
                />
                
                <SettingItem
                  label="Reduced motion"
                  description="Minimize animations"
                  defaultChecked={false}
                />
              </div>

              <div className="mt-4 pt-3 border-t border-gray-200">
                <div className="text-xs text-gray-500 text-center">
                  MARTA Platform v1.0.0
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Quick Stats */}
      <div className="mt-6 bg-white rounded-xl shadow-lg border border-gray-200 p-4 w-48">
        <h4 className="font-semibold text-gray-900 mb-3 text-sm">Quick Stats</h4>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-600">Active Layers:</span>
            <span className="font-medium text-gray-900">
              {Object.values(layers).filter(Boolean).length}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Last Update:</span>
            <span className="font-medium text-gray-900">
              {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Status:</span>
            <span className="font-medium text-green-600">Online</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Settings Item Component
const SettingItem = ({ label, description, defaultChecked = false }) => {
  const [checked, setChecked] = useState(defaultChecked);

  return (
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <p className="font-medium text-gray-900 text-sm">{label}</p>
        <p className="text-xs text-gray-600">{description}</p>
      </div>
      <button
        onClick={() => setChecked(!checked)}
        className={`
          relative inline-flex h-5 w-9 items-center rounded-full transition-colors
          ${checked ? 'bg-blue-600' : 'bg-gray-300'}
        `}
      >
        <span
          className={`
            inline-block h-3 w-3 transform rounded-full bg-white transition-transform
            ${checked ? 'translate-x-5' : 'translate-x-1'}
          `}
        />
      </button>
    </div>
  );
};

export default FloatingButtons;

