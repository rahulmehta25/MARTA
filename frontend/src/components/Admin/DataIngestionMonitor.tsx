// frontend/src/components/Admin/DataIngestionMonitor.tsx

import React, { useState, useEffect } from 'react';
import { Database, Activity, CheckCircle, AlertCircle, Clock, RefreshCw } from 'lucide-react';

interface DataSource {
  id: string;
  name: string;
  type: 'APC' | 'Weather' | 'Traffic';
  status: 'active' | 'error' | 'paused';
  lastSync: string;
  frequency: string;
  recordsToday: number;
  errorRate: number;
}

interface DataIngestionMonitorProps {
  lastSync: string;
}

const DataIngestionMonitor: React.FC<DataIngestionMonitorProps> = ({ lastSync }) => {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchDataSources();
    const interval = setInterval(fetchDataSources, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchDataSources = async () => {
    // TODO: Fetch real data source status from API
    const mockSources: DataSource[] = [
      {
        id: 'apc',
        name: 'Automated Passenger Counter',
        type: 'APC',
        status: 'active',
        lastSync: new Date(Date.now() - 30 * 1000).toISOString(),
        frequency: '30 seconds',
        recordsToday: Math.floor(Math.random() * 50000) + 10000,
        errorRate: Math.random() * 2,
      },
      {
        id: 'weather',
        name: 'OpenWeatherMap API',
        type: 'Weather',
        status: 'active',
        lastSync: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
        frequency: '15 minutes',
        recordsToday: Math.floor(Math.random() * 1000) + 100,
        errorRate: Math.random() * 1,
      },
      {
        id: 'traffic',
        name: 'TomTom Traffic API',
        type: 'Traffic',
        status: Math.random() > 0.8 ? 'error' : 'active',
        lastSync: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
        frequency: '5 minutes',
        recordsToday: Math.floor(Math.random() * 5000) + 1000,
        errorRate: Math.random() * 5,
      },
    ];
    setDataSources(mockSources);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchDataSources();
    setTimeout(() => setRefreshing(false), 1000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'paused':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getTimeSinceSync = (syncTime: string) => {
    const diff = Date.now() - new Date(syncTime).getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    if (minutes > 60) {
      const hours = Math.floor(minutes / 60);
      return `${hours}h ${minutes % 60}m ago`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s ago`;
    } else {
      return `${seconds}s ago`;
    }
  };

  return (
    <div id="data-ingestion-monitor" className="space-y-6">
      {/* Overview Card */}
      <div id="ingestion-overview" className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <Database className="h-6 w-6 text-blue-500 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">Data Ingestion Status</h3>
          </div>
          <button
            id="refresh-ingestion"
            onClick={handleRefresh}
            className="p-2 text-gray-400 hover:text-gray-500"
          >
            <RefreshCw className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Active Sources</p>
            <p className="text-2xl font-bold text-gray-900">
              {dataSources.filter(s => s.status === 'active').length} / {dataSources.length}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Total Records Today</p>
            <p className="text-2xl font-bold text-gray-900">
              {dataSources.reduce((sum, s) => sum + s.recordsToday, 0).toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Average Error Rate</p>
            <p className="text-2xl font-bold text-gray-900">
              {(dataSources.reduce((sum, s) => sum + s.errorRate, 0) / dataSources.length).toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Data Sources */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-gray-700">Data Sources</h4>
          {dataSources.map((source) => (
            <div
              key={source.id}
              id={`source-${source.id}`}
              className="border border-gray-200 rounded-lg p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center">
                    {getStatusIcon(source.status)}
                    <h5 className="ml-2 text-sm font-medium text-gray-900">{source.name}</h5>
                    <span className="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                      {source.type}
                    </span>
                  </div>

                  <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Status:</span>
                      <p className={`font-medium capitalize ${
                        source.status === 'active' ? 'text-green-600' :
                        source.status === 'error' ? 'text-red-600' : 'text-yellow-600'
                      }`}>
                        {source.status}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500">Last Sync:</span>
                      <p className="font-medium text-gray-900">
                        {getTimeSinceSync(source.lastSync)}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-500">Frequency:</span>
                      <p className="font-medium text-gray-900">{source.frequency}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Records Today:</span>
                      <p className="font-medium text-gray-900">
                        {source.recordsToday.toLocaleString()}
                      </p>
                    </div>
                  </div>

                  {source.errorRate > 3 && (
                    <div className="mt-2 flex items-center text-sm text-red-600">
                      <AlertCircle className="h-4 w-4 mr-1" />
                      High error rate: {source.errorRate.toFixed(2)}%
                    </div>
                  )}
                </div>

                <div className="flex space-x-2">
                  <button className="text-sm text-blue-600 hover:text-blue-700">
                    Configure
                  </button>
                  {source.status === 'paused' ? (
                    <button className="text-sm text-green-600 hover:text-green-700">
                      Resume
                    </button>
                  ) : (
                    <button className="text-sm text-yellow-600 hover:text-yellow-700">
                      Pause
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Ingestion Activity */}
      <div id="ingestion-activity" className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Ingestion Activity</h3>

        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center text-sm">
              <Activity className="h-4 w-4 text-gray-400 mr-2" />
              <span className="text-gray-500">
                {new Date(Date.now() - i * 5 * 60 * 1000).toLocaleTimeString()}
              </span>
              <span className="mx-2 text-gray-400">•</span>
              <span className="text-gray-700">
                {['APC', 'Weather', 'Traffic'][i % 3]} data ingested
              </span>
              <span className="ml-auto text-gray-500">
                {Math.floor(Math.random() * 1000) + 100} records
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DataIngestionMonitor;