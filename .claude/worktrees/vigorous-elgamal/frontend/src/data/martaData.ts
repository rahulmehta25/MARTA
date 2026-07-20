// Real MARTA system data
export interface Stop {
  id: string;
  name: string;
  lat: number;
  lng: number;
  routes: string[];
  type: 'rail' | 'bus';
  accessibility: boolean;
  parking: boolean;
}

export interface Route {
  id: string;
  name: string;
  color: string;
  type: 'rail' | 'bus';
  stops: string[];
  coordinates: [number, number][];
}

// MARTA Rail Stations
export const martaStops: Stop[] = [
  // Red Line (North-South)
  { id: 'AIRPORT', name: 'Airport', lat: 33.6407, lng: -84.4462, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: true },
  { id: 'COLLEGE_PARK', name: 'College Park', lat: 33.6514, lng: -84.4486, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: true },
  { id: 'EAST_POINT', name: 'East Point', lat: 33.6766, lng: -84.4402, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: true },
  { id: 'LAKEWOOD', name: 'Lakewood/Fort McPherson', lat: 33.7005, lng: -84.4291, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: true },
  { id: 'OAKLAND_CITY', name: 'Oakland City', lat: 33.7172, lng: -84.4252, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: false },
  { id: 'WEST_END', name: 'West End', lat: 33.7359, lng: -84.4139, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: false },
  { id: 'GARNETT', name: 'Garnett', lat: 33.7480, lng: -84.3959, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: false },
  { id: 'FIVE_POINTS', name: 'Five Points', lat: 33.7537, lng: -84.3918, routes: ['RED', 'GOLD', 'BLUE', 'GREEN'], type: 'rail', accessibility: true, parking: false },
  { id: 'PEACHTREE_CENTER', name: 'Peachtree Center', lat: 33.7596, lng: -84.3875, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: false },
  { id: 'CIVIC_CENTER', name: 'Civic Center', lat: 33.7664, lng: -84.3869, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: false },
  { id: 'NORTH_AVE', name: 'North Avenue', lat: 33.7718, lng: -84.3854, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: false },
  { id: 'MIDTOWN', name: 'Midtown', lat: 33.7806, lng: -84.3831, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: false },
  { id: 'ARTS_CENTER', name: 'Arts Center', lat: 33.7891, lng: -84.3871, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: false },
  { id: 'LINDBERGH', name: 'Lindbergh Center', lat: 33.8230, lng: -84.3694, routes: ['RED', 'GOLD'], type: 'rail', accessibility: true, parking: true },
  { id: 'BUCKHEAD', name: 'Buckhead', lat: 33.8484, lng: -84.3671, routes: ['RED'], type: 'rail', accessibility: true, parking: true },
  { id: 'MEDICAL_CENTER', name: 'Medical Center', lat: 33.9106, lng: -84.3513, routes: ['RED'], type: 'rail', accessibility: true, parking: true },
  { id: 'DUNWOODY', name: 'Dunwoody', lat: 33.9211, lng: -84.3444, routes: ['RED'], type: 'rail', accessibility: true, parking: true },
  { id: 'SANDY_SPRINGS', name: 'Sandy Springs', lat: 33.9318, lng: -84.3507, routes: ['RED'], type: 'rail', accessibility: true, parking: true },
  { id: 'NORTH_SPRINGS', name: 'North Springs', lat: 33.9458, lng: -84.3567, routes: ['RED'], type: 'rail', accessibility: true, parking: true },
  
  // Gold Line (Northeast)
  { id: 'LENOX', name: 'Lenox', lat: 33.8470, lng: -84.3570, routes: ['GOLD'], type: 'rail', accessibility: true, parking: true },
  { id: 'BROOKHAVEN', name: 'Brookhaven/Oglethorpe', lat: 33.8598, lng: -84.3394, routes: ['GOLD'], type: 'rail', accessibility: true, parking: true },
  { id: 'CHAMBLEE', name: 'Chamblee', lat: 33.8872, lng: -84.3074, routes: ['GOLD'], type: 'rail', accessibility: true, parking: true },
  { id: 'DORAVILLE', name: 'Doraville', lat: 33.9026, lng: -84.2803, routes: ['GOLD'], type: 'rail', accessibility: true, parking: true },
  
  // Blue Line (West-East)
  { id: 'HAMILTON_HOLMES', name: 'H.E. Holmes', lat: 33.7545, lng: -84.4701, routes: ['BLUE'], type: 'rail', accessibility: true, parking: true },
  { id: 'WEST_LAKE', name: 'West Lake', lat: 33.7532, lng: -84.4453, routes: ['BLUE'], type: 'rail', accessibility: true, parking: true },
  { id: 'ASHBY', name: 'Ashby', lat: 33.7564, lng: -84.4169, routes: ['BLUE', 'GREEN'], type: 'rail', accessibility: true, parking: true },
  { id: 'VINE_CITY', name: 'Vine City', lat: 33.7569, lng: -84.4041, routes: ['BLUE', 'GREEN'], type: 'rail', accessibility: true, parking: false },
  { id: 'GEORGIA_STATE', name: 'Georgia State', lat: 33.7502, lng: -84.3860, routes: ['BLUE', 'GREEN'], type: 'rail', accessibility: true, parking: false },
  { id: 'KING_MEMORIAL', name: 'King Memorial', lat: 33.7501, lng: -84.3754, routes: ['BLUE', 'GREEN'], type: 'rail', accessibility: true, parking: false },
  { id: 'INMAN_PARK', name: 'Inman Park/Reynoldstown', lat: 33.7577, lng: -84.3528, routes: ['BLUE', 'GREEN'], type: 'rail', accessibility: true, parking: true },
  { id: 'EDGEWOOD', name: 'Edgewood/Candler Park', lat: 33.7619, lng: -84.3396, routes: ['BLUE', 'GREEN'], type: 'rail', accessibility: true, parking: true },
  { id: 'EAST_LAKE', name: 'East Lake', lat: 33.7651, lng: -84.3127, routes: ['BLUE'], type: 'rail', accessibility: true, parking: true },
  { id: 'DECATUR', name: 'Decatur', lat: 33.7746, lng: -84.2958, routes: ['BLUE'], type: 'rail', accessibility: true, parking: false },
  { id: 'AVONDALE', name: 'Avondale', lat: 33.7750, lng: -84.2821, routes: ['BLUE'], type: 'rail', accessibility: true, parking: true },
  { id: 'KENSINGTON', name: 'Kensington', lat: 33.7727, lng: -84.2520, routes: ['BLUE'], type: 'rail', accessibility: true, parking: true },
  { id: 'INDIAN_CREEK', name: 'Indian Creek', lat: 33.7698, lng: -84.2297, routes: ['BLUE'], type: 'rail', accessibility: true, parking: true },
  
  // Green Line (Bankhead to Edgewood)
  { id: 'BANKHEAD', name: 'Bankhead', lat: 33.7720, lng: -84.4288, routes: ['GREEN'], type: 'rail', accessibility: true, parking: true },
];

// MARTA Rail Routes
export const martaRoutes: Route[] = [
  {
    id: 'RED',
    name: 'Red Line',
    color: '#FF0000',
    type: 'rail',
    stops: ['AIRPORT', 'COLLEGE_PARK', 'EAST_POINT', 'LAKEWOOD', 'OAKLAND_CITY', 'WEST_END', 'GARNETT', 'FIVE_POINTS', 
            'PEACHTREE_CENTER', 'CIVIC_CENTER', 'NORTH_AVE', 'MIDTOWN', 'ARTS_CENTER', 'LINDBERGH', 'BUCKHEAD', 
            'MEDICAL_CENTER', 'DUNWOODY', 'SANDY_SPRINGS', 'NORTH_SPRINGS'],
    coordinates: [] // Will be generated from stops
  },
  {
    id: 'GOLD',
    name: 'Gold Line',
    color: '#FFB500',
    type: 'rail',
    stops: ['AIRPORT', 'COLLEGE_PARK', 'EAST_POINT', 'LAKEWOOD', 'OAKLAND_CITY', 'WEST_END', 'GARNETT', 'FIVE_POINTS',
            'PEACHTREE_CENTER', 'CIVIC_CENTER', 'NORTH_AVE', 'MIDTOWN', 'ARTS_CENTER', 'LINDBERGH', 'LENOX', 
            'BROOKHAVEN', 'CHAMBLEE', 'DORAVILLE'],
    coordinates: []
  },
  {
    id: 'BLUE',
    name: 'Blue Line',
    color: '#0066CC',
    type: 'rail',
    stops: ['HAMILTON_HOLMES', 'WEST_LAKE', 'ASHBY', 'VINE_CITY', 'FIVE_POINTS', 'GEORGIA_STATE', 'KING_MEMORIAL',
            'INMAN_PARK', 'EDGEWOOD', 'EAST_LAKE', 'DECATUR', 'AVONDALE', 'KENSINGTON', 'INDIAN_CREEK'],
    coordinates: []
  },
  {
    id: 'GREEN',
    name: 'Green Line',
    color: '#00AA00',
    type: 'rail',
    stops: ['BANKHEAD', 'ASHBY', 'VINE_CITY', 'FIVE_POINTS', 'GEORGIA_STATE', 'KING_MEMORIAL', 
            'INMAN_PARK', 'EDGEWOOD'],
    coordinates: []
  }
];

// Generate route coordinates from stops
martaRoutes.forEach(route => {
  route.coordinates = route.stops
    .map(stopId => {
      const stop = martaStops.find(s => s.id === stopId);
      return stop ? [stop.lng, stop.lat] : null;
    })
    .filter(coord => coord !== null) as [number, number][];
});

// Search helpers
export function searchStops(query: string): Stop[] {
  const lowerQuery = query.toLowerCase();
  return martaStops.filter(stop => 
    stop.name.toLowerCase().includes(lowerQuery) ||
    stop.routes.some(route => route.toLowerCase().includes(lowerQuery))
  );
}

export function getStopsByRoute(routeId: string): Stop[] {
  return martaStops.filter(stop => stop.routes.includes(routeId));
}

export function getRoutesByStop(stopId: string): Route[] {
  const stop = martaStops.find(s => s.id === stopId);
  if (!stop) return [];
  return martaRoutes.filter(route => stop.routes.includes(route.id));
}