import React from 'react';
import { LucideIcon, Inbox, Search, FileX, Database, MapPin } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('empty-state', className)}>
      <Icon className="empty-state-icon" />
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-description">{description}</p>
      {action && (
        <Button onClick={action.onClick} className="mt-4" variant="outline">
          {action.label}
        </Button>
      )}
    </div>
  );
}

export function NoSearchResults({ query }: { query: string }) {
  return (
    <EmptyState
      icon={Search}
      title="No results found"
      description={`No stations or routes match "${query}". Try a different search term.`}
    />
  );
}

export function NoDataAvailable() {
  return (
    <EmptyState
      icon={Database}
      title="No data available"
      description="Data is currently unavailable. Please check back later or refresh the page."
    />
  );
}

export function NoRouteSelected() {
  return (
    <EmptyState
      icon={MapPin}
      title="No route selected"
      description="Select a route from the list to view its details and performance metrics."
    />
  );
}

export function NoStationSelected() {
  return (
    <EmptyState
      icon={MapPin}
      title="No station selected"
      description="Click on a station on the map or search for one to view details."
    />
  );
}

export function NoForecastData() {
  return (
    <EmptyState
      icon={FileX}
      title="No forecast data"
      description="Forecast data is not available for the selected date range or station."
    />
  );
}
