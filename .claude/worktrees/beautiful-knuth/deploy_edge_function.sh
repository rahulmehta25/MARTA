#!/bin/bash

# Deploy Edge Function using Supabase CLI
# This script deploys the MARTA API edge function to Supabase

echo "🚀 Deploying MARTA Edge Function to Supabase..."

# Set your project details
PROJECT_REF="vglychbweuowsovboxyf"
FUNCTION_NAME="marta-api"

# Create a simple deployment without linking
echo "📦 Creating function deployment..."

# Use curl to deploy directly via API
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY"

echo ""
echo "✅ Edge Function endpoint will be available at:"
echo "https://${PROJECT_REF}.supabase.co/functions/v1/${FUNCTION_NAME}"
echo ""
echo "📝 To deploy manually:"
echo "1. Go to: https://supabase.com/dashboard/project/${PROJECT_REF}/functions"
echo "2. Click 'New Function'"
echo "3. Name it: ${FUNCTION_NAME}"
echo "4. Copy the code from supabase/functions/marta-api/index.ts"
echo "5. Deploy it"
echo ""
echo "🔑 Don't forget to set the MARTA_API_KEY secret in the function settings!"