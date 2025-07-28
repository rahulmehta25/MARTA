import { create } from 'zustand';
import { apiService } from '@/lib/api';

export interface TransitStop {
  id: string;
  name: string;
  lat: number;
  lng: number;
  demandLevel: 'low' | 'medium' | 'high';
  currentPassengers: number;
  predictedDemand: number;
  routes: string[];
}

export interface TransitRoute {
  id: string;
  name: string;
  color: string;
  stops: string[];
  coordinates: [number, number][];
  capacity: number;
  currentLoad: number;
  optimization: {
    efficiency: number;
    waitTime: number;
    coverage: number;
  };
}

export interface AppState {
  // Map state
  mapStyle: 'light' | 'dark' | 'satellite';
  selectedStop: TransitStop | null;
  selectedRoute: TransitRoute | null;
  showDemandHeatmap: boolean;
  
  // UI state
  drawerOpen: boolean;
  drawerHeight: number;
  activeTab: 'overview' | 'demand' | 'optimization' | 'analytics';
  searchQuery: string;
  searchResults: (TransitStop | TransitRoute)[];
  
  // Data
  stops: TransitStop[];
  routes: TransitRoute[];
  demandPredictions: Record<string, number[]>;
  
  // Real-time
  isConnected: boolean;
  lastUpdate: Date | null;
}

export interface AppActions {
  // Map actions
  setMapStyle: (style: AppState['mapStyle']) => void;
  setSelectedStop: (stop: TransitStop | null) => void;
  setSelectedRoute: (route: TransitRoute | null) => void;
  toggleDemandHeatmap: () => void;
  
  // UI actions
  setDrawerOpen: (open: boolean) => void;
  setDrawerHeight: (height: number) => void;
  setActiveTab: (tab: AppState['activeTab']) => void;
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: (TransitStop | TransitRoute)[]) => void;
  
  // Data actions
  setStops: (stops: TransitStop[]) => void;
  setRoutes: (routes: TransitRoute[]) => void;
  updateDemandPredictions: (predictions: Record<string, number[]>) => void;
  
  // Real-time actions
  setConnected: (connected: boolean) => void;
  updateLastUpdate: () => void;
  
  // API actions
  fetchStops: () => Promise<void>;
  fetchRoutes: () => Promise<void>;
  optimizeRoutes: (request: any) => Promise<any>;
  simulateRoutes: (request: any) => Promise<any>;
}

export const useAppStore = create<AppState & AppActions>((set, get) => ({
  // Initial state
  mapStyle: 'light',
  selectedStop: null,
  selectedRoute: null,
  showDemandHeatmap: true,
  
  drawerOpen: true,
  drawerHeight: 300,
  activeTab: 'overview',
  searchQuery: '',
  searchResults: [],
  
  stops: [],
  routes: [],
  demandPredictions: {},
  
  isConnected: false,
  lastUpdate: null,
  
  // Actions
  setMapStyle: (style) => set({ mapStyle: style }),
  setSelectedStop: (stop) => set({ selectedStop: stop }),
  setSelectedRoute: (route) => set({ selectedRoute: route }),
  toggleDemandHeatmap: () => set((state) => ({ showDemandHeatmap: !state.showDemandHeatmap })),
  
  setDrawerOpen: (open) => set({ drawerOpen: open }),
  setDrawerHeight: (height) => set({ drawerHeight: Math.max(200, Math.min(height, 600)) }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchResults: (results) => set({ searchResults: results }),
  
  setStops: (stops) => set({ stops }),
  setRoutes: (routes) => set({ routes }),
  updateDemandPredictions: (predictions) => set({ demandPredictions: predictions }),
  
  setConnected: (connected) => set({ isConnected: connected }),
  updateLastUpdate: () => set({ lastUpdate: new Date() }),
  
  // API actions
  fetchStops: async () => {
    try {
      const stops = await apiService.getStops();
      set({ stops });
    } catch (error) {
      console.error('Failed to fetch stops:', error);
    }
  },
  
  fetchRoutes: async () => {
    try {
      const routes = await apiService.getRoutes();
      set({ routes });
    } catch (error) {
      console.error('Failed to fetch routes:', error);
    }
  },
  
  optimizeRoutes: async (request) => {
    try {
      const result = await apiService.optimizeRoutes(request);
      return result;
    } catch (error) {
      console.error('Failed to optimize routes:', error);
      throw error;
    }
  },
  
  simulateRoutes: async (request) => {
    try {
      const result = await apiService.simulateRoutes(request);
      return result;
    } catch (error) {
      console.error('Failed to simulate routes:', error);
      throw error;
    }
  },
}));