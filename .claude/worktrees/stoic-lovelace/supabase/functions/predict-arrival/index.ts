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
    const line = url.searchParams.get('line')
    const direction = url.searchParams.get('direction') || 'N'

    if (!stationId || !line) {
      throw new Error('station_id and line are required')
    }

    // Create Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? ''
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Get recent arrivals for this station/line to calculate patterns
    const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
    
    const { data: recentArrivals, error: arrivalError } = await supabase
      .from('arrivals')
      .select('*')
      .eq('station_id', stationId)
      .eq('line', line)
      .gte('collected_at', since)
      .order('collected_at', { ascending: false })
      .limit(100)

    if (arrivalError) throw arrivalError

    // Calculate prediction based on historical patterns
    const now = new Date()
    const hour = now.getHours()
    const dayOfWeek = now.getDay()
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6
    const isRushHour = (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19)

    // Filter arrivals for similar conditions
    const similarArrivals = recentArrivals.filter(arrival => {
      const arrivalDate = new Date(arrival.collected_at)
      const arrivalHour = arrivalDate.getHours()
      const arrivalDay = arrivalDate.getDay()
      const arrivalIsWeekend = arrivalDay === 0 || arrivalDay === 6
      
      return (
        Math.abs(arrivalHour - hour) <= 1 && // Similar hour
        arrivalIsWeekend === isWeekend // Same weekend/weekday pattern
      )
    })

    // Calculate average waiting time
    let predictedSeconds = 600 // Default 10 minutes
    let confidence = 0.5

    if (similarArrivals.length > 0) {
      const waitTimes = similarArrivals
        .map(a => a.waiting_seconds)
        .filter(w => w > 0 && w < 3600) // Filter outliers

      if (waitTimes.length > 0) {
        predictedSeconds = Math.round(
          waitTimes.reduce((sum, w) => sum + w, 0) / waitTimes.length
        )
        
        // Calculate confidence based on sample size and variance
        const variance = waitTimes.reduce((sum, w) => 
          sum + Math.pow(w - predictedSeconds, 2), 0
        ) / waitTimes.length
        
        const stdDev = Math.sqrt(variance)
        const sampleSizeFactor = Math.min(waitTimes.length / 20, 1)
        const varianceFactor = Math.max(0, 1 - (stdDev / predictedSeconds))
        
        confidence = Math.round((sampleSizeFactor * 0.5 + varianceFactor * 0.5) * 100) / 100
      }
    }

    // Adjust for rush hour
    if (isRushHour) {
      predictedSeconds = Math.round(predictedSeconds * 1.2)
    }

    // Check if we have an ML model prediction
    const { data: mlModel } = await supabase
      .from('ml_models')
      .select('*')
      .eq('model_type', 'arrival_prediction')
      .eq('is_active', true)
      .single()

    let method = 'statistical'
    if (mlModel && mlModel.accuracy > 70) {
      method = 'ml_enhanced'
      confidence = Math.max(confidence, mlModel.accuracy / 100)
    }

    // Store prediction for validation
    const prediction = {
      station_id: stationId,
      line,
      direction,
      predicted_arrival: new Date(Date.now() + predictedSeconds * 1000).toISOString(),
      predicted_seconds: predictedSeconds,
      confidence,
      prediction_method: method,
      model_version: mlModel?.version || '1.0.0',
      factors: {
        is_rush_hour: isRushHour,
        is_weekend: isWeekend,
        sample_size: similarArrivals.length,
        hour_of_day: hour
      }
    }

    // Store prediction
    await supabase.from('arrival_predictions').insert({
      station_id: stationId,
      line,
      predicted_arrival: prediction.predicted_arrival,
      confidence,
      prediction_method: method,
      model_version: prediction.model_version
    })

    return new Response(
      JSON.stringify(prediction),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    )
  }
})