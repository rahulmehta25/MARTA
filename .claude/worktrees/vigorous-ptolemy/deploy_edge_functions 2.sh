#!/bin/bash

# Deploy Supabase Edge Functions for MARTA Transit Analytics
# Ensure you have Supabase CLI installed and are logged in

echo "🚀 Deploying MARTA Transit Analytics Edge Functions..."

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI is not installed. Please install it first:"
    echo "   brew install supabase/tap/supabase"
    exit 1
fi

# Get project ID from environment or prompt
PROJECT_ID=${SUPABASE_PROJECT_ID:-"vglychbweuowsovboxyf"}
echo "📦 Using Supabase project: $PROJECT_ID"

# Deploy each edge function
echo ""
echo "1️⃣ Deploying marta-arrivals function..."
supabase functions deploy marta-arrivals --project-ref $PROJECT_ID

echo ""
echo "2️⃣ Deploying analytics-performance function..."
supabase functions deploy analytics-performance --project-ref $PROJECT_ID

echo ""
echo "3️⃣ Deploying analytics-insights function..."
supabase functions deploy analytics-insights --project-ref $PROJECT_ID

echo ""
echo "4️⃣ Deploying predict-arrival function..."
supabase functions deploy predict-arrival --project-ref $PROJECT_ID

echo ""
echo "5️⃣ Deploying delay-patterns function..."
supabase functions deploy delay-patterns --project-ref $PROJECT_ID

echo ""
echo "6️⃣ Deploying demand-forecast function..."
supabase functions deploy demand-forecast --project-ref $PROJECT_ID

echo ""
echo "7️⃣ Deploying realtime-subscribe function..."
supabase functions deploy realtime-subscribe --project-ref $PROJECT_ID

echo ""
echo "8️⃣ Deploying push-notify function..."
supabase functions deploy push-notify --project-ref $PROJECT_ID

echo ""
echo "✅ All edge functions deployed successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. Run the push notifications schema: psql < push_notifications_schema.sql"
echo "   2. Set environment variables in Supabase dashboard"
echo "   3. Test the functions using the provided URLs"
echo ""
echo "🔗 Function URLs:"
echo "   - https://$PROJECT_ID.supabase.co/functions/v1/marta-arrivals"
echo "   - https://$PROJECT_ID.supabase.co/functions/v1/analytics-performance"
echo "   - https://$PROJECT_ID.supabase.co/functions/v1/analytics-insights"
echo "   - https://$PROJECT_ID.supabase.co/functions/v1/predict-arrival"
echo "   - https://$PROJECT_ID.supabase.co/functions/v1/delay-patterns"
echo "   - https://$PROJECT_ID.supabase.co/functions/v1/demand-forecast"
echo "   - https://$PROJECT_ID.supabase.co/functions/v1/realtime-subscribe"
echo "   - https://$PROJECT_ID.supabase.co/functions/v1/push-notify"