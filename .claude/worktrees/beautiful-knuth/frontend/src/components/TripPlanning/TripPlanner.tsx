import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  MapPin, 
  Navigation, 
  Clock, 
  TrendingUp, 
  AlertTriangle,
  ArrowRight,
  Train,
  Footprints,
  Zap
} from 'lucide-react';
import { motion } from 'framer-motion';

interface TripOption {
  duration: number;
  transfers: number;
  steps: TripStep[];
  crowdingLevel?: number;
  delayRisk?: number;
  mlConfidence?: number;
}

interface TripStep {
  type: 'walk' | 'train';
  line?: string;
  from: string;
  to: string;
  duration: number;
  distance?: number;
  direction?: string;
  predictedArrival?: number;
}

export const TripPlanner: React.FC = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [tripOptions, setTripOptions] = useState<TripOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedOption, setSelectedOption] = useState(0);
  
  const API_BASE = import.meta.env.VITE_API_URL || 'https://marta-rail-api.up.railway.app';

  const planTrip = async () => {
    if (!origin || !destination) return;
    
    setLoading(true);
    
    // Simulate trip planning with multiple options
    // In production, this would call a real routing API
    setTimeout(() => {
      const mockOptions: TripOption[] = [
        {
          duration: 25,
          transfers: 0,
          crowdingLevel: 3,
          delayRisk: 0.15,
          mlConfidence: 0.82,
          steps: [
            {
              type: 'walk',
              from: origin,
              to: 'FIVE POINTS STATION',
              duration: 5,
              distance: 0.3
            },
            {
              type: 'train',
              line: 'RED',
              from: 'FIVE POINTS STATION',
              to: destination,
              duration: 20,
              direction: 'N',
              predictedArrival: 180
            }
          ]
        },
        {
          duration: 32,
          transfers: 1,
          crowdingLevel: 2,
          delayRisk: 0.08,
          mlConfidence: 0.75,
          steps: [
            {
              type: 'walk',
              from: origin,
              to: 'PEACHTREE CENTER STATION',
              duration: 8,
              distance: 0.5
            },
            {
              type: 'train',
              line: 'GOLD',
              from: 'PEACHTREE CENTER STATION',
              to: 'LINDBERGH STATION',
              duration: 12,
              direction: 'N',
              predictedArrival: 240
            },
            {
              type: 'train',
              line: 'RED',
              from: 'LINDBERGH STATION',
              to: destination,
              duration: 12,
              direction: 'N',
              predictedArrival: 360
            }
          ]
        },
        {
          duration: 40,
          transfers: 0,
          crowdingLevel: 1,
          delayRisk: 0.05,
          mlConfidence: 0.88,
          steps: [
            {
              type: 'walk',
              from: origin,
              to: 'WEST END STATION',
              duration: 12,
              distance: 0.8
            },
            {
              type: 'train',
              line: 'BLUE',
              from: 'WEST END STATION',
              to: destination,
              duration: 28,
              direction: 'E',
              predictedArrival: 420
            }
          ]
        }
      ];
      
      setTripOptions(mockOptions);
      setLoading(false);
    }, 1500);
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

  const getCrowdingBadge = (level: number) => {
    if (level <= 2) return { text: 'Low', color: 'bg-green-500' };
    if (level <= 3) return { text: 'Medium', color: 'bg-yellow-500' };
    return { text: 'High', color: 'bg-red-500' };
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Navigation className="h-5 w-5" />
          Trip Planner
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Input Section */}
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="origin">From</Label>
            <div className="relative">
              <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="origin"
                placeholder="Enter origin station or address"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="destination">To</Label>
            <div className="relative">
              <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="destination"
                placeholder="Enter destination"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </div>
        
        <Button 
          onClick={planTrip} 
          disabled={loading || !origin || !destination}
          className="w-full md:w-auto"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
              Planning...
            </>
          ) : (
            <>
              <Navigation className="h-4 w-4 mr-2" />
              Plan Trip
            </>
          )}
        </Button>
        
        {/* Results Section */}
        {tripOptions.length > 0 && (
          <div className="space-y-4">
            <Tabs value={selectedOption.toString()} onValueChange={(v) => setSelectedOption(parseInt(v))}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="0" className="flex items-center gap-1">
                  <Zap className="h-3 w-3" />
                  Fastest
                </TabsTrigger>
                <TabsTrigger value="1" className="flex items-center gap-1">
                  <Train className="h-3 w-3" />
                  Fewest Transfers
                </TabsTrigger>
                <TabsTrigger value="2" className="flex items-center gap-1">
                  <Footprints className="h-3 w-3" />
                  Less Crowded
                </TabsTrigger>
              </TabsList>
              
              {tripOptions.map((option, idx) => (
                <TabsContent key={idx} value={idx.toString()} className="space-y-4">
                  {/* Trip Summary */}
                  <div className="flex items-center justify-between p-4 bg-secondary/50 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div>
                        <div className="text-2xl font-bold">{option.duration} min</div>
                        <div className="text-sm text-muted-foreground">
                          {option.transfers === 0 ? 'Direct' : `${option.transfers} transfer${option.transfers > 1 ? 's' : ''}`}
                        </div>
                      </div>
                      
                      {option.crowdingLevel && (
                        <Badge className={`${getCrowdingBadge(option.crowdingLevel).color} text-white`}>
                          {getCrowdingBadge(option.crowdingLevel).text} Crowding
                        </Badge>
                      )}
                      
                      {option.delayRisk && option.delayRisk > 0.1 && (
                        <Badge variant="outline" className="border-yellow-500 text-yellow-600">
                          <AlertTriangle className="h-3 w-3 mr-1" />
                          {Math.round(option.delayRisk * 100)}% delay risk
                        </Badge>
                      )}
                    </div>
                    
                    {option.mlConfidence && (
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <TrendingUp className="h-4 w-4" />
                        ML Confidence: {Math.round(option.mlConfidence * 100)}%
                      </div>
                    )}
                  </div>
                  
                  {/* Trip Steps */}
                  <div className="space-y-3">
                    {option.steps.map((step, stepIdx) => (
                      <motion.div
                        key={stepIdx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: stepIdx * 0.1 }}
                        className="flex items-start gap-3 p-3 rounded-lg hover:bg-secondary/30 transition-colors"
                      >
                        {step.type === 'walk' ? (
                          <>
                            <div className="mt-1">
                              <Footprints className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <div className="flex-1">
                              <div className="font-medium">Walk to {step.to}</div>
                              <div className="text-sm text-muted-foreground">
                                {step.duration} min • {step.distance} miles
                              </div>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className={`w-3 h-12 rounded-full ${getLineColor(step.line!)}`} />
                            <div className="flex-1">
                              <div className="font-medium flex items-center gap-2">
                                <Train className="h-4 w-4" />
                                {step.line} Line - {step.direction}
                              </div>
                              <div className="text-sm text-muted-foreground mt-1">
                                {step.from} <ArrowRight className="inline h-3 w-3 mx-1" /> {step.to}
                              </div>
                              <div className="flex items-center gap-3 mt-1">
                                <span className="text-sm text-muted-foreground">
                                  <Clock className="inline h-3 w-3 mr-1" />
                                  {step.duration} min
                                </span>
                                {step.predictedArrival && (
                                  <Badge variant="outline" className="text-xs">
                                    Next train: {Math.floor(step.predictedArrival / 60)} min
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </>
                        )}
                      </motion.div>
                    ))}
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default TripPlanner;