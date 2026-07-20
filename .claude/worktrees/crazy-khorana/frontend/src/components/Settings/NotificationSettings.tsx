import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Bell, BellOff, Smartphone, AlertCircle, TestTube } from 'lucide-react';
import { usePushNotifications } from '@/hooks/usePushNotifications';
import { toast } from '@/components/ui/use-toast';

export const NotificationSettings: React.FC = () => {
  const {
    isSupported,
    isSubscribed,
    subscribe,
    unsubscribe,
    sendTestNotification
  } = usePushNotifications();

  const handleToggle = async () => {
    if (isSubscribed) {
      await unsubscribe();
    } else {
      await subscribe();
    }
  };

  if (!isSupported) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            Notifications Not Supported
          </CardTitle>
          <CardDescription>
            Your browser doesn't support push notifications. Try using a modern browser like Chrome, Firefox, or Safari.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Notification Settings
        </CardTitle>
        <CardDescription>
          Manage your push notification preferences for real-time MARTA updates
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Main toggle */}
        <div className="flex items-center justify-between space-x-2">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              {isSubscribed ? (
                <Bell className="h-4 w-4 text-green-500" />
              ) : (
                <BellOff className="h-4 w-4 text-muted-foreground" />
              )}
              <Label htmlFor="notifications" className="text-base">
                Push Notifications
              </Label>
            </div>
            <p className="text-sm text-muted-foreground">
              Receive alerts about delays, arrivals, and service disruptions
            </p>
          </div>
          <Switch
            id="notifications"
            checked={isSubscribed}
            onCheckedChange={handleToggle}
          />
        </div>

        {isSubscribed && (
          <>
            {/* Notification types */}
            <div className="space-y-4 border-t pt-4">
              <h4 className="text-sm font-medium">Notification Types</h4>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="delays" className="text-sm">Delay Alerts</Label>
                    <p className="text-xs text-muted-foreground">
                      Get notified when trains are delayed by 5+ minutes
                    </p>
                  </div>
                  <Switch id="delays" defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="arrivals" className="text-sm">Arrival Updates</Label>
                    <p className="text-xs text-muted-foreground">
                      Real-time updates for your saved stations
                    </p>
                  </div>
                  <Switch id="arrivals" defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="service" className="text-sm">Service Alerts</Label>
                    <p className="text-xs text-muted-foreground">
                      Important service disruptions and maintenance
                    </p>
                  </div>
                  <Switch id="service" defaultChecked />
                </div>
              </div>
            </div>

            {/* Test notification */}
            <div className="border-t pt-4">
              <Button
                variant="outline"
                onClick={sendTestNotification}
                className="w-full"
              >
                <TestTube className="h-4 w-4 mr-2" />
                Send Test Notification
              </Button>
            </div>
          </>
        )}

        {/* Installation hint */}
        {!isSubscribed && (
          <div className="rounded-lg bg-secondary/50 p-4">
            <div className="flex gap-3">
              <Smartphone className="h-5 w-5 text-primary mt-0.5" />
              <div className="space-y-1">
                <p className="text-sm font-medium">
                  Enable notifications to:
                </p>
                <ul className="text-xs text-muted-foreground space-y-1 ml-4">
                  <li>• Get real-time delay alerts</li>
                  <li>• Receive arrival predictions</li>
                  <li>• Stay informed about service changes</li>
                  <li>• Work offline with cached data</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default NotificationSettings;