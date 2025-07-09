import React, { useState, useEffect } from 'react';
import { ChevronUp, ChevronDown, X, MapPin, Clock, Users, TrendingUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../../utils/api';
import { formatters, colors } from '../../utils/helpers';
import { Button } from '../ui/Button';

export const BottomDrawer = ({ isOpen, onClose, selectedStop, onStopSelect }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [demandData, setDemandData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Load demand data when stop is selected
  useEffect(() => {
    if (selectedStop) {
      loadDemandData();
    }
  }, [selectedStop]);

  const loadDemandData = async () => {
    if (!selectedStop) return;
    
    setLoading(true);
    try {
      const prediction = await api.predictDemand(
        selectedStop.stop_id,
        new Date().toISOString()
      );
      setDemandData(prediction);
    } catch (error) {
      console.error('Error loading demand data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDragEnd = (event, info) => {
    const threshold = 100;
    if (info.offset.y > threshold) {
      if (isExpanded) {
        setIsExpanded(false);
      } else {
        onClose();
      }
    } else if (info.offset.y < -threshold) {
      setIsExpanded(true);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: MapPin },
    { id: 'demand', label: 'Demand', icon: Users },
    { id: 'schedule', label: 'Schedule', icon: Clock },
    { id: 'trends', label: 'Trends', icon: TrendingUp }
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-25 z-40"
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: isExpanded ? '20%' : '60%' }}
            exit={{ y: '100%' }}
            drag="y"
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={0.1}
            onDragEnd={handleDragEnd}
            className="fixed inset-x-0 bottom-0 z-50 bg-white rounded-t-3xl shadow-2xl"
            style={{ height: '80vh' }}
          >
            {/* Drag Handle */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-12 h-1 bg-gray-300 rounded-full cursor-grab active:cursor-grabbing" />
            </div>

            {/* Header */}
            <div className="px-6 pb-4 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  {selectedStop ? (
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {selectedStop.stop_name}
                      </h2>
                      <p className="text-sm text-gray-500">
                        Stop ID: {selectedStop.stop_id}
                        {selectedStop.zone_id && ` • ${selectedStop.zone_id}`}
                      </p>
                    </div>
                  ) : (
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        MARTA Dashboard
                      </h2>
                      <p className="text-sm text-gray-500">
                        Select a stop to view details
                      </p>
                    </div>
                  )}
                </div>
                
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-5 w-5 text-gray-600" />
                    ) : (
                      <ChevronUp className="h-5 w-5 text-gray-600" />
                    )}
                  </button>
                  
                  <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                  >
                    <X className="h-5 w-5 text-gray-600" />
                  </button>
                </div>
              </div>

              {/* Current Demand Status */}
              {demandData && (
                <div className="mt-4 p-3 rounded-lg bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Current Demand</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {formatters.formatRiders(demandData.predicted_riders)} riders
                      </p>
                    </div>
                    <div className={`
                      px-3 py-1 rounded-full text-sm font-medium
                      ${demandData.demand_level === 'Overloaded' ? 'bg-red-100 text-red-800' :
                        demandData.demand_level === 'High' ? 'bg-orange-100 text-orange-800' :
                        demandData.demand_level === 'Normal' ? 'bg-blue-100 text-blue-800' :
                        'bg-green-100 text-green-800'
                      }
                    `}>
                      {demandData.demand_level}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
              {selectedStop ? (
                <>
                  {/* Tabs */}
                  <div className="px-6 pt-4">
                    <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
                      {tabs.map((tab) => {
                        const Icon = tab.icon;
                        return (
                          <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`
                              flex-1 flex items-center justify-center space-x-2 py-2 px-3 rounded-md text-sm font-medium transition-colors
                              ${activeTab === tab.id 
                                ? 'bg-white text-blue-600 shadow-sm' 
                                : 'text-gray-600 hover:text-gray-900'
                              }
                            `}
                          >
                            <Icon className="h-4 w-4" />
                            <span>{tab.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Tab Content */}
                  <div className="flex-1 overflow-y-auto px-6 py-4">
                    {activeTab === 'overview' && (
                      <OverviewTab stop={selectedStop} demandData={demandData} />
                    )}
                    {activeTab === 'demand' && (
                      <DemandTab stop={selectedStop} demandData={demandData} />
                    )}
                    {activeTab === 'schedule' && (
                      <ScheduleTab stop={selectedStop} />
                    )}
                    {activeTab === 'trends' && (
                      <TrendsTab stop={selectedStop} />
                    )}
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center p-6">
                  <div className="text-center">
                    <MapPin className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      No Stop Selected
                    </h3>
                    <p className="text-gray-500">
                      Click on a stop on the map to view detailed information
                    </p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// Overview Tab Component
const OverviewTab = ({ stop, demandData }) => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-600 mb-1">Location</h4>
          <p className="text-lg font-semibold text-gray-900">
            {stop.stop_lat?.toFixed(4)}, {stop.stop_lon?.toFixed(4)}
          </p>
        </div>
        
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-600 mb-1">Zone</h4>
          <p className="text-lg font-semibold text-gray-900">
            {stop.zone_id || 'N/A'}
          </p>
        </div>
      </div>

      {demandData && (
        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-800 mb-2">
            Current Status
          </h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-blue-700">Predicted Riders:</span>
              <span className="font-semibold text-blue-900">
                {formatters.formatRiders(demandData.predicted_riders)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-700">Demand Level:</span>
              <span className="font-semibold text-blue-900">
                {demandData.demand_level}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-700">Last Updated:</span>
              <span className="font-semibold text-blue-900">
                {formatters.formatTime(demandData.timestamp)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Demand Tab Component
const DemandTab = ({ stop, demandData }) => {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Demand Forecasting
        </h3>
        <p className="text-gray-600">
          Real-time and predicted ridership data
        </p>
      </div>

      {demandData ? (
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-900 mb-2">
                {formatters.formatRiders(demandData.predicted_riders)}
              </div>
              <div className="text-sm text-gray-600 mb-4">
                Predicted riders in next 15 minutes
              </div>
              <div className={`
                inline-flex items-center px-3 py-1 rounded-full text-sm font-medium
                ${colors.getDemandColor(demandData.demand_level) === '#F44336' ? 'bg-red-100 text-red-800' :
                  colors.getDemandColor(demandData.demand_level) === '#FF9800' ? 'bg-orange-100 text-orange-800' :
                  colors.getDemandColor(demandData.demand_level) === '#2196F3' ? 'bg-blue-100 text-blue-800' :
                  'bg-green-100 text-green-800'
                }
              `}>
                {demandData.demand_level}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-8">
          <Users className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">Loading demand data...</p>
        </div>
      )}
    </div>
  );
};

// Schedule Tab Component
const ScheduleTab = ({ stop }) => {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Schedule Information
        </h3>
        <p className="text-gray-600">
          Upcoming arrivals and departures
        </p>
      </div>

      <div className="text-center py-8">
        <Clock className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">Schedule data coming soon...</p>
      </div>
    </div>
  );
};

// Trends Tab Component
const TrendsTab = ({ stop }) => {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Historical Trends
        </h3>
        <p className="text-gray-600">
          Ridership patterns and analytics
        </p>
      </div>

      <div className="text-center py-8">
        <TrendingUp className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">Trends analysis coming soon...</p>
      </div>
    </div>
  );
};

export default BottomDrawer;

