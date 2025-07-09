import { format, parseISO, isValid } from 'date-fns';

// Date and time formatting utilities
export const formatters = {
  // Format timestamp for display
  formatTime: (timestamp) => {
    try {
      const date = typeof timestamp === 'string' ? parseISO(timestamp) : timestamp;
      return isValid(date) ? format(date, 'HH:mm') : 'Invalid time';
    } catch (error) {
      console.error('Error formatting time:', error);
      return 'Invalid time';
    }
  },

  // Format date for display
  formatDate: (timestamp) => {
    try {
      const date = typeof timestamp === 'string' ? parseISO(timestamp) : timestamp;
      return isValid(date) ? format(date, 'MMM dd, yyyy') : 'Invalid date';
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Invalid date';
    }
  },

  // Format datetime for API calls
  formatDateTime: (timestamp) => {
    try {
      const date = typeof timestamp === 'string' ? parseISO(timestamp) : timestamp;
      return isValid(date) ? date.toISOString() : null;
    } catch (error) {
      console.error('Error formatting datetime:', error);
      return null;
    }
  },

  // Format numbers with appropriate units
  formatRiders: (count) => {
    if (count === null || count === undefined) return 'N/A';
    if (count < 1000) return count.toString();
    if (count < 1000000) return `${(count / 1000).toFixed(1)}K`;
    return `${(count / 1000000).toFixed(1)}M`;
  },

  // Format percentage
  formatPercentage: (value, decimals = 1) => {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(decimals)}%`;
  }
};

// Color utilities for demand levels and data visualization
export const colors = {
  // Demand level colors
  getDemandColor: (level) => {
    const colorMap = {
      'Underloaded': '#4CAF50',  // Green
      'Low': '#4CAF50',
      'Normal': '#2196F3',       // Blue
      'Medium': '#FF9800',       // Orange
      'High': '#FF9800',
      'Overloaded': '#F44336'    // Red
    };
    return colorMap[level] || '#9E9E9E'; // Default gray
  },

  // Get color based on intensity (0-1)
  getIntensityColor: (intensity) => {
    if (intensity <= 0.25) return '#4CAF50';  // Green
    if (intensity <= 0.5) return '#2196F3';   // Blue
    if (intensity <= 0.75) return '#FF9800';  // Orange
    return '#F44336';                         // Red
  },

  // Generate color palette for charts
  getChartColors: (count) => {
    const baseColors = [
      '#2196F3', '#4CAF50', '#FF9800', '#F44336', 
      '#9C27B0', '#00BCD4', '#FFEB3B', '#795548'
    ];
    
    const colors = [];
    for (let i = 0; i < count; i++) {
      colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
  }
};

// Geospatial utilities
export const geo = {
  // Calculate distance between two points (Haversine formula)
  calculateDistance: (lat1, lon1, lat2, lon2) => {
    const R = 6371; // Earth's radius in kilometers
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
      Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  },

  // Check if point is within bounds
  isWithinBounds: (lat, lng, bounds) => {
    return lat >= bounds.south && lat <= bounds.north &&
           lng >= bounds.west && lng <= bounds.east;
  },

  // Get center point of bounds
  getBoundsCenter: (bounds) => {
    return {
      lat: (bounds.north + bounds.south) / 2,
      lng: (bounds.east + bounds.west) / 2
    };
  },

  // Convert coordinates to GeoJSON point
  toGeoJSONPoint: (lat, lng, properties = {}) => {
    return {
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [lng, lat]
      },
      properties
    };
  }
};

// Data processing utilities
export const dataUtils = {
  // Group array of objects by a key
  groupBy: (array, key) => {
    return array.reduce((groups, item) => {
      const group = item[key];
      groups[group] = groups[group] || [];
      groups[group].push(item);
      return groups;
    }, {});
  },

  // Sort array by multiple criteria
  sortBy: (array, ...criteria) => {
    return array.sort((a, b) => {
      for (const criterion of criteria) {
        const { key, order = 'asc' } = typeof criterion === 'string' 
          ? { key: criterion } 
          : criterion;
        
        const aVal = a[key];
        const bVal = b[key];
        
        if (aVal < bVal) return order === 'asc' ? -1 : 1;
        if (aVal > bVal) return order === 'asc' ? 1 : -1;
      }
      return 0;
    });
  },

  // Calculate statistics for an array of numbers
  getStats: (numbers) => {
    if (!numbers.length) return null;
    
    const sorted = [...numbers].sort((a, b) => a - b);
    const sum = numbers.reduce((a, b) => a + b, 0);
    const mean = sum / numbers.length;
    
    return {
      min: sorted[0],
      max: sorted[sorted.length - 1],
      mean,
      median: sorted[Math.floor(sorted.length / 2)],
      sum,
      count: numbers.length
    };
  },

  // Debounce function for API calls
  debounce: (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  // Throttle function for frequent events
  throttle: (func, limit) => {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
};

// Local storage utilities with error handling
export const storage = {
  set: (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error('Error saving to localStorage:', error);
      return false;
    }
  },

  get: (key, defaultValue = null) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return defaultValue;
    }
  },

  remove: (key) => {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error('Error removing from localStorage:', error);
      return false;
    }
  },

  clear: () => {
    try {
      localStorage.clear();
      return true;
    } catch (error) {
      console.error('Error clearing localStorage:', error);
      return false;
    }
  }
};

// Validation utilities
export const validators = {
  isValidCoordinate: (lat, lng) => {
    return typeof lat === 'number' && typeof lng === 'number' &&
           lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
  },

  isValidStopId: (stopId) => {
    return typeof stopId === 'string' && stopId.length > 0;
  },

  isValidTimestamp: (timestamp) => {
    const date = new Date(timestamp);
    return date instanceof Date && !isNaN(date);
  }
};

export default {
  formatters,
  colors,
  geo,
  dataUtils,
  storage,
  validators
};

