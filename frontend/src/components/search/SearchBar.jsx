import React, { useState, useEffect, useRef } from 'react';
import { Search, MapPin, Clock, X } from 'lucide-react';
import { api } from '../../utils/api';
import { dataUtils, storage } from '../../utils/helpers';

export const SearchBar = ({ value, onChange, onSelect, placeholder }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  
  const inputRef = useRef();
  const resultsRef = useRef();

  // Load recent searches from localStorage
  useEffect(() => {
    const recent = storage.get('recentSearches', []);
    setRecentSearches(recent);
  }, []);

  // Debounced search function
  const debouncedSearch = dataUtils.debounce(async (query) => {
    if (query.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const searchResults = await api.searchStops(query);
      setResults(searchResults);
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, 300);

  // Handle input change
  const handleInputChange = (e) => {
    const newValue = e.target.value;
    onChange(newValue);
    setSelectedIndex(-1);
    
    if (newValue.trim()) {
      setIsOpen(true);
      debouncedSearch(newValue);
    } else {
      setIsOpen(false);
      setResults([]);
    }
  };

  // Handle result selection
  const handleSelect = (result) => {
    onSelect(result);
    setIsOpen(false);
    setSelectedIndex(-1);
    
    // Add to recent searches
    const updatedRecent = [
      result,
      ...recentSearches.filter(item => item.stop_id !== result.stop_id)
    ].slice(0, 5);
    
    setRecentSearches(updatedRecent);
    storage.set('recentSearches', updatedRecent);
  };

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (!isOpen) return;

    const totalResults = results.length + (value.length === 0 ? recentSearches.length : 0);

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < totalResults - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > -1 ? prev - 1 : prev);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          const allResults = value.length === 0 ? recentSearches : results;
          if (allResults[selectedIndex]) {
            handleSelect(allResults[selectedIndex]);
          }
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  // Handle focus
  const handleFocus = () => {
    setIsOpen(true);
    if (value.length === 0 && recentSearches.length > 0) {
      // Show recent searches when focused with empty input
    }
  };

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (resultsRef.current && !resultsRef.current.contains(event.target)) {
        setIsOpen(false);
        setSelectedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Clear search
  const handleClear = () => {
    onChange('');
    setResults([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const showRecentSearches = value.length === 0 && recentSearches.length > 0;
  const displayResults = showRecentSearches ? recentSearches : results;

  return (
    <div className="relative w-full max-w-md mx-auto" ref={resultsRef}>
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          placeholder={placeholder}
          className="
            w-full pl-10 pr-10 py-3 
            bg-white rounded-xl shadow-lg
            border border-gray-200 
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            text-gray-900 placeholder-gray-500
            transition-all duration-200
          "
        />
        
        {value && (
          <button
            onClick={handleClear}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
          >
            <X className="h-5 w-5 text-gray-400 hover:text-gray-600" />
          </button>
        )}
      </div>

      {/* Search Results Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-200 max-h-80 overflow-y-auto z-50">
          {loading && (
            <div className="p-4 text-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-gray-500 text-sm mt-2">Searching...</p>
            </div>
          )}

          {!loading && showRecentSearches && (
            <>
              <div className="px-4 py-2 border-b border-gray-100">
                <h3 className="text-sm font-medium text-gray-700 flex items-center">
                  <Clock className="h-4 w-4 mr-2" />
                  Recent Searches
                </h3>
              </div>
              {recentSearches.map((item, index) => (
                <SearchResultItem
                  key={`recent-${item.stop_id}`}
                  result={item}
                  isSelected={selectedIndex === index}
                  onClick={() => handleSelect(item)}
                  isRecent={true}
                />
              ))}
            </>
          )}

          {!loading && !showRecentSearches && results.length > 0 && (
            <>
              <div className="px-4 py-2 border-b border-gray-100">
                <h3 className="text-sm font-medium text-gray-700">
                  Search Results ({results.length})
                </h3>
              </div>
              {results.map((result, index) => (
                <SearchResultItem
                  key={result.stop_id}
                  result={result}
                  isSelected={selectedIndex === index}
                  onClick={() => handleSelect(result)}
                />
              ))}
            </>
          )}

          {!loading && !showRecentSearches && results.length === 0 && value.length >= 2 && (
            <div className="p-4 text-center text-gray-500">
              <MapPin className="h-8 w-8 mx-auto mb-2 text-gray-300" />
              <p>No stops found for "{value}"</p>
              <p className="text-sm">Try searching for a different location</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Individual search result item component
const SearchResultItem = ({ result, isSelected, onClick, isRecent = false }) => {
  return (
    <button
      onClick={onClick}
      className={`
        w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors
        flex items-center space-x-3 border-b border-gray-50 last:border-b-0
        ${isSelected ? 'bg-blue-50 border-blue-100' : ''}
      `}
    >
      <div className={`
        p-2 rounded-lg flex-shrink-0
        ${isRecent ? 'bg-gray-100' : 'bg-blue-100'}
      `}>
        {isRecent ? (
          <Clock className="h-4 w-4 text-gray-600" />
        ) : (
          <MapPin className="h-4 w-4 text-blue-600" />
        )}
      </div>
      
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">
          {result.stop_name}
        </p>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <span>Stop ID: {result.stop_id}</span>
          {result.zone_id && (
            <>
              <span>•</span>
              <span>{result.zone_id}</span>
            </>
          )}
        </div>
      </div>
      
      {isSelected && (
        <div className="text-blue-500">
          <Search className="h-4 w-4" />
        </div>
      )}
    </button>
  );
};

export default SearchBar;

