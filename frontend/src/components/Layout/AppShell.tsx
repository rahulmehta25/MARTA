import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppHeader } from './AppHeader';
import { BottomNav } from './BottomNav';
import { ServiceAlertsBanner } from '@/components/Common/ServiceAlertsBanner';

interface AppShellProps {
  /** When true, the content area grows to fill remaining height (used for the map page) */
  fullHeight?: boolean;
}

export const AppShell: React.FC<AppShellProps> = () => {
  return (
    <div id="app-shell" className="flex flex-col h-screen bg-gray-50 overflow-hidden">
      {/* Fixed header + status strips */}
      <AppHeader />
      <ServiceAlertsBanner />

      {/* Page content — scrollable on non-map pages */}
      <main
        id="app-shell-main"
        className="flex-1 overflow-y-auto overflow-x-hidden relative"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <Outlet />
      </main>

      {/* Mobile bottom navigation */}
      <BottomNav />
    </div>
  );
};

export default AppShell;
