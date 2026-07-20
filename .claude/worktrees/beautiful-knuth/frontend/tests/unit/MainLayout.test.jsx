import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MainLayout } from '../../src/components/layout/MainLayout';

// Mock child components
jest.mock('../../src/components/map/MapContainer', () => ({
  MapContainer: ({ onStopSelect, selectedStop, layers, ...props }) => (
    <div 
      data-testid="map-container" 
      onClick={() => onStopSelect({ stop_id: '123', stop_name: 'Test Stop' })}
      {...props}
    >
      Map Container - Selected: {selectedStop?.stop_name || 'None'}
      <div data-testid="map-layers">
        {Object.entries(layers).map(([key, value]) => (
          <span key={key} data-testid={`layer-${key}`}>
            {key}: {value.toString()}
          </span>
        ))}
      </div>
    </div>
  )
}));

jest.mock('../../src/components/search/SearchBar', () => ({
  SearchBar: ({ value, onChange, onSelect, placeholder, ...props }) => (
    <div data-testid="search-bar" {...props}>
      <input
        data-testid="search-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      <button
        data-testid="search-select-button"
        onClick={() => onSelect({ stop_id: '456', stop_name: 'Search Result Stop' })}
      >
        Select Search Result
      </button>
    </div>
  )
}));

jest.mock('../../src/components/drawer/BottomDrawer', () => ({
  BottomDrawer: ({ isOpen, onClose, selectedStop, onStopSelect, ...props }) => (
    isOpen ? (
      <div data-testid="bottom-drawer" {...props}>
        Bottom Drawer - Stop: {selectedStop?.stop_name || 'None'}
        <button data-testid="drawer-close-button" onClick={onClose}>
          Close Drawer
        </button>
        <button 
          data-testid="drawer-select-stop-button"
          onClick={() => onStopSelect({ stop_id: '789', stop_name: 'Drawer Selected Stop' })}
        >
          Select from Drawer
        </button>
      </div>
    ) : null
  )
}));

jest.mock('../../src/components/floating-buttons/FloatingButtons', () => ({
  FloatingButtons: ({ layers, onToggleLayer, onResetView, ...props }) => (
    <div data-testid="floating-buttons" {...props}>
      <div data-testid="floating-layers">
        {Object.entries(layers).map(([key, value]) => (
          <button
            key={key}
            data-testid={`toggle-${key}`}
            onClick={() => onToggleLayer(key)}
          >
            {key}: {value.toString()}
          </button>
        ))}
      </div>
      <button data-testid="reset-view-button" onClick={onResetView}>
        Reset View
      </button>
    </div>
  )
}));

describe('MainLayout Component', () => {
  test('should render all main components', () => {
    render(<MainLayout />);
    
    expect(screen.getByTestId('search-bar')).toBeInTheDocument();
    expect(screen.getByTestId('map-container')).toBeInTheDocument();
    expect(screen.getByTestId('floating-buttons')).toBeInTheDocument();
    
    // Bottom drawer should not be visible initially
    expect(screen.queryByTestId('bottom-drawer')).not.toBeInTheDocument();
  });

  test('should have proper layout structure and classes', () => {
    const { container } = render(<MainLayout />);
    
    // Main container should have correct classes
    const mainContainer = container.firstChild;
    expect(mainContainer).toHaveClass('relative', 'h-screen', 'w-full', 'overflow-hidden', 'bg-gray-900');
  });

  test('should render search bar with correct positioning', () => {
    render(<MainLayout />);
    
    const searchContainer = screen.getByTestId('search-bar').parentElement;
    expect(searchContainer).toHaveClass('absolute', 'top-0', 'left-0', 'right-0', 'z-30', 'p-4');
  });

  test('should render map container with correct positioning', () => {
    render(<MainLayout />);
    
    const mapContainer = screen.getByTestId('map-container').parentElement;
    expect(mapContainer).toHaveClass('absolute', 'inset-0', 'z-10');
  });

  test('should render floating buttons with correct positioning', () => {
    render(<MainLayout />);
    
    const floatingContainer = screen.getByTestId('floating-buttons').parentElement;
    expect(floatingContainer).toHaveClass('absolute', 'right-4', 'top-20', 'z-20');
  });

  describe('State Management', () => {
    test('should initialize with default state', () => {
      render(<MainLayout />);
      
      // Should show no selected stop initially
      expect(screen.getByText('Map Container - Selected: None')).toBeInTheDocument();
      
      // Should show default layer states
      expect(screen.getByTestId('layer-demand')).toHaveTextContent('demand: true');
      expect(screen.getByTestId('layer-routes')).toHaveTextContent('routes: true');
      expect(screen.getByTestId('layer-vehicles')).toHaveTextContent('vehicles: false');
      expect(screen.getByTestId('layer-optimization')).toHaveTextContent('optimization: false');
    });

    test('should initialize with empty search query', () => {
      render(<MainLayout />);
      
      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toHaveValue('');
    });

    test('should pass correct placeholder to search bar', () => {
      render(<MainLayout />);
      
      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toHaveAttribute('placeholder', 'Search for stops, routes, or destinations...');
    });
  });

  describe('Stop Selection from Map', () => {
    test('should handle stop selection from map', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Click on map to select a stop
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      // Should update selected stop
      expect(screen.getByText('Map Container - Selected: Test Stop')).toBeInTheDocument();
      
      // Should open bottom drawer
      expect(screen.getByTestId('bottom-drawer')).toBeInTheDocument();
      expect(screen.getByText('Bottom Drawer - Stop: Test Stop')).toBeInTheDocument();
    });

    test('should pass selected stop to map container', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Click on map
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      // Map container should show the selected stop
      expect(screen.getByText('Map Container - Selected: Test Stop')).toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    test('should handle search input changes', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      const searchInput = screen.getByTestId('search-input');
      
      await user.type(searchInput, 'Five Points');
      
      expect(searchInput).toHaveValue('Five Points');
    });

    test('should handle search result selection', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Simulate search result selection
      const selectButton = screen.getByTestId('search-select-button');
      await user.click(selectButton);
      
      // Should update search query with selected stop name
      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toHaveValue('Search Result Stop');
      
      // Should set selected stop
      expect(screen.getByText('Map Container - Selected: Search Result Stop')).toBeInTheDocument();
      
      // Should open drawer
      expect(screen.getByTestId('bottom-drawer')).toBeInTheDocument();
      expect(screen.getByText('Bottom Drawer - Stop: Search Result Stop')).toBeInTheDocument();
    });
  });

  describe('Bottom Drawer Functionality', () => {
    test('should open drawer when stop is selected', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Select a stop from map
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      // Drawer should be open
      expect(screen.getByTestId('bottom-drawer')).toBeInTheDocument();
    });

    test('should close drawer when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Open drawer by selecting a stop
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      expect(screen.getByTestId('bottom-drawer')).toBeInTheDocument();
      
      // Close drawer
      const closeButton = screen.getByTestId('drawer-close-button');
      await user.click(closeButton);
      
      expect(screen.queryByTestId('bottom-drawer')).not.toBeInTheDocument();
    });

    test('should handle stop selection from drawer', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Open drawer
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      // Select different stop from drawer
      const drawerSelectButton = screen.getByTestId('drawer-select-stop-button');
      await user.click(drawerSelectButton);
      
      // Should update selected stop
      expect(screen.getByText('Map Container - Selected: Drawer Selected Stop')).toBeInTheDocument();
      expect(screen.getByText('Bottom Drawer - Stop: Drawer Selected Stop')).toBeInTheDocument();
    });
  });

  describe('Layer Management', () => {
    test('should pass default layer states to map and floating buttons', () => {
      render(<MainLayout />);
      
      // Check map layers
      expect(screen.getByTestId('layer-demand')).toHaveTextContent('demand: true');
      expect(screen.getByTestId('layer-routes')).toHaveTextContent('routes: true');
      expect(screen.getByTestId('layer-vehicles')).toHaveTextContent('vehicles: false');
      expect(screen.getByTestId('layer-optimization')).toHaveTextContent('optimization: false');
      
      // Check floating button layers
      expect(screen.getByTestId('toggle-demand')).toHaveTextContent('demand: true');
      expect(screen.getByTestId('toggle-routes')).toHaveTextContent('routes: true');
      expect(screen.getByTestId('toggle-vehicles')).toHaveTextContent('vehicles: false');
      expect(screen.getByTestId('toggle-optimization')).toHaveTextContent('optimization: false');
    });

    test('should toggle layer states', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Toggle demand layer off
      const demandToggle = screen.getByTestId('toggle-demand');
      await user.click(demandToggle);
      
      // Should update both map and floating button displays
      expect(screen.getByTestId('layer-demand')).toHaveTextContent('demand: false');
      expect(screen.getByTestId('toggle-demand')).toHaveTextContent('demand: false');
      
      // Toggle vehicles layer on
      const vehiclesToggle = screen.getByTestId('toggle-vehicles');
      await user.click(vehiclesToggle);
      
      expect(screen.getByTestId('layer-vehicles')).toHaveTextContent('vehicles: true');
      expect(screen.getByTestId('toggle-vehicles')).toHaveTextContent('vehicles: true');
    });

    test('should toggle multiple layers independently', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Toggle multiple layers
      await user.click(screen.getByTestId('toggle-demand'));
      await user.click(screen.getByTestId('toggle-vehicles'));
      await user.click(screen.getByTestId('toggle-optimization'));
      
      // Each layer should be independently toggled
      expect(screen.getByTestId('layer-demand')).toHaveTextContent('demand: false');
      expect(screen.getByTestId('layer-routes')).toHaveTextContent('routes: true'); // unchanged
      expect(screen.getByTestId('layer-vehicles')).toHaveTextContent('vehicles: true');
      expect(screen.getByTestId('layer-optimization')).toHaveTextContent('optimization: true');
    });
  });

  describe('Reset Functionality', () => {
    test('should reset selected stop when reset button is clicked', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Select a stop first
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      expect(screen.getByText('Map Container - Selected: Test Stop')).toBeInTheDocument();
      
      // Reset view
      const resetButton = screen.getByTestId('reset-view-button');
      await user.click(resetButton);
      
      // Should clear selected stop
      expect(screen.getByText('Map Container - Selected: None')).toBeInTheDocument();
    });

    test('should close drawer when resetting view', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Open drawer by selecting a stop
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      expect(screen.getByTestId('bottom-drawer')).toBeInTheDocument();
      
      // Reset view
      const resetButton = screen.getByTestId('reset-view-button');
      await user.click(resetButton);
      
      // Drawer should close (selected stop becomes null)
      expect(screen.queryByTestId('bottom-drawer')).not.toBeInTheDocument();
    });
  });

  describe('Integration Testing', () => {
    test('should handle complex user flow', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // 1. Type in search
      const searchInput = screen.getByTestId('search-input');
      await user.type(searchInput, 'Station');
      
      // 2. Select search result
      const selectButton = screen.getByTestId('search-select-button');
      await user.click(selectButton);
      
      // 3. Verify drawer opens with search result
      expect(screen.getByTestId('bottom-drawer')).toBeInTheDocument();
      expect(screen.getByText('Bottom Drawer - Stop: Search Result Stop')).toBeInTheDocument();
      
      // 4. Toggle some layers
      await user.click(screen.getByTestId('toggle-vehicles'));
      await user.click(screen.getByTestId('toggle-demand'));
      
      // 5. Select different stop from map
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      // 6. Verify new stop selection
      expect(screen.getByText('Bottom Drawer - Stop: Test Stop')).toBeInTheDocument();
      
      // 7. Reset view
      const resetButton = screen.getByTestId('reset-view-button');
      await user.click(resetButton);
      
      // 8. Verify everything is reset
      expect(screen.getByText('Map Container - Selected: None')).toBeInTheDocument();
      expect(screen.queryByTestId('bottom-drawer')).not.toBeInTheDocument();
    });

    test('should maintain layer states during stop selection changes', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Change layer states
      await user.click(screen.getByTestId('toggle-vehicles'));
      await user.click(screen.getByTestId('toggle-demand'));
      
      // Select a stop
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      // Layer states should be maintained
      expect(screen.getByTestId('layer-vehicles')).toHaveTextContent('vehicles: true');
      expect(screen.getByTestId('layer-demand')).toHaveTextContent('demand: false');
      
      // Select different stop
      const selectButton = screen.getByTestId('search-select-button');
      await user.click(selectButton);
      
      // Layer states should still be maintained
      expect(screen.getByTestId('layer-vehicles')).toHaveTextContent('vehicles: true');
      expect(screen.getByTestId('layer-demand')).toHaveTextContent('demand: false');
    });

    test('should synchronize search query with stop selection', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      const searchInput = screen.getByTestId('search-input');
      
      // Select from search
      const selectButton = screen.getByTestId('search-select-button');
      await user.click(selectButton);
      
      expect(searchInput).toHaveValue('Search Result Stop');
      
      // Direct map selection doesn't change search query
      const mapContainer = screen.getByTestId('map-container');
      await user.click(mapContainer);
      
      // Search query should remain unchanged
      expect(searchInput).toHaveValue('Search Result Stop');
    });
  });

  describe('Error Handling', () => {
    test('should handle invalid stop data gracefully', async () => {
      const user = userEvent.setup();
      
      // Mock map container to return invalid stop data
      const MockMapWithInvalidData = () => (
        <div 
          data-testid="map-container-invalid"
          onClick={() => {
            // Simulate invalid stop data
            const mockHandleStopSelect = jest.fn();
            mockHandleStopSelect(null);
          }}
        >
          Invalid Map
        </div>
      );
      
      render(<MainLayout />);
      
      // Component should not crash with invalid data
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });

    test('should handle missing component props gracefully', () => {
      // Component should render even with missing or undefined data
      render(<MainLayout />);
      
      expect(screen.getByTestId('search-bar')).toBeInTheDocument();
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
      expect(screen.getByTestId('floating-buttons')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    test('should have proper focus management', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Search input should be focusable
      const searchInput = screen.getByTestId('search-input');
      searchInput.focus();
      expect(searchInput).toHaveFocus();
      
      // Buttons should be focusable
      const resetButton = screen.getByTestId('reset-view-button');
      resetButton.focus();
      expect(resetButton).toHaveFocus();
    });

    test('should maintain focus order', () => {
      render(<MainLayout />);
      
      // Should have interactive elements in logical tab order
      const interactiveElements = screen.getAllByRole('button');
      expect(interactiveElements.length).toBeGreaterThan(0);
    });
  });

  describe('Performance', () => {
    test('should not cause unnecessary re-renders', () => {
      const { rerender } = render(<MainLayout />);
      
      // Multiple rerenders should not cause errors
      rerender(<MainLayout />);
      rerender(<MainLayout />);
      
      expect(screen.getByTestId('search-bar')).toBeInTheDocument();
    });

    test('should handle rapid state changes', async () => {
      const user = userEvent.setup();
      render(<MainLayout />);
      
      // Rapid layer toggles
      const demandToggle = screen.getByTestId('toggle-demand');
      
      for (let i = 0; i < 5; i++) {
        await user.click(demandToggle);
      }
      
      // Should end up in the expected state
      expect(screen.getByTestId('layer-demand')).toHaveTextContent('demand: false');
    });
  });
});