import React, { useState, useRef, useEffect } from 'react';
import {
  MapPin,
  Navigation,
  Clock,
  ArrowRight,
  Train,
  Footprints,
  Zap,
  Users,
  AlertTriangle,
  CheckCircle2,
  ArrowUpDown,
  ChevronDown,
  Calendar,
  Star
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { searchStops } from '@/data/martaData';

interface TripStep {
  type: 'walk' | 'train';
  line?: string;
  from: string;
  to: string;
  duration: number;
  distance?: number;
  direction?: string;
  predictedArrival?: number;
}

interface TripOption {
  id: string;
  badge?: 'fastest' | 'recommended' | 'less_crowded';
  duration: number;
  walkingMinutes: number;
  transfers: number;
  steps: TripStep[];
  crowdingLevel: 1 | 2 | 3 | 4 | 5;
  delayRisk: number;
  mlConfidence: number;
  departureIn: number; // seconds until departure
}

const LINE_COLORS: Record<string, { bg: string; text: string; hex: string }> = {
  RED:   { bg: 'bg-red-500',   text: 'text-white', hex: '#EF4444' },
  GOLD:  { bg: 'bg-amber-500', text: 'text-white', hex: '#F59E0B' },
  BLUE:  { bg: 'bg-blue-600',  text: 'text-white', hex: '#0075BF' },
  GREEN: { bg: 'bg-green-600', text: 'text-white', hex: '#16A34A' },
};

const crowdingLabel = (level: number) => {
  if (level <= 1) return { text: 'Empty', color: 'text-green-700 bg-green-50' };
  if (level <= 2) return { text: 'Low', color: 'text-green-700 bg-green-50' };
  if (level <= 3) return { text: 'Moderate', color: 'text-amber-700 bg-amber-50' };
  if (level <= 4) return { text: 'Busy', color: 'text-orange-700 bg-orange-50' };
  return { text: 'Very busy', color: 'text-red-700 bg-red-50' };
};

const CrowdingDots: React.FC<{ level: number }> = ({ level }) => (
  <div className="flex items-center gap-0.5">
    {[1, 2, 3, 4, 5].map((n) => (
      <div
        key={n}
        className={`w-1.5 h-1.5 rounded-full ${
          n <= level
            ? level <= 2 ? 'bg-green-500' : level <= 3 ? 'bg-amber-500' : 'bg-red-500'
            : 'bg-gray-200'
        }`}
      />
    ))}
  </div>
);

interface StationInputProps {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  icon: React.ReactNode;
}

const StationInput: React.FC<StationInputProps> = ({ id, label, value, onChange, placeholder, icon }) => {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleChange = (v: string) => {
    onChange(v);
    if (v.length > 1) {
      const matches = searchStops(v)
        .slice(0, 6)
        .map((s) => s.name);
      setSuggestions(matches);
      setOpen(matches.length > 0);
    } else {
      setSuggestions([]);
      setOpen(false);
    }
  };

  return (
    <div id={`station-input-wrapper-${id}`} ref={ref} className="relative">
      <label htmlFor={id} className="block text-xs font-semibold text-gray-600 mb-1.5">
        {label}
      </label>
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">{icon}</div>
        <input
          id={id}
          type="text"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onFocus={() => {
            if (suggestions.length > 0) setOpen(true);
          }}
          placeholder={placeholder}
          className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={open}
          role="combobox"
        />
      </div>
      <AnimatePresence>
        {open && (
          <motion.ul
            id={`autocomplete-${id}`}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden"
            role="listbox"
          >
            {suggestions.map((s, i) => (
              <li
                key={i}
                id={`suggestion-${id}-${i}`}
                role="option"
                aria-selected={false}
                onClick={() => { onChange(s); setOpen(false); }}
                className="flex items-center gap-2.5 px-4 py-3 text-sm text-gray-800 hover:bg-blue-50 cursor-pointer transition-colors border-b border-gray-50 last:border-0"
              >
                <Train className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                {s}
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
};

const RouteOptionCard: React.FC<{
  option: TripOption;
  selected: boolean;
  onSelect: () => void;
  index: number;
}> = ({ option, selected, onSelect, index }) => {
  const [expanded, setExpanded] = useState(false);
  const crowding = crowdingLabel(option.crowdingLevel);

  const badgeConfig = {
    fastest: { text: 'Fastest', color: 'bg-blue-600 text-white' },
    recommended: { text: 'Recommended', color: 'bg-emerald-600 text-white' },
    less_crowded: { text: 'Less crowded', color: 'bg-purple-600 text-white' },
  };

  const departureMin = Math.floor(option.departureIn / 60);

  return (
    <motion.div
      id={`route-option-${option.id}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07 }}
      className={`border rounded-2xl overflow-hidden transition-all duration-200 cursor-pointer ${
        selected
          ? 'border-blue-500 shadow-md ring-2 ring-blue-100'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
      }`}
      onClick={onSelect}
      role="button"
      aria-pressed={selected}
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect()}
    >
      {/* Card header */}
      <div id={`route-option-header-${option.id}`} className="flex items-start gap-3 p-4 bg-white">
        {/* Duration */}
        <div id={`route-duration-${option.id}`} className="flex-shrink-0">
          <div className="text-3xl font-black text-gray-900 tabular-nums leading-none">
            {option.duration}
          </div>
          <div className="text-[11px] text-gray-500 font-medium mt-0.5">min</div>
        </div>

        {/* Route summary */}
        <div id={`route-summary-${option.id}`} className="flex-1 min-w-0">
          {/* Line chips */}
          <div className="flex items-center gap-1.5 flex-wrap mb-2">
            {option.badge && (
              <span
                id={`route-badge-${option.id}`}
                className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${badgeConfig[option.badge].color}`}
              >
                {badgeConfig[option.badge].text}
              </span>
            )}
            {option.steps
              .filter((s) => s.type === 'train')
              .map((s, i) => {
                const lc = LINE_COLORS[s.line?.toUpperCase() || ''] || LINE_COLORS.BLUE;
                return (
                  <span
                    key={i}
                    id={`route-line-chip-${option.id}-${i}`}
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${lc.bg} ${lc.text}`}
                  >
                    {s.line}
                  </span>
                );
              })}
          </div>

          {/* Stats row */}
          <div
            id={`route-stats-${option.id}`}
            className="flex items-center gap-3 text-xs text-gray-600 flex-wrap"
          >
            <span className="flex items-center gap-1">
              <ArrowRight className="w-3 h-3 text-gray-400" />
              {option.transfers === 0 ? 'Direct' : `${option.transfers} transfer${option.transfers > 1 ? 's' : ''}`}
            </span>
            <span className="flex items-center gap-1">
              <Footprints className="w-3 h-3 text-gray-400" />
              {option.walkingMinutes} min walk
            </span>
            <span className="flex items-center gap-1">
              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${crowding.color}`}>
                {crowding.text}
              </span>
              <CrowdingDots level={option.crowdingLevel} />
            </span>
          </div>
        </div>

        {/* Departure */}
        <div
          id={`route-departure-${option.id}`}
          className="flex-shrink-0 text-right"
        >
          <div className={`text-sm font-bold ${departureMin <= 3 ? 'text-amber-600' : 'text-gray-700'}`}>
            {departureMin <= 0 ? 'Now' : `${departureMin} min`}
          </div>
          <div className="text-[10px] text-gray-400">departs</div>
          {option.delayRisk > 0.15 && (
            <div
              id={`route-delay-risk-${option.id}`}
              className="flex items-center gap-0.5 text-[10px] text-amber-600 mt-0.5"
            >
              <AlertTriangle className="w-3 h-3" />
              {Math.round(option.delayRisk * 100)}% delay risk
            </div>
          )}
        </div>
      </div>

      {/* Expandable steps */}
      <AnimatePresence>
        {selected && (
          <motion.div
            id={`route-steps-${option.id}`}
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-gray-100"
          >
            <div className="px-4 py-3 bg-gray-50 space-y-2">
              {option.steps.map((step, si) => (
                <div
                  key={si}
                  id={`route-step-${option.id}-${si}`}
                  className="flex items-center gap-3"
                >
                  {step.type === 'walk' ? (
                    <>
                      <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                        <Footprints className="w-4 h-4 text-gray-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold text-gray-800">
                          Walk to {step.to}
                        </div>
                        <div className="text-[11px] text-gray-500">
                          {step.duration} min
                          {step.distance ? ` · ${step.distance} mi` : ''}
                        </div>
                      </div>
                    </>
                  ) : (
                    <>
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: LINE_COLORS[step.line?.toUpperCase() || '']?.hex || '#0075BF' }}
                      >
                        <Train className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold text-gray-800 flex items-center gap-1.5">
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                              LINE_COLORS[step.line?.toUpperCase() || '']?.bg || 'bg-blue-600'
                            } text-white`}
                          >
                            {step.line}
                          </span>
                          {step.from}
                          <ArrowRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
                          {step.to}
                        </div>
                        <div className="text-[11px] text-gray-500">
                          {step.duration} min
                          {step.direction ? ` · ${step.direction === 'N' ? 'Northbound' : step.direction === 'S' ? 'Southbound' : step.direction === 'E' ? 'Eastbound' : step.direction === 'W' ? 'Westbound' : step.direction}` : ''}
                          {step.predictedArrival ? ` · Next train ${Math.floor(step.predictedArrival / 60)} min` : ''}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export const TripPlanner: React.FC = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departTime, setDepartTime] = useState('now');
  const [tripOptions, setTripOptions] = useState<TripOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string>('');

  const swapLocations = () => {
    setOrigin(destination);
    setDestination(origin);
    setTripOptions([]);
  };

  const planTrip = async () => {
    if (!origin || !destination) return;
    setLoading(true);
    setTripOptions([]);

    await new Promise((r) => setTimeout(r, 1400));

    const options: TripOption[] = [
      {
        id: 'opt-1',
        badge: 'fastest',
        duration: 24,
        walkingMinutes: 4,
        transfers: 0,
        crowdingLevel: 3,
        delayRisk: 0.08,
        mlConfidence: 0.84,
        departureIn: 180,
        steps: [
          { type: 'walk', from: origin, to: 'Five Points Station', duration: 4, distance: 0.3 },
          { type: 'train', line: 'RED', from: 'Five Points', to: destination, duration: 20, direction: 'N', predictedArrival: 180 },
        ],
      },
      {
        id: 'opt-2',
        badge: 'recommended',
        duration: 28,
        walkingMinutes: 6,
        transfers: 1,
        crowdingLevel: 2,
        delayRisk: 0.05,
        mlConfidence: 0.79,
        departureIn: 240,
        steps: [
          { type: 'walk', from: origin, to: 'Peachtree Center', duration: 6, distance: 0.4 },
          { type: 'train', line: 'GOLD', from: 'Peachtree Center', to: 'Lindbergh', duration: 10, direction: 'N', predictedArrival: 240 },
          { type: 'train', line: 'RED', from: 'Lindbergh', to: destination, duration: 12, direction: 'N', predictedArrival: 360 },
        ],
      },
      {
        id: 'opt-3',
        badge: 'less_crowded',
        duration: 38,
        walkingMinutes: 11,
        transfers: 0,
        crowdingLevel: 1,
        delayRisk: 0.03,
        mlConfidence: 0.91,
        departureIn: 420,
        steps: [
          { type: 'walk', from: origin, to: 'West End Station', duration: 11, distance: 0.7 },
          { type: 'train', line: 'BLUE', from: 'West End', to: destination, duration: 27, direction: 'E', predictedArrival: 420 },
        ],
      },
    ];

    setTripOptions(options);
    setSelectedOption(options[0].id);
    setLoading(false);
  };

  const canPlan = origin.trim().length > 0 && destination.trim().length > 0;

  return (
    <div id="trip-planner" className="space-y-5">
      {/* Input card */}
      <div id="trip-planner-inputs" className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4">
        <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
          <Navigation className="w-4 h-4 text-blue-600" />
          Plan Your Trip
        </h2>

        <div className="relative space-y-3">
          <StationInput
            id="trip-origin"
            label="From"
            value={origin}
            onChange={setOrigin}
            placeholder="Starting station or address"
            icon={<div className="w-2 h-2 rounded-full bg-green-500" />}
          />

          {/* Swap button */}
          <button
            id="trip-swap-btn"
            onClick={swapLocations}
            className="absolute right-0 top-1/2 -translate-y-1/2 -translate-x-2 z-10 w-8 h-8 flex items-center justify-center bg-white border-2 border-gray-200 rounded-full hover:border-blue-400 hover:bg-blue-50 transition-all shadow-sm"
            aria-label="Swap origin and destination"
          >
            <ArrowUpDown className="w-3.5 h-3.5 text-gray-500" />
          </button>

          <StationInput
            id="trip-destination"
            label="To"
            value={destination}
            onChange={setDestination}
            placeholder="Destination station or address"
            icon={<MapPin className="w-4 h-4" />}
          />
        </div>

        {/* Departure time */}
        <div id="trip-departure-row" className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <select
            id="trip-depart-select"
            value={departTime}
            onChange={(e) => setDepartTime(e.target.value)}
            className="flex-1 text-sm bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Departure time"
          >
            <option value="now">Depart now</option>
            <option value="15">In 15 minutes</option>
            <option value="30">In 30 minutes</option>
            <option value="60">In 1 hour</option>
            <option value="custom">Choose time...</option>
          </select>
        </div>

        <button
          id="trip-plan-btn"
          onClick={planTrip}
          disabled={!canPlan || loading}
          className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl font-semibold text-sm text-white transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            background: canPlan && !loading ? 'linear-gradient(135deg, #0075BF, #0091e6)' : '#9CA3AF'
          }}
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              Finding routes...
            </>
          ) : (
            <>
              <Navigation className="w-4 h-4" />
              Get Directions
            </>
          )}
        </button>
      </div>

      {/* Results */}
      <AnimatePresence>
        {tripOptions.length > 0 && (
          <motion.div
            id="trip-results"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-3"
          >
            <div id="trip-results-header" className="flex items-center justify-between px-1">
              <h3 className="text-sm font-bold text-gray-900">
                {tripOptions.length} routes found
              </h3>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                ML-optimized
              </div>
            </div>

            {tripOptions.map((opt, i) => (
              <RouteOptionCard
                key={opt.id}
                option={opt}
                selected={selectedOption === opt.id}
                onSelect={() => setSelectedOption(opt.id === selectedOption ? '' : opt.id)}
                index={i}
              />
            ))}

            {/* ML confidence note */}
            <div id="trip-ml-note" className="px-1">
              <p className="text-[11px] text-gray-400">
                Routes optimized using real-time delay data and ML predictions. Tap a route to see step-by-step directions.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state - no search yet */}
      {!loading && tripOptions.length === 0 && !origin && !destination && (
        <div id="trip-planner-empty" className="text-center py-6">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center mx-auto mb-3">
            <Navigation className="w-6 h-6 text-blue-500" />
          </div>
          <p className="text-sm font-medium text-gray-700">Enter your start and end points</p>
          <p className="text-xs text-gray-400 mt-1">We'll find the best routes using live data</p>
        </div>
      )}
    </div>
  );
};

export default TripPlanner;
