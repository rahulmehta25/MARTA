// Supabase Edge Function for MARTA Real-time API
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const url = new URL(req.url)
    const path = url.pathname.replace('/marta-api', '')

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_ANON_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Route handlers
    switch (path) {
      case '/arrivals':
      case '/':
        return await getArrivals(supabase)
      
      case '/stations':
        return await getStations(supabase)
      
      case '/collect':
        return await collectData(supabase)
      
      case '/metrics':
        return await getMetrics(supabase)
      
      case '/predictions':
        return await getPredictions(supabase, url)
      
      default:
        return new Response(
          JSON.stringify({ error: 'Not found' }),
          { 
            status: 404,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
    }
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})

async function getArrivals(supabase: any) {
  // Get recent arrivals from database
  const { data: recentArrivals, error: dbError } = await supabase
    .from('arrivals')
    .select('*')
    .order('collected_at', { ascending: false })
    .limit(300)

  if (dbError) {
    console.error('Database error:', dbError)
  }

  // Also fetch fresh data from MARTA API
  const martaApiKey = Deno.env.get('MARTA_API_KEY')
  const martaUrl = `https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata?apiKey=${martaApiKey}`
  
  try {
    const response = await fetch(martaUrl)
    const freshData = await response.json()
    
    // Store fresh data in background (don't wait)
    storeArrivals(supabase, freshData)
    
    // Return fresh data
    return new Response(
      JSON.stringify(freshData),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    // If MARTA API fails, return recent data from database
    if (recentArrivals && recentArrivals.length > 0) {
      // Transform to MARTA API format
      const transformed = recentArrivals.map((a: any) => ({
        STATION: a.station_id,
        LINE: a.line,
        DESTINATION: a.destination,
        DIRECTION: a.direction,
        NEXT_ARR: a.arrival_time,
        WAITING_SECONDS: a.waiting_seconds,
        TRAIN_ID: a.train_id,
        EVENT_TIME: a.event_time,
        DELAY: a.delay_seconds ? `${a.delay_seconds}` : '0'
      }))
      
      return new Response(
        JSON.stringify(transformed),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }
    
    throw error
  }
}

async function getStations(supabase: any) {
  const { data, error } = await supabase
    .from('stations')
    .select('*')
    .order('name')

  if (error) throw error

  return new Response(
    JSON.stringify(data),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function collectData(supabase: any) {
  const martaApiKey = Deno.env.get('MARTA_API_KEY')
  const martaUrl = `https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata?apiKey=${martaApiKey}`
  
  const response = await fetch(martaUrl)
  const data = await response.json()
  
  const stored = await storeArrivals(supabase, data)
  
  return new Response(
    JSON.stringify({ 
      message: 'Data collected successfully',
      count: data.length,
      stored: stored
    }),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function storeArrivals(supabase: any, arrivals: any[]) {
  try {
    // Transform and store arrivals
    const records = arrivals.map(arrival => ({
      station_id: arrival.STATION,
      line: arrival.LINE,
      destination: arrival.DESTINATION,
      direction: arrival.DIRECTION,
      arrival_time: arrival.NEXT_ARR,
      waiting_seconds: parseInt(arrival.WAITING_SECONDS || '0'),
      delay_seconds: parseInt(arrival.DELAY || '0'),
      train_id: arrival.TRAIN_ID,
      event_time: arrival.EVENT_TIME
    }))

    const { error } = await supabase
      .from('arrivals')
      .insert(records)

    if (error) {
      console.error('Error storing arrivals:', error)
      return false
    }

    // Update stations
    const stations = new Set(arrivals.map(a => a.STATION))
    for (const stationId of stations) {
      const stationArrivals = arrivals.filter(a => a.STATION === stationId)
      const lines = [...new Set(stationArrivals.map(a => a.LINE))]
      
      await supabase
        .from('stations')
        .upsert({
          station_id: stationId,
          name: stationId,
          lines: lines
        }, {
          onConflict: 'station_id'
        })
    }

    return true
  } catch (error) {
    console.error('Store error:', error)
    return false
  }
}

async function getMetrics(supabase: any) {
  // Get current system metrics using the view
  const { data, error } = await supabase
    .from('current_system_status')
    .select('*')
    .single()

  if (error) throw error

  return new Response(
    JSON.stringify(data),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function getPredictions(supabase: any, url: URL) {
  const stationId = url.searchParams.get('station_id')
  const line = url.searchParams.get('line')

  if (!stationId) {
    return new Response(
      JSON.stringify({ error: 'station_id parameter required' }),
      { 
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }

  // Call the prediction function in the database
  const { data, error } = await supabase
    .rpc('predict_next_arrival', {
      p_station_id: stationId,
      p_line: line
    })

  if (error) throw error

  return new Response(
    JSON.stringify(data),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}