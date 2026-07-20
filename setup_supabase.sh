#!/bin/bash

# MARTA Analytics - Supabase Setup Script

echo "🚀 MARTA Analytics - Supabase Setup"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.supabase .env
fi

# Prompt for Supabase credentials
echo "Please enter your Supabase project details:"
echo "(You can find these in your Supabase project settings)"
echo ""

read -p "Enter your Supabase Project URL (e.g., https://xxx.supabase.co): " SUPABASE_URL
read -p "Enter your Supabase Anon Key: " SUPABASE_ANON_KEY
read -p "Enter your Supabase Service Role Key (optional, for admin tasks): " SUPABASE_SERVICE_KEY

# Update .env file
echo ""
echo "Updating .env file..."

# Create a temporary file with the updates
cat > .env.supabase.temp << EOF
# Supabase Configuration for MARTA Analytics

# Backend Configuration
SUPABASE_URL=$SUPABASE_URL
SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY

# Frontend Configuration
VITE_SUPABASE_URL=$SUPABASE_URL
VITE_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY

# Edge Functions URLs
VITE_DEMAND_FORECAST_URL=$SUPABASE_URL/functions/v1/demand-forecast
VITE_SURGE_DETECTION_URL=$SUPABASE_URL/functions/v1/surge-detection
VITE_ROUTE_OPTIMIZATION_URL=$SUPABASE_URL/functions/v1/route-optimization

# Real-time Configuration
VITE_ENABLE_REALTIME=true
VITE_REALTIME_CHANNEL=marta-updates

# Keep existing MARTA API configuration
EOF

# Append MARTA configuration from existing .env
echo "" >> .env.supabase.temp
echo "# MARTA API Configuration (preserved from original)" >> .env.supabase.temp
grep -E "MARTA_|VITE_MAPBOX" .env >> .env.supabase.temp 2>/dev/null || true

# Backup existing .env
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "Backed up existing .env file"
fi

# Replace .env with new configuration
mv .env.supabase.temp .env

echo "✅ .env file updated with Supabase configuration"
echo ""

# Update frontend .env
if [ -d "frontend" ]; then
    echo "Updating frontend/.env.local..."
    cat > frontend/.env.local << EOF
# Frontend Environment Variables
VITE_SUPABASE_URL=$SUPABASE_URL
VITE_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
VITE_MAPBOX_TOKEN=$(grep VITE_MAPBOX_TOKEN .env | cut -d= -f2)
VITE_ENABLE_REALTIME=true
EOF
    echo "✅ Frontend configuration updated"
fi

echo ""
echo "🎯 Next Steps:"
echo "=============="
echo ""
echo "1. Deploy database migrations:"
echo "   supabase db push"
echo ""
echo "2. Deploy Edge Functions:"
echo "   supabase functions deploy demand-forecast"
echo "   supabase functions deploy surge-detection"
echo ""
echo "3. Install frontend dependencies:"
echo "   cd frontend && npm install"
echo ""
echo "4. Start the frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "5. Test the ML endpoints:"
echo "   Visit http://localhost:5173 and check the ML Dashboard"
echo ""
echo "✨ Setup complete! Your Supabase backend is ready."