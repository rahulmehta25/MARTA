import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../src/App';
import * as api from '../../src/utils/api';

// Mock all external dependencies
jest.mock('../../src/utils/api');
jest.mock('../../src/utils/config', () => ({
  config: {
    apiUrl: 'http://localhost:3001',
    mapboxToken: 'mock-token'
  },
  validateConfig: jest.fn()
}));

// Mock components that require external resources
jest.mock('../../src/components/map/MapContainer', () => ({
  MapContainer: ({ onStopSelect, selectedStop }) => (
    <div data-testid="map-container">
      <button 
        data-testid="mock-map-stop"
        onClick={() => onStopSelect({ 
          stop_id: 'TEST123', 
          stop_name: 'Test Station',
          stop_lat: 33.7539,
          stop_lon: -84.3910
        })}
      >
        Click to select stop
      </button>
      {selectedStop && (
        <div data-testid="selected-stop-display">
          Selected: {selectedStop.stop_name}
        </div>
      )}
    </div>
  )
}));

jest.mock('../../src/components/floating-buttons/FloatingButtons', () => ({
  FloatingButtons: ({ layers, onToggleLayer, onResetView }) => (
    <div data-testid="floating-buttons">
      {Object.entries(layers).map(([key, value]) => (
        <button 
          key={key}
          data-testid={`layer-toggle-${key}`}
          onClick={() => onToggleLayer(key)}
        >
          {key}: {value.toString()}
        </button>
      ))}
      <button data-testid="reset-view" onClick={onResetView}>
        Reset
      </button>
    </div>
  )
}));

describe('App Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    api.searchStops = jest.fn();
    api.predictDemand = jest.fn();
  });

  describe('Full Application Flow', () => {
    test('should render complete application layout', () => {
      render(<App />);

      // Check for main layout components
      expect(screen.getByPlaceholderText(/Search for stops/)).toBeInTheDocument();
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
      expect(screen.getByTestId('floating-buttons')).toBeInTheDocument();

      // Bottom drawer should not be visible initially
      expect(screen.queryByText('No Stop Selected')).not.toBeInTheDocument();
    });

    test('should handle complete user interaction flow', async () => {
      const user = userEvent.setup();
      const mockSearchResults = [
        { stop_id: 'SEARCH123', stop_name: 'Five Points Station' }
      ];
      const mockDemandData = {
        predicted_riders: 150,
        demand_level: 'High',
        timestamp: new Date().toISOString()
      };

      api.searchStops.mockResolvedValue(mockSearchResults);
      api.predictDemand.mockResolvedValue(mockDemandData);

      render(<App />);

      // Step 1: Search for a stop
      const searchInput = screen.getByPlaceholderText(/Search for stops/);
      await user.type(searchInput, 'Five Points');

      // Verify search API is called
      await waitFor(() => {
        expect(api.searchStops).toHaveBeenCalledWith('Five Points');
      });

      // Step 2: Select stop from map
      const mapStopButton = screen.getByTestId('mock-map-stop');
      await user.click(mapStopButton);

      // Verify stop selection
      expect(screen.getByTestId('selected-stop-display')).toHaveTextContent('Selected: Test Station');

      // Step 3: Verify drawer opens with stop details
      await waitFor(() => {
        expect(screen.getByText('Test Station')).toBeInTheDocument();
        expect(screen.getByText('Stop ID: TEST123')).toBeInTheDocument();
      });

      // Step 4: Toggle map layers
      const demandToggle = screen.getByTestId('layer-toggle-demand');
      await user.click(demandToggle);

      // Verify layer state changes
      expect(demandToggle).toHaveTextContent('demand: false');

      // Step 5: Reset view
      const resetButton = screen.getByTestId('reset-view');
      await user.click(resetButton);

      // Verify reset clears selection
      expect(screen.queryByTestId('selected-stop-display')).not.toBeInTheDocument();
    });

    test('should handle search and selection integration', async () => {
      const user = userEvent.setup();
      const mockSearchResults = [
        { stop_id: 'AIRPORT', stop_name: 'Airport Station' },
        { stop_id: 'DOWNTOWN', stop_name: 'Downtown Station' }
      ];

      api.searchStops.mockResolvedValue(mockSearchResults);

      render(<App />);

      const searchInput = screen.getByPlaceholderText(/Search for stops/);
      
      // Type search query
      await user.type(searchInput, 'Station');
      
      // Wait for search results
      await waitFor(() => {
        expect(api.searchStops).toHaveBeenCalledWith('Station');
      });

      // Verify search results appear
      await waitFor(() => {
        expect(screen.getByText('Airport Station')).toBeInTheDocument();
        expect(screen.getByText('Downtown Station')).toBeInTheDocument();
      });

      // Select a search result
      await user.click(screen.getByText('Airport Station'));

      // Verify selection updates search input
      expect(searchInput).toHaveValue('Airport Station');

      // Verify drawer opens
      await waitFor(() => {
        expect(screen.getByText('Airport Station')).toBeInTheDocument();
      });
    });

    test('should handle error states gracefully', async () => {
      const user = userEvent.setup();
      
      // Mock API failures
      api.searchStops.mockRejectedValue(new Error('Search API Error'));
      api.predictDemand.mockRejectedValue(new Error('Prediction API Error'));

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      render(<App />);

      // Try to search with failing API
      const searchInput = screen.getByPlaceholderText(/Search for stops/);
      await user.type(searchInput, 'Test');

      // Should handle error gracefully
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Search error:', expect.any(Error));
      });

      // App should still be functional
      expect(screen.getByTestId('map-container')).toBeInTheDocument();

      // Try to select stop with failing prediction API
      const mapStopButton = screen.getByTestId('mock-map-stop');
      await user.click(mapStopButton);

      // Should handle error gracefully
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Error loading demand data:', expect.any(Error));
      });

      // Drawer should still open even without demand data
      expect(screen.getByText('Test Station')).toBeInTheDocument();

      consoleSpy.mockRestore();
    });

    test('should handle rapid user interactions', async () => {
      const user = userEvent.setup();
      api.searchStops.mockResolvedValue([]);

      render(<App />);

      const searchInput = screen.getByPlaceholderText(/Search for stops/);
      const mapStopButton = screen.getByTestId('mock-map-stop');
      const demandToggle = screen.getByTestId('layer-toggle-demand');

      // Rapid interactions
      for (let i = 0; i < 5; i++) {
        await user.type(searchInput, `Query ${i}`);
        await user.clear(searchInput);
        await user.click(mapStopButton);
        await user.click(demandToggle);
      }

      // App should remain stable
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
      expect(screen.getByTestId('floating-buttons')).toBeInTheDocument();
    });

    test('should maintain state consistency across interactions', async () => {
      const user = userEvent.setup();
      
      render(<App />);

      // Initial state
      expect(screen.getByTestId('layer-toggle-demand')).toHaveTextContent('demand: true');
      expect(screen.getByTestId('layer-toggle-routes')).toHaveTextContent('routes: true');
      expect(screen.getByTestId('layer-toggle-vehicles')).toHaveTextContent('vehicles: false');

      // Change layer states
      await user.click(screen.getByTestId('layer-toggle-demand'));
      await user.click(screen.getByTestId('layer-toggle-vehicles'));

      // Select a stop
      await user.click(screen.getByTestId('mock-map-stop'));

      // Layer states should be preserved
      expect(screen.getByTestId('layer-toggle-demand')).toHaveTextContent('demand: false');
      expect(screen.getByTestId('layer-toggle-vehicles')).toHaveTextContent('vehicles: true');

      // Close drawer and reopen
      const closeButton = screen.getByTestId('drawer-close-button');
      await user.click(closeButton);

      await user.click(screen.getByTestId('mock-map-stop'));

      // States should still be preserved
      expect(screen.getByTestId('layer-toggle-demand')).toHaveTextContent('demand: false');
      expect(screen.getByTestId('layer-toggle-vehicles')).toHaveTextContent('vehicles: true');
    });
  });

  describe('Component Integration', () => {
    test('should integrate search bar with map selection', async () => {
      const user = userEvent.setup();
      const mockSearchResults = [
        { stop_id: 'INT123', stop_name: 'Integration Station' }
      ];

      api.searchStops.mockResolvedValue(mockSearchResults);

      render(<App />);

      // Search for station
      const searchInput = screen.getByPlaceholderText(/Search for stops/);
      await user.type(searchInput, 'Integration');

      await waitFor(() => {
        expect(screen.getByText('Integration Station')).toBeInTheDocument();
      });

      // Select from search results
      await user.click(screen.getByText('Integration Station'));

      // Verify integration with map
      expect(screen.getByTestId('selected-stop-display')).toHaveTextContent('Selected: Integration Station');
    });

    test('should integrate floating buttons with map layers', async () => {
      const user = userEvent.setup();

      render(<App />);

      // Toggle various layers
      await user.click(screen.getByTestId('layer-toggle-demand'));
      await user.click(screen.getByTestId('layer-toggle-optimization'));

      // All components should reflect layer changes
      expect(screen.getByTestId('layer-toggle-demand')).toHaveTextContent('demand: false');
      expect(screen.getByTestId('layer-toggle-optimization')).toHaveTextContent('optimization: true');
    });

    test('should integrate drawer with stop selection', async () => {
      const user = userEvent.setup();
      const mockDemandData = {
        predicted_riders: 200,
        demand_level: 'Normal',
        timestamp: new Date().toISOString()
      };

      api.predictDemand.mockResolvedValue(mockDemandData);

      render(<App />);

      // Select stop from map
      await user.click(screen.getByTestId('mock-map-stop'));

      // Verify drawer opens with correct data
      await waitFor(() => {
        expect(screen.getByText('Test Station')).toBeInTheDocument();
        expect(screen.getByText('Stop ID: TEST123')).toBeInTheDocument();
      });

      // Verify demand prediction is called
      expect(api.predictDemand).toHaveBeenCalledWith('TEST123', expect.any(String));
    });
  });

  describe('Performance and Reliability', () => {
    test('should handle component unmounting gracefully', () => {
      const { unmount } = render(<App />);
      
      // Should not throw errors during cleanup
      expect(() => unmount()).not.toThrow();
    });

    test('should handle prop updates without breaking', () => {
      const { rerender } = render(<App />);
      
      // Multiple rerenders should not cause issues
      for (let i = 0; i < 5; i++) {
        rerender(<App />);
      }
      
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('should handle concurrent state updates', async () => {
      const user = userEvent.setup();
      
      render(<App />);

      // Simulate concurrent interactions
      const promises = [
        user.click(screen.getByTestId('layer-toggle-demand')),
        user.click(screen.getByTestId('layer-toggle-routes')),
        user.click(screen.getByTestId('mock-map-stop')),
        user.type(screen.getByPlaceholderText(/Search for stops/), 'Test')
      ];

      await Promise.all(promises);

      // Application should remain stable
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });

  describe('Accessibility Integration', () => {
    test('should maintain focus order through interactions', async () => {
      const user = userEvent.setup();
      
      render(<App />);

      // Tab through interactive elements
      await user.tab();
      expect(screen.getByPlaceholderText(/Search for stops/)).toHaveFocus();

      await user.tab();
      // Should focus on next interactive element
      // (Exact element depends on implementation)
    });

    test('should handle keyboard navigation', async () => {
      render(<App />);

      const searchInput = screen.getByPlaceholderText(/Search for stops/);
      
      // Should be accessible via keyboard
      searchInput.focus();
      expect(searchInput).toHaveFocus();

      // Should handle keyboard events
      fireEvent.keyDown(searchInput, { key: 'Enter' });
      // Should not crash
    });
  });
});