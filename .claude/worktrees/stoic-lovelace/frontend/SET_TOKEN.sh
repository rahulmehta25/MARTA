#!/bin/bash
# Quick script to set your Mapbox token

read -p "Paste your new Mapbox token here: " TOKEN

# Update local .env
sed -i '' "s/VITE_MAPBOX_TOKEN=.*/VITE_MAPBOX_TOKEN=$TOKEN/" .env
sed -i '' "s/VITE_MAPBOX_TOKEN=.*/VITE_MAPBOX_TOKEN=$TOKEN/" .env.production

# Update Vercel
vercel env rm VITE_MAPBOX_TOKEN production --yes 2>/dev/null
echo "$TOKEN" | vercel env add VITE_MAPBOX_TOKEN production

# Deploy
vercel --prod --yes

echo "✅ Token updated and deploying!"