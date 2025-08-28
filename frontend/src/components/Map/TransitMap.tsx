import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useAppStore } from '@/store';
import { martaStops, martaRoutes } from '@/data/martaData';

// Get Mapbox token from environment variable or use public token
const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || 'pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw';

interface TransitMapProps {
  className?: string;
}

export const TransitMap: React.FC<TransitMapProps> = ({ className }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  
  const {
    mapStyle,
    selectedStop,
    selectedRoute,
    showDemandHeatmap,
    stops,
    routes,
    setSelectedStop,
    setSelectedRoute,
  } = useAppStore();

  // Get demand level based on number of routes (stations with more routes typically have higher demand)
  const getDemandLevel = (routeCount: number): 'high' | 'medium' | 'low' => {
    if (routeCount >= 3) return 'high';
    if (routeCount === 2) return 'medium';
    return 'low';
  };

  // Generate random passenger counts for demo
  const getPassengerCount = (demandLevel: string) => {
    switch(demandLevel) {
      case 'high': return Math.floor(Math.random() * 30) + 40;
      case 'medium': return Math.floor(Math.random() * 25) + 20;
      default: return Math.floor(Math.random() * 20) + 5;
    }
  };

  const getMapStyle = () => {
    switch (mapStyle) {
      case 'dark':
        return 'mapbox://styles/mapbox/dark-v10';
      case 'satellite':
        return 'mapbox://styles/mapbox/satellite-v9';
      default:
        return 'mapbox://styles/mapbox/light-v10';
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

  const createMarkerElement = (stop: any) => {
    const el = document.createElement('div');
    const isPulse = stop.demandLevel === 'high';
    
    // Determine marker color based on routes
    let markerColor = '#999999';
    if (stop.routes.length === 1) {
      markerColor = getRouteColor(stop.routes[0]);
    } else if (stop.routes.length > 1) {
      // Multi-line stations get a purple color
      markerColor = '#9C27B0';
    }
    
    el.innerHTML = `
      <div class="relative">
        ${isPulse ? `<div class="absolute inset-0 w-8 h-8 bg-red-500 rounded-full opacity-75 animate-ping"></div>` : ''}
        <div style="
          width: 24px;
          height: 24px;
          background: linear-gradient(135deg, ${markerColor}, ${markerColor}dd);
          border: 3px solid white;
          border-radius: 50%;
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
          ${stop.currentPassengers}
        </div>
      </div>
    `;
    return el;
  };

  // Initialize map with error handling
  useEffect(() => {
    if (!mapContainer.current) {
      console.error('Map container not found');
      return;
    }

    // Set the Mapbox access token
    mapboxgl.accessToken = MAPBOX_TOKEN;
    console.log('Initializing map with token:', MAPBOX_TOKEN.substring(0, 20) + '...');
    
    try {
      // Initialize map
      console.log('Creating map instance...');
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: getMapStyle(),
        center: [-84.3880, 33.7490], // Atlanta center
        zoom: 11,
        pitch: 0,
        bearing: 0,
      });
      console.log('Map instance created');

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
          // Add source for each route
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

          // Add layer for each route
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
              'line-width': [
                'case',
                ['boolean', ['feature-state', 'selected'], false],
                6,
                4
              ],
              'line-opacity': [
                'case',
                ['boolean', ['feature-state', 'selected'], false],
                1,
                0.7
              ]
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

        // Add all MARTA transit stops with enhanced markers
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
            // Smooth fly to selected stop
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

          // Enhanced popup with better styling and route colors
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
                <div class="flex justify-between">
                  <span class="text-gray-600">Predicted:</span>
                  <span class="font-semibold">${predictedDemand} passengers</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Demand:</span>
                  <span class="font-semibold capitalize" style="color: ${getDemandColor(demandLevel)}">${demandLevel}</span>
                </div>
                ${stop.parking ? '<div class="flex justify-between"><span class="text-gray-600">Features:</span><span class="font-semibold">🅿️ Parking Available</span></div>' : ''}
                ${stop.accessibility ? '<div class="flex justify-between"><span class="text-gray-600"></span><span class="font-semibold">♿ Accessible</span></div>' : ''}
              </div>
            </div>
          `);

          marker.setPopup(popup);
        });

        // Enhanced demand heatmap
        if (showDemandHeatmap) {
          map.current!.addSource('demand-heatmap', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: martaStops.map(stop => {
                const demandLevel = getDemandLevel(stop.routes.length);
                const weight = demandLevel === 'high' ? 1 : demandLevel === 'medium' ? 0.6 : 0.3;
                return {
                  type: 'Feature',
                  properties: {
                    demand: getPassengerCount(demandLevel),
                    weight: weight
                  },
                  geometry: {
                    type: 'Point',
                    coordinates: [stop.lng, stop.lat]
                  }
                };
              })
            }
          });

          map.current!.addLayer({
            id: 'demand-heatmap',
            type: 'heatmap',
            source: 'demand-heatmap',
            maxzoom: 15,
            paint: {
              'heatmap-weight': ['get', 'weight'],
              'heatmap-intensity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 1,
                15, 4
              ],
              'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0, 'rgba(0, 200, 83, 0)',
                0.1, 'rgba(0, 200, 83, 0.1)',
                0.3, 'rgba(255, 193, 7, 0.3)',
                0.5, 'rgba(255, 152, 0, 0.5)',
                0.7, 'rgba(255, 87, 34, 0.7)',
                1, 'rgba(244, 67, 54, 0.9)'
              ],
              'heatmap-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 30,
                15, 80
              ],
              'heatmap-opacity': 0.6
            }
          });
        }
      });

      // Handle selected route highlighting
      if (selectedRoute && map.current.isStyleLoaded()) {
        martaRoutes.forEach((route) => {
          if (map.current!.getLayer(`route-${route.id}`)) {
            map.current!.setPaintProperty(`route-${route.id}`, 'line-opacity', 
              route.id === selectedRoute.id ? 1 : 0.3
            );
            map.current!.setPaintProperty(`route-${route.id}`, 'line-width', 
              route.id === selectedRoute.id ? 6 : 3
            );
          }
        });
      }

    } catch (error) {
      console.error('Error initializing map:', error);
    }

    // Cleanup
    return () => {
      markersRef.current.forEach(marker => marker.remove());
      map.current?.remove();
    };
  }, [mapStyle, showDemandHeatmap, selectedRoute]);

  return (
    <div className={`relative w-full h-full ${className}`}>
      <div 
        ref={mapContainer} 
        className="w-full h-full rounded-xl overflow-hidden shadow-lg"
        style={{ minHeight: '400px' }}
      />
      
      {/* Map overlays */}
      <div className="absolute top-4 left-4 z-10 space-y-3">
        {/* Real-time Status */}
        <div className="bg-card/95 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-border/50">
          <div className="text-sm font-semibold mb-2 flex items-center gap-2">
            <div className="w-2 h-2 bg-marta-green rounded-full animate-pulse"></div>
            Live System Status
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">System:</span>
              <span className="text-marta-green font-medium">Operational</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Active Stations:</span>
              <span className="font-medium">{martaStops.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Rail Lines:</span>
              <span className="font-medium">{martaRoutes.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Transfer Stations:</span>
              <span className="text-purple-500 font-medium">
                {martaStops.filter(s => s.routes.length > 1).length}
              </span>
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

        {/* Demand Levels Legend */}
        <div className="bg-card/95 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-border/50">
          <div className="text-sm font-semibold mb-3">Demand Levels</div>
          <div className="space-y-2">
            {[
              { level: 'high', color: '#FF1744', label: 'High Demand' },
              { level: 'medium', color: '#FF9800', label: 'Medium Demand' },
              { level: 'low', color: '#00C853', label: 'Low Demand' }
            ].map(item => (
              <div key={item.level} className="flex items-center gap-2 text-xs">
                <div 
                  className="w-3 h-3 rounded-full shadow-sm"
                  style={{ backgroundColor: item.color }}
                />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};