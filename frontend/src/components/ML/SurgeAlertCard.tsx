import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Loader2, AlertTriangle, MapPin, Clock, Users, Lightbulb } from 'lucide-react';
import { mlService, SurgeDetectionResponse } from '../../services/mlService';

interface SurgeAlertCardProps {
  locationId: string;
  locationName?: string;
  currentDemand: number;
  historicalBaseline: number;
  refreshInterval?: number; // in milliseconds
}

export const SurgeAlertCard: React.FC<SurgeAlertCardProps> = ({
  locationId,
  locationName = 'Unknown Location',
  currentDemand,
  historicalBaseline,
  refreshInterval = 60000, // 1 minute
}) => {
  const [surgeData, setSurgeData] = useState<SurgeDetectionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkSurge = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await mlService.detectSurge({
        location_id: locationId,
        current_demand: currentDemand,
        historical_baseline: historicalBaseline,
      });
      setSurgeData(data);
      setLastChecked(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check surge conditions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkSurge();
    
    if (refreshInterval > 0) {
      const interval = setInterval(checkSurge, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [locationId, currentDemand, historicalBaseline, refreshInterval]);

  const getSurgeSeverity = () => {
    if (!surgeData?.surge_detected) return 'none';
    if (surgeData.surge_magnitude >= 3) return 'severe';
    if (surgeData.surge_magnitude >= 2) return 'moderate';
    return 'mild';
  };

  const getSurgeColor = () => {
    const severity = getSurgeSeverity();
    switch (severity) {
      case 'severe': return 'text-red-600 bg-red-50 border-red-200';
      case 'moderate': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'mild': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default: return 'text-green-600 bg-green-50 border-green-200';
    }
  };

  const severity = getSurgeSeverity();

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">
          Surge Detection - {locationName}
        </CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={checkSurge}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            'Check'
          )}
        </Button>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="text-red-500 text-sm mb-4 p-2 bg-red-50 rounded">
            {error}
          </div>
        )}
        
        {surgeData && (
          <div className="space-y-4">
            {/* Surge Status */}
            <Alert className={getSurgeColor()}>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                {surgeData.surge_detected ? (
                  <div>
                    <div className="font-semibold">
                      SURGE DETECTED - {severity.toUpperCase()}
                    </div>
                    <div className="text-sm mt-1">
                      {surgeData.surge_magnitude}x normal demand
                    </div>
                  </div>
                ) : (
                  <div className="font-semibold text-green-700">
                    No surge detected - Normal conditions
                  </div>
                )}
              </AlertDescription>
            </Alert>

            {/* Surge Details */}
            {surgeData.surge_detected && (
              <div className="space-y-3">
                {/* Magnitude and Confidence */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Users className="h-4 w-4 text-blue-500" />
                    <span className="text-sm font-medium">Surge Magnitude</span>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-red-600">
                      {surgeData.surge_magnitude}x
                    </div>
                    <div className="text-xs text-gray-500">
                      {Math.round(surgeData.confidence * 100)}% confidence
                    </div>
                  </div>
                </div>

                {/* Contributing Factors */}
                {surgeData.contributing_factors.length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-2 flex items-center space-x-2">
                      <AlertTriangle className="h-4 w-4 text-orange-500" />
                      <span>Contributing Factors</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {surgeData.contributing_factors.map((factor, index) => (
                        <Badge key={index} variant="secondary" className="text-xs">
                          {factor}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Affected Areas */}
                {surgeData.affected_areas.length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-2 flex items-center space-x-2">
                      <MapPin className="h-4 w-4 text-blue-500" />
                      <span>Affected Areas</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {surgeData.affected_areas.map((area, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {area}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommended Actions */}
                {surgeData.recommended_actions.length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-2 flex items-center space-x-2">
                      <Lightbulb className="h-4 w-4 text-yellow-500" />
                      <span>Recommended Actions</span>
                    </div>
                    <ul className="space-y-1">
                      {surgeData.recommended_actions.map((action, index) => (
                        <li key={index} className="text-sm text-gray-700 flex items-start space-x-2">
                          <span className="text-blue-500 mt-1">•</span>
                          <span>{action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* External Factors */}
                {surgeData.external_factors && (
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium">Weather Severity:</span>
                      <span className="ml-2">
                        {surgeData.external_factors.weather_severity}/5
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">Traffic Index:</span>
                      <span className="ml-2">
                        {surgeData.external_factors.traffic_index.toFixed(1)}x
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Last Checked */}
            {lastChecked && (
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <Clock className="h-3 w-3" />
                <span>Last checked {lastChecked.toLocaleTimeString()}</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default SurgeAlertCard;


