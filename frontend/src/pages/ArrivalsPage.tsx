import React, { useState } from 'react';
import { Train, Search, ChevronDown } from 'lucide-react';
import { ArrivalBoard } from '@/components/RealTime/ArrivalBoard';
import { motion } from 'framer-motion';

const POPULAR_STATIONS = [
  { id: 'FIVE POINTS STATION', label: 'Five Points', lines: ['RED', 'GOLD', 'BLUE', 'GREEN'] },
  { id: 'AIRPORT STATION', label: 'Airport', lines: ['RED', 'GOLD'] },
  { id: 'LINDBERGH STATION', label: 'Lindbergh', lines: ['RED', 'GOLD'] },
  { id: 'PEACHTREE CENTER STATION', label: 'Peachtree Ctr', lines: ['RED', 'GOLD'] },
  { id: 'NORTH SPRINGS STATION', label: 'North Springs', lines: ['RED'] },
  { id: 'CIVIC CENTER STATION', label: 'Civic Center', lines: ['RED', 'GOLD'] },
  { id: 'MIDTOWN STATION', label: 'Midtown', lines: ['RED', 'GOLD'] },
  { id: 'ARTS CENTER STATION', label: 'Arts Center', lines: ['RED', 'GOLD'] },
];

const LINE_COLORS: Record<string, string> = {
  RED: 'bg-red-500',
  GOLD: 'bg-amber-500',
  BLUE: 'bg-blue-600',
  GREEN: 'bg-green-600',
};

export const ArrivalsPage: React.FC = () => {
  const [primaryStation, setPrimaryStation] = useState('FIVE POINTS STATION');
  const [secondaryStation, setSecondaryStation] = useState('AIRPORT STATION');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredStations = searchQuery.trim()
    ? POPULAR_STATIONS.filter((s) =>
        s.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.id.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : POPULAR_STATIONS;

  return (
    <div id="arrivals-page" className="min-h-full pb-20 md:pb-6">
      {/* Page header */}
      <div
        id="arrivals-page-header"
        className="bg-white border-b border-gray-200 px-4 md:px-6 py-4"
      >
        <div className="max-w-4xl mx-auto">
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Train className="w-5 h-5 text-blue-600" />
            Real-Time Arrivals
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Live train arrival times with ML-powered predictions
          </p>
        </div>
      </div>

      <div id="arrivals-page-content" className="max-w-4xl mx-auto px-4 md:px-6 py-5 space-y-5">
        {/* Station selector */}
        <div id="station-selector" className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4">
          <div id="station-selector-header" className="flex items-center gap-2 mb-3">
            <Search className="w-4 h-4 text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-700">Select Stations</h2>
          </div>

          {/* Search */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              id="station-search-input"
              type="text"
              placeholder="Search stations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Station grid */}
          <div
            id="station-chips"
            className="flex flex-wrap gap-2"
          >
            {filteredStations.map((station) => {
              const isPrimary = primaryStation === station.id;
              const isSecondary = secondaryStation === station.id;
              return (
                <button
                  key={station.id}
                  id={`station-chip-${station.id.replace(/\s+/g, '-').toLowerCase()}`}
                  onClick={() => {
                    if (isPrimary) {
                      setPrimaryStation('');
                    } else if (isSecondary) {
                      setSecondaryStation('');
                    } else if (!primaryStation) {
                      setPrimaryStation(station.id);
                    } else {
                      setSecondaryStation(station.id);
                    }
                  }}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium border transition-all ${
                    isPrimary
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : isSecondary
                      ? 'bg-blue-50 text-blue-700 border-blue-300'
                      : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <span>{station.label}</span>
                  <div className="flex gap-0.5">
                    {station.lines.slice(0, 2).map((line) => (
                      <span
                        key={line}
                        id={`chip-line-${station.id}-${line}`}
                        className={`w-2 h-2 rounded-full ${LINE_COLORS[line] || 'bg-gray-400'}`}
                      />
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Arrival boards grid */}
        <div id="arrival-boards-grid" className="grid gap-4 md:grid-cols-2">
          {primaryStation && (
            <motion.div
              id="primary-arrival-board-wrapper"
              key={primaryStation}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <ArrivalBoard stationId={primaryStation} limit={8} />
            </motion.div>
          )}
          {secondaryStation && (
            <motion.div
              id="secondary-arrival-board-wrapper"
              key={secondaryStation}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <ArrivalBoard stationId={secondaryStation} limit={8} />
            </motion.div>
          )}
        </div>

        {/* Empty state */}
        {!primaryStation && !secondaryStation && (
          <div id="arrivals-empty-state" className="text-center py-12">
            <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
              <Train className="w-7 h-7 text-gray-400" />
            </div>
            <p className="text-sm font-semibold text-gray-700">Select a station above</p>
            <p className="text-xs text-gray-400 mt-1">Arrival boards will appear here</p>
          </div>
        )}

        {/* Info footer */}
        <div id="arrivals-info-footer" className="bg-blue-50 rounded-xl p-4 border border-blue-100">
          <p className="text-xs text-blue-700 font-medium">
            Arrival times update every 30 seconds via MARTA's real-time API.
            Predictions are powered by ML with 77% confidence.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ArrivalsPage;
