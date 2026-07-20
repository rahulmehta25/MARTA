import React, { useState, useRef, useEffect } from 'react';
import { Search, MapPin, Route, Clock, Train, Bus } from 'lucide-react';
import { useAppStore } from '@/store';
import { motion, AnimatePresence } from 'framer-motion';
import { martaStops, martaRoutes, searchStops } from '@/data/martaData';

interface SearchResult {
  id: string;
  type: 'stop' | 'route' | 'address';
  name: string;
  subtitle?: string;
  icon: React.ReactNode;
}

export const SearchBar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [recentSearches, setRecentSearches] = useState<SearchResult[]>(() => {
    // Load recent searches from localStorage
    const saved = localStorage.getItem('martaRecentSearches');
    if (saved) {
      return JSON.parse(saved);
    }
    // Default recent searches
    return [
      { id: 'FIVE_POINTS', type: 'stop', name: 'Five Points', subtitle: 'Red, Gold, Blue & Green Lines', icon: <Train className="w-4 h-4" /> },
      { id: 'RED', type: 'route', name: 'Red Line', subtitle: 'North Springs to Airport', icon: <Route className="w-4 h-4 text-red-500" /> },
      { id: 'LINDBERGH', type: 'stop', name: 'Lindbergh Center', subtitle: 'Red & Gold Lines • Parking Available', icon: <Train className="w-4 h-4" /> },
    ];
  });
  
  const {
    searchQuery,
    setSearchQuery,
    setSelectedStop,
    setSelectedRoute,
  } = useAppStore();
  
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Helper function to get route color
  const getRouteColor = (routeId: string) => {
    const colors: Record<string, string> = {
      RED: 'text-red-500',
      GOLD: 'text-yellow-500',
      BLUE: 'text-blue-500',
      GREEN: 'text-green-500'
    };
    return colors[routeId] || 'text-gray-500';
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    
    if (query.length > 0) {
      const results: SearchResult[] = [];
      
      // Search stops
      const matchingStops = searchStops(query).slice(0, 5);
      matchingStops.forEach(stop => {
        const routeNames = stop.routes.join(', ');
        const features = [];
        if (stop.parking) features.push('Parking');
        if (stop.accessibility) features.push('Accessible');
        
        results.push({
          id: stop.id,
          type: 'stop',
          name: stop.name,
          subtitle: `${routeNames} Lines${features.length ? ' • ' + features.join(' • ') : ''}`,
          icon: <Train className={`w-4 h-4 ${stop.routes.length > 2 ? 'text-purple-500' : getRouteColor(stop.routes[0])}`} />
        });
      });
      
      // Search routes
      const matchingRoutes = martaRoutes.filter(route =>
        route.name.toLowerCase().includes(query.toLowerCase()) ||
        route.id.toLowerCase().includes(query.toLowerCase())
      ).slice(0, 3);
      
      matchingRoutes.forEach(route => {
        const firstStop = martaStops.find(s => s.id === route.stops[0]);
        const lastStop = martaStops.find(s => s.id === route.stops[route.stops.length - 1]);
        
        results.push({
          id: route.id,
          type: 'route',
          name: route.name,
          subtitle: `${firstStop?.name} to ${lastStop?.name} • ${route.stops.length} stops`,
          icon: <Route className={`w-4 h-4 ${getRouteColor(route.id)}`} />
        });
      });
      
      setSearchResults(results);
    } else {
      setSearchResults([]);
    }
  };

  const handleSelectResult = (result: SearchResult) => {
    setSearchQuery(result.name);
    setIsOpen(false);
    
    // Add to recent searches
    const updatedRecent = [result, ...recentSearches.filter(r => r.id !== result.id)].slice(0, 5);
    setRecentSearches(updatedRecent);
    localStorage.setItem('martaRecentSearches', JSON.stringify(updatedRecent));
    
    if (result.type === 'stop') {
      // Find the actual stop data
      const stop = martaStops.find(s => s.id === result.id);
      if (stop) {
        const selectedStopData = {
          id: stop.id,
          name: stop.name,
          lat: stop.lat,
          lng: stop.lng,
          demandLevel: 'medium' as const, // This would come from real-time data
          currentPassengers: Math.floor(Math.random() * 60) + 10,
          predictedDemand: Math.floor(Math.random() * 70) + 15,
          routes: stop.routes
        };
        setSelectedStop(selectedStopData);
      }
    } else if (result.type === 'route') {
      // Handle route selection
      const route = martaRoutes.find(r => r.id === result.id);
      if (route) {
        setSelectedRoute(route);
      }
    }
  };

  const displayResults = searchQuery.length > 0 ? searchResults : recentSearches;

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Search stops, routes, or addresses..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => setIsOpen(true)}
          className="w-full pl-10 pr-4 py-3 bg-card border border-border rounded-xl shadow-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-smooth"
        />
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
            className="absolute top-full left-0 right-0 mt-2 bg-card border border-border rounded-xl shadow-lg overflow-hidden z-50"
          >
            {searchQuery.length === 0 && (
              <div className="px-4 py-3 border-b border-border">
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <Clock className="w-4 h-4" />
                  Recent Searches
                </div>
              </div>
            )}
            
            <div className="max-h-80 overflow-y-auto">
              {displayResults.length > 0 ? (
                displayResults.map((result, index) => (
                  <motion.button
                    key={result.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => handleSelectResult(result)}
                    className="w-full px-4 py-3 text-left hover:bg-secondary transition-colors duration-fast flex items-center gap-3 group"
                  >
                    <div className="flex-shrink-0">
                      {result.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm group-hover:text-primary transition-colors">
                        {result.name}
                      </div>
                      {result.subtitle && (
                        <div className="text-xs text-muted-foreground mt-0.5">
                          {result.subtitle}
                        </div>
                      )}
                    </div>
                    <div className="flex-shrink-0 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                      →
                    </div>
                  </motion.button>
                ))
              ) : (
                <div className="px-4 py-6 text-center text-muted-foreground">
                  <div className="text-sm">No results found</div>
                  <div className="text-xs mt-1">Try searching for a station name or route</div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};