import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface SurgeDetectionRequest {
  location_id: string
  current_demand: number
  historical_baseline: number
  external_factors?: {
    weather_severity?: number
    traffic_index?: number
    event_proximity?: number
  }
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const request = await req.json() as SurgeDetectionRequest
    const { location_id, current_demand, historical_baseline, external_factors } = request

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!
    const supabase = createClient(supabaseUrl, supabaseAnonKey)

    // Calculate surge metrics
    const surgeRatio = current_demand / (historical_baseline || 1)
    const isSurge = surgeRatio > 1.5

    if (!isSurge) {
      return new Response(
        JSON.stringify({
          surge_detected: false,
          location_id,
          message: "No surge detected"
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 200
        }
      )
    }

    // Analyze surge characteristics
    const currentTime = new Date()
    const hour = currentTime.getHours()

    // Determine contributing factors
    const factors = []
    if ((hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19)) {
      factors.push("Rush hour traffic")
    }
    if (external_factors?.weather_severity && external_factors.weather_severity > 3) {
      factors.push("Severe weather conditions")
    }
    if (external_factors?.traffic_index && external_factors.traffic_index > 1.5) {
      factors.push("Heavy traffic congestion")
    }
    if (external_factors?.event_proximity) {
      factors.push("Nearby event")
    }
    if (factors.length === 0) {
      factors.push("Unexpected demand spike")
    }

    // Generate recommendations based on surge magnitude
    const recommendations = []
    if (surgeRatio > 3.0) {
      recommendations.push("URGENT: Deploy 2-3 additional vehicles immediately")
      recommendations.push("Activate express service pattern")
      recommendations.push("Alert passengers via all channels")
      recommendations.push("Station additional staff at key stops")
    } else if (surgeRatio > 2.0) {
      recommendations.push("Deploy 1-2 additional vehicles within 15 minutes")
      recommendations.push("Consider skip-stop service")
      recommendations.push("Increase service frequency")
      recommendations.push("Monitor situation closely")
    } else {
      recommendations.push("Monitor situation for escalation")
      recommendations.push("Prepare reserve vehicles")
      recommendations.push("Alert dispatch team")
    }

    // Predict affected areas (simplified)
    const affectedAreas = [location_id]
    if (surgeRatio > 2.0) {
      affectedAreas.push(`${location_id}_upstream`, `${location_id}_downstream`)
    }

    // Calculate confidence based on data quality
    const confidence = Math.min(0.95, 0.5 + (surgeRatio - 1.5) * 0.3)

    // Store surge event for analysis
    const surgeEvent = {
      location_id,
      surge_magnitude: surgeRatio,
      surge_start_time: currentTime.toISOString(),
      confidence,
      contributing_factors: factors,
      affected_areas: affectedAreas,
      recommended_actions: recommendations,
      external_factors
    }

    const { error: insertError } = await supabase
      .from('surge_events')
      .insert([surgeEvent])

    if (insertError) console.error('Error storing surge event:', insertError)

    // Send real-time alert via broadcast
    const channel = supabase.channel('surge-alerts')
    channel.send({
      type: 'broadcast',
      event: 'surge-detected',
      payload: surgeEvent
    })

    return new Response(
      JSON.stringify({
        surge_detected: true,
        ...surgeEvent
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200
      }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400
      }
    )
  }
})