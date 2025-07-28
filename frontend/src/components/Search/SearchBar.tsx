import React, { useState, useRef, useEffect } from 'react';
import { Search, MapPin, Route, Clock } from 'lucide-react';
import { useAppStore } from '@/store';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchResult {
  id: string;
  type: 'stop' | 'route' | 'address';
  name: string;
  subtitle?: string;
  icon: React.ReactNode;
}

export const SearchBar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [recentSearches] = useState<SearchResult[]>([
    { id: '1', type: 'stop', name: 'Five Points Station', subtitle: 'Red & Blue Lines', icon: <MapPin className="w-4 h-4" /> },
    { id: '2', type: 'route', name: 'Red Line', subtitle: 'North Springs to Airport', icon: <Route className="w-4 h-4" /> },
    { id: '3', type: 'stop', name: 'Peachtree Center', subtitle: 'Red & Gold Lines', icon: <MapPin className="w-4 h-4" /> },
  ]);
  
  const {
    searchQuery,
    setSearchQuery,
    setSelectedStop,
    setSelectedRoute,
  } = useAppStore();
  
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Demo search suggestions
  const suggestions: SearchResult[] = [
    { id: '1', type: 'stop', name: 'Five Points Station', subtitle: 'Red & Blue Lines • High Demand', icon: <MapPin className="w-4 h-4 text-marta-red" /> },
    { id: '2', type: 'stop', name: 'Peachtree Center', subtitle: 'Red & Gold Lines • Medium Demand', icon: <MapPin className="w-4 h-4 text-marta-orange" /> },
    { id: '3', type: 'stop', name: 'Midtown Station', subtitle: 'Red Line • High Demand', icon: <MapPin className="w-4 h-4 text-marta-red" /> },
    { id: '4', type: 'stop', name: 'North Avenue', subtitle: 'Red & Gold Lines • Low Demand', icon: <MapPin className="w-4 h-4 text-marta-green" /> },
    { id: '5', type: 'stop', name: 'Buckhead Station', subtitle: 'Red Line • Medium Demand', icon: <MapPin className="w-4 h-4 text-marta-orange" /> },
    { id: '6', type: 'route', name: 'Red Line', subtitle: 'North Springs to Airport', icon: <Route className="w-4 h-4 text-marta-blue" /> },
    { id: '7', type: 'route', name: 'Blue Line', subtitle: 'Hamilton E Holmes to Indian Creek', icon: <Route className="w-4 h-4 text-marta-blue" /> },
    { id: '8', type: 'route', name: 'Gold Line', subtitle: 'Doraville to Airport', icon: <Route className="w-4 h-4 text-marta-blue" /> },
  ];

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
      const filtered = suggestions.filter(item =>
        item.name.toLowerCase().includes(query.toLowerCase()) ||
        item.subtitle?.toLowerCase().includes(query.toLowerCase())
      );
      setSearchResults(filtered);
    } else {
      setSearchResults([]);
    }
  };

  const handleSelectResult = (result: SearchResult) => {
    setSearchQuery(result.name);
    setIsOpen(false);
    
    // Demo: Simulate selecting a stop or route
    if (result.type === 'stop') {
      const demoStop = {
        id: result.id,
        name: result.name,
        lat: 33.7537,
        lng: -84.3918,
        demandLevel: 'high' as const,
        currentPassengers: 45,
        predictedDemand: 52,
        routes: ['Red', 'Blue']
      };
      setSelectedStop(demoStop);
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