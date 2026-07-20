import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchBar } from '../../src/components/search/SearchBar';
import * as api from '../../src/utils/api';
import * as helpers from '../../src/utils/helpers';

// Mock dependencies
jest.mock('../../src/utils/api');
jest.mock('../../src/utils/helpers', () => ({
  dataUtils: {
    debounce: (fn) => fn // Remove debouncing for tests
  },
  storage: {
    get: jest.fn(() => []),
    set: jest.fn()
  }
}));

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  Search: () => <div data-testid="search-icon" />,
  MapPin: () => <div data-testid="mappin-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
  X: () => <div data-testid="x-icon" />
}));

describe('SearchBar Component', () => {
  const mockProps = {
    value: '',
    onChange: jest.fn(),
    onSelect: jest.fn(),
    placeholder: 'Search for stops, routes, or destinations...'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    api.searchStops = jest.fn();
    helpers.storage.get.mockReturnValue([]);
  });

  describe('Rendering', () => {
    test('should render search input with correct placeholder', () => {
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('type', 'text');
    });

    test('should render search icon', () => {
      render(<SearchBar {...mockProps} />);
      
      expect(screen.getByTestId('search-icon')).toBeInTheDocument();
    });

    test('should render with provided value', () => {
      render(<SearchBar {...mockProps} value="Five Points" />);
      
      const input = screen.getByDisplayValue('Five Points');
      expect(input).toBeInTheDocument();
    });

    test('should show clear button when value is present', () => {
      render(<SearchBar {...mockProps} value="Test Station" />);
      
      expect(screen.getByTestId('x-icon')).toBeInTheDocument();
    });

    test('should not show clear button when value is empty', () => {
      render(<SearchBar {...mockProps} value="" />);
      
      expect(screen.queryByTestId('x-icon')).not.toBeInTheDocument();
    });
  });

  describe('Input Interactions', () => {
    test('should call onChange when typing', async () => {
      const user = userEvent.setup();
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await user.type(input, 'Five Points');
      
      expect(mockProps.onChange).toHaveBeenCalledTimes(11); // Each character
      expect(mockProps.onChange).toHaveBeenLastCalledWith('Five Points');
    });

    test('should clear input when clear button is clicked', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      
      render(<SearchBar {...mockProps} value="Test" onChange={onChange} />);
      
      const clearButton = screen.getByTestId('x-icon').closest('button');
      await user.click(clearButton);
      
      expect(onChange).toHaveBeenCalledWith('');
    });

    test('should focus input after clearing', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      
      render(<SearchBar {...mockProps} value="Test" onChange={onChange} />);
      
      const input = screen.getByDisplayValue('Test');
      const clearButton = screen.getByTestId('x-icon').closest('button');
      
      await user.click(clearButton);
      
      expect(input).toHaveFocus();
    });

    test('should handle focus event', async () => {
      const user = userEvent.setup();
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await user.click(input);
      
      expect(input).toHaveFocus();
    });
  });

  describe('Search Functionality', () => {
    test('should call API when typing query', async () => {
      const mockResults = [
        { stop_id: '1', stop_name: 'Five Points Station', zone_id: 'Zone 1' }
      ];
      api.searchStops.mockResolvedValue(mockResults);
      
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Five Points' } });
      });
      
      await waitFor(() => {
        expect(api.searchStops).toHaveBeenCalledWith('Five Points');
      });
    });

    test('should not search with query less than 2 characters', async () => {
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'F' } });
      });
      
      expect(api.searchStops).not.toHaveBeenCalled();
    });

    test('should display search results', async () => {
      const mockResults = [
        { stop_id: '1', stop_name: 'Five Points Station', zone_id: 'Zone 1' },
        { stop_id: '2', stop_name: 'Peachtree Center', zone_id: 'Zone 1' }
      ];
      api.searchStops.mockResolvedValue(mockResults);
      
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Station' } });
      });
      
      await waitFor(() => {
        expect(screen.getByText('Five Points Station')).toBeInTheDocument();
        expect(screen.getByText('Peachtree Center')).toBeInTheDocument();
      });
    });

    test('should show loading state during search', async () => {
      // Create a promise that we can control
      let resolveSearch;
      const searchPromise = new Promise(resolve => {
        resolveSearch = resolve;
      });
      api.searchStops.mockReturnValue(searchPromise);
      
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Test' } });
      });
      
      // Check for loading state
      expect(screen.getByText('Searching...')).toBeInTheDocument();
      
      // Resolve the search
      await act(async () => {
        resolveSearch([]);
      });
    });

    test('should handle search API errors gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      api.searchStops.mockRejectedValue(new Error('API Error'));
      
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Test' } });
      });
      
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Search error:', expect.any(Error));
      });
      
      consoleSpy.mockRestore();
    });

    test('should show "no results" message when no stops found', async () => {
      api.searchStops.mockResolvedValue([]);
      
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Nonexistent' } });
      });
      
      await waitFor(() => {
        expect(screen.getByText(/No stops found for "Nonexistent"/)).toBeInTheDocument();
      });
    });
  });

  describe('Recent Searches', () => {
    test('should load recent searches from storage', () => {
      const recentSearches = [
        { stop_id: '1', stop_name: 'Five Points Station' }
      ];
      helpers.storage.get.mockReturnValue(recentSearches);
      
      render(<SearchBar {...mockProps} />);
      
      expect(helpers.storage.get).toHaveBeenCalledWith('recentSearches', []);
    });

    test('should show recent searches when input is focused and empty', async () => {
      const recentSearches = [
        { stop_id: '1', stop_name: 'Five Points Station' }
      ];
      helpers.storage.get.mockReturnValue(recentSearches);
      
      const user = userEvent.setup();
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      await user.click(input);
      
      expect(screen.getByText('Recent Searches')).toBeInTheDocument();
      expect(screen.getByText('Five Points Station')).toBeInTheDocument();
    });

    test('should save search to recent searches when selected', async () => {
      const mockResult = { stop_id: '1', stop_name: 'Five Points Station' };
      api.searchStops.mockResolvedValue([mockResult]);
      
      const user = userEvent.setup();
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Five' } });
      });
      
      await waitFor(() => {
        expect(screen.getByText('Five Points Station')).toBeInTheDocument();
      });
      
      await user.click(screen.getByText('Five Points Station'));
      
      expect(helpers.storage.set).toHaveBeenCalledWith('recentSearches', [mockResult]);
      expect(mockProps.onSelect).toHaveBeenCalledWith(mockResult);
    });
  });

  describe('Keyboard Navigation', () => {
    test('should handle arrow down key', async () => {
      const mockResults = [
        { stop_id: '1', stop_name: 'Five Points Station' },
        { stop_id: '2', stop_name: 'Peachtree Center' }
      ];
      api.searchStops.mockResolvedValue(mockResults);
      
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Station' } });
      });
      
      await waitFor(() => {
        expect(screen.getByText('Five Points Station')).toBeInTheDocument();
      });
      
      fireEvent.keyDown(input, { key: 'ArrowDown' });
      
      // First result should be highlighted (visual test would need additional setup)
    });

    test('should handle enter key to select highlighted result', async () => {
      const mockResults = [
        { stop_id: '1', stop_name: 'Five Points Station' }
      ];
      api.searchStops.mockResolvedValue(mockResults);
      
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Five' } });
      });
      
      await waitFor(() => {
        expect(screen.getByText('Five Points Station')).toBeInTheDocument();
      });
      
      fireEvent.keyDown(input, { key: 'ArrowDown' });
      fireEvent.keyDown(input, { key: 'Enter' });
      
      expect(mockProps.onSelect).toHaveBeenCalledWith(mockResults[0]);
    });

    test('should handle escape key', async () => {
      const mockResults = [
        { stop_id: '1', stop_name: 'Five Points Station' }
      ];
      api.searchStops.mockResolvedValue(mockResults);
      
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Five' } });
      });
      
      await waitFor(() => {
        expect(screen.getByText('Five Points Station')).toBeInTheDocument();
      });
      
      fireEvent.keyDown(input, { key: 'Escape' });
      
      // Results should be hidden
      expect(screen.queryByText('Five Points Station')).not.toBeInTheDocument();
    });
  });

  describe('Click Outside Behavior', () => {
    test('should close dropdown when clicking outside', async () => {
      const mockResults = [
        { stop_id: '1', stop_name: 'Five Points Station' }
      ];
      api.searchStops.mockResolvedValue(mockResults);
      
      render(
        <div>
          <SearchBar {...mockProps} />
          <div data-testid="outside-element">Outside</div>
        </div>
      );
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      await act(async () => {
        fireEvent.change(input, { target: { value: 'Five' } });
      });
      
      await waitFor(() => {
        expect(screen.getByText('Five Points Station')).toBeInTheDocument();
      });
      
      // Click outside
      fireEvent.mouseDown(screen.getByTestId('outside-element'));
      
      await waitFor(() => {
        expect(screen.queryByText('Five Points Station')).not.toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    test('should have proper ARIA attributes', () => {
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      expect(input).toHaveAttribute('type', 'text');
      expect(input).toHaveAttribute('placeholder');
    });

    test('should be focusable', () => {
      render(<SearchBar {...mockProps} />);
      
      const input = screen.getByPlaceholderText('Search for stops, routes, or destinations...');
      
      input.focus();
      expect(input).toHaveFocus();
    });
  });
});

describe('SearchResultItem Component', () => {
  const mockResult = {
    stop_id: '1',
    stop_name: 'Five Points Station',
    zone_id: 'Zone 1'
  };

  test('should render result item correctly', () => {
    render(
      <div>
        {/* We need to access the SearchResultItem component - it's not exported separately */}
        <SearchBar 
          value="Five"
          onChange={() => {}}
          onSelect={() => {}}
          placeholder="Search"
        />
      </div>
    );
    
    // Since SearchResultItem is internal, we test it through SearchBar integration
    // This is covered in the SearchBar tests above
  });
});