// frontend/src/components/Admin/AdminDashboard.tsx

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import {
  Users,
  Activity,
  Database,
  AlertTriangle,
  Settings,
  BarChart3,
  Server,
  Shield,
  Clock,
  TrendingUp,
  RefreshCw,
  Key,
} from 'lucide-react';
import SystemHealthCard from './SystemHealthCard';
import UserManagementPanel from './UserManagementPanel';
import APIKeyManager from './APIKeyManager';
import DataIngestionMonitor from './DataIngestionMonitor';
import MLModelStatus from './MLModelStatus';
import SystemLogsViewer from './SystemLogsViewer';

interface SystemMetrics {
  activeUsers: number;
  apiCalls24h: number;
  dataPoints24h: number;
  systemHealth: 'healthy' | 'degraded' | 'down';
  uptime: string;
  lastDataSync: string;
  activeAlerts: number;
  modelAccuracy: number;
}

const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [metrics, setMetrics] = useState<SystemMetrics>({
    activeUsers: 0,
    apiCalls24h: 0,
    dataPoints24h: 0,
    systemHealth: 'healthy',
    uptime: '99.98%',
    lastDataSync: new Date().toISOString(),
    activeAlerts: 0,
    modelAccuracy: 0.92,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSystemMetrics();
    const interval = setInterval(fetchSystemMetrics, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchSystemMetrics = async () => {
    try {
      // TODO: Fetch real metrics from API
      setMetrics({
        activeUsers: Math.floor(Math.random() * 100) + 50,
        apiCalls24h: Math.floor(Math.random() * 10000) + 5000,
        dataPoints24h: Math.floor(Math.random() * 100000) + 50000,
        systemHealth: Math.random() > 0.9 ? 'degraded' : 'healthy',
        uptime: '99.98%',
        lastDataSync: new Date().toISOString(),
        activeAlerts: Math.floor(Math.random() * 5),
        modelAccuracy: 0.88 + Math.random() * 0.08,
      });
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch system metrics:', error);
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'data', label: 'Data Ingestion', icon: Database },
    { id: 'models', label: 'ML Models', icon: TrendingUp },
    { id: 'api-keys', label: 'API Keys', icon: Key },
    { id: 'logs', label: 'System Logs', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div id="admin-dashboard" className="min-h-screen bg-gray-100">
      {/* Header */}
      <div id="admin-header" className="bg-white shadow-sm border-b">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 id="admin-title" className="text-2xl font-bold text-gray-900">
                Admin Dashboard
              </h1>
              <p id="admin-subtitle" className="text-sm text-gray-500">
                MARTA Transit Analytics Platform
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <button
                id="refresh-button"
                onClick={fetchSystemMetrics}
                className="p-2 text-gray-400 hover:text-gray-500"
              >
                <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
              <div id="admin-user-info" className="flex items-center">
                <Shield className="h-5 w-5 text-green-500 mr-2" />
                <span className="text-sm text-gray-700">{user?.email}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div id="admin-tabs" className="bg-white border-b">
        <div className="px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm flex items-center
                    ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div id="admin-content" className="px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <div id="overview-panel">
            {/* Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div id="metric-active-users" className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Active Users</p>
                    <p className="text-2xl font-bold text-gray-900">{metrics.activeUsers}</p>
                    <p className="text-xs text-gray-500">Last 24 hours</p>
                  </div>
                  <Users className="h-8 w-8 text-blue-500" />
                </div>
              </div>

              <div id="metric-api-calls" className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">API Calls</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {metrics.apiCalls24h.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">Last 24 hours</p>
                  </div>
                  <Activity className="h-8 w-8 text-green-500" />
                </div>
              </div>

              <div id="metric-data-points" className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Data Points</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {metrics.dataPoints24h.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">Last 24 hours</p>
                  </div>
                  <Database className="h-8 w-8 text-purple-500" />
                </div>
              </div>

              <div id="metric-alerts" className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Active Alerts</p>
                    <p className="text-2xl font-bold text-gray-900">{metrics.activeAlerts}</p>
                    <p className="text-xs text-gray-500">Requires attention</p>
                  </div>
                  <AlertTriangle
                    className={`h-8 w-8 ${
                      metrics.activeAlerts > 0 ? 'text-red-500' : 'text-gray-400'
                    }`}
                  />
                </div>
              </div>
            </div>

            {/* System Health and Status */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <SystemHealthCard health={metrics.systemHealth} uptime={metrics.uptime} />
              <MLModelStatus accuracy={metrics.modelAccuracy} />
            </div>

            {/* Data Ingestion Status */}
            <DataIngestionMonitor lastSync={metrics.lastDataSync} />
          </div>
        )}

        {activeTab === 'users' && <UserManagementPanel />}
        {activeTab === 'data' && <DataIngestionMonitor lastSync={metrics.lastDataSync} />}
        {activeTab === 'models' && <MLModelStatus accuracy={metrics.modelAccuracy} />}
        {activeTab === 'api-keys' && <APIKeyManager />}
        {activeTab === 'logs' && <SystemLogsViewer />}
        {activeTab === 'settings' && (
          <div id="settings-panel" className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">System Settings</h3>
            <p className="text-gray-500">Settings configuration coming soon...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;