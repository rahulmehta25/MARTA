# MARTA Demand Forecasting & Route Optimization Platform

A professional React TypeScript frontend for transit analytics that helps MARTA optimize bus routes using machine learning predictions. Built with a map-first interface inspired by Uber's design philosophy.

![MARTA Analytics Dashboard](https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&h=400&fit=crop)

## 🚀 Features

### Interactive Map Dashboard
- **Mapbox GL JS Integration**: Real-time transit visualization with professional map controls
- **Demand-Based Markers**: Color-coded transit stops showing current demand levels
- **Route Overlays**: Visual representation of bus routes with capacity indicators
- **Live Heatmaps**: Dynamic demand intensity visualization with 30-second updates
- **Interactive Controls**: Click interactions for detailed stop/route information

### Search & Navigation
- **Uber-style Search**: Intelligent autocomplete with keyboard navigation
- **Multi-type Results**: Search stops, routes, and addresses seamlessly
- **Recent History**: localStorage-powered search history
- **Real-time Suggestions**: Dynamic filtering with instant results

### Bottom Drawer Interface
- **Four Main Tabs**: Overview, Demand Forecasting, Route Optimization, Analytics
- **Drag-to-Resize**: Smooth animations with Framer Motion
- **Real-time Data**: Live updates via WebSocket connection
- **Professional Metrics**: KPI dashboards and performance visualizations

### Data Visualization
- **Recharts Integration**: Beautiful, responsive charts for demand trends
- **Before/After Comparisons**: Visual optimization impact analysis
- **Performance Metrics**: Historical trends and real-time monitoring
- **Interactive Overlays**: Demand heatmaps with intensity gradients

## 🛠️ Technology Stack

- **React 18+** with TypeScript
- **Vite** for lightning-fast development
- **Tailwind CSS** with custom MARTA design system
- **Mapbox GL JS** for professional mapping
- **Zustand** for state management
- **React Query** for API state and caching
- **Framer Motion** for smooth animations
- **Recharts** for data visualization
- **shadcn/ui** for consistent UI components

## 🎨 Design System

Built with MARTA's official color palette:
- **MARTA Blue** (#2196F3) - Primary brand color
- **MARTA Green** (#00C853) - Success/optimal states
- **MARTA Orange** (#FF9800) - Warning/medium demand
- **MARTA Red** (#FF1744) - Critical/high demand

### Typography
- **Inter Font** - Clean, professional typography
- **Consistent Hierarchy** - Structured text sizing and spacing
- **4px Base Unit** - Mathematical spacing system

## 🏃‍♂️ Quick Start

### Prerequisites
- Node.js 16+ 
- npm or pnpm
- Mapbox account (for map functionality)

### Installation

```bash
# Clone the repository
git clone <project-url>
cd marta-analytics

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Add your Mapbox token to .env.local

# Start development server
npm run dev
```

### Environment Configuration

Create a `.env.local` file with:

```env
VITE_API_BASE_URL=http://localhost:8001
VITE_MAPBOX_TOKEN=pk.your_mapbox_token_here
VITE_DEFAULT_LAT=33.7490
VITE_DEFAULT_LNG=-84.3880
```

## 🔌 API Integration

The frontend integrates with the MARTA backend API running on `localhost:8001`:

### Key Endpoints
- `POST /optimize` - Route optimization
- `POST /simulate` - Route simulation  
- `GET /health` - System health check
- `GET /routes` - Transit routes data
- `GET /stops` - Transit stops data
- `GET /demand/predict` - Demand forecasting
- `WebSocket /ws/realtime` - Live data stream

### Real-time Features
- **WebSocket Connection**: Live data updates every 30 seconds
- **Optimistic Updates**: Smooth UX with immediate UI feedback
- **Error Handling**: Robust connection management and fallbacks
- **Offline Support**: PWA capabilities for offline functionality

## 📊 Core Functionality

### Demand Forecasting
- **Live Heatmaps**: Real-time demand visualization
- **1-4 Hour Predictions**: Stop-level passenger forecasting
- **Confidence Intervals**: Model accuracy and reliability metrics
- **Historical Comparisons**: Trend analysis and pattern recognition

### Route Optimization
- **Parameter Controls**: Configurable optimization constraints
- **Progress Tracking**: Real-time optimization status
- **Impact Visualization**: Before/after route comparisons
- **Performance Metrics**: Wait times, coverage, and utilization analysis

### Analytics Dashboard
- **KPI Monitoring**: System-wide performance tracking
- **Cost-Benefit Analysis**: ROI and savings calculations
- **Custom Filtering**: Date range and route-specific analysis
- **Export Functionality**: Report generation and data export

## 🏗️ Project Structure

```
src/
├── components/
│   ├── Layout/           # Main layout components
│   ├── Map/             # Mapbox integration
│   ├── Search/          # Search functionality
│   ├── Drawer/          # Bottom drawer interface
│   │   └── tabs/        # Individual tab components
│   └── ui/              # shadcn/ui components
├── store/               # Zustand state management
├── lib/                 # Utilities and API client
├── hooks/               # Custom React hooks
└── pages/               # Route components
```

## 🎯 Performance Optimizations

- **Code Splitting**: Lazy-loaded routes and components
- **React Query Caching**: Intelligent API response caching
- **Mapbox Optimization**: Efficient marker clustering and rendering
- **Bundle Analysis**: Optimized build output and tree-shaking
- **Memory Management**: Proper cleanup and event handling

## 🧪 Development

### Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking
```

### Code Quality
- **ESLint + Prettier**: Consistent code formatting
- **TypeScript**: Full type safety
- **Error Boundaries**: Robust error handling
- **Performance Monitoring**: React DevTools integration

## 🚀 Deployment

The application is optimized for modern deployment platforms:

- **Vercel/Netlify**: Static site deployment
- **Docker**: Containerized deployment
- **PWA Support**: Offline functionality and app-like experience
- **CDN Optimization**: Fast global content delivery

## 📱 Responsive Design

- **Mobile-First**: Optimized for all device sizes
- **Touch Interactions**: Gesture-based navigation
- **Adaptive UI**: Context-aware interface elements
- **Performance**: 60fps animations on all devices

## 🔧 Customization

The platform is built for extensibility:

- **Design System**: Easily customizable color palette and typography
- **Component Library**: Reusable, composable UI components
- **API Layer**: Flexible backend integration
- **State Management**: Scalable state architecture

## 📄 License

This project is part of the MARTA transit system optimization initiative.

## 🤝 Contributing

For contribution guidelines and development standards, please contact the MARTA development team.

---

**Built with ❤️ for MARTA Transit System**
