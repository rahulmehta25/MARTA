import React from 'react';
import { Navigation, Zap, Users, ShieldCheck } from 'lucide-react';
import { TripPlanner } from '@/components/TripPlanning/TripPlanner';

export const PlanPage: React.FC = () => {
  return (
    <div id="plan-page" className="min-h-full pb-20 md:pb-6">
      {/* Page header */}
      <div id="plan-page-header" className="bg-white border-b border-gray-200 px-4 md:px-6 py-4">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Navigation className="w-5 h-5 text-blue-600" />
            Plan Your Trip
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Find the best route using real-time schedules
          </p>
        </div>
      </div>

      <div id="plan-page-content" className="max-w-2xl mx-auto px-4 md:px-6 py-5 space-y-5">
        {/* Trip planner */}
        <TripPlanner />

        {/* Feature callouts */}
        <div id="plan-features" className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div id="plan-feature-smart" className="flex items-start gap-3 p-4 bg-white rounded-2xl border border-gray-200 shadow-sm">
            <div className="w-9 h-9 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
              <Zap className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Smart Routing</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                AI-optimized routes considering real-time delays
              </p>
            </div>
          </div>
          <div id="plan-feature-live" className="flex items-start gap-3 p-4 bg-white rounded-2xl border border-gray-200 shadow-sm">
            <div className="w-9 h-9 bg-green-50 rounded-xl flex items-center justify-center flex-shrink-0">
              <Users className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Crowding Info</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                Know how crowded each train will be before you board
              </p>
            </div>
          </div>
          <div id="plan-feature-reliable" className="flex items-start gap-3 p-4 bg-white rounded-2xl border border-gray-200 shadow-sm">
            <div className="w-9 h-9 bg-purple-50 rounded-xl flex items-center justify-center flex-shrink-0">
              <ShieldCheck className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Delay Risk</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                ML-predicted delay probability so you can plan ahead
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlanPage;
