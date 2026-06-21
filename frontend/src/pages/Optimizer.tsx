import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import {
  Play,
  Settings2,
  TrendingUp,
  Clock,
  Users,
  DollarSign,
  RotateCcw,
} from 'lucide-react';
import { martaRoutes } from '@/data/martaData';
import { cn } from '@/lib/utils';

interface OptimizationConfig {
  targetRoutes: string[];
  optimizeFor: ('efficiency' | 'coverage' | 'wait_time')[];
  maxFrequencyIncrease: number;
  maxCapacityIncrease: number;
  budget: number;
}

interface Recommendation {
  id: string;
  routeId: string;
  routeName: string;
  type: 'frequency' | 'capacity' | 'schedule';
  description: string;
  impact: {
    ridership: number;
    waitTime: number;
    cost: number;
  };
  priority: 'high' | 'medium' | 'low';
}

export default function OptimizerPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [hasResults, setHasResults] = useState(false);
  const [config, setConfig] = useState<OptimizationConfig>({
    targetRoutes: [],
    optimizeFor: ['efficiency', 'wait_time'],
    maxFrequencyIncrease: 30,
    maxCapacityIncrease: 20,
    budget: 500000,
  });

  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  const runOptimization = async () => {
    setIsRunning(true);
    setProgress(0);
    setHasResults(false);

    // Simulate optimization progress
    for (let i = 0; i <= 100; i += 10) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      setProgress(i);
    }

    // Generate sample recommendations
    setRecommendations([
      {
        id: '1',
        routeId: 'RED',
        routeName: 'Red Line',
        type: 'frequency',
        description: 'Increase frequency during peak hours (7-9 AM, 5-7 PM) from 10 min to 8 min intervals',
        impact: { ridership: 12, waitTime: -20, cost: 45000 },
        priority: 'high',
      },
      {
        id: '2',
        routeId: 'BLUE',
        routeName: 'Blue Line',
        type: 'capacity',
        description: 'Add 2 additional cars to rush hour trains',
        impact: { ridership: 8, waitTime: -5, cost: 28000 },
        priority: 'medium',
      },
      {
        id: '3',
        routeId: 'GOLD',
        routeName: 'Gold Line',
        type: 'schedule',
        description: 'Adjust schedule to better align with airport flight arrivals',
        impact: { ridership: 15, waitTime: -10, cost: 12000 },
        priority: 'high',
      },
      {
        id: '4',
        routeId: 'GREEN',
        routeName: 'Green Line',
        type: 'frequency',
        description: 'Extend peak service hours to 9 PM for event traffic',
        impact: { ridership: 6, waitTime: -8, cost: 18000 },
        priority: 'low',
      },
    ]);

    setIsRunning(false);
    setHasResults(true);
  };

  const resetOptimization = () => {
    setHasResults(false);
    setRecommendations([]);
    setProgress(0);
  };

  const lineGradients: Record<string, string> = {
    RED: 'from-red-500/10 to-transparent',
    BLUE: 'from-blue-500/10 to-transparent',
    GOLD: 'from-amber-500/10 to-transparent',
    GREEN: 'from-green-500/10 to-transparent',
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-semibold">Route Optimizer</h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI-powered route optimization for improved efficiency
          </p>
        </div>
        {hasResults && (
          <div className="animate-fade-in-scale">
            <Button variant="outline" onClick={resetOptimization} className="gap-2">
              <RotateCcw className="h-4 w-4" />
              New Optimization
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="col-span-1 space-y-4 animate-slide-in-left">
          <Card className="hover-lift">
            <CardHeader className="pb-4">
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <Settings2 className="h-4 w-4" />
                Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Target Routes */}
              <div className="space-y-2">
                <Label className="text-sm">Target Routes</Label>
                <Select>
                  <SelectTrigger>
                    <SelectValue placeholder="All routes" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Routes</SelectItem>
                    {martaRoutes.map((route) => (
                      <SelectItem key={route.id} value={route.id}>
                        {route.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Optimization goals */}
              <div className="space-y-3">
                <Label className="text-sm">Optimize For</Label>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-xs font-normal">Efficiency</Label>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label className="text-xs font-normal">Wait Time</Label>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label className="text-xs font-normal">Coverage</Label>
                    <Switch />
                  </div>
                </div>
              </div>

              {/* Constraints */}
              <div className="space-y-4">
                <Label className="text-sm">Constraints</Label>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span>Max Frequency Increase</span>
                    <span className="font-medium">{config.maxFrequencyIncrease}%</span>
                  </div>
                  <Slider
                    value={[config.maxFrequencyIncrease]}
                    onValueChange={([v]) =>
                      setConfig({ ...config, maxFrequencyIncrease: v })
                    }
                    max={100}
                    step={5}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span>Max Capacity Increase</span>
                    <span className="font-medium">{config.maxCapacityIncrease}%</span>
                  </div>
                  <Slider
                    value={[config.maxCapacityIncrease]}
                    onValueChange={([v]) =>
                      setConfig({ ...config, maxCapacityIncrease: v })
                    }
                    max={50}
                    step={5}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-xs">Budget Limit</Label>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">$</span>
                    <Input
                      type="number"
                      value={config.budget}
                      onChange={(e) =>
                        setConfig({ ...config, budget: parseInt(e.target.value) || 0 })
                      }
                      className="text-sm"
                    />
                  </div>
                </div>
              </div>

              <Button
                className="w-full gap-2"
                onClick={runOptimization}
                disabled={isRunning}
              >
                {isRunning ? (
                  <>Running...</>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    Run Optimization
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Results Panel */}
        <div className="col-span-2 space-y-4">
          {isRunning && (
            <div className="animate-fade-in-up">
              <Card>
                <CardContent className="p-6">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground mb-4">
                      Analyzing routes and computing optimal configurations...
                    </p>
                    <Progress value={progress} className="h-2" />
                    <p className="text-xs text-muted-foreground mt-2">{progress}%</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {hasResults && (
            <div className="space-y-4 animate-fade-in-scale">
              {/* Summary metrics */}
              <div className="grid grid-cols-4 gap-4">
                {[
                  { icon: TrendingUp, label: 'Ridership', value: '+10.2%', color: 'text-green-600' },
                  { icon: Clock, label: 'Wait Time', value: '-12.5%', color: 'text-blue-600' },
                  { icon: Users, label: 'Coverage', value: '+5.8%', color: 'text-purple-600' },
                  { icon: DollarSign, label: 'Est. Cost', value: '$103K', color: 'text-foreground' },
                ].map((metric, i) => (
                  <div key={metric.label} className={cn('animate-fade-in-up', `stagger-${i + 1}`)}>
                    <Card className="hover-lift">
                      <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <metric.icon className={cn('h-4 w-4', metric.color)} />
                          <span className="text-sm text-muted-foreground">{metric.label}</span>
                        </div>
                        <p className={cn('text-xl font-semibold', metric.color)}>
                          {metric.value}
                        </p>
                      </CardContent>
                    </Card>
                  </div>
                ))}
              </div>

              {/* Recommendations */}
              <Card className="hover-lift">
                <CardHeader className="pb-4">
                  <CardTitle className="text-base font-medium">
                    Recommendations
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {recommendations.map((rec, i) => {
                      const route = martaRoutes.find((r) => r.id === rec.routeId);
                      return (
                        <div
                          key={rec.id}
                          className={cn(
                            'p-4 rounded-lg border border-border bg-gradient-to-r hover-lift animate-fade-in-up',
                            lineGradients[rec.routeId] || '',
                            i < 6 ? `stagger-${i + 1}` : 'stagger-6'
                          )}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span
                                className="h-2.5 w-2.5 rounded-full"
                                style={{ backgroundColor: route?.color }}
                              />
                              <span className="font-medium text-sm">{rec.routeName}</span>
                              <span
                                className={cn(
                                  'px-1.5 py-0.5 rounded text-2xs font-medium',
                                  rec.priority === 'high' && 'bg-red-100 text-red-700',
                                  rec.priority === 'medium' && 'bg-amber-100 text-amber-700',
                                  rec.priority === 'low' && 'bg-gray-100 text-gray-700'
                                )}
                              >
                                {rec.priority}
                              </span>
                            </div>
                            <span className="text-xs text-muted-foreground capitalize">
                              {rec.type}
                            </span>
                          </div>

                          <p className="text-sm text-muted-foreground mb-3">
                            {rec.description}
                          </p>

                          <div className="flex items-center gap-6 text-xs">
                            <div className="flex items-center gap-1">
                              <Users className="h-3 w-3 text-muted-foreground" />
                              <span className="text-green-600 font-medium">
                                +{rec.impact.ridership}%
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3 text-muted-foreground" />
                              <span className="text-blue-600 font-medium">
                                {rec.impact.waitTime}%
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              <DollarSign className="h-3 w-3 text-muted-foreground" />
                              <span className="font-medium">
                                ${(rec.impact.cost / 1000).toFixed(0)}K
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Before/After comparison */}
              <Card className="hover-lift">
                <CardHeader className="pb-4">
                  <CardTitle className="text-base font-medium">
                    Impact Comparison
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-8">
                    <div className="space-y-3">
                      <p className="text-sm font-medium text-muted-foreground">Current</p>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Avg Wait Time</span>
                          <span className="font-medium">8.2 min</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Daily Ridership</span>
                          <span className="font-medium">142,000</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Operating Cost</span>
                          <span className="font-medium">$1.2M/month</span>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <p className="text-sm font-medium text-green-600">Optimized</p>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Avg Wait Time</span>
                          <span className="font-medium text-green-600">7.2 min</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Daily Ridership</span>
                          <span className="font-medium text-green-600">156,500</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Operating Cost</span>
                          <span className="font-medium">$1.3M/month</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {!isRunning && !hasResults && (
            <div className="animate-fade-in-scale stagger-2">
              <Card className="h-96">
                <CardContent className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <Settings2 className="h-12 w-12 mx-auto text-muted-foreground/30 mb-4" />
                    <p className="text-lg font-medium mb-1">Configure and Run</p>
                    <p className="text-sm text-muted-foreground max-w-sm">
                      Set your optimization parameters and click "Run Optimization" to
                      generate AI-powered recommendations.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
