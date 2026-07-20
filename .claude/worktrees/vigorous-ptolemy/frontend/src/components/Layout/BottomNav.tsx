import React from 'react';
import { NavLink } from 'react-router-dom';
import { Map, Clock, Navigation, AlertTriangle, Bookmark } from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Map', icon: Map },
  { path: '/arrivals', label: 'Arrivals', icon: Clock },
  { path: '/plan', label: 'Plan', icon: Navigation },
  { path: '/alerts', label: 'Alerts', icon: AlertTriangle },
  { path: '/saved', label: 'Saved', icon: Bookmark },
];

export const BottomNav: React.FC = () => {
  return (
    <nav
      id="bottom-nav"
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200 pb-safe"
      role="navigation"
      aria-label="Main navigation"
    >
      <div id="bottom-nav-inner" className="flex items-stretch h-16">
        {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            id={`bottom-nav-${label.toLowerCase()}`}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center gap-1 min-w-0 transition-colors duration-150 ${
                isActive ? 'text-blue-700' : 'text-gray-400 hover:text-gray-600'
              }`
            }
            aria-label={label}
          >
            {({ isActive }) => (
              <>
                <div
                  id={`bottom-nav-icon-${label.toLowerCase()}`}
                  className={`relative p-1 rounded-xl transition-all duration-150 ${
                    isActive ? 'bg-blue-50' : ''
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {isActive && (
                    <span
                      id={`bottom-nav-dot-${label.toLowerCase()}`}
                      className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-blue-600 rounded-full border-2 border-white"
                    />
                  )}
                </div>
                <span
                  id={`bottom-nav-label-${label.toLowerCase()}`}
                  className="text-[10px] font-medium leading-none"
                >
                  {label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
};

export default BottomNav;
