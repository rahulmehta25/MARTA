// frontend/src/components/Admin/SystemLogsViewer.tsx

import React, { useState, useEffect, useRef } from 'react';
import {
  Activity,
  Filter,
  Download,
  RefreshCw,
  AlertCircle,
  Info,
  AlertTriangle,
  XCircle,
  Search,
} from 'lucide-react';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
  service: string;
  message: string;
  details?: any;
}

const SystemLogsViewer: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [filterLevel, setFilterLevel] = useState('all');
  const [filterService, setFilterService] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const services = ['api', 'auth', 'ml-pipeline', 'data-ingestion', 'websocket'];

  useEffect(() => {
    fetchLogs();
    const interval = autoRefresh ? setInterval(fetchLogs, 5000) : null;
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  useEffect(() => {
    applyFilters();
  }, [logs, filterLevel, filterService, searchTerm]);

  const fetchLogs = async () => {
    try {
      // TODO: Fetch real logs from API
      const mockLogs: LogEntry[] = Array.from({ length: 50 }, (_, i) => ({
        id: `log-${Date.now()}-${i}`,
        timestamp: new Date(Date.now() - i * 60 * 1000).toISOString(),
        level: ['INFO', 'WARNING', 'ERROR', 'DEBUG'][Math.floor(Math.random() * 4)] as any,
        service: services[Math.floor(Math.random() * services.length)],
        message: getRandomLogMessage(i),
        details: Math.random() > 0.7 ? { requestId: `req-${i}`, userId: `user-${i}` } : undefined,
      }));
      setLogs(mockLogs);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
      setLoading(false);
    }
  };

  const getRandomLogMessage = (index: number) => {
    const messages = [
      'User authentication successful',
      'API request completed',
      'Database query executed',
      'ML model prediction generated',
      'Data ingestion cycle completed',
      'WebSocket connection established',
      'Rate limit exceeded for IP',
      'Failed to connect to external service',
      'Cache invalidated',
      'Background job started',
    ];
    return messages[index % messages.length];
  };

  const applyFilters = () => {
    let filtered = [...logs];

    if (filterLevel !== 'all') {
      filtered = filtered.filter(log => log.level === filterLevel);
    }

    if (filterService !== 'all') {
      filtered = filtered.filter(log => log.service === filterService);
    }

    if (searchTerm) {
      filtered = filtered.filter(log =>
        log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.service.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    setFilteredLogs(filtered);
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'INFO':
        return <Info className="h-4 w-4 text-blue-500" />;
      case 'WARNING':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'ERROR':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'DEBUG':
        return <Activity className="h-4 w-4 text-gray-500" />;
      default:
        return null;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'INFO':
        return 'text-blue-600 bg-blue-50';
      case 'WARNING':
        return 'text-yellow-600 bg-yellow-50';
      case 'ERROR':
        return 'text-red-600 bg-red-50';
      case 'DEBUG':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const handleExport = () => {
    const logText = filteredLogs.map(log =>
      `[${log.timestamp}] [${log.level}] [${log.service}] ${log.message}`
    ).join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `system-logs-${new Date().toISOString()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div id="system-logs-viewer" className="space-y-6">
      {/* Header and Controls */}
      <div id="logs-header" className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <Activity className="h-6 w-6 text-gray-500 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">System Logs</h3>
          </div>
          <div className="flex items-center space-x-2">
            <button
              id="toggle-auto-refresh"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1 text-sm rounded-md ${
                autoRefresh
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-700'
              }`}
            >
              {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
            </button>
            <button
              id="refresh-logs"
              onClick={fetchLogs}
              className="p-2 text-gray-400 hover:text-gray-500"
            >
              <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              id="export-logs"
              onClick={handleExport}
              className="p-2 text-gray-400 hover:text-gray-500"
            >
              <Download className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div id="logs-filters" className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                id="logs-search"
                type="text"
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-3 py-2 w-full border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
          <select
            id="level-filter"
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Levels</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="DEBUG">DEBUG</option>
          </select>
          <select
            id="service-filter"
            value={filterService}
            onChange={(e) => setFilterService(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Services</option>
            {services.map(service => (
              <option key={service} value={service}>{service}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Logs Display */}
      <div id="logs-display" className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200">
          <p className="text-sm text-gray-500">
            Showing {filteredLogs.length} of {logs.length} log entries
          </p>
        </div>
        <div className="max-h-96 overflow-y-auto p-4 font-mono text-sm">
          {filteredLogs.map((log) => (
            <div
              key={log.id}
              id={log.id}
              className="flex items-start space-x-2 py-1 hover:bg-gray-50"
            >
              {getLevelIcon(log.level)}
              <span className="text-gray-500 whitespace-nowrap">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${getLevelColor(log.level)}`}>
                {log.level}
              </span>
              <span className="text-purple-600">[{log.service}]</span>
              <span className="text-gray-700 flex-1">{log.message}</span>
              {log.details && (
                <span className="text-gray-400 text-xs">
                  {JSON.stringify(log.details)}
                </span>
              )}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={scrollToBottom}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Scroll to bottom
          </button>
        </div>
      </div>
    </div>
  );
};

export default SystemLogsViewer;