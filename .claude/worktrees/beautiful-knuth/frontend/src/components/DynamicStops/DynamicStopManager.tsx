import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Clock, MapPin, Users, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { useToast } from '@/components/ui/use-toast';
import { motion, AnimatePresence } from 'framer-motion';

interface DynamicStop {
  id?: number;
  lat: number;
  lon: number;
  demand_threshold: number;
  duration_minutes: number;
  routes?: string[];
  created_at?: string;
  expires_at?: string;
  status?: string;
}

export const DynamicStopManager: React.FC = () => {
  const [dynamicStops, setDynamicStops] = useState<DynamicStop[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  
  const [newStop, setNewStop] = useState<DynamicStop>({
    lat: 33.7490,
    lon: -84.3880,
    demand_threshold: 40,
    duration_minutes: 180,
    routes: []
  });

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

  // Fetch dynamic stops
  const fetchDynamicStops = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/dynamic-stops`);
      if (response.ok) {
        const data = await response.json();
        setDynamicStops(data.stops || []);
      }
    } catch (error) {
      console.error('Failed to fetch dynamic stops:', error);
      toast({
        title: "Error",
        description: "Failed to fetch dynamic stops",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    fetchDynamicStops();
    const interval = setInterval(fetchDynamicStops, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Create new dynamic stop
  const createDynamicStop = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/dynamic-stops`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newStop)
      });
      
      if (response.ok) {
        const data = await response.json();
        toast({
          title: "Success",
          description: "Dynamic stop created successfully",
        });
        
        // Reset form
        setNewStop({
          lat: 33.7490,
          lon: -84.3880,
          demand_threshold: 40,
          duration_minutes: 180,
          routes: []
        });
        setIsCreating(false);
        
        // Refresh list
        await fetchDynamicStops();
      }
    } catch (error) {
      console.error('Failed to create dynamic stop:', error);
      toast({
        title: "Error",
        description: "Failed to create dynamic stop",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // Delete/expire dynamic stop
  const deleteDynamicStop = async (stopId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/dynamic-stops/${stopId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        toast({
          title: "Success",
          description: "Dynamic stop expired",
        });
        await fetchDynamicStops();
      }
    } catch (error) {
      console.error('Failed to delete dynamic stop:', error);
      toast({
        title: "Error",
        description: "Failed to expire dynamic stop",
        variant: "destructive",
      });
    }
  };

  // Get current location
  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setNewStop({
            ...newStop,
            lat: position.coords.latitude,
            lon: position.coords.longitude
          });
          toast({
            title: "Location Updated",
            description: "Using your current location",
          });
        },
        (error) => {
          console.error('Error getting location:', error);
          toast({
            title: "Location Error",
            description: "Could not get your location",
            variant: "destructive",
          });
        }
      );
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <MapPin className="w-5 h-5" />
            Dynamic Bus Stops
          </span>
          <Button
            onClick={() => setIsCreating(!isCreating)}
            size="sm"
            variant={isCreating ? "secondary" : "default"}
          >
            <Plus className="w-4 h-4 mr-1" />
            {isCreating ? 'Cancel' : 'New Stop'}
          </Button>
        </CardTitle>
        <CardDescription>
          Create temporary bus stops based on real-time demand
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Create new stop form */}
        <AnimatePresence>
          {isCreating && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-4 border p-4 rounded-lg bg-secondary/20"
            >
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="lat">Latitude</Label>
                  <Input
                    id="lat"
                    type="number"
                    step="0.0001"
                    value={newStop.lat}
                    onChange={(e) => setNewStop({ ...newStop, lat: parseFloat(e.target.value) })}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="lon">Longitude</Label>
                  <Input
                    id="lon"
                    type="number"
                    step="0.0001"
                    value={newStop.lon}
                    onChange={(e) => setNewStop({ ...newStop, lon: parseFloat(e.target.value) })}
                  />
                </div>
              </div>
              
              <Button
                onClick={getCurrentLocation}
                variant="outline"
                size="sm"
                className="w-full"
              >
                <MapPin className="w-4 h-4 mr-2" />
                Use Current Location
              </Button>
              
              <div className="space-y-2">
                <Label>
                  Demand Threshold: {newStop.demand_threshold} passengers
                </Label>
                <Slider
                  value={[newStop.demand_threshold]}
                  onValueChange={(value) => setNewStop({ ...newStop, demand_threshold: value[0] })}
                  min={10}
                  max={100}
                  step={5}
                />
              </div>
              
              <div className="space-y-2">
                <Label>
                  Duration: {newStop.duration_minutes} minutes
                </Label>
                <Slider
                  value={[newStop.duration_minutes]}
                  onValueChange={(value) => setNewStop({ ...newStop, duration_minutes: value[0] })}
                  min={30}
                  max={480}
                  step={30}
                />
              </div>
              
              <Button
                onClick={createDynamicStop}
                disabled={loading}
                className="w-full"
              >
                {loading ? 'Creating...' : 'Create Dynamic Stop'}
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Active dynamic stops */}
        <div className="space-y-3">
          {dynamicStops.length === 0 ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                No active dynamic stops. Create one to handle demand surges!
              </AlertDescription>
            </Alert>
          ) : (
            dynamicStops.map((stop) => (
              <motion.div
                key={stop.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center justify-between p-3 border rounded-lg bg-card hover:bg-secondary/20 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-pink-500 rounded-sm animate-pulse" />
                    <div>
                      <div className="font-medium text-sm">
                        Dynamic Stop #{stop.id}
                      </div>
                      <div className="text-xs text-muted-foreground space-x-3">
                        <span className="inline-flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {stop.demand_threshold} threshold
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {stop.duration_minutes} min
                        </span>
                        {stop.expires_at && (
                          <span className="inline-flex items-center gap-1">
                            Expires: {new Date(stop.expires_at).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <Badge variant={stop.status === 'active' ? 'default' : 'secondary'}>
                    {stop.status || 'active'}
                  </Badge>
                  <Button
                    onClick={() => stop.id && deleteDynamicStop(stop.id)}
                    size="sm"
                    variant="ghost"
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};