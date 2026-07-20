import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Train, Clock, Wifi, WifiOff, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRealtimeSubscription } from '@/hooks/useRealtimeSubscription';

interface Arrival {
  train_id?: string;
  station: string;
  line: string;
  destination: string;
  waiting_seconds: number;
  waiting_time: string;
  direction: string;
  delay: string;
  predicted_seconds?: number;
  confidence?: number;
}

interface ArrivalBoardProps {
  stationId?: string;
  limit?: number;
  compact?: boolean;
}

const LINE_COLORS: Record<string, { bg: string; text: string; border: string; hex: string }> = {
  RED:   { bg: 'bg-red-500',   text: 'text-white', border: 'border-red-400',   hex: '#EF4444' },
  GOLD:  { bg: 'bg-amber-500', text: 'text-white', border: 'border-amber-400', hex: '#F59E0B' },
  BLUE:  { bg: 'bg-blue-600',  text: 'text-white', border: 'border-blue-500',  hex: '#0075BF' },
  GREEN: { bg: 'bg-green-600', text: 'text-white', border: 'border-green-500', hex: '#16A34A' },
};

/** Live countdown hook — counts down every second from the given initial seconds */
function useLiveCountdown(initialSeconds: number) {
  const [seconds, setSeconds] = useState(initialSeconds);
  const ref = useRef(initialSeconds);

  useEffect(() => {
    ref.current = initialSeconds;
    setSeconds(initialSeconds);
    const timer = setInterval(() => {
      ref.current = Math.max(0, ref.current - 1);
      setSeconds(ref.current);
    }, 1000);
    return () => clearInterval(timer);
  }, [initialSeconds]);

  return seconds;
}

const ArrivalCard: React.FC<{ arrival: Arrival; index: number; compact?: boolean }> = ({
  arrival,
  index,
  compact = false,
}) => {
  const liveSeconds = useLiveCountdown(arrival.waiting_seconds);
  const lineColor = LINE_COLORS[arrival.line?.toUpperCase()] || LINE_COLORS.BLUE;

  const isArriving = liveSeconds < 60;
  const isSoon = liveSeconds >= 60 && liveSeconds < 3 * 60;
  const delaySeconds = parseInt(arrival.delay) || 0;
  const isDelayed = delaySeconds > 60;
  const isMajorDelay = delaySeconds > 300;

  const formatCountdown = (secs: number): { value: string; unit: string } => {
    if (secs < 60) return { value: 'NOW', unit: '' };
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    if (m < 10) return { value: `${m}:${String(s).padStart(2, '0')}`, unit: 'min' };
    return { value: String(m), unit: 'min' };
  };

  const { value, unit } = formatCountdown(liveSeconds);

  return (
    <motion.div
      id={`arrival-card-${arrival.train_id || index}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ delay: index * 0.04, duration: 0.25 }}
      className={`flex items-center gap-3 ${compact ? 'py-2.5' : 'py-3.5'} px-4 border-b border-gray-100 last:border-b-0 hover:bg-gray-50 transition-colors group`}
    >
      {/* Line color bar */}
      <div
        id={`arrival-line-bar-${arrival.train_id || index}`}
        className="flex-shrink-0 w-1 rounded-full self-stretch min-h-[40px]"
        style={{ backgroundColor: lineColor.hex }}
      />

      {/* Line chip + destination */}
      <div id={`arrival-info-${arrival.train_id || index}`} className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span
            id={`arrival-line-chip-${arrival.train_id || index}`}
            className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${lineColor.bg} ${lineColor.text}`}
          >
            {arrival.line}
          </span>
          <span
            id={`arrival-destination-${arrival.train_id || index}`}
            className="text-sm font-semibold text-gray-900 truncate"
          >
            {arrival.destination}
          </span>
        </div>
        <div id={`arrival-meta-${arrival.train_id || index}`} className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{arrival.direction === 'N' ? 'Northbound' : arrival.direction === 'S' ? 'Southbound' : arrival.direction === 'E' ? 'Eastbound' : arrival.direction === 'W' ? 'Westbound' : arrival.direction}</span>
          {isDelayed && (
            <span
              id={`arrival-delay-badge-${arrival.train_id || index}`}
              className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                isMajorDelay ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
              }`}
            >
              {isMajorDelay ? 'Delayed' : 'Minor delay'}
            </span>
          )}
          {!isDelayed && (
            <span
              id={`arrival-ontime-badge-${arrival.train_id || index}`}
              className="text-[10px] font-semibold text-green-700 flex items-center gap-0.5"
            >
              <CheckCircle2 className="w-3 h-3" />
              On time
            </span>
          )}
        </div>
      </div>

      {/* Countdown */}
      <div id={`arrival-countdown-${arrival.train_id || index}`} className="flex-shrink-0 flex flex-col items-center gap-0.5">
        <div className="flex items-baseline gap-1">
          {isArriving ? (
            <div className="flex items-center gap-1.5">
              <div
                id={`arrival-pulse-dot-${arrival.train_id || index}`}
                className="w-2.5 h-2.5 rounded-full bg-red-500 arrival-pulse"
              />
              <span
                className="text-lg font-black text-red-600 tracking-tight"
                style={{ animation: isArriving ? 'count-pulse 1s ease-in-out infinite' : 'none' }}
              >
                NOW
              </span>
            </div>
          ) : (
            <>
              <span
                id={`arrival-time-value-${arrival.train_id || index}`}
                className={`text-2xl font-black tabular-nums tracking-tight leading-none ${
                  isSoon ? 'text-amber-600' : 'text-gray-900'
                }`}
              >
                {value}
              </span>
              {unit && (
                <span
                  id={`arrival-time-unit-${arrival.train_id || index}`}
                  className={`text-xs font-semibold ${isSoon ? 'text-amber-500' : 'text-gray-400'}`}
                >
                  {unit}
                </span>
              )}
            </>
          )}
        </div>
        {isSoon && !isArriving && (
          <div
            id={`arrival-approaching-dot-${arrival.train_id || index}`}
            className="w-1.5 h-1.5 rounded-full bg-amber-400 arrival-pulse"
          />
        )}
      </div>
    </motion.div>
  );
};

export const ArrivalBoard: React.FC<ArrivalBoardProps> = ({
  stationId = 'FIVE POINTS STATION',
  limit = 8,
  compact = false,
}) => {
  const [arrivals, setArrivals] = useState<Arrival[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState(false);

  const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://vglychbweuowsovboxyf.supabase.co';
  const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY';

  const handleRealtimeUpdate = useCallback((data: any) => {
    if (Array.isArray(data)) {
      setArrivals(data.slice(0, limit));
    } else if (data && data.station_id === stationId) {
      setArrivals((prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((a) => a.train_id === data.train_id);
        if (idx >= 0) updated[idx] = data;
        else updated.push(data);
        return updated.sort((a, b) => a.waiting_seconds - b.waiting_seconds).slice(0, limit);
      });
    }
    setLastUpdate(new Date());
  }, [stationId, limit]);

  const { isConnected } = useRealtimeSubscription({
    channel: 'arrivals',
    stationId,
    onMessage: handleRealtimeUpdate,
  });

  const fetchArrivals = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${SUPABASE_URL}/functions/v1/marta-arrivals?station=${encodeURIComponent(stationId)}`,
        {
          headers: {
            apikey: SUPABASE_ANON_KEY,
            Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          },
        }
      );
      if (!response.ok) throw new Error(`Failed to fetch arrivals (${response.status})`);
      const data = await response.json();
      const sorted = [...data]
        .sort((a: Arrival, b: Arrival) => a.waiting_seconds - b.waiting_seconds)
        .slice(0, limit);
      setArrivals(sorted);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load arrivals');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [stationId, limit, SUPABASE_URL, SUPABASE_ANON_KEY]);

  useEffect(() => {
    fetchArrivals();
    const interval = setInterval(() => fetchArrivals(), 30000);
    return () => clearInterval(interval);
  }, [fetchArrivals]);

  const displayName = stationId
    .replace(' STATION', '')
    .split(' ')
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ');

  if (loading && arrivals.length === 0) {
    return (
      <div id={`arrival-board-loading-${stationId}`} className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-100">
          <div className="h-5 w-40 bg-gray-100 rounded shimmer" />
        </div>
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-3.5 border-b border-gray-100 last:border-0">
            <div className="w-1 h-10 bg-gray-100 rounded shimmer" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-32 bg-gray-100 rounded shimmer" />
              <div className="h-3 w-20 bg-gray-100 rounded shimmer" />
            </div>
            <div className="w-12 h-8 bg-gray-100 rounded shimmer" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div id={`arrival-board-error-${stationId}`} className="bg-white rounded-2xl border border-red-100 shadow-sm overflow-hidden">
        <div className="p-6 flex flex-col items-center gap-3 text-center">
          <AlertCircle className="w-8 h-8 text-red-400" />
          <div>
            <p className="text-sm font-semibold text-gray-900">Unable to load arrivals</p>
            <p className="text-xs text-gray-500 mt-1">{error}</p>
          </div>
          <button
            onClick={() => fetchArrivals()}
            className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-700 px-3 py-1.5 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      id={`arrival-board-${stationId.replace(/\s+/g, '-').toLowerCase()}`}
      className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden"
    >
      {/* Board header */}
      <div
        id={`arrival-board-header-${stationId.replace(/\s+/g, '-').toLowerCase()}`}
        className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50/50"
      >
        <div className="flex items-center gap-2">
          <Train className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-bold text-gray-900">{displayName}</h3>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1 text-[10px] font-medium ${
              isConnected ? 'text-green-600' : 'text-gray-400'
            }`}
          >
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {isConnected ? 'Live' : 'Offline'}
          </div>
          <div className="flex items-center gap-1 text-[10px] text-gray-400">
            <Clock className="w-3 h-3" />
            {lastUpdate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
          <button
            id={`refresh-btn-${stationId.replace(/\s+/g, '-').toLowerCase()}`}
            onClick={() => fetchArrivals(true)}
            disabled={refreshing}
            className="p-1 rounded hover:bg-gray-200 transition-colors text-gray-400 hover:text-gray-600"
            aria-label="Refresh arrivals"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Arrival list */}
      <div id={`arrival-list-${stationId.replace(/\s+/g, '-').toLowerCase()}`} className="divide-y-0">
        <AnimatePresence mode="popLayout">
          {arrivals.length > 0 ? (
            arrivals.map((arrival, i) => (
              <ArrivalCard
                key={`${arrival.train_id || arrival.line}-${i}`}
                arrival={arrival}
                index={i}
                compact={compact}
              />
            ))
          ) : (
            <div
              id={`arrival-empty-${stationId.replace(/\s+/g, '-').toLowerCase()}`}
              className="py-10 text-center"
            >
              <Train className="w-8 h-8 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500 font-medium">No upcoming arrivals</p>
              <p className="text-xs text-gray-400 mt-1">Check back shortly</p>
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer */}
      <div
        id={`arrival-board-footer-${stationId.replace(/\s+/g, '-').toLowerCase()}`}
        className="px-4 py-2 bg-gray-50/50 border-t border-gray-100"
      >
        <p className="text-[10px] text-gray-400">
          Refreshes every 30 seconds &nbsp;·&nbsp; Live data from MARTA API
        </p>
      </div>
    </div>
  );
};

export default ArrivalBoard;
