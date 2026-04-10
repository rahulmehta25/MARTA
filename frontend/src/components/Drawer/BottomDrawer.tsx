import React, { useRef, useEffect } from 'react';
import { motion, PanInfo } from 'framer-motion';
import { useAppStore } from '@/store';
import { OverviewTab } from './tabs/OverviewTab';
import { DemandTab } from './tabs/DemandTab';
import { OptimizationTab } from './tabs/OptimizationTab';
import { AnalyticsTab } from './tabs/AnalyticsTab';
import { GripHorizontal, Layers } from 'lucide-react';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'demand', label: 'Demand' },
  { id: 'optimization', label: 'Optimization' },
  { id: 'analytics', label: 'Analytics' },
] as const;

export const BottomDrawer: React.FC = () => {
  const {
    drawerOpen,
    drawerHeight,
    activeTab,
    setDrawerOpen,
    setDrawerHeight,
    setActiveTab,
  } = useAppStore();
  
  const constraintsRef = useRef<HTMLDivElement>(null);

  const handleDragEnd = (event: any, info: PanInfo) => {
    const threshold = 50;
    const velocity = info.velocity.y;
    
    if (velocity > 500 || info.offset.y > threshold) {
      setDrawerOpen(false);
    } else if (velocity < -500 || info.offset.y < -threshold) {
      setDrawerHeight(Math.min(drawerHeight + Math.abs(info.offset.y), 600));
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewTab />;
      case 'demand':
        return <DemandTab />;
      case 'optimization':
        return <OptimizationTab />;
      case 'analytics':
        return <AnalyticsTab />;
      default:
        return <OverviewTab />;
    }
  };

  return (
    <>
      {/* Backdrop */}
      {drawerOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/20 z-40"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* Drawer */}
      <div ref={constraintsRef} className="fixed inset-x-0 bottom-0 z-50 pointer-events-none">
        <motion.div
          drag="y"
          dragConstraints={constraintsRef}
          dragElastic={0.1}
          onDragEnd={handleDragEnd}
          initial={false}
          animate={{
            y: drawerOpen ? 0 : drawerHeight - 60,
            height: drawerHeight,
          }}
          transition={{
            type: 'spring',
            damping: 30,
            stiffness: 300,
          }}
          className="bg-card border-t border-border rounded-t-2xl shadow-2xl pointer-events-auto overflow-hidden"
          style={{ height: drawerHeight }}
          role="dialog"
          aria-label="Data panel"
          aria-hidden={!drawerOpen}
        >
          {/* Handle */}
          <div
            id="drawer-handle"
            className="flex justify-center py-3 bg-secondary/50 cursor-grab active:cursor-grabbing touch-target"
            role="separator"
            aria-label="Drag to resize panel"
          >
            <GripHorizontal className="w-8 h-6 text-muted-foreground" aria-hidden="true" />
          </div>

          {/* Tab Navigation */}
          <div id="drawer-tabs" className="flex border-b border-border bg-card" role="tablist" aria-label="Data views">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 px-3 sm:px-4 py-3 text-xs sm:text-sm font-medium transition-colors relative touch-target ${
                  activeTab === tab.id
                    ? 'text-primary'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`tabpanel-${tab.id}`}
                id={`tab-${tab.id}`}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
                    transition={{ type: 'spring', damping: 30, stiffness: 400 }}
                  />
                )}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div
            className="flex-1 overflow-y-auto"
            role="tabpanel"
            id={`tabpanel-${activeTab}`}
            aria-labelledby={`tab-${activeTab}`}
          >
            {renderTabContent()}
          </div>
        </motion.div>
      </div>

      {/* Toggle button when drawer is closed */}
      {!drawerOpen && (
        <motion.button
          id="drawer-toggle"
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          onClick={() => setDrawerOpen(true)}
          className="fixed bottom-6 right-6 z-50 bg-primary text-primary-foreground rounded-full w-14 h-14 flex items-center justify-center shadow-lg hover:shadow-xl hover:bg-primary/90 transition-all focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label="Open data panel"
        >
          <Layers className="w-5 h-5" aria-hidden="true" />
        </motion.button>
      )}
    </>
  );
};