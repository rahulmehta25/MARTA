import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { 
  Brain, 
  TrendingUp, 
  AlertTriangle, 
  Users, 
  MapPin, 
  RefreshCw,
  Activity,
  BarChart3
} from 'lucide-react';
import DemandForecastCard from './DemandForecastCard';
import SurgeAlertCard from './SurgeAlertCard';
import { mlService, SurgeDetectionResponse } from '../../services/mlService';
import { realtimeService } from '../../services/realtimeService';

// Mock data for demonstration - in real app, this would come from your transit data
const MOCK_STOPS = [
  { id: 'FIVE_POINTS', name: 'Five Points Station', currentDemand: 150, baseline: 50 },
  { id: 'NORTH_SPRINGS', name: 'North Springs Station', currentDemand: 80, baseline: 60 },
  { id: 'SANDY_SPRINGS', name: 'Sandy Springs Station', currentDemand: 45, baseline: 40 },
  { id: 'DUNWOODY', name: 'Dunwoody Station', currentDemand: 120, baseline: 45 },
  { id: 'MEDICAL_CENTER', name: 'Medical Center Station', currentDemand: 90, baseline: 70 },
];

export const MLDashboard: React.FC = () => {
  const [activeSurges, setActiveSurges] = useState<SurgeDetectionResponse[]>([]);
  const [systemStatus, setSystemStatus] = useState<'healthy' | 'warning' | 'critical'>('healthy');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [loading, setLoading] = useState(false);
  const [realtimeConnected, setRealtimeConnected] = useState(false);
  const [systemMetrics, setSystemMetrics] = useState({
    activeCrowdingAlerts: 0,
    activeSurges: 0,
    pendingRepositions: 0,
    avgSystemOccupancy: 0,
    reportingStops: 0
  });

  const checkAllSurges = async () => {
    setLoading(true);
    try {
      const surgeChecks = await mlService.monitorSurgeConditions(
        MOCK_STOPS.map(stop => ({
          location_id: stop.id,
          current_demand: stop.currentDemand,
          historical_baseline: stop.baseline,
        }))
      );
      
      const activeSurges = surgeChecks.filter(surge => surge.surge_detected);
      setActiveSurges(activeSurges);
      
      // Update system status based on surge severity
      if (activeSurges.some(surge => surge.surge_magnitude >= 3)) {
        setSystemStatus('critical');
      } else if (activeSurges.length > 0) {
        setSystemStatus('warning');
      } else {
        setSystemStatus('healthy');
      }
      
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Failed to check surges:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemMetrics = async () => {
    try {
      const response = await fetch('https://gszmaaefdekacgqtetqd.supabase.co/rest/v1/current_system_status', {
        headers: {
          'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdzem1hYWVmZGVrYWNncXRldHFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc4NzUwMDUsImV4cCI6MjA3MzQ1MTAwNX0.Gk0moC-kk9hBuDTmDwPEqUhmsFP6Q1Z_1t1pjhMNluY',
          'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdzem1hYWVmZGVrYWNncXRldHFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc4NzUwMDUsImV4cCI6MjA3MzQ1MTAwNX0.Gk0moC-kk9hBuDTmDwPEqUhmsFP6Q1Z_1t1pjhMNluY'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSystemMetrics(data[0]);
      }
    } catch (error) {
      console.error('Failed to fetch system metrics:', error);
    }
  };

  const setupRealtimeSubscriptions = () => {
    // Subscribe to system status updates
    const systemStatusSub = realtimeService.subscribeToSystemStatus((payload) => {
      console.log('System status update:', payload);
      if (payload.new) {
        setSystemMetrics(payload.new);
      }
    });

    // Subscribe to surge events
    const surgeEventsSub = realtimeService.subscribeToSurgeEvents((payload) => {
      console.log('Surge event update:', payload);
      if (payload.eventType === 'INSERT' && payload.new) {
        // Add new surge to active surges
        setActiveSurges(prev => [...prev, payload.new]);
      }
    });

    // Subscribe to crowding alerts
    const crowdingAlertsSub = realtimeService.subscribeToCrowdingAlerts((payload) => {
      console.log('Crowding alert update:', payload);
      // Update system metrics when crowding alerts change
      fetchSystemMetrics();
    });

    setRealtimeConnected(true);
    
    return () => {
      systemStatusSub.unsubscribe();
      surgeEventsSub.unsubscribe();
      crowdingAlertsSub.unsubscribe();
      setRealtimeConnected(false);
    };
  };

  useEffect(() => {
    checkAllSurges();
    fetchSystemMetrics();
    
    // Set up real-time subscriptions
    const cleanup = setupRealtimeSubscriptions();
    
    // Check for surges every 2 minutes
    const interval = setInterval(checkAllSurges, 120000);
    
    return () => {
      cleanup();
      clearInterval(interval);
    };
  }, []);

  const getSystemStatusColor = () => {
    switch (systemStatus) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'warning': return 'text-orange-600 bg-orange-50 border-orange-200';
      default: return 'text-green-600 bg-green-50 border-green-200';
    }
  };

  const getSystemStatusIcon = () => {
    switch (systemStatus) {
      case 'critical': return <AlertTriangle className="h-4 w-4" />;
      case 'warning': return <Activity className="h-4 w-4" />;
      default: return <Users className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center space-x-2">
            <Brain className="h-8 w-8 text-blue-600" />
            <span>ML Transit Analytics</span>
          </h1>
          <p className="text-gray-600 mt-1">
            AI-powered demand forecasting and surge detection
          </p>
        </div>
        <Button
          onClick={checkAllSurges}
          disabled={loading}
          className="flex items-center space-x-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh All</span>
        </Button>
      </div>

      {/* System Status */}
      <Alert className={getSystemStatusColor()}>
        {getSystemStatusIcon()}
        <AlertDescription>
          <div className="flex items-center justify-between">
            <div>
              <span className="font-semibold">System Status: </span>
              <span className="uppercase">{systemStatus}</span>
              {systemMetrics.activeSurges > 0 && (
                <span className="ml-2">
                  ({systemMetrics.activeSurges} active surge{systemMetrics.activeSurges !== 1 ? 's' : ''})
                </span>
              )}
              {realtimeConnected && (
                <span className="ml-2 text-green-600">● Live</span>
              )}
            </div>
            <div className="text-sm">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </div>
          </div>
        </AlertDescription>
      </Alert>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="overview" className="flex items-center space-x-2">
            <BarChart3 className="h-4 w-4" />
            <span>Overview</span>
          </TabsTrigger>
          <TabsTrigger value="forecasts" className="flex items-center space-x-2">
            <TrendingUp className="h-4 w-4" />
            <span>Demand Forecasts</span>
          </TabsTrigger>
          <TabsTrigger value="surges" className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4" />
            <span>Surge Alerts</span>
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* System Metrics */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Surges</CardTitle>
                <AlertTriangle className="h-4 w-4 text-orange-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics.activeSurges}</div>
                <p className="text-xs text-gray-500">
                  {systemMetrics.activeSurges === 0 ? 'No active surges' : 'Requires attention'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Crowding Alerts</CardTitle>
                <MapPin className="h-4 w-4 text-red-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics.activeCrowdingAlerts}</div>
                <p className="text-xs text-gray-500">Active alerts</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Reporting Stops</CardTitle>
                <Activity className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics.reportingStops}</div>
                <p className="text-xs text-gray-500">Live data feeds</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">System Health</CardTitle>
                <Activity className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  <Badge 
                    variant={
                      systemStatus === 'critical' ? 'destructive' : 
                      systemStatus === 'warning' ? 'secondary' : 'default'
                    }
                  >
                    {systemStatus.toUpperCase()}
                  </Badge>
                </div>
                <p className="text-xs text-gray-500">Overall system status</p>
              </CardContent>
            </Card>
          </div>

          {/* Recent Surge Alerts */}
          {activeSurges.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  <span>Active Surge Alerts</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {activeSurges.map((surge, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-200">
                      <div>
                        <div className="font-semibold text-red-800">
                          {surge.location_id} - {surge.surge_magnitude}x Surge
                        </div>
                        <div className="text-sm text-red-600">
                          {surge.contributing_factors.join(', ')}
                        </div>
                      </div>
                      <Badge variant="destructive">
                        {Math.round(surge.confidence * 100)}% confidence
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Demand Forecasts Tab */}
        <TabsContent value="forecasts" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {MOCK_STOPS.map((stop) => (
              <DemandForecastCard
                key={stop.id}
                stopId={stop.id}
                stopName={stop.name}
                refreshInterval={300000} // 5 minutes
              />
            ))}
          </div>
        </TabsContent>

        {/* Surge Alerts Tab */}
        <TabsContent value="surges" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {MOCK_STOPS.map((stop) => (
              <SurgeAlertCard
                key={stop.id}
                locationId={stop.id}
                locationName={stop.name}
                currentDemand={stop.currentDemand}
                historicalBaseline={stop.baseline}
                refreshInterval={60000} // 1 minute
              />
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MLDashboard;
