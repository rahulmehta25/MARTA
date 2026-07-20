export interface StationAnalytics {
  stationId: string;
  name: string;
  dailyRidership: number;
  hourlyPattern: number[];
  peakHours: string[];
  predictedDemand: number;
  crowdingLevel: 'low' | 'moderate' | 'high';
  onTimeRate: number;
}

const RUSH_PATTERN = [
  0.08, 0.04, 0.03, 0.02, 0.04, 0.12, 0.42, 0.88, 1.0, 0.68,
  0.45, 0.38, 0.42, 0.38, 0.45, 0.58, 0.82, 1.0, 0.78, 0.45,
  0.28, 0.18, 0.12, 0.08,
];

const AIRPORT_PATTERN = [
  0.3, 0.22, 0.15, 0.12, 0.18, 0.32, 0.52, 0.7, 0.82, 0.78,
  0.72, 0.75, 0.8, 0.85, 0.9, 0.92, 1.0, 0.95, 0.88, 0.78,
  0.65, 0.55, 0.45, 0.35,
];

const SUBURBAN_PATTERN = [
  0.05, 0.02, 0.02, 0.02, 0.05, 0.15, 0.55, 0.92, 1.0, 0.58,
  0.3, 0.22, 0.28, 0.22, 0.3, 0.52, 0.88, 1.0, 0.65, 0.32,
  0.18, 0.1, 0.08, 0.05,
];

interface StationConfig {
  name: string;
  base: number;
  pattern: number[];
  crowding: 'low' | 'moderate' | 'high';
  onTime: number;
}

const configs: Record<string, StationConfig> = {
  AIRPORT: { name: 'Airport', base: 11200, pattern: AIRPORT_PATTERN, crowding: 'high', onTime: 0.91 },
  COLLEGE_PARK: { name: 'College Park', base: 4200, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.93 },
  EAST_POINT: { name: 'East Point', base: 4800, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.94 },
  LAKEWOOD: { name: 'Lakewood/Ft McPherson', base: 3200, pattern: SUBURBAN_PATTERN, crowding: 'low', onTime: 0.95 },
  OAKLAND_CITY: { name: 'Oakland City', base: 3000, pattern: SUBURBAN_PATTERN, crowding: 'low', onTime: 0.95 },
  WEST_END: { name: 'West End', base: 5100, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.94 },
  GARNETT: { name: 'Garnett', base: 4500, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.95 },
  FIVE_POINTS: { name: 'Five Points', base: 15800, pattern: RUSH_PATTERN, crowding: 'high', onTime: 0.92 },
  PEACHTREE_CENTER: { name: 'Peachtree Center', base: 12400, pattern: RUSH_PATTERN, crowding: 'high', onTime: 0.93 },
  CIVIC_CENTER: { name: 'Civic Center', base: 6800, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.94 },
  NORTH_AVE: { name: 'North Avenue', base: 5500, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.94 },
  MIDTOWN: { name: 'Midtown', base: 9200, pattern: RUSH_PATTERN, crowding: 'high', onTime: 0.93 },
  ARTS_CENTER: { name: 'Arts Center', base: 7400, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.94 },
  LINDBERGH: { name: 'Lindbergh Center', base: 8900, pattern: RUSH_PATTERN, crowding: 'high', onTime: 0.93 },
  BUCKHEAD: { name: 'Buckhead', base: 8200, pattern: RUSH_PATTERN, crowding: 'high', onTime: 0.94 },
  MEDICAL_CENTER: { name: 'Medical Center', base: 5800, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.95 },
  DUNWOODY: { name: 'Dunwoody', base: 6500, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.95 },
  SANDY_SPRINGS: { name: 'Sandy Springs', base: 5200, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.96 },
  NORTH_SPRINGS: { name: 'North Springs', base: 4800, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.96 },
  LENOX: { name: 'Lenox', base: 7800, pattern: RUSH_PATTERN, crowding: 'high', onTime: 0.94 },
  BROOKHAVEN: { name: 'Brookhaven/Oglethorpe', base: 4500, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.95 },
  CHAMBLEE: { name: 'Chamblee', base: 4200, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.95 },
  DORAVILLE: { name: 'Doraville', base: 5100, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.95 },
  HAMILTON_HOLMES: { name: 'H.E. Holmes', base: 4800, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.94 },
  WEST_LAKE: { name: 'West Lake', base: 3500, pattern: SUBURBAN_PATTERN, crowding: 'low', onTime: 0.95 },
  ASHBY: { name: 'Ashby', base: 4200, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.94 },
  VINE_CITY: { name: 'Vine City', base: 3800, pattern: RUSH_PATTERN, crowding: 'low', onTime: 0.95 },
  GEORGIA_STATE: { name: 'Georgia State', base: 7200, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.93 },
  KING_MEMORIAL: { name: 'King Memorial', base: 4800, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.94 },
  INMAN_PARK: { name: 'Inman Park/Reynoldstown', base: 5200, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.94 },
  EDGEWOOD: { name: 'Edgewood/Candler Park', base: 4500, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.95 },
  EAST_LAKE: { name: 'East Lake', base: 3800, pattern: SUBURBAN_PATTERN, crowding: 'low', onTime: 0.95 },
  DECATUR: { name: 'Decatur', base: 6200, pattern: RUSH_PATTERN, crowding: 'moderate', onTime: 0.94 },
  AVONDALE: { name: 'Avondale', base: 4200, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.95 },
  KENSINGTON: { name: 'Kensington', base: 3500, pattern: SUBURBAN_PATTERN, crowding: 'low', onTime: 0.96 },
  INDIAN_CREEK: { name: 'Indian Creek', base: 4100, pattern: SUBURBAN_PATTERN, crowding: 'moderate', onTime: 0.96 },
  BANKHEAD: { name: 'Bankhead', base: 3200, pattern: SUBURBAN_PATTERN, crowding: 'low', onTime: 0.95 },
};

function buildAnalytics(id: string, cfg: StationConfig): StationAnalytics {
  const maxHourly = cfg.base / 10;
  const hourly = cfg.pattern.map((p) => Math.round(p * maxHourly));
  const peakHours: string[] = [];
  cfg.pattern.forEach((p, i) => {
    if (p >= 0.85) peakHours.push(`${i}:00`);
  });
  return {
    stationId: id,
    name: cfg.name,
    dailyRidership: cfg.base,
    hourlyPattern: hourly,
    peakHours,
    predictedDemand: Math.round(cfg.base * (0.95 + Math.random() * 0.1)),
    crowdingLevel: cfg.crowding,
    onTimeRate: cfg.onTime,
  };
}

export const stationAnalyticsMap: Record<string, StationAnalytics> = {};
Object.entries(configs).forEach(([id, cfg]) => {
  stationAnalyticsMap[id] = buildAnalytics(id, cfg);
});

export function getStationAnalytics(id: string): StationAnalytics | undefined {
  return stationAnalyticsMap[id];
}

export function getDemandAtHour(stationId: string, hour: number): number {
  const a = stationAnalyticsMap[stationId];
  if (!a) return 0;
  return a.hourlyPattern[Math.floor(hour) % 24];
}

export function getLSTMPrediction(stationId: string): number[] {
  const a = stationAnalyticsMap[stationId];
  if (!a) return Array(24).fill(0);
  return a.hourlyPattern.map((v) => Math.round(v * (0.88 + Math.random() * 0.24)));
}

export const stationPositions: Record<string, { x: number; y: number }> = {
  AIRPORT: { x: 480, y: 750 },
  COLLEGE_PARK: { x: 480, y: 710 },
  EAST_POINT: { x: 480, y: 675 },
  LAKEWOOD: { x: 480, y: 640 },
  OAKLAND_CITY: { x: 480, y: 605 },
  WEST_END: { x: 480, y: 570 },
  GARNETT: { x: 480, y: 530 },
  FIVE_POINTS: { x: 480, y: 460 },
  PEACHTREE_CENTER: { x: 480, y: 420 },
  CIVIC_CENTER: { x: 480, y: 385 },
  NORTH_AVE: { x: 480, y: 350 },
  MIDTOWN: { x: 480, y: 315 },
  ARTS_CENTER: { x: 480, y: 280 },
  LINDBERGH: { x: 480, y: 230 },
  BUCKHEAD: { x: 480, y: 180 },
  MEDICAL_CENTER: { x: 480, y: 145 },
  DUNWOODY: { x: 480, y: 110 },
  SANDY_SPRINGS: { x: 480, y: 75 },
  NORTH_SPRINGS: { x: 480, y: 40 },
  LENOX: { x: 555, y: 195 },
  BROOKHAVEN: { x: 625, y: 160 },
  CHAMBLEE: { x: 695, y: 125 },
  DORAVILLE: { x: 765, y: 90 },
  HAMILTON_HOLMES: { x: 60, y: 460 },
  WEST_LAKE: { x: 130, y: 460 },
  ASHBY: { x: 210, y: 460 },
  VINE_CITY: { x: 300, y: 460 },
  GEORGIA_STATE: { x: 560, y: 460 },
  KING_MEMORIAL: { x: 630, y: 460 },
  INMAN_PARK: { x: 700, y: 460 },
  EDGEWOOD: { x: 765, y: 460 },
  EAST_LAKE: { x: 825, y: 460 },
  DECATUR: { x: 880, y: 460 },
  AVONDALE: { x: 930, y: 460 },
  KENSINGTON: { x: 975, y: 460 },
  INDIAN_CREEK: { x: 1020, y: 460 },
  BANKHEAD: { x: 150, y: 395 },
};

export const ADJACENCY: Record<string, string[]> = {};
const LINES = {
  RED: ['AIRPORT','COLLEGE_PARK','EAST_POINT','LAKEWOOD','OAKLAND_CITY','WEST_END','GARNETT','FIVE_POINTS','PEACHTREE_CENTER','CIVIC_CENTER','NORTH_AVE','MIDTOWN','ARTS_CENTER','LINDBERGH','BUCKHEAD','MEDICAL_CENTER','DUNWOODY','SANDY_SPRINGS','NORTH_SPRINGS'],
  GOLD: ['AIRPORT','COLLEGE_PARK','EAST_POINT','LAKEWOOD','OAKLAND_CITY','WEST_END','GARNETT','FIVE_POINTS','PEACHTREE_CENTER','CIVIC_CENTER','NORTH_AVE','MIDTOWN','ARTS_CENTER','LINDBERGH','LENOX','BROOKHAVEN','CHAMBLEE','DORAVILLE'],
  BLUE: ['HAMILTON_HOLMES','WEST_LAKE','ASHBY','VINE_CITY','FIVE_POINTS','GEORGIA_STATE','KING_MEMORIAL','INMAN_PARK','EDGEWOOD','EAST_LAKE','DECATUR','AVONDALE','KENSINGTON','INDIAN_CREEK'],
  GREEN: ['BANKHEAD','ASHBY','VINE_CITY','FIVE_POINTS','GEORGIA_STATE','KING_MEMORIAL','INMAN_PARK','EDGEWOOD'],
};

Object.values(LINES).forEach((stops) => {
  for (let i = 0; i < stops.length - 1; i++) {
    const a = stops[i], b = stops[i + 1];
    if (!ADJACENCY[a]) ADJACENCY[a] = [];
    if (!ADJACENCY[b]) ADJACENCY[b] = [];
    if (!ADJACENCY[a].includes(b)) ADJACENCY[a].push(b);
    if (!ADJACENCY[b].includes(a)) ADJACENCY[b].push(a);
  }
});

export function findRoute(from: string, to: string): string[] | null {
  if (from === to) return [from];
  const visited = new Set<string>();
  const queue: string[][] = [[from]];
  visited.add(from);
  while (queue.length > 0) {
    const path = queue.shift()!;
    const current = path[path.length - 1];
    for (const neighbor of ADJACENCY[current] || []) {
      if (neighbor === to) return [...path, neighbor];
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([...path, neighbor]);
      }
    }
  }
  return null;
}

export function getLineForSegment(a: string, b: string): string {
  for (const [line, stops] of Object.entries(LINES)) {
    for (let i = 0; i < stops.length - 1; i++) {
      if ((stops[i] === a && stops[i + 1] === b) || (stops[i] === b && stops[i + 1] === a)) {
        return line;
      }
    }
  }
  return 'BLUE';
}

export const LINE_COLORS: Record<string, string> = {
  RED: '#E53935',
  GOLD: '#F9A825',
  BLUE: '#1E88E5',
  GREEN: '#43A047',
};

export { LINES };
