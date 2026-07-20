import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Loader2, TrendingUp, Users, AlertTriangle, Clock } from 'lucide-react';
import { mlService, DemandForecastResponse } from '../../services/mlService';

interface DemandForecastCardProps {
  stopId: string;
  stopName?: string;
  refreshInterval?: number; // in milliseconds
}

export const DemandForecastCard: React.FC<DemandForecastCardProps> = ({
  stopId,
  stopName = 'Unknown Stop',
  refreshInterval = 300000, // 5 minutes
}) => {
  const [forecast, setForecast] = useState<DemandForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchForecast = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await mlService.getDemandForecast({
        stop_id: stopId,
        horizon_hours: 24,
      });
      setForecast(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch forecast');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecast();
    
    if (refreshInterval > 0) {
      const interval = setInterval(fetchForecast, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [stopId, refreshInterval]);

  const getCurrentDemand = () => {
    if (!forecast?.predictions.length) return null;
    return forecast.predictions[0];
  };

  const getPeakDemand = () => {
    if (!forecast?.predictions.length) return null;
    return forecast.predictions.reduce((max, pred) => 
      pred.predicted_demand > max.predicted_demand ? pred : max
    );
  };

  const getSurgeRisk = () => {
    if (!forecast?.predictions.length) return 'low';
    const highSurgePredictions = forecast.predictions.filter(p => p.surge_probability > 0.5);
    if (highSurgePredictions.length > 3) return 'high';
    if (highSurgePredictions.length > 0) return 'medium';
    return 'low';
  };

  const currentDemand = getCurrentDemand();
  const peakDemand = getPeakDemand();
  const surgeRisk = getSurgeRisk();

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">
          Demand Forecast - {stopName}
        </CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchForecast}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            'Refresh'
          )}
        </Button>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="text-red-500 text-sm mb-4 p-2 bg-red-50 rounded">
            {error}
          </div>
        )}
        
        {forecast && (
          <div className="space-y-4">
            {/* Current Demand */}
            {currentDemand && (
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Users className="h-4 w-4 text-blue-500" />
                  <span className="text-sm font-medium">Current Demand</span>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-blue-600">
                    {currentDemand.predicted_demand}
                  </div>
                  <div className="text-xs text-gray-500">
                    ±{Math.round((currentDemand.confidence_upper - currentDemand.confidence_lower) / 2)}
                  </div>
                </div>
              </div>
            )}

            {/* Peak Demand */}
            {peakDemand && (
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium">Peak Demand</span>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-green-600">
                    {peakDemand.predicted_demand}
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(peakDemand.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            )}

            {/* Surge Risk */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-orange-500" />
                <span className="text-sm font-medium">Surge Risk</span>
              </div>
              <Badge 
                variant={
                  surgeRisk === 'high' ? 'destructive' : 
                  surgeRisk === 'medium' ? 'secondary' : 'default'
                }
              >
                {surgeRisk.toUpperCase()}
              </Badge>
            </div>

            {/* Model Confidence */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Model Confidence</span>
              <div className="flex items-center space-x-2">
                <div className="w-16 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full" 
                    style={{ width: `${(forecast.model_confidence * 100)}%` }}
                  />
                </div>
                <span className="text-sm text-gray-600">
                  {Math.round(forecast.model_confidence * 100)}%
                </span>
              </div>
            </div>

            {/* Last Updated */}
            {lastUpdated && (
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <Clock className="h-3 w-3" />
                <span>Updated {lastUpdated.toLocaleTimeString()}</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default DemandForecastCard;


