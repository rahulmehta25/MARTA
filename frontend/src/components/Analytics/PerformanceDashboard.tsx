import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Activity, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle,
  XCircle,
  Brain,
  BarChart3,
  Users
} from 'lucide-react';
import { motion } from 'framer-motion';

interface SystemHealth {
  health_status: string;
  health_score: number;
  line_performance?: Record<string, any>;
  method?: string;
}

interface Insight {
  type: string;
  message: string;
  severity: 'info' | 'warning' | 'success';
}

interface DelayPattern {
  type: string;
  line: string;
  average_delay: number;
  frequency: number;
}

export const PerformanceDashboard: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [patterns, setPatterns] = useState<DelayPattern[]>([]);
  const [loading, setLoading] = useState(true);
  
  const API_BASE = import.meta.env.VITE_API_URL || 'https://marta-rail-api.up.railway.app';

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        
        // Fetch all analytics data in parallel
        const [healthRes, insightsRes, patternsRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/analytics/performance`),
          fetch(`${API_BASE}/api/v1/analytics/insights`),
          fetch(`${API_BASE}/api/v1/analytics/delay-patterns`)
        ]);
        
        if (healthRes.ok) {
          const healthData = await healthRes.json();
          setHealth(healthData);
        }
        
        if (insightsRes.ok) {
          const insightsData = await insightsRes.json();
          setInsights(insightsData.insights || []);
        }
        
        if (patternsRes.ok) {
          const patternsData = await patternsRes.json();
          setPatterns(patternsData.patterns || []);
        }
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 60000); // Refresh every minute
    
    return () => clearInterval(interval);
  }, []);

  const getHealthColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'excellent': return 'text-green-500';
      case 'good': return 'text-blue-500';
      case 'fair': return 'text-yellow-500';
      case 'poor': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'excellent': return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'good': return <Activity className="h-5 w-5 text-blue-500" />;
      case 'fair': return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'poor': return <XCircle className="h-5 w-5 text-red-500" />;
      default: return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  const getInsightIcon = (severity: string) => {
    switch (severity) {
      case 'success': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'warning': return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default: return <Activity className="h-4 w-4 text-blue-500" />;
    }
  };

  const getLineColor = (line: string) => {
    switch (line?.toUpperCase()) {
      case 'RED': return 'bg-red-500';
      case 'GOLD': return 'bg-yellow-500';
      case 'BLUE': return 'bg-blue-500';
      case 'GREEN': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="h-20 bg-secondary/20" />
            <CardContent className="h-32 bg-secondary/10" />
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* System Health Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Health Status Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                System Health
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className={`text-2xl font-bold ${getHealthColor(health?.health_status || '')}`}>
                    {health?.health_status || 'Unknown'}
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Score: {health?.health_score || 0}%
                  </div>
                </div>
                {getHealthIcon(health?.health_status || '')}
              </div>
              <Progress value={health?.health_score || 0} className="mt-3" />
            </CardContent>
          </Card>
        </motion.div>

        {/* ML Status Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                ML Analytics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">Active</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    {health?.method === 'analytics_engine' ? 'Real-time' : 'Basic'} Mode
                  </div>
                </div>
                <Brain className="h-5 w-5 text-purple-500" />
              </div>
              <Badge className="mt-3 bg-purple-500/10 text-purple-600">
                77% Confidence
              </Badge>
            </CardContent>
          </Card>
        </motion.div>

        {/* Delay Patterns Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Delay Patterns
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">{patterns.length}</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Patterns Identified
                  </div>
                </div>
                <BarChart3 className="h-5 w-5 text-orange-500" />
              </div>
              {patterns.length > 0 && (
                <div className="mt-3 text-xs text-muted-foreground">
                  Avg delay: {Math.round(patterns[0].average_delay)}s
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Active Insights Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Active Insights
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">{insights.length}</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Recommendations
                  </div>
                </div>
                <TrendingUp className="h-5 w-5 text-blue-500" />
              </div>
              <div className="mt-3 flex gap-1">
                {insights.slice(0, 3).map((_, i) => (
                  <div key={i} className="w-2 h-2 bg-blue-500 rounded-full" />
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Line Performance */}
      {health?.line_performance && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Line Performance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {Object.entries(health.line_performance).map(([line, stats]: [string, any]) => (
                <motion.div
                  key={line}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="p-4 rounded-lg border bg-card"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${getLineColor(line)}`} />
                      <span className="font-medium">{line} Line</span>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {stats.stations} stations
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">On-time</span>
                      <span className="font-medium">{stats.on_time_percentage?.toFixed(1)}%</span>
                    </div>
                    <Progress value={stats.on_time_percentage || 0} className="h-2" />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Reliability: {stats.reliability_score?.toFixed(1)}</span>
                      <span>Delay: {Math.round(stats.avg_delay_seconds || 0)}s</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* System Insights */}
      {insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              System Insights & Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {insights.map((insight, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`flex items-start gap-3 p-3 rounded-lg ${
                    insight.severity === 'warning' ? 'bg-yellow-500/10' :
                    insight.severity === 'success' ? 'bg-green-500/10' :
                    'bg-blue-500/10'
                  }`}
                >
                  {getInsightIcon(insight.severity)}
                  <div className="flex-1">
                    <p className="text-sm">{insight.message}</p>
                    <Badge variant="outline" className="mt-2 text-xs">
                      {insight.type}
                    </Badge>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Delay Patterns */}
      {patterns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Identified Delay Patterns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {patterns.map((pattern, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-8 rounded-full ${getLineColor(pattern.line)}`} />
                    <div>
                      <div className="font-medium capitalize">{pattern.type} Pattern</div>
                      <div className="text-sm text-muted-foreground">
                        {pattern.line} Line • Frequency: {pattern.frequency}x
                      </div>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-orange-600">
                    Avg: {Math.round(pattern.average_delay)}s delay
                  </Badge>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PerformanceDashboard;