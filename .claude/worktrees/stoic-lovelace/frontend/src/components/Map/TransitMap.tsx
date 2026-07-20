
import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useAppStore } from '@/store';
import { martaStops, martaRoutes } from '@/data/martaData';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useToast } from '@/components/ui/use-toast';

// Get Mapbox token from environment variable (required - set VITE_MAPBOX_TOKEN in .env)
const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || '';

interface TransitMapProps {
  className?: string;
}

interface Vehicle {
  id: string;
  lat: number;
  lon: number;
  route: string;
  bearing?: number;
  speed?: number;
}

export const TransitMap: React.FC<TransitMapProps> = ({ className }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const vehicleMarkersRef = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const [dynamicStops, setDynamicStops] = useState<any[]>([]);
  
  const { toast } = useToast();
  
  const {
    mapStyle,
    selectedStop,
    selectedRoute,
    showDemandHeatmap,
    setSelectedStop,
    setSelectedRoute,
  } = useAppStore();

  // WebSocket connection for live vehicles
  const wsUrl = import.meta.env.VITE_API_BASE_URL?.replace('http', 'ws') || 'ws://localhost:8001';
  const { lastMessage, isConnected } = useWebSocket(`${wsUrl}/ws/vehicles`);

  // Fetch dynamic stops
  useEffect(() => {
    const fetchDynamicStops = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'}/dynamic-stops`);
        if (response.ok) {
          const data = await response.json();
          setDynamicStops(data.stops || []);
        }
      } catch (error) {
        console.error('Failed to fetch dynamic stops:', error);
      }
    };

    fetchDynamicStops();
    const interval = setInterval(fetchDynamicStops, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Update vehicle positions from WebSocket
  useEffect(() => {
    if (!lastMessage || !map.current) return;

    const { vehicles } = lastMessage;
    if (!vehicles || !Array.isArray(vehicles)) return;

    vehicles.forEach((vehicle: Vehicle) => {
      let marker = vehicleMarkersRef.current.get(vehicle.id);
      
      if (!marker) {
        // Create new vehicle marker
        const el = document.createElement('div');
        el.className = 'vehicle-marker';
        el.innerHTML = `
          <div style="
            width: 20px;
            height: 20px;
            background: linear-gradient(135deg, #4CAF50, #45a049);
            border: 2px solid white;
            border-radius: 50%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            animation: pulse 2s infinite;
          ">
            <div style="
              width: 6px;
              height: 6px;
              background: white;
              border-radius: 50%;
            "></div>
          </div>
        `;
        
        marker = new mapboxgl.Marker(el)
          .setLngLat([vehicle.lon, vehicle.lat])
          .addTo(map.current!);
          
        const popup = new mapboxgl.Popup({ offset: 25 })
          .setHTML(`
            <div class="p-2">
              <strong>Vehicle ${vehicle.id}</strong><br/>
              Route: ${vehicle.route}<br/>
              ${vehicle.speed ? `Speed: ${vehicle.speed} mph` : ''}
            </div>
          `);
        
        marker.setPopup(popup);
        vehicleMarkersRef.current.set(vehicle.id, marker);
      } else {
        // Update existing marker position
        marker.setLngLat([vehicle.lon, vehicle.lat]);
      }
    });
  }, [lastMessage]);

  const getMapStyle = () => {
    switch (mapStyle) {
      case 'dark':
        return 'mapbox://styles/mapbox/dark-v11';
      case 'satellite':
        return 'mapbox://styles/mapbox/satellite-streets-v12';
      default:
        return 'mapbox://styles/mapbox/light-v11';
    }
  };

  const getDemandLevel = (routeCount: number): 'high' | 'medium' | 'low' => {
    if (routeCount >= 3) return 'high';
    if (routeCount === 2) return 'medium';
    return 'low';
  };

  const getPassengerCount = (demandLevel: string) => {
    switch(demandLevel) {
      case 'high': return Math.floor(Math.random() * 30) + 40;
      case 'medium': return Math.floor(Math.random() * 25) + 20;
      default: return Math.floor(Math.random() * 20) + 5;
    }
  };

  const getDemandColor = (level: string) => {
    switch (level) {
      case 'high': return '#FF1744';
      case 'medium': return '#FF9800'; 
      case 'low': return '#00C853';
      default: return '#2196F3';
    }
  };

  const getRouteColor = (routeId: string) => {
    const route = martaRoutes.find(r => r.id === routeId);
    return route ? route.color : '#999999';
  };

  const createMarkerElement = (stop: any, isDynamic = false) => {
    const el = document.createElement('div');
    const isPulse = stop.demandLevel === 'high' || isDynamic;
    
    let markerColor = '#999999';
    if (isDynamic) {
      markerColor = '#E91E63'; // Pink for dynamic stops
    } else if (stop.routes?.length === 1) {
      markerColor = getRouteColor(stop.routes[0]);
    } else if (stop.routes?.length > 1) {
      markerColor = '#9C27B0'; // Purple for multi-line stations
    }
    
    el.innerHTML = `
      <div class="relative">
        ${isPulse ? `<div class="absolute inset-0 w-8 h-8 bg-pink-500 rounded-full opacity-75 animate-ping"></div>` : ''}
        <div style="
          width: 24px;
          height: 24px;
          background: linear-gradient(135deg, ${markerColor}, ${markerColor}dd);
          border: 3px solid white;
          border-radius: ${isDynamic ? '4px' : '50%'};
          box-shadow: 0 4px 12px rgba(0,0,0,0.25);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 10px;
          font-weight: bold;
          color: white;
          position: relative;
          z-index: 10;
          transition: all 0.3s ease;
        " 
        onmouseover="this.style.transform='scale(1.2)'; this.style.boxShadow='0 6px 20px rgba(0,0,0,0.4)'"
        onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.25)'"
        >
          ${isDynamic ? '⚡' : stop.currentPassengers || ''}
        </div>
      </div>
    `;
    return el;
  };

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;
    
    try {
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: getMapStyle(),
        center: [-84.3880, 33.7490], // Atlanta center
        zoom: 11,
        pitch: 0,
        bearing: 0,
      });

      // Add navigation controls
      map.current.addControl(
        new mapboxgl.NavigationControl({
          visualizePitch: true,
        }),
        'top-right'
      );

      // Add geolocate control
      map.current.addControl(
        new mapboxgl.GeolocateControl({
          positionOptions: {
            enableHighAccuracy: true
          },
          trackUserLocation: true,
          showUserHeading: true
        }),
        'top-right'
      );

      map.current.on('load', () => {
        // Clear existing markers
        markersRef.current.forEach(marker => marker.remove());
        markersRef.current = [];

        // Add all MARTA rail routes as colored lines
        martaRoutes.forEach((route) => {
          if (map.current!.getSource(`route-${route.id}`)) {
            map.current!.removeLayer(`route-${route.id}`);
            map.current!.removeSource(`route-${route.id}`);
          }

          map.current!.addSource(`route-${route.id}`, {
            type: 'geojson',
            data: {
              type: 'Feature',
              properties: {
                name: route.name,
                color: route.color
              },
              geometry: {
                type: 'LineString',
                coordinates: route.coordinates
              }
            }
          });

          map.current!.addLayer({
            id: `route-${route.id}`,
            type: 'line',
            source: `route-${route.id}`,
            layout: {
              'line-join': 'round',
              'line-cap': 'round'
            },
            paint: {
              'line-color': route.color,
              'line-width': 4,
              'line-opacity': 0.7
            }
          });

          // Add click handler for route
          map.current!.on('click', `route-${route.id}`, () => {
            setSelectedRoute(route);
          });

          // Change cursor on hover
          map.current!.on('mouseenter', `route-${route.id}`, () => {
            if (map.current) map.current.getCanvas().style.cursor = 'pointer';
          });
          map.current!.on('mouseleave', `route-${route.id}`, () => {
            if (map.current) map.current.getCanvas().style.cursor = '';
          });
        });

        // Add MARTA transit stops
        martaStops.forEach((stop) => {
          const demandLevel = getDemandLevel(stop.routes.length);
          const currentPassengers = getPassengerCount(demandLevel);
          const predictedDemand = currentPassengers + Math.floor(Math.random() * 10);
          
          const stopData = {
            ...stop,
            demandLevel,
            currentPassengers,
            predictedDemand
          };

          const el = createMarkerElement(stopData);
          
          el.addEventListener('click', () => {
            setSelectedStop(stopData);
            map.current?.flyTo({
              center: [stop.lng, stop.lat],
              zoom: 14,
              duration: 1000
            });
          });

          const marker = new mapboxgl.Marker(el)
            .setLngLat([stop.lng, stop.lat])
            .addTo(map.current!);

          markersRef.current.push(marker);

          // Enhanced popup
          const routeColors = stop.routes.map(r => {
            const route = martaRoutes.find(rt => rt.id === r);
            return route ? `<span style="color: ${route.color}; font-weight: bold;">${route.name}</span>` : r;
          }).join(', ');

          const popup = new mapboxgl.Popup({
            offset: 30,
            closeButton: true,
            closeOnClick: false,
            className: 'custom-popup'
          }).setHTML(`
            <div class="p-4 min-w-[250px]">
              <div class="flex items-center gap-2 mb-3">
                <div class="w-3 h-3 rounded-full" style="background-color: ${getDemandColor(demandLevel)}"></div>
                <h3 class="font-bold text-base">${stop.name}</h3>
              </div>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-600">Type:</span>
                  <span class="font-semibold capitalize">${stop.type === 'rail' ? '🚇 Rail Station' : '🚌 Bus Stop'}</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-gray-600">Lines:</span>
                  <span>${routeColors}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Current:</span>
                  <span class="font-semibold">${currentPassengers} passengers</span>
                </div>
                ${stop.parking ? '<div class="flex justify-between"><span class="text-gray-600">Features:</span><span class="font-semibold">🅿️ Parking</span></div>' : ''}
                ${stop.accessibility ? '<div class="flex justify-between"><span class="text-gray-600"></span><span class="font-semibold">♿ Accessible</span></div>' : ''}
              </div>
            </div>
          `);

          marker.setPopup(popup);
        });

        // Add dynamic stops
        dynamicStops.forEach((stop) => {
          const el = createMarkerElement(stop, true);
          
          const marker = new mapboxgl.Marker(el)
            .setLngLat([stop.lon, stop.lat])
            .addTo(map.current!);

          const popup = new mapboxgl.Popup({
            offset: 30,
            closeButton: true,
            closeOnClick: false,
          }).setHTML(`
            <div class="p-4 min-w-[200px]">
              <h3 class="font-bold text-base mb-2">⚡ Dynamic Stop</h3>
              <div class="space-y-1 text-sm">
                <div>Demand Threshold: ${stop.demand_threshold}</div>
                <div>Duration: ${stop.duration_minutes} min</div>
                <div>Routes: ${(stop.routes || []).join(', ') || 'All'}</div>
                <div class="text-xs text-gray-500 mt-2">
                  Expires: ${stop.expires_at ? new Date(stop.expires_at).toLocaleTimeString() : 'N/A'}
                </div>
              </div>
            </div>
          `);

          marker.setPopup(popup);
          markersRef.current.push(marker);
        });
      });

    } catch (error) {
      console.error('Error initializing map:', error);
      toast({
        title: "Map Error",
        description: "Failed to initialize map. Please check your connection.",
        variant: "destructive",
      });
    }

    // Cleanup
    return () => {
      vehicleMarkersRef.current.forEach(marker => marker.remove());
      vehicleMarkersRef.current.clear();
      markersRef.current.forEach(marker => marker.remove());
      map.current?.remove();
    };
  }, [mapStyle, showDemandHeatmap, selectedRoute, dynamicStops, toast]);

  return (
    <div className={`relative w-full h-full ${className}`}>
      <div 
        ref={mapContainer} 
        className="w-full h-full rounded-xl overflow-hidden shadow-lg"
        style={{ minHeight: '400px' }}
      />
      
      {/* Map overlays */}
      <div className="absolute top-4 left-4 z-10 space-y-3">
        {/* Connection Status */}
        <div className="bg-card/95 backdrop-blur-sm p-3 rounded-xl shadow-lg border border-border/50">
          <div className="text-xs font-semibold mb-2 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
            {isConnected ? 'Live Updates' : 'Reconnecting...'}
          </div>
        </div>

        {/* Real-time Status */}
        <div className="bg-card/95 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-border/50">
          <div className="text-sm font-semibold mb-2 flex items-center gap-2">
            <div className="w-2 h-2 bg-marta-green rounded-full animate-pulse"></div>
            Live System Status
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Stations:</span>
              <span className="font-medium">{martaStops.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Rail Lines:</span>
              <span className="font-medium">{martaRoutes.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Dynamic Stops:</span>
              <span className="font-medium text-pink-500">{dynamicStops.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Live Vehicles:</span>
              <span className="font-medium text-green-500">{vehicleMarkersRef.current.size}</span>
            </div>
          </div>
        </div>

        {/* Route Legend */}
        <div className="bg-card/95 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-border/50">
          <div className="text-sm font-semibold mb-3">Rail Lines</div>
          <div className="space-y-2">
            {martaRoutes.map(route => (
              <div 
                key={route.id} 
                className="flex items-center gap-2 text-xs cursor-pointer hover:opacity-80 transition-opacity"
                onClick={() => setSelectedRoute(route)}
              >
                <div 
                  className="w-3 h-3 rounded-full shadow-sm"
                  style={{ backgroundColor: route.color }}
                />
                <span className={selectedRoute?.id === route.id ? 'font-bold' : ''}>
                  {route.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Add CSS for pulse animation */}
      <style>{`
        @keyframes pulse {
          0% {
            box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
          }
          70% {
            box-shadow: 0 0 0 10px rgba(76, 175, 80, 0);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
          }
        }
      `}</style>
    </div>
  );
};