import React, { useState } from 'react';
import {
  Bookmark,
  Train,
  Clock,
  ArrowRight,
  Star,
  StarOff,
  Plus,
  ChevronRight,
  History,
  Trash2,
  Navigation
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

interface SavedRoute {
  id: string;
  from: string;
  to: string;
  lines: string[];
  avgDuration: number;
  transfers: number;
  starred: boolean;
  lastUsed?: string;
  usageCount: number;
}

interface RecentTrip {
  id: string;
  from: string;
  to: string;
  lines: string[];
  duration: number;
  date: string;
  time: string;
}

const INITIAL_SAVED: SavedRoute[] = [
  {
    id: 'sr-1',
    from: 'Lindbergh Center',
    to: 'Airport Station',
    lines: ['RED'],
    avgDuration: 28,
    transfers: 0,
    starred: true,
    lastUsed: 'Today',
    usageCount: 47,
  },
  {
    id: 'sr-2',
    from: 'North Springs',
    to: 'Five Points',
    lines: ['RED'],
    avgDuration: 35,
    transfers: 0,
    starred: true,
    lastUsed: 'Yesterday',
    usageCount: 23,
  },
  {
    id: 'sr-3',
    from: 'Doraville',
    to: 'Midtown',
    lines: ['GOLD'],
    avgDuration: 22,
    transfers: 0,
    starred: false,
    lastUsed: '3 days ago',
    usageCount: 8,
  },
];

const RECENT_TRIPS: RecentTrip[] = [
  {
    id: 'rt-1',
    from: 'Lindbergh Center',
    to: 'Airport Station',
    lines: ['RED'],
    duration: 27,
    date: 'Today',
    time: '8:42 AM',
  },
  {
    id: 'rt-2',
    from: 'Airport Station',
    to: 'Lindbergh Center',
    lines: ['RED'],
    duration: 29,
    date: 'Today',
    time: '6:15 PM',
  },
  {
    id: 'rt-3',
    from: 'North Springs',
    to: 'Five Points',
    lines: ['RED'],
    duration: 34,
    date: 'Yesterday',
    time: '9:05 AM',
  },
  {
    id: 'rt-4',
    from: 'Five Points',
    to: 'Doraville',
    lines: ['GOLD'],
    duration: 20,
    date: 'Yesterday',
    time: '5:48 PM',
  },
];

const LINE_COLORS: Record<string, { bg: string; text: string }> = {
  RED:   { bg: 'bg-red-500',   text: 'text-white' },
  GOLD:  { bg: 'bg-amber-500', text: 'text-white' },
  BLUE:  { bg: 'bg-blue-600',  text: 'text-white' },
  GREEN: { bg: 'bg-green-600', text: 'text-white' },
};

const SavedRouteCard: React.FC<{
  route: SavedRoute;
  onToggleStar: () => void;
  onDelete: () => void;
  index: number;
}> = ({ route, onToggleStar, onDelete, index }) => {
  const navigate = useNavigate();

  return (
    <motion.div
      id={`saved-route-${route.id}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ delay: index * 0.05 }}
      className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden"
    >
      <div className="flex items-center gap-3 p-4">
        {/* Line indicator */}
        <div id={`saved-route-lines-${route.id}`} className="flex flex-col gap-1 flex-shrink-0">
          {route.lines.map((line) => (
            <div
              key={line}
              className={`w-2.5 h-2.5 rounded-full ${LINE_COLORS[line]?.bg || 'bg-gray-400'}`}
            />
          ))}
        </div>

        {/* Route info */}
        <div id={`saved-route-info-${route.id}`} className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-900 truncate">
            <span className="truncate">{route.from}</span>
            <ArrowRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            <span className="truncate">{route.to}</span>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              ~{route.avgDuration} min
            </div>
            <span className="text-xs text-gray-400">
              {route.transfers === 0 ? 'Direct' : `${route.transfers} transfer`}
            </span>
            {route.lastUsed && (
              <span className="text-xs text-gray-400">{route.lastUsed}</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div id={`saved-route-actions-${route.id}`} className="flex items-center gap-1 flex-shrink-0">
          <button
            id={`star-btn-${route.id}`}
            onClick={(e) => { e.stopPropagation(); onToggleStar(); }}
            className="p-2 rounded-xl hover:bg-gray-100 transition-colors"
            aria-label={route.starred ? 'Remove from favorites' : 'Add to favorites'}
          >
            {route.starred ? (
              <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
            ) : (
              <StarOff className="w-4 h-4 text-gray-300" />
            )}
          </button>
          <button
            id={`navigate-btn-${route.id}`}
            onClick={() => navigate('/plan')}
            className="p-2 rounded-xl hover:bg-blue-50 text-blue-500 transition-colors"
            aria-label="Plan this route"
          >
            <Navigation className="w-4 h-4" />
          </button>
          <button
            id={`delete-btn-${route.id}`}
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="p-2 rounded-xl hover:bg-red-50 text-red-400 transition-colors"
            aria-label="Delete saved route"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export const SavedRoutesPage: React.FC = () => {
  const [saved, setSaved] = useState<SavedRoute[]>(INITIAL_SAVED);
  const [activeTab, setActiveTab] = useState<'saved' | 'history'>('saved');
  const navigate = useNavigate();

  const toggleStar = (id: string) => {
    setSaved((prev) =>
      prev.map((r) => (r.id === id ? { ...r, starred: !r.starred } : r))
    );
  };

  const deleteRoute = (id: string) => {
    setSaved((prev) => prev.filter((r) => r.id !== id));
  };

  const starred = saved.filter((r) => r.starred);
  const unstarred = saved.filter((r) => !r.starred);

  return (
    <div id="saved-routes-page" className="min-h-full pb-20 md:pb-6">
      {/* Page header */}
      <div id="saved-routes-header" className="bg-white border-b border-gray-200 px-4 md:px-6 py-4">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Bookmark className="w-5 h-5 text-blue-600" />
            Saved Routes
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {saved.length} saved &nbsp;·&nbsp; {RECENT_TRIPS.length} recent trips
          </p>
        </div>
      </div>

      <div id="saved-routes-content" className="max-w-2xl mx-auto px-4 md:px-6 py-5 space-y-5">
        {/* Tabs */}
        <div
          id="saved-routes-tabs"
          className="flex bg-gray-100 rounded-xl p-1 gap-1"
          role="tablist"
        >
          {[
            { id: 'saved', label: 'Saved Routes', icon: Bookmark },
            { id: 'history', label: 'Trip History', icon: History },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`tab-${id}`}
              role="tab"
              aria-selected={activeTab === id}
              onClick={() => setActiveTab(id as any)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === id
                  ? 'bg-white text-blue-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Saved routes tab */}
        {activeTab === 'saved' && (
          <div id="saved-tab-content" className="space-y-4">
            {saved.length === 0 ? (
              <div id="saved-empty" className="text-center py-12">
                <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                  <Bookmark className="w-7 h-7 text-gray-300" />
                </div>
                <p className="text-sm font-semibold text-gray-700">No saved routes yet</p>
                <p className="text-xs text-gray-400 mt-1">Plan a trip and save it for quick access</p>
                <button
                  id="go-plan-btn"
                  onClick={() => navigate('/plan')}
                  className="mt-4 flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700 mx-auto"
                >
                  <Plus className="w-4 h-4" />
                  Plan a trip
                </button>
              </div>
            ) : (
              <>
                {starred.length > 0 && (
                  <div id="starred-routes-section">
                    <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <Star className="w-3.5 h-3.5 text-amber-500" />
                      Favorites
                    </h2>
                    <AnimatePresence mode="popLayout">
                      {starred.map((route, i) => (
                        <SavedRouteCard
                          key={route.id}
                          route={route}
                          onToggleStar={() => toggleStar(route.id)}
                          onDelete={() => deleteRoute(route.id)}
                          index={i}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                )}

                {unstarred.length > 0 && (
                  <div id="other-routes-section">
                    {starred.length > 0 && (
                      <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 mt-4">
                        Other Saved
                      </h2>
                    )}
                    <AnimatePresence mode="popLayout">
                      {unstarred.map((route, i) => (
                        <SavedRouteCard
                          key={route.id}
                          route={route}
                          onToggleStar={() => toggleStar(route.id)}
                          onDelete={() => deleteRoute(route.id)}
                          index={starred.length + i}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* History tab */}
        {activeTab === 'history' && (
          <div id="history-tab-content" className="space-y-2">
            {RECENT_TRIPS.map((trip, i) => (
              <motion.div
                key={trip.id}
                id={`history-trip-${trip.id}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="flex items-center gap-3 bg-white rounded-2xl border border-gray-200 shadow-sm p-3.5 hover:border-gray-300 transition-colors group cursor-pointer"
                onClick={() => navigate('/plan')}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && navigate('/plan')}
                aria-label={`Trip from ${trip.from} to ${trip.to}`}
              >
                {/* Line dots */}
                <div className="flex gap-1 flex-shrink-0">
                  {trip.lines.map((line) => (
                    <div
                      key={line}
                      id={`history-line-dot-${trip.id}-${line}`}
                      className={`w-2.5 h-2.5 rounded-full ${LINE_COLORS[line]?.bg || 'bg-gray-400'}`}
                    />
                  ))}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1 text-sm font-semibold text-gray-800 truncate">
                    <span className="truncate">{trip.from}</span>
                    <ArrowRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    <span className="truncate">{trip.to}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-gray-500">{trip.date} · {trip.time}</span>
                    <span className="text-xs text-gray-400">{trip.duration} min</span>
                  </div>
                </div>

                <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors flex-shrink-0" />
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SavedRoutesPage;
