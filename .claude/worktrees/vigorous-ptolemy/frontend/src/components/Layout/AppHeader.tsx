import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Map,
  Clock,
  Navigation,
  AlertTriangle,
  Bookmark,
  Menu,
  X,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useAppStore } from '@/store';
import { motion, AnimatePresence } from 'framer-motion';
import { LineStatusBar } from '@/components/Common/LineStatusBar';

const NAV_LINKS = [
  { path: '/', label: 'Map', icon: Map },
  { path: '/arrivals', label: 'Arrivals', icon: Clock },
  { path: '/plan', label: 'Plan Trip', icon: Navigation },
  { path: '/alerts', label: 'Alerts', icon: AlertTriangle },
  { path: '/saved', label: 'Saved', icon: Bookmark },
];

export const AppHeader: React.FC = () => {
  const { isConnected } = useAppStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <header id="app-header" className="bg-white border-b border-gray-200 shadow-sm z-30 flex-shrink-0">
      {/* Main header row */}
      <div id="app-header-inner" className="flex items-center h-14 px-4 md:px-6 gap-4">
        {/* Logo */}
        <button
          id="app-logo-btn"
          onClick={() => navigate('/')}
          className="flex items-center gap-2.5 flex-shrink-0 group"
          aria-label="MARTA - Go to map"
        >
          <div
            id="app-logo-icon"
            className="w-9 h-9 rounded-xl flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow"
            style={{ background: 'linear-gradient(135deg, #0075BF, #0091e6)' }}
          >
            <span className="text-white font-black text-base leading-none select-none">M</span>
          </div>
          <div id="app-logo-text" className="hidden sm:block">
            <div className="text-base font-bold text-gray-900 leading-tight">MARTA</div>
            <div className="text-[10px] text-gray-500 leading-tight font-medium tracking-wide uppercase">
              Metropolitan Atlanta Rapid Transit
            </div>
          </div>
        </button>

        {/* Desktop navigation */}
        <nav id="app-nav-desktop" className="hidden md:flex items-center gap-1 ml-4">
          {NAV_LINKS.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              id={`nav-link-${label.toLowerCase().replace(' ', '-')}`}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`w-4 h-4 ${isActive ? 'text-blue-600' : ''}`} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Live status indicator */}
        <div
          id="live-status-indicator"
          className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium ${
            isConnected
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-gray-50 text-gray-500 border border-gray-200'
          }`}
          aria-label={isConnected ? 'Live data active' : 'Reconnecting'}
        >
          {isConnected ? (
            <Wifi className="w-3.5 h-3.5" />
          ) : (
            <WifiOff className="w-3.5 h-3.5" />
          )}
          <div
            className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 arrival-pulse' : 'bg-gray-400'}`}
          />
          {isConnected ? 'Live' : 'Offline'}
        </div>

        {/* Mobile menu toggle */}
        <button
          id="mobile-menu-toggle"
          className="md:hidden p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
          onClick={() => setMobileMenuOpen((v) => !v)}
          aria-label="Toggle navigation menu"
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Line status bar */}
      <LineStatusBar />

      {/* Mobile nav dropdown */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.nav
            id="app-nav-mobile"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="md:hidden overflow-hidden border-t border-gray-100 bg-white"
          >
            <div id="app-nav-mobile-inner" className="px-4 py-2 space-y-0.5">
              {NAV_LINKS.map(({ path, label, icon: Icon }) => (
                <NavLink
                  key={path}
                  to={path}
                  end={path === '/'}
                  id={`mobile-nav-${label.toLowerCase().replace(' ', '-')}`}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon className={`w-5 h-5 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
                      {label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
};

export default AppHeader;
