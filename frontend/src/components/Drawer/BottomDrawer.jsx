import React, { useState, useEffect } from 'react';
import { ChevronUp, ChevronDown, X, MapPin, Clock, Users, TrendingUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import apiService from '../../lib/api';
import { Button } from '../ui/button';

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
      const prediction = await apiService.get('/stops');
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
                        {selectedStop.name || selectedStop.stop_name}
                      </h2>
                      <p className="text-sm text-gray-500">
                        Stop ID: {selectedStop.id || selectedStop.stop_id}
                      </p>
                    </div>
                  ) : (
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        MARTA Analytics
                      </h2>
                      <p className="text-sm text-gray-500">
                        Select a stop to view details
                      </p>
                    </div>
                  )}
                </div>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-gray-100">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
                    activeTab === tab.id
                      ? 'text-blue-600 border-b-2 border-blue-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-center gap-2">
                    <tab.icon className="w-4 h-4" />
                    {tab.label}
                  </div>
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Stop Overview</h3>
                  {selectedStop ? (
                    <div className="space-y-3">
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-sm text-gray-600">Location</div>
                        <div className="font-medium">
                          {selectedStop.lat}, {selectedStop.lng}
                        </div>
                      </div>
                      {selectedStop.routes && (
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <div className="text-sm text-gray-600">Routes</div>
                          <div className="font-medium">
                            {selectedStop.routes.join(', ')}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500">Select a stop to view details</p>
                  )}
                </div>
              )}

              {activeTab === 'demand' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Demand Analysis</h3>
                  {loading ? (
                    <div className="text-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                      <p className="text-gray-500 mt-2">Loading demand data...</p>
                    </div>
                  ) : demandData ? (
                    <div className="space-y-3">
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <div className="text-sm text-blue-600">Current Demand</div>
                        <div className="font-medium text-blue-800">
                          {demandData.length} active stops
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-500">No demand data available</p>
                  )}
                </div>
              )}

              {activeTab === 'schedule' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Schedule Information</h3>
                  <p className="text-gray-500">Schedule data coming soon...</p>
                </div>
              )}

              {activeTab === 'trends' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Trend Analysis</h3>
                  <p className="text-gray-500">Trend data coming soon...</p>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default BottomDrawer;
