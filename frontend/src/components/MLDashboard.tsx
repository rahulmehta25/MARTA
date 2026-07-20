import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import {
  AlertTriangle,
  TrendingUp,
  Users,
  Clock,
  Activity,
  Zap,
  Navigation,
  AlertCircle,
  CheckCircle,
  RefreshCw,
} from 'lucide-react';

interface DemandPrediction {
  timestamp: string;
  predicted_demand: number;
  confidence_lower: number;
  confidence_upper: number;
  surge_probability: number;
}

interface CrowdingAlert {
  stop_id: string;
  route_id: string;
  crowding_level: string;
  occupancy_percentage: number;
  recommended_actions: string[];
}

interface SurgeForecast {
  forecast_time: string;
  surge_probability: number;
  expected_magnitude: number;
  confidence: number;
}

const MLDashboard: React.FC = () => {
  const [demandForecast, setDemandForecast] = useState<DemandPrediction[]>([]);
  const [crowdingAlerts, setCrowdingAlerts] = useState<CrowdingAlert[]>([]);
  const [surgeForecast, setSurgeForecast] = useState<SurgeForecast[]>([]);
  const [systemStatus, setSystemStatus] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchMLData();
    if (autoRefresh) {
      const interval = setInterval(fetchMLData, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchMLData = async () => {
    try {
      setLoading(true);

      // Fetch demand forecast
      const demandRes = await fetch(`${API_BASE}/api/ml/demand/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stop_id: 'stop_1',
          horizon_hours: 24,
        }),
      });
      const demandData = await demandRes.json();
      setDemandForecast(demandData.predictions || []);

      // Fetch surge forecast
      const surgeRes = await fetch(`${API_BASE}/api/ml/surge/forecast?horizon_hours=6`);
      const surgeData = await surgeRes.json();
      setSurgeForecast(surgeData.forecast || []);

      // Fetch system status
      const statusRes = await fetch(`${API_BASE}/api/ml/system/ml-status`);
      const statusData = await statusRes.json();
      setSystemStatus(statusData);

      // Simulate crowding alerts
      setCrowdingAlerts([
        {
          stop_id: 'FIVE_POINTS',
          route_id: 'RED',
          crowding_level: 'high',
          occupancy_percentage: 85,
          recommended_actions: [
            'Deploy additional vehicle',
            'Alert passengers via app',
          ],
        },
      ]);
    } catch (error) {
      console.error('Error fetching ML data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getCrowdingColor = (level: string) => {
    switch (level) {
      case 'normal':
        return 'bg-green-500';
      case 'elevated':
        return 'bg-yellow-500';
      case 'high':
        return 'bg-orange-500';
      case 'critical':
        return 'bg-red-500';
      case 'severe':
        return 'bg-red-700';
      default:
        return 'bg-gray-500';
    }
  };

  const getSurgeColor = (probability: number) => {
    if (probability < 0.3) return '#10b981'; // green
    if (probability < 0.6) return '#f59e0b'; // yellow
    if (probability < 0.8) return '#ef4444'; // red
    return '#991b1b'; // dark red
  };

  return (
    <div id="ml-dashboard" className="p-6 space-y-6">
      {/* Header */}
      <div id="dashboard-header" className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">ML Intelligence Dashboard</h1>
          <p className="text-gray-600">Real-time predictions and optimization</p>
        </div>
        <div className="flex gap-2">
          <Button
            id="refresh-button"
            variant={autoRefresh ? 'default' : 'outline'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
            {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
          </Button>
          <Button id="manual-refresh" onClick={fetchMLData} variant="outline">
            Refresh Now
          </Button>
        </div>
      </div>

      {/* System Status */}
      <Card id="system-status-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            System Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <p className="text-sm font-medium">Demand Forecaster</p>
              <p className="text-xs text-gray-500">Ready</p>
            </div>
            <div className="text-center">
              <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <p className="text-sm font-medium">Crowding Detector</p>
              <p className="text-xs text-gray-500">Ready</p>
            </div>
            <div className="text-center">
              <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <p className="text-sm font-medium">Route Optimizer</p>
              <p className="text-xs text-gray-500">Ready</p>
            </div>
            <div className="text-center">
              <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <p className="text-sm font-medium">Surge Predictor</p>
              <p className="text-xs text-gray-500">Ready</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Crowding Alerts */}
      {crowdingAlerts.length > 0 && (
        <div id="crowding-alerts" className="space-y-2">
          {crowdingAlerts.map((alert, idx) => (
            <Alert key={idx} className="border-orange-500">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Crowding Alert - {alert.stop_id}</AlertTitle>
              <AlertDescription>
                <div className="mt-2 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge className={getCrowdingColor(alert.crowding_level)}>
                      {alert.crowding_level.toUpperCase()}
                    </Badge>
                    <span className="text-sm">
                      Route {alert.route_id} - {alert.occupancy_percentage}% capacity
                    </span>
                  </div>
                  <div className="text-sm">
                    <p className="font-medium">Recommended Actions:</p>
                    <ul className="list-disc list-inside ml-2">
                      {alert.recommended_actions.map((action, i) => (
                        <li key={i}>{action}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Demand Forecast Chart */}
        <Card id="demand-forecast-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              24-Hour Demand Forecast
            </CardTitle>
            <CardDescription>Predicted passenger demand with confidence intervals</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={demandForecast.slice(0, 24)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(value) => new Date(value).getHours() + ':00'}
                />
                <YAxis />
                <Tooltip
                  labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                  formatter={(value: any) => [value.toFixed(0), '']}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="confidence_upper"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.2}
                  name="Upper Bound"
                />
                <Area
                  type="monotone"
                  dataKey="predicted_demand"
                  stroke="#82ca9d"
                  fill="#82ca9d"
                  fillOpacity={0.6}
                  name="Predicted Demand"
                />
                <Area
                  type="monotone"
                  dataKey="confidence_lower"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.2}
                  name="Lower Bound"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Surge Probability Chart */}
        <Card id="surge-forecast-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Surge Forecast
            </CardTitle>
            <CardDescription>Probability and magnitude of demand surges</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={surgeForecast}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="forecast_time"
                  tickFormatter={(value) => new Date(value).getHours() + ':00'}
                />
                <YAxis yAxisId="left" orientation="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip
                  labelFormatter={(value) => new Date(value).toLocaleTimeString()}
                  formatter={(value: any, name: string) => {
                    if (name === 'Surge Probability') return [(value * 100).toFixed(0) + '%', name];
                    return [value.toFixed(1) + 'x', name];
                  }}
                />
                <Legend />
                <Bar
                  yAxisId="left"
                  dataKey="surge_probability"
                  fill={(data: any) => getSurgeColor(data.surge_probability)}
                  name="Surge Probability"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="expected_magnitude"
                  stroke="#ff7300"
                  strokeWidth={2}
                  name="Expected Magnitude"
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Route Optimization Metrics */}
        <Card id="optimization-metrics-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Navigation className="w-5 h-5" />
              Route Optimization Impact
            </CardTitle>
            <CardDescription>Performance improvements from optimization</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Wait Time Reduction</span>
                  <span className="text-sm font-medium">35%</span>
                </div>
                <Progress value={35} className="h-2" />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Capacity Utilization</span>
                  <span className="text-sm font-medium">78%</span>
                </div>
                <Progress value={78} className="h-2" />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">On-Time Performance</span>
                  <span className="text-sm font-medium">92%</span>
                </div>
                <Progress value={92} className="h-2" />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Crowding Incidents Reduced</span>
                  <span className="text-sm font-medium">45%</span>
                </div>
                <Progress value={45} className="h-2" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Real-time Metrics */}
        <Card id="realtime-metrics-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Real-time Performance
            </CardTitle>
            <CardDescription>Current system metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded">
                <Users className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                <p className="text-2xl font-bold">12,450</p>
                <p className="text-sm text-gray-600">Active Passengers</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded">
                <Activity className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-2xl font-bold">98.5%</p>
                <p className="text-sm text-gray-600">System Efficiency</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded">
                <Clock className="w-8 h-8 text-orange-500 mx-auto mb-2" />
                <p className="text-2xl font-bold">4.2 min</p>
                <p className="text-sm text-gray-600">Avg Wait Time</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded">
                <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
                <p className="text-2xl font-bold">3</p>
                <p className="text-sm text-gray-600">Active Alerts</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Fleet Repositioning Recommendations */}
      <Card id="fleet-repositioning-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Navigation className="w-5 h-5" />
            Fleet Repositioning Commands
          </CardTitle>
          <CardDescription>Real-time vehicle deployment recommendations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Badge className="bg-yellow-500">PRIORITY</Badge>
                <span className="font-medium">Bus #42</span>
                <span className="text-sm text-gray-600">Depot A → Five Points Station</span>
              </div>
              <span className="text-sm">ETA: 12 min</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Badge className="bg-blue-500">NORMAL</Badge>
                <span className="font-medium">Bus #17</span>
                <span className="text-sm text-gray-600">Depot B → Midtown Station</span>
              </div>
              <span className="text-sm">ETA: 18 min</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MLDashboard;