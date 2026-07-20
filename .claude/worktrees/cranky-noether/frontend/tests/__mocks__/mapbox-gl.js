// Mock Mapbox GL for testing
const mapboxgl = {
  Map: jest.fn().mockImplementation(() => ({
    on: jest.fn(),
    off: jest.fn(),
    remove: jest.fn(),
    addSource: jest.fn(),
    removeSource: jest.fn(),
    addLayer: jest.fn(),
    removeLayer: jest.fn(),
    setLayoutProperty: jest.fn(),
    setPaintProperty: jest.fn(),
    flyTo: jest.fn(),
    fitBounds: jest.fn(),
    getBounds: jest.fn(),
    getZoom: jest.fn(),
    getCenter: jest.fn(),
    resize: jest.fn()
  })),
  
  Marker: jest.fn().mockImplementation(() => ({
    setLngLat: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn().mockReturnThis(),
    setPopup: jest.fn().mockReturnThis()
  })),
  
  Popup: jest.fn().mockImplementation(() => ({
    setLngLat: jest.fn().mockReturnThis(),
    setHTML: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn().mockReturnThis()
  })),
  
  NavigationControl: jest.fn(),
  GeolocateControl: jest.fn(),
  ScaleControl: jest.fn(),
  
  supported: jest.fn(() => true),
  accessToken: '',
  
  LngLat: jest.fn().mockImplementation((lng, lat) => ({ lng, lat })),
  LngLatBounds: jest.fn()
};

export default mapboxgl;