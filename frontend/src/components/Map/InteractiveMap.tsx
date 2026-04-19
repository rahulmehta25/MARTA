import React, { useEffect, useRef, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useAppStore } from '@/store';
import { martaStops, martaRoutes } from '@/data/martaData';
import { MapSkeleton } from '@/components/common/LoadingState';
import { cn } from '@/lib/utils';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN ?? '';

interface InteractiveMapProps {
  className?: string;
  onStationSelect?: (stationId: string) => void;
  onRouteSelect?: (routeId: string) => void;
}

export function InteractiveMap({
  className,
  onStationSelect,
  onRouteSelect,
}: InteractiveMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);

  const {
    center,
    zoom,
    selectedStation,
    selectedRoute,
    showHeatmap,
    showStations,
    setSelectedStation,
    setSelectedRoute,
  } = useAppStore();

  const getRouteColor = useCallback((routeId: string): string => {
    const colors: Record<string, string> = {
      RED: '#dc2626',
      GOLD: '#f59e0b',
      BLUE: '#2563eb',
      GREEN: '#16a34a',
    };
    return colors[routeId] || '#6b7280';
  }, []);

  const getDemandColor = useCallback((routeCount: number): string => {
    if (routeCount >= 3) return '#dc2626';
    if (routeCount === 2) return '#f59e0b';
    return '#16a34a';
  }, []);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: center,
      zoom: zoom,
      attributionControl: false,
    });

    map.current.addControl(
      new mapboxgl.NavigationControl({ showCompass: false }),
      'top-right'
    );

    map.current.addControl(
      new mapboxgl.AttributionControl({ compact: true }),
      'bottom-right'
    );

    map.current.on('load', () => {
      setIsLoading(false);

      // Add route lines
      martaRoutes.forEach((route) => {
        const sourceId = `route-${route.id}`;
        const layerId = `route-line-${route.id}`;

        if (!map.current!.getSource(sourceId)) {
          map.current!.addSource(sourceId, {
            type: 'geojson',
            data: {
              type: 'Feature',
              properties: { name: route.name },
              geometry: {
                type: 'LineString',
                coordinates: route.coordinates,
              },
            },
          });

          map.current!.addLayer({
            id: layerId,
            type: 'line',
            source: sourceId,
            layout: {
              'line-join': 'round',
              'line-cap': 'round',
            },
            paint: {
              'line-color': route.color,
              'line-width': 4,
              'line-opacity': 0.8,
            },
          });

          map.current!.on('click', layerId, () => {
            const fullRoute = martaRoutes.find((r) => r.id === route.id);
            if (fullRoute) {
              setSelectedRoute(fullRoute as any);
              onRouteSelect?.(route.id);
            }
          });

          map.current!.on('mouseenter', layerId, () => {
            if (map.current) map.current.getCanvas().style.cursor = 'pointer';
          });

          map.current!.on('mouseleave', layerId, () => {
            if (map.current) map.current.getCanvas().style.cursor = '';
          });
        }
      });

      // Add station markers
      if (showStations) {
        addStationMarkers();
      }
    });

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      map.current?.remove();
      map.current = null;
    };
  }, []);

  const addStationMarkers = useCallback(() => {
    if (!map.current) return;

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    martaStops.forEach((stop) => {
      const el = document.createElement('div');
      el.className = 'station-marker';

      const color = stop.routes.length > 1
        ? '#6366f1'
        : getRouteColor(stop.routes[0]);

      el.innerHTML = `
        <div style="
          width: 12px;
          height: 12px;
          background: ${color};
          border: 2px solid white;
          border-radius: 50%;
          box-shadow: 0 1px 3px rgba(0,0,0,0.2);
          cursor: pointer;
          transition: transform 0.15s ease;
        "></div>
      `;

      el.addEventListener('mouseenter', () => {
        el.firstElementChild?.setAttribute(
          'style',
          el.firstElementChild.getAttribute('style') + 'transform: scale(1.3);'
        );
      });

      el.addEventListener('mouseleave', () => {
        el.firstElementChild?.setAttribute(
          'style',
          el.firstElementChild
            .getAttribute('style')
            ?.replace('transform: scale(1.3);', '') || ''
        );
      });

      el.addEventListener('click', () => {
        const stationData = {
          id: stop.id,
          name: stop.name,
          lat: stop.lat,
          lng: stop.lng,
          routes: stop.routes,
          type: stop.type,
          accessibility: stop.accessibility,
          parking: stop.parking,
        };
        setSelectedStation(stationData as any);
        onStationSelect?.(stop.id);

        map.current?.flyTo({
          center: [stop.lng, stop.lat],
          zoom: 14,
          duration: 800,
        });
      });

      const marker = new mapboxgl.Marker(el)
        .setLngLat([stop.lng, stop.lat])
        .addTo(map.current!);

      // Add popup
      const popup = new mapboxgl.Popup({
        offset: 15,
        closeButton: false,
        className: 'station-popup',
      }).setHTML(`
        <div style="padding: 8px 12px; font-family: Inter, system-ui, sans-serif;">
          <div style="font-weight: 600; font-size: 13px; color: #1f2937; margin-bottom: 4px;">
            ${stop.name}
          </div>
          <div style="display: flex; gap: 4px; flex-wrap: wrap;">
            ${stop.routes
              .map(
                (r) => `
              <span style="
                display: inline-block;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                color: white;
                background: ${getRouteColor(r)};
              ">${r}</span>
            `
              )
              .join('')}
          </div>
        </div>
      `);

      marker.setPopup(popup);
      markersRef.current.push(marker);
    });
  }, [showStations, getRouteColor, setSelectedStation, onStationSelect]);

  // Update markers when showStations changes
  useEffect(() => {
    if (!map.current || isLoading) return;

    if (showStations) {
      addStationMarkers();
    } else {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
    }
  }, [showStations, isLoading, addStationMarkers]);

  return (
    <div className={cn('relative h-full w-full', className)}>
      {isLoading && (
        <div className="absolute inset-0 z-10">
          <MapSkeleton />
        </div>
      )}
      <div ref={mapContainer} className="h-full w-full rounded-lg" />

      {/* Map controls overlay */}
      <div className="absolute bottom-4 left-4 flex flex-col gap-2">
        {/* Legend */}
        <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
          <p className="mb-2 text-xs font-medium text-muted-foreground">Lines</p>
          <div className="space-y-1.5">
            {martaRoutes.map((route) => (
              <button
                key={route.id}
                onClick={() => {
                  setSelectedRoute(route as any);
                  onRouteSelect?.(route.id);
                }}
                className={cn(
                  'flex items-center gap-2 text-xs transition-colors hover:opacity-80',
                  selectedRoute?.id === route.id && 'font-medium'
                )}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: route.color }}
                />
                <span>{route.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
