import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface SubscriptionRequest {
  channel: 'arrivals' | 'delays' | 'alerts'
  stationId?: string
  lineColor?: string
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { channel, stationId, lineColor } = await req.json() as SubscriptionRequest

    // Get Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Create SSE response
    const encoder = new TextEncoder()
    const body = new ReadableStream({
      async start(controller) {
        // Send initial connection message
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ 
          type: 'connected', 
          channel,
          timestamp: new Date().toISOString() 
        })}\n\n`))

        // Set up real-time subscription based on channel
        let subscription: any

        switch (channel) {
          case 'arrivals':
            // Subscribe to arrival updates for specific station
            subscription = supabase
              .channel(`arrivals:${stationId || 'all'}`)
              .on(
                'postgres_changes',
                {
                  event: '*',
                  schema: 'public',
                  table: 'train_arrivals',
                  filter: stationId ? `station_id=eq.${stationId}` : undefined
                },
                (payload) => {
                  controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                    type: 'arrival_update',
                    data: payload.new,
                    timestamp: new Date().toISOString()
                  })}\n\n`))
                }
              )
              .subscribe()
            break

          case 'delays':
            // Subscribe to delay pattern updates
            subscription = supabase
              .channel(`delays:${lineColor || 'all'}`)
              .on(
                'postgres_changes',
                {
                  event: '*',
                  schema: 'public',
                  table: 'delay_patterns',
                  filter: lineColor ? `line=eq.${lineColor}` : undefined
                },
                (payload) => {
                  controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                    type: 'delay_update',
                    data: payload.new,
                    timestamp: new Date().toISOString()
                  })}\n\n`))
                }
              )
              .subscribe()
            break

          case 'alerts':
            // Subscribe to system alerts and notifications
            subscription = supabase
              .channel('alerts:system')
              .on(
                'postgres_changes',
                {
                  event: 'INSERT',
                  schema: 'public',
                  table: 'system_alerts'
                },
                (payload) => {
                  controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                    type: 'alert',
                    data: payload.new,
                    timestamp: new Date().toISOString()
                  })}\n\n`))
                }
              )
              .subscribe()
            break
        }

        // Send heartbeat every 30 seconds to keep connection alive
        const heartbeatInterval = setInterval(() => {
          try {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({
              type: 'heartbeat',
              timestamp: new Date().toISOString()
            })}\n\n`))
          } catch (e) {
            // Connection closed, clean up
            clearInterval(heartbeatInterval)
            if (subscription) {
              supabase.removeChannel(subscription)
            }
          }
        }, 30000)

        // Also fetch and send current data immediately
        if (channel === 'arrivals' && stationId) {
          const { data: arrivals } = await supabase
            .from('train_arrivals')
            .select('*')
            .eq('station_id', stationId)
            .order('arrival_time', { ascending: true })
            .limit(10)

          if (arrivals) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({
              type: 'initial_data',
              data: arrivals,
              timestamp: new Date().toISOString()
            })}\n\n`))
          }
        }
      }
    })

    return new Response(body, {
      headers: {
        ...corsHeaders,
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    })
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