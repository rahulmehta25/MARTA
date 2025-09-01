import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

const MARTA_API_URL = 'https://developerservices.itsmarta.com:18096/itsmarta/railrealtimearrivals/developerservices/traindata'
const MARTA_API_KEY = 'ff98ada7-0436-42c5-b9bf-1071245ad1a0'

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const url = new URL(req.url)
    const station = url.searchParams.get('station')
    const line = url.searchParams.get('line')
    const direction = url.searchParams.get('direction')

    // Fetch from MARTA API
    const martaResponse = await fetch(`${MARTA_API_URL}?apiKey=${MARTA_API_KEY}`)
    if (!martaResponse.ok) {
      throw new Error('Failed to fetch MARTA data')
    }

    const martaData = await martaResponse.json()

    // Store in Supabase if configured
    const supabaseUrl = Deno.env.get('SUPABASE_URL')
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
    
    if (supabaseUrl && supabaseKey) {
      const supabase = createClient(supabaseUrl, supabaseKey)
      
      // Transform and store arrivals
      const arrivals = martaData.slice(0, 50).map((train: any) => ({
        station_id: train.STATION,
        line: train.LINE,
        destination: train.DESTINATION,
        direction: train.DIRECTION,
        event_time: train.EVENT_TIME,
        train_id: train.TRAIN_ID,
        waiting_seconds: parseInt(train.WAITING_SECONDS) || 0,
        waiting_time: train.WAITING_TIME,
        delay_seconds: parseInt(train.DELAY?.replace(/\D/g, '') || '0'),
        collected_at: new Date().toISOString()
      }))

      // Insert arrivals (ignore duplicates)
      await supabase.from('arrivals').insert(arrivals)
    }

    // Filter and format response
    let filteredData = martaData
    
    if (station) {
      filteredData = filteredData.filter((train: any) => 
        train.STATION?.toUpperCase().includes(station.toUpperCase())
      )
    }
    
    if (line) {
      filteredData = filteredData.filter((train: any) => 
        train.LINE === line.toUpperCase()
      )
    }
    
    if (direction) {
      filteredData = filteredData.filter((train: any) => 
        train.DIRECTION === direction.toUpperCase()
      )
    }

    // Format response
    const arrivals = filteredData.map((train: any) => ({
      station: train.STATION,
      line: train.LINE,
      destination: train.DESTINATION,
      direction: train.DIRECTION,
      event_time: train.EVENT_TIME,
      train_id: train.TRAIN_ID,
      waiting_seconds: parseInt(train.WAITING_SECONDS) || 0,
      waiting_time: train.WAITING_TIME,
      delay: train.DELAY || '0 Seconds',
      next_arrival: train.NEXT_ARR
    }))

    // Sort by waiting time
    arrivals.sort((a: any, b: any) => a.waiting_seconds - b.waiting_seconds)

    return new Response(
      JSON.stringify(arrivals),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    )
  }
})