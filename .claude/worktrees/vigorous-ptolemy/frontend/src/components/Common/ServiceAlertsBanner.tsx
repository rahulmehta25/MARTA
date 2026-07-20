import React, { useState } from 'react';
import { AlertTriangle, Info, X, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

export interface ServiceAlert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  line?: string;
  timestamp: string;
}

const ACTIVE_ALERTS: ServiceAlert[] = [
  {
    id: 'alert-1',
    severity: 'warning',
    title: 'Minor delays on Gold Line near Doraville Station',
    line: 'GOLD',
    timestamp: '10 min ago'
  }
];

const severityConfig = {
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-800',
    icon: Info,
    iconColor: 'text-blue-600',
    dot: 'bg-blue-500'
  },
  warning: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-900',
    icon: AlertTriangle,
    iconColor: 'text-amber-600',
    dot: 'bg-amber-500'
  },
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-900',
    icon: AlertTriangle,
    iconColor: 'text-red-600',
    dot: 'bg-red-500'
  }
};

export const ServiceAlertsBanner: React.FC = () => {
  const [dismissed, setDismissed] = useState<string[]>([]);
  const navigate = useNavigate();

  const visibleAlerts = ACTIVE_ALERTS.filter((a) => !dismissed.includes(a.id));

  if (visibleAlerts.length === 0) return null;

  const alert = visibleAlerts[0];
  const config = severityConfig[alert.severity];
  const AlertIcon = config.icon;

  return (
    <AnimatePresence>
      <motion.div
        id="service-alerts-banner"
        key={alert.id}
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: 'auto', opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className={`${config.bg} ${config.border} border-b overflow-hidden`}
        role="alert"
        aria-live="polite"
      >
        <div id="service-alerts-banner-inner" className="flex items-center gap-3 px-4 md:px-6 py-2.5">
          <div id="service-alerts-icon" className={`flex-shrink-0 ${config.iconColor}`}>
            <AlertIcon className="w-4 h-4" />
          </div>
          <div id="service-alerts-content" className="flex-1 min-w-0 flex items-center gap-2">
            {alert.line && (
              <span
                id={`alert-line-chip-${alert.id}`}
                className={`flex-shrink-0 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded text-white ${
                  alert.line === 'RED' ? 'bg-red-500' :
                  alert.line === 'GOLD' ? 'bg-amber-500' :
                  alert.line === 'BLUE' ? 'bg-blue-600' : 'bg-green-600'
                }`}
              >
                {alert.line}
              </span>
            )}
            <p id={`alert-text-${alert.id}`} className={`text-xs font-medium ${config.text} truncate`}>
              {alert.title}
            </p>
            <span id={`alert-time-${alert.id}`} className={`flex-shrink-0 text-[10px] ${config.text} opacity-70`}>
              {alert.timestamp}
            </span>
          </div>
          {visibleAlerts.length > 1 && (
            <span id="alert-count" className={`flex-shrink-0 text-[10px] font-semibold ${config.text} opacity-70`}>
              +{visibleAlerts.length - 1} more
            </span>
          )}
          <button
            id="alerts-view-all-btn"
            onClick={() => navigate('/alerts')}
            className={`flex-shrink-0 flex items-center gap-0.5 text-xs font-semibold ${config.text} hover:underline`}
            aria-label="View all alerts"
          >
            View all
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
          <button
            id={`dismiss-alert-${alert.id}`}
            onClick={() => setDismissed((d) => [...d, alert.id])}
            className={`flex-shrink-0 p-0.5 rounded hover:bg-black/10 transition-colors ${config.iconColor}`}
            aria-label="Dismiss alert"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ServiceAlertsBanner;
