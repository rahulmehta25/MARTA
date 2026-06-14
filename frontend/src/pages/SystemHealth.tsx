import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Server,
  Database,
  Cpu,
  Activity,
  CheckCircle,
  AlertCircle,
  XCircle,
  Clock,
  Wifi,
  HardDrive,
  Brain,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ServiceStatus {
  name: string;
  status: 'operational' | 'degraded' | 'outage';
  latency?: number;
  uptime: number;
  lastCheck: string;
}

interface DataSource {
  name: string;
  lastUpdated: string;
  recordCount: number;
  staleness: 'fresh' | 'stale' | 'critical';
}

interface ModelMetric {
  name: string;
  version: string;
  accuracy: number;
  lastTrained: string;
  status: 'healthy' | 'warning' | 'critical';
  drift: number;
}

const services: ServiceStatus[] = [
  { name: 'API Gateway', status: 'operational', latency: 45, uptime: 99.98, lastCheck: '1m ago' },
  { name: 'Database', status: 'operational', latency: 12, uptime: 99.99, lastCheck: '1m ago' },
  { name: 'Real-time Feed', status: 'operational', latency: 89, uptime: 99.95, lastCheck: '1m ago' },
  { name: 'ML Pipeline', status: 'operational', latency: 156, uptime: 99.87, lastCheck: '2m ago' },
  { name: 'Cache Layer', status: 'operational', latency: 3, uptime: 99.99, lastCheck: '1m ago' },
  { name: 'WebSocket Server', status: 'degraded', latency: 234, uptime: 98.5, lastCheck: '1m ago' },
];

const dataSources: DataSource[] = [
  { name: 'GTFS Static', lastUpdated: '2 hours ago', recordCount: 45234, staleness: 'fresh' },
  { name: 'Real-time Positions', lastUpdated: '30 seconds ago', recordCount: 89, staleness: 'fresh' },
  { name: 'Historical Ridership', lastUpdated: '1 day ago', recordCount: 2456789, staleness: 'fresh' },
  { name: 'Weather Data', lastUpdated: '15 minutes ago', recordCount: 1440, staleness: 'fresh' },
  { name: 'Event Calendar', lastUpdated: '6 hours ago', recordCount: 156, staleness: 'stale' },
];

const models: ModelMetric[] = [
  { name: 'Demand Forecaster', version: 'v2.3.1', accuracy: 94.2, lastTrained: '3 days ago', status: 'healthy', drift: 1.2 },
  { name: 'Route Optimizer', version: 'v1.8.0', accuracy: 91.5, lastTrained: '1 week ago', status: 'healthy', drift: 2.1 },
  { name: 'Arrival Predictor', version: 'v3.1.0', accuracy: 87.8, lastTrained: '2 days ago', status: 'healthy', drift: 0.8 },
  { name: 'Anomaly Detector', version: 'v1.2.3', accuracy: 89.1, lastTrained: '5 days ago', status: 'warning', drift: 4.5 },
];

const systemMetrics = {
  cpu: 42,
  memory: 68,
  disk: 54,
  network: 23,
};

function StatusIcon({ status }: { status: 'operational' | 'degraded' | 'outage' | 'healthy' | 'warning' | 'critical' }) {
  if (status === 'operational' || status === 'healthy') {
    return (
      <span className="relative flex h-4 w-4 items-center justify-center">
        <CheckCircle className="h-4 w-4 text-green-600" />
      </span>
    );
  }
  if (status === 'degraded' || status === 'warning') {
    return <AlertCircle className="h-4 w-4 text-amber-600" />;
  }
  return <XCircle className="h-4 w-4 text-red-600" />;
}

function StatusBadge({ status }: { status: string }) {
  const isActive = status === 'operational' || status === 'healthy' || status === 'fresh';
  return (
    <Badge
      variant="secondary"
      className={cn(
        'relative',
        isActive
          ? 'bg-green-50 text-green-700'
          : status === 'degraded' || status === 'warning' || status === 'stale'
          ? 'bg-amber-50 text-amber-700'
          : 'bg-red-50 text-red-700'
      )}
    >
      {isActive && (
        <span className="relative flex h-1.5 w-1.5 mr-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-green-500" />
        </span>
      )}
      {status}
    </Badge>
  );
}

const metricIcons = [
  { icon: Cpu, label: 'CPU', key: 'cpu' as const },
  { icon: HardDrive, label: 'Memory', key: 'memory' as const },
  { icon: Database, label: 'Disk', key: 'disk' as const },
  { icon: Wifi, label: 'Network', key: 'network' as const },
];

export default function SystemHealthPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-semibold">System Health</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Infrastructure monitoring and model performance
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-50 animate-fade-in-scale">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <span className="text-sm font-medium text-green-700">All Systems Operational</span>
        </div>
      </div>

      {/* System metrics */}
      <div className="grid grid-cols-4 gap-4">
        {metricIcons.map(({ icon: Icon, label, key }, i) => {
          const value = systemMetrics[key];
          const displayValue = key === 'network' ? `${value} MB/s` : `${value}%`;
          const progressValue = key === 'network' ? value * 2 : value;
          return (
            <div key={key} className={cn('animate-fade-in-up', `stagger-${i + 1}`)}>
              <Card className="hover-lift">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">{label}</span>
                    </div>
                    <span className="text-lg font-semibold tabular-nums">{displayValue}</span>
                  </div>
                  <Progress value={progressValue} className="h-1.5" />
                </CardContent>
              </Card>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Services status */}
        <div className="animate-fade-in-scale stagger-3">
          <Card className="hover-lift">
            <CardHeader className="pb-4">
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <Server className="h-4 w-4" />
                Services
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {services.map((service, i) => (
                  <div
                    key={service.name}
                    className={cn(
                      'flex items-center justify-between py-2 border-b border-border last:border-0 animate-fade-in-up',
                      i < 6 ? `stagger-${i + 1}` : 'stagger-6'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <StatusIcon status={service.status} />
                      <div>
                        <p className="text-sm font-medium">{service.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {service.latency}ms latency
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <StatusBadge status={service.status} />
                      <p className="text-2xs text-muted-foreground mt-1">
                        {service.uptime}% uptime
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Data freshness */}
        <div className="animate-fade-in-scale stagger-4">
          <Card className="hover-lift">
            <CardHeader className="pb-4">
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <RefreshCw className="h-4 w-4" />
                Data Freshness
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {dataSources.map((source, i) => (
                  <div
                    key={source.name}
                    className={cn(
                      'flex items-center justify-between py-2 border-b border-border last:border-0 animate-fade-in-up',
                      i < 6 ? `stagger-${i + 1}` : 'stagger-6'
                    )}
                  >
                    <div>
                      <p className="text-sm font-medium">{source.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {source.recordCount.toLocaleString()} records
                      </p>
                    </div>
                    <div className="text-right">
                      <StatusBadge status={source.staleness} />
                      <p className="text-2xs text-muted-foreground mt-1">
                        {source.lastUpdated}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Model health */}
      <div className="animate-fade-in-scale stagger-5">
        <Card className="hover-lift">
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Brain className="h-4 w-4" />
              ML Model Performance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4">
              {models.map((model, i) => (
                <div
                  key={model.name}
                  className={cn(
                    'p-4 rounded-lg border border-border hover-lift animate-fade-in-up',
                    i < 6 ? `stagger-${i + 1}` : 'stagger-6'
                  )}
                >
                  <div className="flex items-center justify-between mb-3">
                    <StatusIcon status={model.status} />
                    <span className="text-2xs text-muted-foreground">{model.version}</span>
                  </div>
                  <p className="text-sm font-medium mb-1">{model.name}</p>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Accuracy</span>
                      <span className="font-medium">{model.accuracy}%</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Drift</span>
                      <span
                        className={cn(
                          'font-medium',
                          model.drift > 3 ? 'text-amber-600' : 'text-green-600'
                        )}
                      >
                        {model.drift}%
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Last trained</span>
                      <span>{model.lastTrained}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Activity log */}
      <div className="animate-fade-in-up stagger-6">
        <Card className="hover-lift">
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { time: '2 min ago', event: 'Demand Forecaster model inference completed', type: 'success' },
                { time: '5 min ago', event: 'Real-time feed reconnected after brief disconnection', type: 'warning' },
                { time: '12 min ago', event: 'Route optimization job completed for Red Line', type: 'success' },
                { time: '25 min ago', event: 'Database backup completed successfully', type: 'success' },
                { time: '1 hour ago', event: 'WebSocket server experiencing elevated latency', type: 'warning' },
              ].map((item, i) => (
                <div
                  key={i}
                  className={cn(
                    'flex items-start gap-3 text-sm animate-fade-in-up',
                    i < 6 ? `stagger-${i + 1}` : 'stagger-6'
                  )}
                >
                  <Clock className="h-4 w-4 text-muted-foreground mt-0.5" />
                  <div className="flex-1">
                    <p className={cn(item.type === 'warning' && 'text-amber-600')}>
                      {item.event}
                    </p>
                    <p className="text-xs text-muted-foreground">{item.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
