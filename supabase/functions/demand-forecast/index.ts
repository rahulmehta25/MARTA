import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const url = new URL(req.url)
    const stationId = url.searchParams.get('station_id')
    const date = url.searchParams.get('date') || new Date().toISOString().split('T')[0]
    const hour = parseInt(url.searchParams.get('hour') || new Date().getHours().toString())

    if (!stationId) {
      throw new Error('station_id is required')
    }

    // Create Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? ''
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Get historical data for this station at similar times
    const targetDate = new Date(date)
    const dayOfWeek = targetDate.getDay()
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6

    // Get arrivals from past 30 days for pattern analysis
    const since = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
    
    const { data: historicalData, error } = await supabase
      .from('arrivals')
      .select('*')
      .eq('station_id', stationId)
      .gte('collected_at', since)
      .order('collected_at', { ascending: false })

    if (error) throw error

    // Filter for similar conditions (same hour, weekend/weekday)
    const similarArrivals = historicalData.filter(arrival => {
      const arrivalDate = new Date(arrival.collected_at)
      const arrivalHour = arrivalDate.getHours()
      const arrivalDay = arrivalDate.getDay()
      const arrivalIsWeekend = arrivalDay === 0 || arrivalDay === 6
      
      return (
        arrivalHour === hour &&
        arrivalIsWeekend === isWeekend
      )
    })

    // Calculate demand metrics
    const trainsPerHour = similarArrivals.length > 0 
      ? similarArrivals.length / Math.max(1, similarArrivals.length / 10)
      : 4 // Default 4 trains per hour

    // Estimate ridership based on time patterns
    let baseRiders = 100
    let congestionLevel = 2
    let peakFactor = 1.0

    // Rush hour adjustments
    if ((hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19)) {
      peakFactor = isWeekend ? 1.5 : 3.0
      congestionLevel = isWeekend ? 3 : 5
    } else if (hour >= 10 && hour <= 16) {
      peakFactor = isWeekend ? 1.2 : 1.5
      congestionLevel = 2
    } else if (hour >= 20 || hour <= 6) {
      peakFactor = 0.5
      congestionLevel = 1
    }

    // Weekend adjustment
    if (isWeekend) {
      baseRiders *= 0.7
      congestionLevel = Math.max(1, congestionLevel - 1)
    }

    // Special events detection (based on unusual patterns)
    const avgDelays = similarArrivals.length > 0
      ? similarArrivals.reduce((sum, a) => sum + (a.delay_seconds || 0), 0) / similarArrivals.length
      : 0

    let eventMultiplier = 1.0
    let specialEvent = null
    
    if (avgDelays > 300) {
      eventMultiplier = 1.3
      specialEvent = 'High demand period detected'
      congestionLevel = Math.min(5, congestionLevel + 1)
    }

    const predictedRiders = Math.round(baseRiders * peakFactor * eventMultiplier)
    const predictedWaitTime = Math.round(60 * congestionLevel)

    // Calculate confidence based on data availability
    const dataSizeFactor = Math.min(similarArrivals.length / 50, 1)
    const confidence = Math.round((0.5 + dataSizeFactor * 0.5) * 100) / 100

    // Store forecast
    const forecast = {
      station_id: stationId,
      forecast_date: date,
      forecast_hour: hour,
      predicted_riders: predictedRiders,
      predicted_congestion_level: congestionLevel,
      predicted_wait_time_seconds: predictedWaitTime,
      trains_per_hour: Math.round(trainsPerHour),
      is_weekend: isWeekend,
      is_rush_hour: peakFactor >= 2.5,
      special_event: specialEvent,
      confidence,
      factors: {
        base_riders: baseRiders,
        peak_factor: peakFactor,
        event_multiplier: eventMultiplier,
        historical_samples: similarArrivals.length,
        avg_historical_delay: Math.round(avgDelays)
      },
      recommendations: generateRecommendations(congestionLevel, hour, isWeekend)
    }

    // Store in database
    await supabase.from('demand_forecasts').upsert({
      station_id: stationId,
      forecast_date: date,
      forecast_hour: hour,
      predicted_riders: predictedRiders,
      predicted_congestion_level: congestionLevel,
      predicted_wait_time_seconds: predictedWaitTime,
      is_holiday: false,
      is_event_day: specialEvent !== null,
      confidence
    }, {
      onConflict: 'station_id,forecast_date,forecast_hour'
    })

    return new Response(
      JSON.stringify(forecast),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    )
  }
})

function generateRecommendations(congestionLevel: number, hour: number, isWeekend: boolean): string[] {
  const recommendations = []
  
  if (congestionLevel >= 4) {
    recommendations.push('Consider alternative travel times to avoid crowds')
    if (hour >= 7 && hour <= 9) {
      recommendations.push('Travel before 7 AM or after 9 AM for less crowding')
    }
    if (hour >= 17 && hour <= 19) {
      recommendations.push('Travel before 5 PM or after 7 PM for comfort')
    }
  }
  
  if (congestionLevel <= 2) {
    recommendations.push('Good time to travel - low congestion expected')
  }
  
  if (isWeekend && hour >= 10 && hour <= 14) {
    recommendations.push('Popular weekend travel time - expect moderate crowds')
  }
  
  if (hour >= 22 || hour <= 5) {
    recommendations.push('Limited service hours - check schedule')
  }
  
  return recommendations
}