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

    // Get recent performance metrics
    const { data: metrics, error: metricsError } = await supabase
      .from('performance_metrics')
      .select('*')
      .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
      .order('on_time_percentage', { ascending: true })

    if (metricsError) throw metricsError

    // Get delay patterns
    const { data: patterns, error: patternsError } = await supabase
      .from('delay_patterns')
      .select('*')
      .order('frequency', { ascending: false })
      .limit(5)

    if (patternsError) throw patternsError

    const insights = []

    // Generate performance insights
    if (metrics && metrics.length > 0) {
      // Worst performing station
      const worst = metrics[0]
      if (worst && worst.on_time_percentage < 70) {
        insights.push({
          type: 'performance',
          message: `${worst.station_id} has only ${worst.on_time_percentage}% on-time performance`,
          severity: 'warning'
        })
      }

      // Best performing station
      const best = metrics[metrics.length - 1]
      if (best && best.on_time_percentage > 85) {
        insights.push({
          type: 'performance',
          message: `${best.station_id} achieving ${best.on_time_percentage}% on-time rate`,
          severity: 'success'
        })
      }

      // System-wide performance
      const avgOnTime = metrics.reduce((sum, m) => sum + (m.on_time_percentage || 0), 0) / metrics.length
      insights.push({
        type: 'health',
        message: `System-wide on-time performance: ${avgOnTime.toFixed(1)}%`,
        severity: avgOnTime > 75 ? 'info' : 'warning'
      })
    }

    // Generate pattern insights
    if (patterns && patterns.length > 0) {
      const topPattern = patterns[0]
      insights.push({
        type: 'pattern',
        message: `Recurring ${topPattern.pattern_type} delays on ${topPattern.line} line (${topPattern.frequency}x)`,
        severity: 'warning'
      })
    }

    // Add ML status
    const { data: models } = await supabase
      .from('ml_models')
      .select('*')
      .eq('is_active', true)
      .single()

    if (models) {
      insights.push({
        type: 'ml',
        message: `ML predictions active with ${models.accuracy}% accuracy`,
        severity: 'info'
      })
    }

    return new Response(
      JSON.stringify({
        insights_count: insights.length,
        insights: insights,
        generated_at: new Date().toISOString()
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