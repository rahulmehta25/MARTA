import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface NotificationRequest {
  type: 'delay' | 'arrival' | 'alert' | 'system'
  title: string
  body: string
  userId?: string
  stationId?: string
  data?: Record<string, any>
}

interface PushSubscription {
  endpoint: string
  keys: {
    p256dh: string
    auth: string
  }
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Handle different endpoints
    const url = new URL(req.url)
    const path = url.pathname.split('/').pop()

    switch (path) {
      case 'subscribe':
        // Register push subscription
        const { subscription, userId } = await req.json()
        
        // Store subscription in database
        const { error: subError } = await supabase
          .from('push_subscriptions')
          .upsert({
            user_id: userId || 'anonymous',
            endpoint: subscription.endpoint,
            p256dh: subscription.keys.p256dh,
            auth: subscription.keys.auth,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }, {
            onConflict: 'endpoint'
          })

        if (subError) throw subError

        return new Response(
          JSON.stringify({ success: true, message: 'Subscription registered' }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )

      case 'notify':
        // Send push notification
        const notification: NotificationRequest = await req.json()
        
        // Get relevant subscriptions
        let query = supabase.from('push_subscriptions').select('*')
        
        if (notification.userId) {
          query = query.eq('user_id', notification.userId)
        }

        const { data: subscriptions, error } = await query
        
        if (error) throw error

        // Send notifications to all relevant subscriptions
        const results = await Promise.allSettled(
          subscriptions.map(async (sub) => {
            const pushSub: PushSubscription = {
              endpoint: sub.endpoint,
              keys: {
                p256dh: sub.p256dh,
                auth: sub.auth
              }
            }

            // Create notification payload
            const payload = JSON.stringify({
              title: notification.title,
              body: notification.body,
              icon: '/icons/icon-192x192.png',
              badge: '/icons/badge-72x72.png',
              data: {
                ...notification.data,
                type: notification.type,
                stationId: notification.stationId,
                timestamp: new Date().toISOString()
              },
              actions: [
                {
                  action: 'view',
                  title: 'View Details'
                },
                {
                  action: 'dismiss',
                  title: 'Dismiss'
                }
              ]
            })

            // Send via web push protocol (simplified for demo)
            const response = await fetch(pushSub.endpoint, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'TTL': '86400', // 24 hours
              },
              body: payload
            })

            return response.ok
          })
        )

        const successCount = results.filter(r => r.status === 'fulfilled' && r.value).length

        // Log notification in database
        await supabase.from('notification_logs').insert({
          type: notification.type,
          title: notification.title,
          body: notification.body,
          recipients_count: subscriptions.length,
          success_count: successCount,
          created_at: new Date().toISOString()
        })

        return new Response(
          JSON.stringify({ 
            success: true, 
            sent: successCount,
            total: subscriptions.length 
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )

      case 'check-delays':
        // Automated delay notification checker
        const { data: delays } = await supabase
          .from('delay_patterns')
          .select('*')
          .gte('avg_delay', 5) // Delays >= 5 minutes
          .gte('created_at', new Date(Date.now() - 3600000).toISOString()) // Last hour

        if (delays && delays.length > 0) {
          // Send notifications for significant delays
          for (const delay of delays) {
            const notifyPayload: NotificationRequest = {
              type: 'delay',
              title: `${delay.line} Line Delays`,
              body: `Average delay of ${Math.round(delay.avg_delay)} minutes at ${delay.station_name}`,
              data: {
                line: delay.line,
                station: delay.station_name,
                avgDelay: delay.avg_delay
              }
            }

            // Send to all subscribed users
            await fetch(`${url.origin}/push-notify/notify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': req.headers.get('Authorization') || ''
              },
              body: JSON.stringify(notifyPayload)
            })
          }
        }

        return new Response(
          JSON.stringify({ 
            success: true, 
            delaysFound: delays?.length || 0 
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )

      default:
        return new Response(
          JSON.stringify({ error: 'Invalid endpoint' }),
          { 
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            status: 404
          }
        )
    }
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500
      }
    )
  }
})