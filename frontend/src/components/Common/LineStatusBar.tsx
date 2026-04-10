import React, { useState } from 'react';
import { CheckCircle2, AlertCircle, XCircle, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface LineStatus {
  line: 'RED' | 'GOLD' | 'BLUE' | 'GREEN';
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  status: 'operational' | 'minor_delays' | 'major_delays' | 'suspended';
  message?: string;
}

const LINE_STATUSES: LineStatus[] = [
  {
    line: 'RED',
    label: 'Red',
    color: '#DC2626',
    bgColor: 'bg-red-500',
    borderColor: 'border-red-200',
    status: 'operational',
    message: 'Normal service'
  },
  {
    line: 'GOLD',
    label: 'Gold',
    color: '#D97706',
    bgColor: 'bg-amber-500',
    borderColor: 'border-amber-200',
    status: 'minor_delays',
    message: 'Minor delays near Doraville'
  },
  {
    line: 'BLUE',
    label: 'Blue',
    color: '#0075BF',
    bgColor: 'bg-blue-600',
    borderColor: 'border-blue-200',
    status: 'operational',
    message: 'Normal service'
  },
  {
    line: 'GREEN',
    label: 'Green',
    color: '#16A34A',
    bgColor: 'bg-green-600',
    borderColor: 'border-green-200',
    status: 'operational',
    message: 'Normal service'
  },
];

const StatusIcon: React.FC<{ status: LineStatus['status']; size?: number }> = ({ status, size = 12 }) => {
  const s = size;
  if (status === 'operational') return <CheckCircle2 style={{ width: s, height: s }} className="text-green-600" />;
  if (status === 'minor_delays') return <AlertCircle style={{ width: s, height: s }} className="text-amber-600" />;
  if (status === 'major_delays') return <AlertCircle style={{ width: s, height: s }} className="text-red-600" />;
  return <XCircle style={{ width: s, height: s }} className="text-red-700" />;
};

const statusLabel = (status: LineStatus['status']): string => {
  if (status === 'operational') return 'Normal';
  if (status === 'minor_delays') return 'Delays';
  if (status === 'major_delays') return 'Major Delays';
  return 'Suspended';
};

export const LineStatusBar: React.FC = () => {
  const [expanded, setExpanded] = useState(false);

  const hasIssues = LINE_STATUSES.some((l) => l.status !== 'operational');

  return (
    <div id="line-status-bar" className="bg-gray-50 border-b border-gray-100">
      {/* Compact strip */}
      <button
        id="line-status-toggle"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 md:px-6 py-1.5 hover:bg-gray-100 transition-colors text-left"
        aria-expanded={expanded}
        aria-label="Toggle line status details"
      >
        <span id="line-status-heading" className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider flex-shrink-0">
          Line Status
        </span>
        <div id="line-status-chips" className="flex items-center gap-2 flex-1 min-w-0 overflow-x-auto scrollbar-hide">
          {LINE_STATUSES.map((ls) => (
            <div
              key={ls.line}
              id={`line-status-chip-${ls.line.toLowerCase()}`}
              className="flex items-center gap-1 flex-shrink-0"
            >
              <div
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: ls.color }}
              />
              <span className="text-[11px] text-gray-600 font-medium">{ls.label}</span>
              <StatusIcon status={ls.status} size={11} />
            </div>
          ))}
        </div>
        {hasIssues && (
          <span
            id="line-status-alert-badge"
            className="flex-shrink-0 text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded-full"
          >
            Alerts
          </span>
        )}
        <ChevronDown
          className={`w-3.5 h-3.5 text-gray-400 flex-shrink-0 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Expanded detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            id="line-status-expanded"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div
              id="line-status-grid"
              className="grid grid-cols-2 md:grid-cols-4 gap-2 px-4 md:px-6 pb-3 pt-1"
            >
              {LINE_STATUSES.map((ls) => (
                <div
                  key={ls.line}
                  id={`line-status-detail-${ls.line.toLowerCase()}`}
                  className="flex items-center gap-2 p-2.5 bg-white rounded-lg border border-gray-100 shadow-sm"
                >
                  <div
                    className="w-3 h-full min-h-[32px] rounded-full flex-shrink-0"
                    style={{ backgroundColor: ls.color, width: '4px' }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1">
                      <span
                        className="text-xs font-bold"
                        style={{ color: ls.color }}
                      >
                        {ls.label} Line
                      </span>
                    </div>
                    <div className="flex items-center gap-1 mt-0.5">
                      <StatusIcon status={ls.status} size={11} />
                      <span className="text-[11px] text-gray-500">{statusLabel(ls.status)}</span>
                    </div>
                    {ls.message && ls.status !== 'operational' && (
                      <p className="text-[10px] text-gray-500 mt-0.5 truncate">{ls.message}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default LineStatusBar;
