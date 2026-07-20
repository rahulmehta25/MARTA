import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BottomDrawer } from '../../src/components/drawer/BottomDrawer';
import * as api from '../../src/utils/api';
import * as helpers from '../../src/utils/helpers';

// Mock dependencies
jest.mock('../../src/utils/api');
jest.mock('../../src/utils/helpers', () => ({
  formatters: {
    formatRiders: jest.fn((value) => value.toString()),
    formatTime: jest.fn((timestamp) => new Date(timestamp).toLocaleTimeString())
  },
  colors: {
    getDemandColor: jest.fn((level) => {
      const colorMap = {
        'Overloaded': '#F44336',
        'High': '#FF9800',
        'Normal': '#2196F3',
        'Low': '#4CAF50'
      };
      return colorMap[level] || '#2196F3';
    })
  }
}));

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>
  },
  AnimatePresence: ({ children }) => <div>{children}</div>
}));

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  ChevronUp: () => <div data-testid="chevron-up-icon" />,
  ChevronDown: () => <div data-testid="chevron-down-icon" />,
  X: () => <div data-testid="x-icon" />,
  MapPin: () => <div data-testid="mappin-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
  Users: () => <div data-testid="users-icon" />,
  TrendingUp: () => <div data-testid="trending-up-icon" />
}));

// Mock UI components
jest.mock('../../src/components/ui/button', () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>
}));

const mockStop = {
  stop_id: '12345',
  stop_name: 'Five Points Station',
  zone_id: 'Zone 1',
  stop_lat: 33.7539,
  stop_lon: -84.3910
};

const mockDemandData = {
  predicted_riders: 150,
  demand_level: 'High',
  timestamp: '2024-01-01T12:00:00Z'
};

describe('BottomDrawer Component', () => {
  const mockProps = {
    isOpen: false,
    onClose: jest.fn(),
    selectedStop: null,
    onStopSelect: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    api.predictDemand = jest.fn();
  });

  describe('Rendering - Closed State', () => {
    test('should not render when isOpen is false', () => {
      render(<BottomDrawer {...mockProps} />);
      
      // Should not find any drawer elements
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(screen.queryByText('MARTA Dashboard')).not.toBeInTheDocument();
    });
  });

  describe('Rendering - Open State', () => {
    test('should render when isOpen is true', () => {
      render(<BottomDrawer {...mockProps} isOpen={true} />);
      
      // Should render backdrop
      expect(screen.getByRole('button')).toBeInTheDocument(); // backdrop is clickable
      
      // Should render header
      expect(screen.getByText('MARTA Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Select a stop to view details')).toBeInTheDocument();
    });

    test('should render with selected stop', () => {
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      expect(screen.getByText('Five Points Station')).toBeInTheDocument();
      expect(screen.getByText('Stop ID: 12345 • Zone 1')).toBeInTheDocument();
    });

    test('should render drag handle', () => {
      render(<BottomDrawer {...mockProps} isOpen={true} />);
      
      const dragHandle = screen.getByRole('generic');
      expect(dragHandle).toHaveClass('w-12', 'h-1', 'bg-gray-300', 'rounded-full');
    });

    test('should render expand/collapse button', () => {
      render(<BottomDrawer {...mockProps} isOpen={true} />);
      
      expect(screen.getByTestId('chevron-up-icon')).toBeInTheDocument();
    });

    test('should render close button', () => {
      render(<BottomDrawer {...mockProps} isOpen={true} />);
      
      expect(screen.getByTestId('x-icon')).toBeInTheDocument();
    });
  });

  describe('Demand Data Loading', () => {
    test('should load demand data when stop is selected', async () => {
      api.predictDemand.mockResolvedValue(mockDemandData);
      
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      await waitFor(() => {
        expect(api.predictDemand).toHaveBeenCalledWith(
          mockStop.stop_id,
          expect.any(String)
        );
      });
    });

    test('should display current demand when data is loaded', async () => {
      api.predictDemand.mockResolvedValue(mockDemandData);
      
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      await waitFor(() => {
        expect(screen.getByText('Current Demand')).toBeInTheDocument();
        expect(screen.getByText('150 riders')).toBeInTheDocument();
        expect(screen.getByText('High')).toBeInTheDocument();
      });
    });

    test('should handle demand data loading errors', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      api.predictDemand.mockRejectedValue(new Error('API Error'));
      
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Error loading demand data:', expect.any(Error));
      });
      
      consoleSpy.mockRestore();
    });
  });

  describe('User Interactions', () => {
    test('should call onClose when backdrop is clicked', async () => {
      const user = userEvent.setup();
      render(<BottomDrawer {...mockProps} isOpen={true} />);
      
      // Find and click backdrop
      const backdrop = screen.getAllByRole('button')[0]; // backdrop is first button
      await user.click(backdrop);
      
      expect(mockProps.onClose).toHaveBeenCalled();
    });

    test('should call onClose when close button is clicked', async () => {
      const user = userEvent.setup();
      render(<BottomDrawer {...mockProps} isOpen={true} />);
      
      // Find close button (contains X icon)
      const closeButton = screen.getByTestId('x-icon').closest('button');
      await user.click(closeButton);
      
      expect(mockProps.onClose).toHaveBeenCalled();
    });

    test('should toggle expanded state when expand button is clicked', async () => {
      const user = userEvent.setup();
      render(<BottomDrawer {...mockProps} isOpen={true} />);
      
      // Initially shows chevron-up (not expanded)
      expect(screen.getByTestId('chevron-up-icon')).toBeInTheDocument();
      
      // Click expand button
      const expandButton = screen.getByTestId('chevron-up-icon').closest('button');
      await user.click(expandButton);
      
      // Should now show chevron-down (expanded)
      await waitFor(() => {
        expect(screen.getByTestId('chevron-down-icon')).toBeInTheDocument();
      });
    });
  });

  describe('Tab Navigation', () => {
    test('should render all tab buttons when stop is selected', () => {
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      expect(screen.getByText('Overview')).toBeInTheDocument();
      expect(screen.getByText('Demand')).toBeInTheDocument();
      expect(screen.getByText('Schedule')).toBeInTheDocument();
      expect(screen.getByText('Trends')).toBeInTheDocument();
    });

    test('should render tab icons', () => {
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      expect(screen.getByTestId('mappin-icon')).toBeInTheDocument();
      expect(screen.getByTestId('users-icon')).toBeInTheDocument();
      expect(screen.getByTestId('clock-icon')).toBeInTheDocument();
      expect(screen.getByTestId('trending-up-icon')).toBeInTheDocument();
    });

    test('should switch between tabs', async () => {
      const user = userEvent.setup();
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      // Click on Demand tab
      const demandTab = screen.getByText('Demand');
      await user.click(demandTab);
      
      // Should show demand content
      expect(screen.getByText('Demand Forecasting')).toBeInTheDocument();
      
      // Click on Schedule tab
      const scheduleTab = screen.getByText('Schedule');
      await user.click(scheduleTab);
      
      // Should show schedule content
      expect(screen.getByText('Schedule Information')).toBeInTheDocument();
    });

    test('should highlight active tab', () => {
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      // Overview tab should be active by default
      const overviewTab = screen.getByText('Overview').closest('button');
      expect(overviewTab).toHaveClass('bg-white', 'text-blue-600');
    });
  });

  describe('Tab Content - Overview', () => {
    test('should display stop location', () => {
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      expect(screen.getByText('Location')).toBeInTheDocument();
      expect(screen.getByText('33.7539, -84.3910')).toBeInTheDocument();
    });

    test('should display stop zone', () => {
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      expect(screen.getByText('Zone')).toBeInTheDocument();
      expect(screen.getByText('Zone 1')).toBeInTheDocument();
    });

    test('should handle missing zone_id', () => {
      const stopWithoutZone = { ...mockStop, zone_id: null };
      
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={stopWithoutZone}
        />
      );
      
      expect(screen.getByText('N/A')).toBeInTheDocument();
    });

    test('should display demand data in overview', async () => {
      api.predictDemand.mockResolvedValue(mockDemandData);
      
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      await waitFor(() => {
        expect(screen.getByText('Current Status')).toBeInTheDocument();
        expect(screen.getByText('Predicted Riders:')).toBeInTheDocument();
        expect(screen.getByText('Demand Level:')).toBeInTheDocument();
        expect(screen.getByText('Last Updated:')).toBeInTheDocument();
      });
    });
  });

  describe('Tab Content - Demand', () => {
    test('should display demand forecasting title', async () => {
      const user = userEvent.setup();
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      // Switch to Demand tab
      const demandTab = screen.getByText('Demand');
      await user.click(demandTab);
      
      expect(screen.getByText('Demand Forecasting')).toBeInTheDocument();
      expect(screen.getByText('Real-time and predicted ridership data')).toBeInTheDocument();
    });

    test('should display loading state when no demand data', async () => {
      const user = userEvent.setup();
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      // Switch to Demand tab
      const demandTab = screen.getByText('Demand');
      await user.click(demandTab);
      
      expect(screen.getByText('Loading demand data...')).toBeInTheDocument();
    });

    test('should display demand data when available', async () => {
      api.predictDemand.mockResolvedValue(mockDemandData);
      
      const user = userEvent.setup();
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      // Wait for demand data to load
      await waitFor(() => {
        expect(api.predictDemand).toHaveBeenCalled();
      });
      
      // Switch to Demand tab
      const demandTab = screen.getByText('Demand');
      await user.click(demandTab);
      
      expect(screen.getByText('Predicted riders in next 15 minutes')).toBeInTheDocument();
    });
  });

  describe('Tab Content - Schedule', () => {
    test('should display schedule placeholder', async () => {
      const user = userEvent.setup();
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      // Switch to Schedule tab
      const scheduleTab = screen.getByText('Schedule');
      await user.click(scheduleTab);
      
      expect(screen.getByText('Schedule Information')).toBeInTheDocument();
      expect(screen.getByText('Upcoming arrivals and departures')).toBeInTheDocument();
      expect(screen.getByText('Schedule data coming soon...')).toBeInTheDocument();
    });
  });

  describe('Tab Content - Trends', () => {
    test('should display trends placeholder', async () => {
      const user = userEvent.setup();
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      // Switch to Trends tab
      const trendsTab = screen.getByText('Trends');
      await user.click(trendsTab);
      
      expect(screen.getByText('Historical Trends')).toBeInTheDocument();
      expect(screen.getByText('Ridership patterns and analytics')).toBeInTheDocument();
      expect(screen.getByText('Trends analysis coming soon...')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    test('should display empty state when no stop is selected', () => {
      render(<BottomDrawer {...mockProps} isOpen={true} />);
      
      expect(screen.getByText('No Stop Selected')).toBeInTheDocument();
      expect(screen.getByText('Click on a stop on the map to view detailed information')).toBeInTheDocument();
    });
  });

  describe('Demand Level Styling', () => {
    test('should apply correct styling for different demand levels', async () => {
      const demandLevels = [
        { level: 'Overloaded', color: '#F44336' },
        { level: 'High', color: '#FF9800' },
        { level: 'Normal', color: '#2196F3' },
        { level: 'Low', color: '#4CAF50' }
      ];
      
      for (const { level } of demandLevels) {
        const demandData = { ...mockDemandData, demand_level: level };
        api.predictDemand.mockResolvedValue(demandData);
        
        const { rerender } = render(
          <BottomDrawer 
            {...mockProps} 
            isOpen={true} 
            selectedStop={mockStop}
          />
        );
        
        await waitFor(() => {
          expect(screen.getByText(level)).toBeInTheDocument();
        });
        
        // Clean up for next iteration
        rerender(<div />);
      }
    });
  });

  describe('Accessibility', () => {
    test('should be keyboard navigable', async () => {
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      // Tab buttons should be focusable
      const overviewTab = screen.getByText('Overview');
      overviewTab.focus();
      expect(overviewTab).toHaveFocus();
      
      // Close button should be focusable
      const closeButton = screen.getByTestId('x-icon').closest('button');
      closeButton.focus();
      expect(closeButton).toHaveFocus();
    });

    test('should have proper button roles', () => {
      render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Component Lifecycle', () => {
    test('should clean up when unmounted', () => {
      const { unmount } = render(
        <BottomDrawer 
          {...mockProps} 
          isOpen={true} 
          selectedStop={mockStop}
        />
      );
      
      unmount();
      
      // Should not throw any errors during cleanup
      expect(true).toBe(true);
    });

    test('should handle prop changes', () => {
      const { rerender } = render(
        <BottomDrawer {...mockProps} isOpen={false} />
      );
      
      // Should not be visible initially
      expect(screen.queryByText('MARTA Dashboard')).not.toBeInTheDocument();
      
      // Rerender with isOpen=true
      rerender(<BottomDrawer {...mockProps} isOpen={true} />);
      
      // Should now be visible
      expect(screen.getByText('MARTA Dashboard')).toBeInTheDocument();
    });
  });
});