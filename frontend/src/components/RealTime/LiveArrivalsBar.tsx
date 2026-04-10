import React, { useState, useEffect, useCallback } from 'react';
import { Train } from 'lucide-react';

// Anon key is safe in frontend bundles - it only grants public read access
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://vglychbweuowsovboxyf.supabase.co';
const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY';

interface Arrival {
  line: string;
  destination: string;
  waiting_seconds: number;
}

const LINE_COLORS: Record<string, string> = {
  RED: '#ef4444',
  GOLD: '#eab308',
  BLUE: '#3b82f6',
  GREEN: '#22c55e',
};

function formatWait(seconds: number): string {
  if (seconds < 60) return 'Now';
  return `${Math.floor(seconds / 60)} min`;
}

function buildTickerText(arrivals: Arrival[]): string {
  if (arrivals.length === 0) return '';
  return arrivals
    .map((a) => `${a.line?.toUpperCase()} → ${a.destination} ${formatWait(a.waiting_seconds)}`)
    .join('  |  ');
}

export const LiveArrivalsBar: React.FC = () => {
  const [arrivals, setArrivals] = useState<Arrival[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchArrivals = useCallback(async () => {
    try {
      const response = await fetch(
        `${SUPABASE_URL}/functions/v1/marta-arrivals?station=${encodeURIComponent('FIVE POINTS STATION')}`,
        {
          headers: {
            apikey: SUPABASE_ANON_KEY,
            Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          },
        }
      );

      if (!response.ok) throw new Error('Failed to fetch');

      const data: Arrival[] = await response.json();
      const sorted = data
        .filter((a) => a.waiting_seconds >= 0)
        .sort((a, b) => a.waiting_seconds - b.waiting_seconds)
        .slice(0, 10);

      setArrivals(sorted);
    } catch {
      // Keep existing data on error, don't clear it
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchArrivals();
    const interval = setInterval(fetchArrivals, 30000);
    return () => clearInterval(interval);
  }, [fetchArrivals]);

  const tickerText = buildTickerText(arrivals);

  return (
    <div
      id="live-arrivals-bar"
      className="flex-shrink-0 bg-black/40 backdrop-blur border-b border-white/10 overflow-hidden"
      style={{ height: '32px' }}
    >
      <div id="live-arrivals-bar-inner" className="flex items-center h-full px-3 gap-3">
        {/* Static label */}
        <div className="flex items-center gap-1.5 flex-shrink-0 text-white/70">
          <Train className="w-3.5 h-3.5" />
          <span className="text-xs font-semibold uppercase tracking-wide whitespace-nowrap">
            Five Points
          </span>
          <span className="text-white/30 text-xs">|</span>
        </div>

        {/* Scrolling ticker */}
        <div className="flex-1 overflow-hidden relative">
          {loading ? (
            <span className="text-xs text-white/40 italic">Live arrivals loading...</span>
          ) : arrivals.length === 0 ? (
            <span className="text-xs text-white/40 italic">No arrival data available</span>
          ) : (
            <div className="live-ticker-wrapper">
              <div className="live-ticker-track">
                {/* Duplicate the text so the scroll loops seamlessly */}
                {[tickerText, tickerText].map((text, textIdx) => (
                  <span
                    key={textIdx}
                    className="live-ticker-segment"
                    aria-hidden={textIdx === 1}
                  >
                    {arrivals.map((arrival, i) => {
                      const color = LINE_COLORS[arrival.line?.toUpperCase()] ?? '#9ca3af';
                      const separator = i < arrivals.length - 1;
                      return (
                        <React.Fragment key={`${textIdx}-${i}`}>
                          <span className="inline-flex items-center gap-1">
                            <span
                              className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                              style={{ backgroundColor: color }}
                            />
                            <span className="font-semibold text-white/90" style={{ color }}>
                              {arrival.line?.toUpperCase()}
                            </span>
                            <span className="text-white/60">→</span>
                            <span className="text-white/80">{arrival.destination}</span>
                            <span
                              className="font-bold"
                              style={{ color }}
                            >
                              {formatWait(arrival.waiting_seconds)}
                            </span>
                          </span>
                          {separator && (
                            <span className="text-white/30 mx-4 select-none">|</span>
                          )}
                        </React.Fragment>
                      );
                    })}
                    <span className="mx-8 text-white/20 select-none">•••</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .live-ticker-wrapper {
          width: 100%;
          overflow: hidden;
        }

        .live-ticker-track {
          display: flex;
          white-space: nowrap;
          animation: live-ticker-scroll 60s linear infinite;
          font-size: 11px;
          line-height: 1;
          align-items: center;
          gap: 0;
        }

        .live-ticker-track:hover {
          animation-play-state: paused;
        }

        .live-ticker-segment {
          display: inline-flex;
          align-items: center;
          gap: 0;
          padding-right: 0;
        }

        @keyframes live-ticker-scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }
      `}</style>
    </div>
  );
};

export default LiveArrivalsBar;
