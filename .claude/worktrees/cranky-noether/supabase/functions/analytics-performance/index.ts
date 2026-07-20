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

    // Get performance metrics from the last 24 hours
    const { data: metrics, error: metricsError } = await supabase
      .from('performance_metrics')
      .select('*')
      .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
      .order('created_at', { ascending: false })

    if (metricsError) throw metricsError

    // Aggregate metrics by line
    const linePerformance: Record<string, any> = {}
    
    for (const metric of metrics || []) {
      const line = metric.line
      if (!linePerformance[line]) {
        linePerformance[line] = {
          stations: 0,
          total_on_time_pct: 0,
          total_reliability: 0,
          total_delay: 0
        }
      }
      linePerformance[line].stations++
      linePerformance[line].total_on_time_pct += metric.on_time_percentage || 0
      linePerformance[line].total_reliability += metric.reliability_score || 0
      linePerformance[line].total_delay += metric.avg_delay_seconds || 0
    }

    // Calculate averages
    for (const line in linePerformance) {
      const stats = linePerformance[line]
      if (stats.stations > 0) {
        stats.on_time_percentage = stats.total_on_time_pct / stats.stations
        stats.reliability_score = stats.total_reliability / stats.stations
        stats.avg_delay_seconds = stats.total_delay / stats.stations
        delete stats.total_on_time_pct
        delete stats.total_reliability
        delete stats.total_delay
      }
    }

    // Calculate system health
    const totalMetrics = metrics?.length || 0
    const avgOnTime = totalMetrics > 0
      ? metrics.reduce((sum, m) => sum + (m.on_time_percentage || 0), 0) / totalMetrics
      : 0

    let health_status = 'unknown'
    if (avgOnTime >= 90) health_status = 'excellent'
    else if (avgOnTime >= 75) health_status = 'good'
    else if (avgOnTime >= 60) health_status = 'fair'
    else health_status = 'poor'

    const response = {
      health_status,
      health_score: Math.round(avgOnTime),
      line_performance: linePerformance,
      total_stations_analyzed: totalMetrics,
      method: 'supabase_edge',
      timestamp: new Date().toISOString()
    }

    return new Response(
      JSON.stringify(response),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    )
  }
})