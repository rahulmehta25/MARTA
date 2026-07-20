import React, { useState } from 'react';
import {
  AlertTriangle,
  Info,
  CheckCircle2,
  XCircle,
  Clock,
  Filter,
  ChevronDown,
  ChevronUp,
  Radio
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'critical' | 'resolved';
  title: string;
  description: string;
  affectedLines: string[];
  affectedStations?: string[];
  startTime: string;
  endTime?: string;
  updates?: { time: string; text: string }[];
}

const MOCK_ALERTS: Alert[] = [
  {
    id: 'alert-001',
    severity: 'warning',
    title: 'Minor delays on Gold Line — Doraville branch',
    description: 'Gold Line trains are experiencing delays of 5–10 minutes between Doraville and Chamblee stations due to a track inspection. MARTA crews are on-site.',
    affectedLines: ['GOLD'],
    affectedStations: ['Doraville', 'Chamblee', 'Brookhaven'],
    startTime: '10:15 AM',
    updates: [
      { time: '10:35 AM', text: 'Trains now moving at reduced speed through affected area.' },
      { time: '10:15 AM', text: 'Track inspection initiated. Expect 5–10 min delays.' },
    ]
  },
  {
    id: 'alert-002',
    severity: 'info',
    title: 'Elevator out of service — Five Points Station',
    description: 'The elevator at Five Points Station (Peachtree Street entrance) is temporarily out of service for maintenance. Alternative accessible entrance available on Alabama Street.',
    affectedLines: ['RED', 'GOLD', 'BLUE', 'GREEN'],
    affectedStations: ['Five Points'],
    startTime: '8:00 AM',
    endTime: '5:00 PM',
  },
  {
    id: 'alert-003',
    severity: 'info',
    title: 'Planned service changes — Sunday, April 13',
    description: 'Due to scheduled track maintenance, Blue and Green Line trains will run on a modified schedule this Sunday between 10 PM and 2 AM. Buses will substitute between East Lake and Indian Creek.',
    affectedLines: ['BLUE', 'GREEN'],
    startTime: '9:00 AM',
  },
  {
    id: 'alert-004',
    severity: 'resolved',
    title: 'Red Line restored — signal issue resolved',
    description: 'The signal issue affecting Red Line service between Lenox and Buckhead has been fully resolved. All trains are running on normal schedule.',
    affectedLines: ['RED'],
    affectedStations: ['Lenox', 'Buckhead'],
    startTime: '7:45 AM',
    endTime: '9:20 AM',
  },
];

const LINE_COLORS: Record<string, { bg: string; text: string }> = {
  RED:   { bg: 'bg-red-500',   text: 'text-white' },
  GOLD:  { bg: 'bg-amber-500', text: 'text-white' },
  BLUE:  { bg: 'bg-blue-600',  text: 'text-white' },
  GREEN: { bg: 'bg-green-600', text: 'text-white' },
};

const severityConfig = {
  info:     { icon: Info,           color: 'text-blue-600',  bg: 'bg-blue-50',  border: 'border-blue-200',  label: 'Info',     labelColor: 'bg-blue-100 text-blue-700' },
  warning:  { icon: AlertTriangle,  color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Delay',    labelColor: 'bg-amber-100 text-amber-800' },
  critical: { icon: XCircle,        color: 'text-red-600',   bg: 'bg-red-50',   border: 'border-red-200',   label: 'Critical', labelColor: 'bg-red-100 text-red-800' },
  resolved: { icon: CheckCircle2,   color: 'text-green-600', bg: 'bg-gray-50',  border: 'border-gray-200',  label: 'Resolved', labelColor: 'bg-green-100 text-green-700' },
};

const AlertCard: React.FC<{ alert: Alert; index: number }> = ({ alert, index }) => {
  const [expanded, setExpanded] = useState(alert.severity !== 'resolved' && index === 0);
  const cfg = severityConfig[alert.severity];
  const AlertIcon = cfg.icon;

  return (
    <motion.div
      id={`alert-card-${alert.id}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className={`bg-white rounded-2xl border ${cfg.border} shadow-sm overflow-hidden ${
        alert.severity === 'resolved' ? 'opacity-60' : ''
      }`}
    >
      {/* Card header */}
      <button
        id={`alert-toggle-${alert.id}`}
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div id={`alert-icon-${alert.id}`} className={`flex-shrink-0 mt-0.5 ${cfg.color}`}>
          <AlertIcon className="w-5 h-5" />
        </div>
        <div id={`alert-header-content-${alert.id}`} className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span
                  id={`alert-severity-badge-${alert.id}`}
                  className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${cfg.labelColor}`}
                >
                  {cfg.label}
                </span>
                {alert.affectedLines.map((line) => (
                  <span
                    key={line}
                    id={`alert-line-chip-${alert.id}-${line}`}
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${LINE_COLORS[line]?.bg || 'bg-gray-400'} ${LINE_COLORS[line]?.text || 'text-white'}`}
                  >
                    {line}
                  </span>
                ))}
              </div>
              <p className="text-sm font-semibold text-gray-900 leading-snug">{alert.title}</p>
            </div>
            <div id={`alert-chevron-${alert.id}`} className="flex-shrink-0 text-gray-400 mt-0.5">
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </div>
          <div id={`alert-time-row-${alert.id}`} className="flex items-center gap-2 mt-1.5">
            <Clock className="w-3 h-3 text-gray-400" />
            <span className="text-[11px] text-gray-500">
              Started {alert.startTime}
              {alert.endTime ? ` · Resolved ${alert.endTime}` : ' · Ongoing'}
            </span>
          </div>
        </div>
      </button>

      {/* Expanded body */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            id={`alert-body-${alert.id}`}
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-gray-100 space-y-3">
              {/* Description */}
              <p
                id={`alert-description-${alert.id}`}
                className="text-sm text-gray-700 pt-3 leading-relaxed"
              >
                {alert.description}
              </p>

              {/* Affected stations */}
              {alert.affectedStations && (
                <div id={`alert-stations-${alert.id}`}>
                  <p className="text-xs font-semibold text-gray-500 mb-1.5">Affected stations</p>
                  <div className="flex flex-wrap gap-1.5">
                    {alert.affectedStations.map((s) => (
                      <span
                        key={s}
                        id={`alert-station-chip-${alert.id}-${s.replace(/\s+/g, '-').toLowerCase()}`}
                        className="text-xs font-medium px-2.5 py-1 bg-gray-100 text-gray-700 rounded-lg"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Update timeline */}
              {alert.updates && alert.updates.length > 0 && (
                <div id={`alert-updates-${alert.id}`}>
                  <p className="text-xs font-semibold text-gray-500 mb-2">Updates</p>
                  <div className="space-y-2 border-l-2 border-gray-200 pl-3">
                    {alert.updates.map((upd, i) => (
                      <div key={i} id={`alert-update-${alert.id}-${i}`} className="relative">
                        <div className="absolute -left-[13px] top-1 w-2 h-2 rounded-full bg-gray-400" />
                        <p className="text-[11px] text-gray-500 font-medium">{upd.time}</p>
                        <p className="text-xs text-gray-700">{upd.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export const AlertsPage: React.FC = () => {
  const [filter, setFilter] = useState<'all' | 'active' | 'info' | 'resolved'>('all');

  const filteredAlerts = MOCK_ALERTS.filter((a) => {
    if (filter === 'all') return true;
    if (filter === 'active') return a.severity !== 'resolved';
    if (filter === 'resolved') return a.severity === 'resolved';
    if (filter === 'info') return a.severity === 'info';
    return true;
  });

  const activeCount = MOCK_ALERTS.filter((a) => a.severity !== 'resolved').length;

  return (
    <div id="alerts-page" className="min-h-full pb-20 md:pb-6">
      {/* Page header */}
      <div id="alerts-page-header" className="bg-white border-b border-gray-200 px-4 md:px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Service Alerts
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">
                {activeCount} active alert{activeCount !== 1 ? 's' : ''} across MARTA system
              </p>
            </div>
            <div
              id="alerts-live-badge"
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-green-50 border border-green-200 rounded-lg"
            >
              <Radio className="w-3.5 h-3.5 text-green-600" />
              <span className="text-xs font-semibold text-green-700">Live</span>
            </div>
          </div>
        </div>
      </div>

      <div id="alerts-page-content" className="max-w-3xl mx-auto px-4 md:px-6 py-5 space-y-4">
        {/* Filter row */}
        <div id="alerts-filter-row" className="flex items-center gap-2 overflow-x-auto pb-1">
          {(['all', 'active', 'info', 'resolved'] as const).map((f) => (
            <button
              key={f}
              id={`alerts-filter-${f}`}
              onClick={() => setFilter(f)}
              className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold capitalize transition-all ${
                filter === f
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              {f} {f === 'all' && `(${MOCK_ALERTS.length})`}
            </button>
          ))}
        </div>

        {/* Alert list */}
        <div id="alerts-list" className="space-y-3">
          {filteredAlerts.length > 0 ? (
            filteredAlerts.map((alert, i) => (
              <AlertCard key={alert.id} alert={alert} index={i} />
            ))
          ) : (
            <div id="alerts-empty" className="text-center py-12">
              <CheckCircle2 className="w-10 h-10 text-green-400 mx-auto mb-3" />
              <p className="text-sm font-semibold text-gray-700">No alerts in this category</p>
              <p className="text-xs text-gray-400 mt-1">MARTA service is running normally</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div id="alerts-footer" className="bg-gray-50 rounded-xl p-4 border border-gray-200">
          <p className="text-xs text-gray-500">
            Alerts are sourced directly from MARTA operations. For emergencies, contact MARTA Police at{' '}
            <a href="tel:404-848-4911" className="font-semibold text-blue-600 hover:underline">
              404-848-4911
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  );
};

export default AlertsPage;
