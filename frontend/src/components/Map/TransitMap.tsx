import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useAppStore } from '@/store';

// Using a demo Mapbox token for demonstration
const MAPBOX_TOKEN = 'pk.eyJ1IjoiZXhhbXBsZXMiLCJhIjoiY2p1dDBzcDlyMDFrYjN5bWtwMHE5eXBtMiJ9.YfLy-qDN3SJRU8bBVqAXBQ';

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

  // Enhanced demo data for MARTA system
  const demoStops = [
    { id: '1', name: 'Five Points', lat: 33.7537, lng: -84.3918, demandLevel: 'high' as const, currentPassengers: 45, predictedDemand: 52, routes: ['Red', 'Blue'] },
    { id: '2', name: 'Peachtree Center', lat: 33.7596, lng: -84.3875, demandLevel: 'medium' as const, currentPassengers: 32, predictedDemand: 38, routes: ['Red', 'Gold'] },
    { id: '3', name: 'Midtown', lat: 33.7806, lng: -84.3831, demandLevel: 'high' as const, currentPassengers: 41, predictedDemand: 47, routes: ['Red'] },
    { id: '4', name: 'North Avenue', lat: 33.7718, lng: -84.3854, demandLevel: 'low' as const, currentPassengers: 18, predictedDemand: 22, routes: ['Red', 'Gold'] },
    { id: '5', name: 'Buckhead', lat: 33.8484, lng: -84.3671, demandLevel: 'medium' as const, currentPassengers: 28, predictedDemand: 33, routes: ['Red'] },
    { id: '6', name: 'Lindbergh Center', lat: 33.8230, lng: -84.3694, demandLevel: 'high' as const, currentPassengers: 52, predictedDemand: 58, routes: ['Red', 'Gold'] },
    { id: '7', name: 'Arts Center', lat: 33.7891, lng: -84.3871, demandLevel: 'medium' as const, currentPassengers: 35, predictedDemand: 29, routes: ['Red'] },
    { id: '8', name: 'Civic Center', lat: 33.7664, lng: -84.3869, demandLevel: 'low' as const, currentPassengers: 15, predictedDemand: 18, routes: ['Red'] },
  ];

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

  const createMarkerElement = (stop: typeof demoStops[0]) => {
    const el = document.createElement('div');
    const isPulse = stop.demandLevel === 'high';
    
    el.innerHTML = `
      <div class="relative">
        ${isPulse ? `<div class="absolute inset-0 w-8 h-8 bg-red-500 rounded-full opacity-75 animate-ping"></div>` : ''}
        <div style="
          width: 24px;
          height: 24px;
          background: linear-gradient(135deg, ${getDemandColor(stop.demandLevel)}, ${getDemandColor(stop.demandLevel)}dd);
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

  // Token input component removed - using demo token
  useEffect(() => {
    if (!mapContainer.current) return;

    // Set the Mapbox access token
    mapboxgl.accessToken = MAPBOX_TOKEN;

    try {
      // Initialize map
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

        // Add transit stops with enhanced markers
        demoStops.forEach((stop) => {
          const el = createMarkerElement(stop);
          
          el.addEventListener('click', () => {
            setSelectedStop(stop);
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

          // Enhanced popup with better styling
          const popup = new mapboxgl.Popup({
            offset: 30,
            closeButton: true,
            closeOnClick: false,
            className: 'custom-popup'
          }).setHTML(`
            <div class="p-4 min-w-[200px]">
              <div class="flex items-center gap-2 mb-3">
                <div class="w-3 h-3 rounded-full" style="background-color: ${getDemandColor(stop.demandLevel)}"></div>
                <h3 class="font-bold text-base">${stop.name}</h3>
              </div>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-600">Current:</span>
                  <span class="font-semibold">${stop.currentPassengers} passengers</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Predicted:</span>
                  <span class="font-semibold">${stop.predictedDemand} passengers</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Demand:</span>
                  <span class="font-semibold capitalize" style="color: ${getDemandColor(stop.demandLevel)}">${stop.demandLevel}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Routes:</span>
                  <span class="font-semibold">${stop.routes.join(', ')}</span>
                </div>
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
              features: demoStops.map(stop => ({
                type: 'Feature',
                properties: {
                  demand: stop.predictedDemand,
                  weight: stop.demandLevel === 'high' ? 1 : stop.demandLevel === 'medium' ? 0.6 : 0.3
                },
                geometry: {
                  type: 'Point',
                  coordinates: [stop.lng, stop.lat]
                }
              }))
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

        // Add route lines
        const routeCoordinates = [
          [-84.3918, 33.7537], // Five Points
          [-84.3875, 33.7596], // Peachtree Center  
          [-84.3854, 33.7718], // North Avenue
          [-84.3831, 33.7806], // Midtown
          [-84.3871, 33.7891], // Arts Center
          [-84.3694, 33.8230], // Lindbergh
          [-84.3671, 33.8484], // Buckhead
        ];

        map.current!.addSource('route', {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: {},
            geometry: {
              type: 'LineString',
              coordinates: routeCoordinates
            }
          }
        });

        map.current!.addLayer({
          id: 'route',
          type: 'line',
          source: 'route',
          layout: {
            'line-join': 'round',
            'line-cap': 'round'
          },
          paint: {
            'line-color': '#2196F3',
            'line-width': 4,
            'line-opacity': 0.8
          }
        });
      });

    } catch (error) {
      console.error('Error initializing map:', error);
    }

    // Cleanup
    return () => {
      markersRef.current.forEach(marker => marker.remove());
      map.current?.remove();
    };
  }, [mapStyle, showDemandHeatmap]);

  const getDemandColor = (level: string) => {
    switch (level) {
      case 'high': return '#FF1744';
      case 'medium': return '#FF9800'; 
      case 'low': return '#00C853';
      default: return '#2196F3';
    }
  };

  return (
    <div className={`relative ${className}`}>
      <div 
        ref={mapContainer} 
        className="absolute inset-0 rounded-xl overflow-hidden shadow-lg"
      />
      
      {/* Map overlays */}
      <div className="absolute top-4 right-4 z-10 space-y-3">
        {/* Real-time Status */}
        <div className="bg-card/95 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-border/50">
          <div className="text-sm font-semibold mb-2 flex items-center gap-2">
            <div className="w-2 h-2 bg-marta-green rounded-full animate-pulse"></div>
            Live Status
          </div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">System:</span>
              <span className="text-marta-green font-medium">Operational</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Active Stops:</span>
              <span className="font-medium">{demoStops.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">High Demand:</span>
              <span className="text-marta-red font-medium">
                {demoStops.filter(s => s.demandLevel === 'high').length}
              </span>
            </div>
          </div>
        </div>

        {/* Map Legend */}
        <div className="bg-card/95 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-border/50">
          <div className="text-sm font-semibold mb-3">Demand Levels</div>
          <div className="space-y-2">
            {[
              { level: 'high', color: '#FF1744', label: 'High' },
              { level: 'medium', color: '#FF9800', label: 'Medium' },
              { level: 'low', color: '#00C853', label: 'Low' }
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