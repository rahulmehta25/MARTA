#!/bin/bash

echo "🗺️ MARTA Mapbox Token Update Script"
echo "===================================="
echo ""
echo "This script will update your Mapbox token in:"
echo "1. Local .env file"
echo "2. Vercel environment variables"
echo "3. Redeploy the app"
echo ""

# Prompt for token
read -p "Enter your Mapbox token (starts with pk.): " MAPBOX_TOKEN

if [[ ! $MAPBOX_TOKEN == pk.* ]]; then
    echo "❌ Error: Token should start with 'pk.'"
    exit 1
fi

echo ""
echo "Updating local .env file..."
cat > .env << EOF
# MARTA Frontend Environment Variables

# Mapbox Configuration
VITE_MAPBOX_TOKEN=$MAPBOX_TOKEN

# Backend API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_KEY=

# Development Configuration
VITE_NODE_ENV=development
VITE_DEBUG=true
EOF

echo "✅ Updated .env"

echo ""
echo "Updating .env.production..."
cat > .env.production << EOF
# Production Environment Variables for MARTA App

# Mapbox Configuration
VITE_MAPBOX_TOKEN=$MAPBOX_TOKEN

# API Configuration
VITE_API_BASE_URL=https://api.marta.example.com
VITE_APP_NAME=MARTA Transit Analytics
VITE_APP_VERSION=1.0.0

# Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_REALTIME=false
EOF

echo "✅ Updated .env.production"

echo ""
echo "Removing old Vercel environment variable..."
vercel env rm VITE_MAPBOX_TOKEN production --yes 2>/dev/null

echo ""
echo "Adding new token to Vercel..."
echo "$MAPBOX_TOKEN" | vercel env add VITE_MAPBOX_TOKEN production

echo ""
echo "Building project..."
npm run build

echo ""
echo "Deploying to Vercel..."
vercel --prod --yes

echo ""
echo "Getting latest deployment URL..."
DEPLOYMENT_URL=$(vercel ls --yes 2>&1 | grep Ready | head -1 | awk '{print $2}')

if [ ! -z "$DEPLOYMENT_URL" ]; then
    echo ""
    echo "Updating marta-eta.vercel.app alias..."
    vercel alias set $DEPLOYMENT_URL marta-eta.vercel.app
    
    echo ""
    echo "✅ Complete! Your app should now have a working map at:"
    echo "   https://marta-eta.vercel.app"
    echo ""
    echo "Test the map at:"
    echo "   https://marta-eta.vercel.app/map-debug.html"
else
    echo "⚠️ Could not get deployment URL. Please check manually with: vercel ls"
fi