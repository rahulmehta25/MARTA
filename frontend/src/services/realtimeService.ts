/**
 * Real-time Service for MARTA Transit Analytics Platform
 * Handles Supabase real-time subscriptions for live updates
 */

import { createClient, RealtimeChannel } from '@supabase/supabase-js';
import { SUPABASE_URL, SUPABASE_ANON_KEY } from '../config/api';

// Initialize Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

export interface RealtimeCallback<T = any> {
  (payload: T): void;
}

export interface RealtimeSubscription {
  channel: RealtimeChannel;
  unsubscribe: () => void;
}

class RealtimeService {
  private subscriptions: Map<string, RealtimeSubscription> = new Map();

  /**
   * Subscribe to demand predictions updates
   */
  subscribeToDemandPredictions(
    callback: RealtimeCallback,
    stopId?: string
  ): RealtimeSubscription {
    const channelName = `demand-predictions${stopId ? `-${stopId}` : ''}`;
    
    // Unsubscribe from existing subscription if any
    this.unsubscribe(channelName);

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'demand_predictions',
          filter: stopId ? `stop_id=eq.${stopId}` : undefined,
        },
        (payload) => {
          console.log('Demand prediction update:', payload);
          callback(payload);
        }
      )
      .subscribe();

    const subscription: RealtimeSubscription = {
      channel,
      unsubscribe: () => {
        supabase.removeChannel(channel);
        this.subscriptions.delete(channelName);
      },
    };

    this.subscriptions.set(channelName, subscription);
    return subscription;
  }

  /**
   * Subscribe to surge events updates
   */
  subscribeToSurgeEvents(
    callback: RealtimeCallback,
    locationId?: string
  ): RealtimeSubscription {
    const channelName = `surge-events${locationId ? `-${locationId}` : ''}`;
    
    // Unsubscribe from existing subscription if any
    this.unsubscribe(channelName);

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'surge_events',
          filter: locationId ? `location_id=eq.${locationId}` : undefined,
        },
        (payload) => {
          console.log('Surge event update:', payload);
          callback(payload);
        }
      )
      .subscribe();

    const subscription: RealtimeSubscription = {
      channel,
      unsubscribe: () => {
        supabase.removeChannel(channel);
        this.subscriptions.delete(channelName);
      },
    };

    this.subscriptions.set(channelName, subscription);
    return subscription;
  }

  /**
   * Subscribe to crowding alerts updates
   */
  subscribeToCrowdingAlerts(
    callback: RealtimeCallback,
    stopId?: string
  ): RealtimeSubscription {
    const channelName = `crowding-alerts${stopId ? `-${stopId}` : ''}`;
    
    // Unsubscribe from existing subscription if any
    this.unsubscribe(channelName);

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'crowding_alerts',
          filter: stopId ? `stop_id=eq.${stopId}` : undefined,
        },
        (payload) => {
          console.log('Crowding alert update:', payload);
          callback(payload);
        }
      )
      .subscribe();

    const subscription: RealtimeSubscription = {
      channel,
      unsubscribe: () => {
        supabase.removeChannel(channel);
        this.subscriptions.delete(channelName);
      },
    };

    this.subscriptions.set(channelName, subscription);
    return subscription;
  }

  /**
   * Subscribe to route optimizations updates
   */
  subscribeToRouteOptimizations(
    callback: RealtimeCallback,
    routeId?: string
  ): RealtimeSubscription {
    const channelName = `route-optimizations${routeId ? `-${routeId}` : ''}`;
    
    // Unsubscribe from existing subscription if any
    this.unsubscribe(channelName);

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'route_optimizations',
          filter: routeId ? `route_id=eq.${routeId}` : undefined,
        },
        (payload) => {
          console.log('Route optimization update:', payload);
          callback(payload);
        }
      )
      .subscribe();

    const subscription: RealtimeSubscription = {
      channel,
      unsubscribe: () => {
        supabase.removeChannel(channel);
        this.subscriptions.delete(channelName);
      },
    };

    this.subscriptions.set(channelName, subscription);
    return subscription;
  }

  /**
   * Subscribe to fleet repositioning updates
   */
  subscribeToFleetRepositioning(
    callback: RealtimeCallback
  ): RealtimeSubscription {
    const channelName = 'fleet-repositioning';
    
    // Unsubscribe from existing subscription if any
    this.unsubscribe(channelName);

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'fleet_repositioning',
        },
        (payload) => {
          console.log('Fleet repositioning update:', payload);
          callback(payload);
        }
      )
      .subscribe();

    const subscription: RealtimeSubscription = {
      channel,
      unsubscribe: () => {
        supabase.removeChannel(channel);
        this.subscriptions.delete(channelName);
      },
    };

    this.subscriptions.set(channelName, subscription);
    return subscription;
  }

  /**
   * Subscribe to system status updates
   */
  subscribeToSystemStatus(callback: RealtimeCallback): RealtimeSubscription {
    const channelName = 'system-status';
    
    // Unsubscribe from existing subscription if any
    this.unsubscribe(channelName);

    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'current_system_status',
        },
        (payload) => {
          console.log('System status update:', payload);
          callback(payload);
        }
      )
      .subscribe();

    const subscription: RealtimeSubscription = {
      channel,
      unsubscribe: () => {
        supabase.removeChannel(channel);
        this.subscriptions.delete(channelName);
      },
    };

    this.subscriptions.set(channelName, subscription);
    return subscription;
  }

  /**
   * Unsubscribe from a specific channel
   */
  unsubscribe(channelName: string): void {
    const subscription = this.subscriptions.get(channelName);
    if (subscription) {
      subscription.unsubscribe();
    }
  }

  /**
   * Unsubscribe from all channels
   */
  unsubscribeAll(): void {
    this.subscriptions.forEach((subscription) => {
      subscription.unsubscribe();
    });
    this.subscriptions.clear();
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): 'connected' | 'disconnected' | 'connecting' {
    // This is a simplified status check
    // In a real implementation, you'd track the actual connection state
    return this.subscriptions.size > 0 ? 'connected' : 'disconnected';
  }

  /**
   * Get active subscriptions count
   */
  getActiveSubscriptionsCount(): number {
    return this.subscriptions.size;
  }
}

export const realtimeService = new RealtimeService();
export default realtimeService;


