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
    // Create Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? ''
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    const supabase = createClient(supabaseUrl, supabaseKey)

    // Get delay patterns from database
    const { data: patterns, error: patternsError } = await supabase
      .from('delay_patterns')
      .select('*')
      .order('last_observed', { ascending: false })
      .limit(10)

    if (patternsError) throw patternsError

    // Get recent delays to identify new patterns
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
    
    const { data: recentDelays, error: delaysError } = await supabase
      .from('arrivals')
      .select('*')
      .gt('delay_seconds', 300) // More than 5 minutes
      .gte('collected_at', since)
      .order('collected_at', { ascending: false })

    if (delaysError) throw delaysError

    // Analyze delays by line and station
    const lineDelays: Record<string, any[]> = {}
    const stationDelays: Record<string, any[]> = {}
    
    for (const delay of recentDelays || []) {
      // Group by line
      if (!lineDelays[delay.line]) {
        lineDelays[delay.line] = []
      }
      lineDelays[delay.line].push(delay)
      
      // Group by station
      if (!stationDelays[delay.station_id]) {
        stationDelays[delay.station_id] = []
      }
      stationDelays[delay.station_id].push(delay)
    }

    // Identify cascade patterns (delays affecting multiple stations on same line)
    const cascadePatterns = []
    for (const [line, delays] of Object.entries(lineDelays)) {
      if (delays.length >= 3) {
        // Check if delays happened within 30 minutes of each other
        const sortedDelays = delays.sort((a, b) => 
          new Date(a.collected_at).getTime() - new Date(b.collected_at).getTime()
        )
        
        const stations = [...new Set(delays.map(d => d.station_id))]
        if (stations.length >= 2) {
          const avgDelay = delays.reduce((sum, d) => sum + d.delay_seconds, 0) / delays.length
          
          cascadePatterns.push({
            type: 'cascade',
            line,
            stations,
            frequency: delays.length,
            average_delay: Math.round(avgDelay),
            last_occurred: sortedDelays[sortedDelays.length - 1].collected_at,
            severity: avgDelay > 600 ? 'high' : avgDelay > 300 ? 'medium' : 'low'
          })
        }
      }
    }

    // Identify hotspot patterns (stations with frequent delays)
    const hotspotPatterns = []
    for (const [station, delays] of Object.entries(stationDelays)) {
      if (delays.length >= 5) {
        const avgDelay = delays.reduce((sum, d) => sum + d.delay_seconds, 0) / delays.length
        const lines = [...new Set(delays.map(d => d.line))]
        
        hotspotPatterns.push({
          type: 'hotspot',
          station,
          lines,
          frequency: delays.length,
          average_delay: Math.round(avgDelay),
          peak_hours: getMostCommonHours(delays),
          severity: delays.length > 10 ? 'high' : 'medium'
        })
      }
    }

    // Combine patterns
    const allPatterns = [
      ...cascadePatterns,
      ...hotspotPatterns,
      ...(patterns || []).map(p => ({
        type: p.pattern_type,
        line: p.line,
        stations: p.affected_stations,
        frequency: p.frequency,
        average_delay: p.avg_impact_minutes * 60,
        last_occurred: p.last_observed,
        from_database: true
      }))
    ]

    // Sort by severity and frequency
    allPatterns.sort((a, b) => b.frequency - a.frequency)

    // Generate insights
    const insights = []
    
    if (cascadePatterns.length > 0) {
      const worst = cascadePatterns[0]
      insights.push({
        type: 'cascade_alert',
        message: `Cascade delays detected on ${worst.line} line affecting ${worst.stations.length} stations`,
        severity: worst.severity,
        affected_stations: worst.stations
      })
    }
    
    if (hotspotPatterns.length > 0) {
      const worst = hotspotPatterns[0]
      insights.push({
        type: 'hotspot_alert',
        message: `${worst.station} experiencing frequent delays (${worst.frequency} in last 24h)`,
        severity: worst.severity,
        peak_hours: worst.peak_hours
      })
    }

    return new Response(
      JSON.stringify({
        patterns_count: allPatterns.length,
        patterns: allPatterns.slice(0, 10),
        insights,
        analysis_period: '24_hours',
        timestamp: new Date().toISOString()
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    )
  }
})

function getMostCommonHours(delays: any[]): number[] {
  const hourCounts: Record<number, number> = {}
  
  for (const delay of delays) {
    const hour = new Date(delay.collected_at).getHours()
    hourCounts[hour] = (hourCounts[hour] || 0) + 1
  }
  
  // Get top 3 hours
  return Object.entries(hourCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([hour]) => parseInt(hour))
}