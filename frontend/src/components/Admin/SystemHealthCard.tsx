// frontend/src/components/Admin/SystemHealthCard.tsx

import React from 'react';
import { Server, CheckCircle, AlertCircle, XCircle, Clock } from 'lucide-react';

interface SystemHealthCardProps {
  health: 'healthy' | 'degraded' | 'down';
  uptime: string;
}

const SystemHealthCard: React.FC<SystemHealthCardProps> = ({ health, uptime }) => {
  const getHealthIcon = () => {
    switch (health) {
      case 'healthy':
        return <CheckCircle className="h-6 w-6 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="h-6 w-6 text-yellow-500" />;
      case 'down':
        return <XCircle className="h-6 w-6 text-red-500" />;
    }
  };

  const getHealthText = () => {
    switch (health) {
      case 'healthy':
        return 'All Systems Operational';
      case 'degraded':
        return 'Degraded Performance';
      case 'down':
        return 'System Outage';
    }
  };

  const getHealthColor = () => {
    switch (health) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800';
      case 'down':
        return 'bg-red-100 text-red-800';
    }
  };

  const services = [
    { name: 'API Gateway', status: health === 'down' ? 'down' : 'healthy' },
    { name: 'Database', status: health === 'degraded' ? 'degraded' : 'healthy' },
    { name: 'ML Pipeline', status: 'healthy' },
    { name: 'Data Ingestion', status: health === 'degraded' ? 'degraded' : 'healthy' },
    { name: 'WebSocket Server', status: 'healthy' },
  ];

  return (
    <div id="system-health-card" className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">System Health</h3>
        <div className="flex items-center space-x-2">
          {getHealthIcon()}
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getHealthColor()}`}>
            {getHealthText()}
          </span>
        </div>
      </div>

      <div id="uptime-display" className="mb-6">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Uptime</span>
          <div className="flex items-center">
            <Clock className="h-4 w-4 text-gray-400 mr-1" />
            <span className="font-medium text-gray-900">{uptime}</span>
          </div>
        </div>
      </div>

      <div id="services-status" className="space-y-3">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Service Status</h4>
        {services.map((service) => (
          <div
            key={service.name}
            id={`service-${service.name.toLowerCase().replace(' ', '-')}`}
            className="flex items-center justify-between"
          >
            <div className="flex items-center">
              <Server className="h-4 w-4 text-gray-400 mr-2" />
              <span className="text-sm text-gray-600">{service.name}</span>
            </div>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                service.status === 'healthy'
                  ? 'bg-green-100 text-green-800'
                  : service.status === 'degraded'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {service.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SystemHealthCard;