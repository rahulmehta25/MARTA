import { useState, useEffect, useCallback } from 'react';
import { toast } from '@/components/ui/use-toast';

const PUBLIC_VAPID_KEY = 'BKd0G7kB6VQ2Tn8Mp3FH3KHDmLfnMlYYbwPvKJvUxR_7zCa8Xs6OFZjVfCqPqhcr4IcFLdilAuK6Qlx_orFOxdE';

export const usePushNotifications = () => {
  const [isSupported, setIsSupported] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscription, setSubscription] = useState<PushSubscription | null>(null);

  useEffect(() => {
    // Check if push notifications are supported
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      setIsSupported(true);
      checkSubscription();
    }
  }, []);

  const checkSubscription = async () => {
    try {
      const registration = await navigator.serviceWorker.ready;
      const sub = await registration.pushManager.getSubscription();
      setIsSubscribed(!!sub);
      setSubscription(sub);
    } catch (error) {
      console.error('Failed to check subscription:', error);
    }
  };

  const urlBase64ToUint8Array = (base64String: string) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  };

  const subscribe = async () => {
    if (!isSupported) {
      toast({
        title: 'Not supported',
        description: 'Push notifications are not supported in this browser',
        variant: 'destructive'
      });
      return;
    }

    try {
      // Request permission
      const permission = await Notification.requestPermission();
      
      if (permission !== 'granted') {
        toast({
          title: 'Permission denied',
          description: 'Please enable notifications to receive updates',
          variant: 'destructive'
        });
        return;
      }

      // Get service worker registration
      const registration = await navigator.serviceWorker.ready;

      // Subscribe to push notifications
      const sub = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY)
      });

      // Send subscription to server
      const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://vglychbweuowsovboxyf.supabase.co';
      const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

      const response = await fetch(`${SUPABASE_URL}/functions/v1/push-notify/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': SUPABASE_ANON_KEY
        },
        body: JSON.stringify({
          subscription: sub.toJSON(),
          userId: localStorage.getItem('userId') || 'anonymous'
        })
      });

      if (response.ok) {
        setIsSubscribed(true);
        setSubscription(sub);
        
        toast({
          title: 'Notifications enabled',
          description: 'You will receive updates about delays and arrivals',
        });
      }
    } catch (error) {
      console.error('Failed to subscribe:', error);
      toast({
        title: 'Subscription failed',
        description: 'Could not enable notifications. Please try again.',
        variant: 'destructive'
      });
    }
  };

  const unsubscribe = async () => {
    if (!subscription) return;

    try {
      await subscription.unsubscribe();
      setIsSubscribed(false);
      setSubscription(null);

      toast({
        title: 'Notifications disabled',
        description: 'You will no longer receive push notifications',
      });
    } catch (error) {
      console.error('Failed to unsubscribe:', error);
    }
  };

  const sendTestNotification = async () => {
    if (!isSubscribed) {
      toast({
        title: 'Not subscribed',
        description: 'Please enable notifications first',
        variant: 'destructive'
      });
      return;
    }

    const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://vglychbweuowsovboxyf.supabase.co';
    const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

    try {
      const response = await fetch(`${SUPABASE_URL}/functions/v1/push-notify/notify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': SUPABASE_ANON_KEY
        },
        body: JSON.stringify({
          type: 'system',
          title: 'Test Notification',
          body: 'This is a test notification from MARTA Transit',
          userId: localStorage.getItem('userId') || 'anonymous'
        })
      });

      if (response.ok) {
        toast({
          title: 'Test sent',
          description: 'Check your notifications',
        });
      }
    } catch (error) {
      console.error('Failed to send test:', error);
    }
  };

  return {
    isSupported,
    isSubscribed,
    subscribe,
    unsubscribe,
    sendTestNotification
  };
};