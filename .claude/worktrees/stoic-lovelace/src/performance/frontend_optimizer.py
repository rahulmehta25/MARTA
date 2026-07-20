"""
MARTA Platform - Frontend Performance Optimizer
Bundle optimization, code splitting, service workers, and Core Web Vitals monitoring
"""
import os
import json
import gzip
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class WebpackConfig:
    """Webpack configuration for optimal bundling"""
    
    @staticmethod
    def generate_config() -> Dict[str, Any]:
        """Generate optimized webpack configuration"""
        return {
            "mode": "production",
            "entry": {
                "main": "./src/index.js",
                "vendor": ["react", "react-dom", "react-router-dom", "axios"]
            },
            "output": {
                "path": "dist",
                "filename": "[name].[contenthash:8].js",
                "chunkFilename": "[name].[contenthash:8].chunk.js",
                "publicPath": "/",
                "clean": True
            },
            "optimization": {
                "minimize": True,
                "minimizer": [
                    {
                        "plugin": "TerserPlugin",
                        "options": {
                            "terserOptions": {
                                "compress": {
                                    "drop_console": True,
                                    "drop_debugger": True,
                                    "pure_funcs": ["console.log"]
                                },
                                "mangle": True,
                                "format": {
                                    "comments": False
                                }
                            },
                            "extractComments": False
                        }
                    },
                    {
                        "plugin": "CssMinimizerPlugin",
                        "options": {
                            "minimizerOptions": {
                                "preset": ["default", {
                                    "discardComments": {"removeAll": True}
                                }]
                            }
                        }
                    }
                ],
                "splitChunks": {
                    "chunks": "all",
                    "cacheGroups": {
                        "vendor": {
                            "test": "/node_modules/",
                            "name": "vendor",
                            "priority": 10,
                            "reuseExistingChunk": True
                        },
                        "common": {
                            "minChunks": 2,
                            "priority": 5,
                            "reuseExistingChunk": True
                        },
                        "react": {
                            "test": "/node_modules/(react|react-dom)/",
                            "name": "react",
                            "priority": 20
                        },
                        "maps": {
                            "test": "/node_modules/(leaflet|mapbox-gl)/",
                            "name": "maps",
                            "priority": 15
                        },
                        "charts": {
                            "test": "/node_modules/(plotly|chart.js|d3)/",
                            "name": "charts",
                            "priority": 15
                        }
                    },
                    "maxAsyncRequests": 30,
                    "maxInitialRequests": 30,
                    "minSize": 20000,
                    "maxSize": 244000
                },
                "runtimeChunk": {
                    "name": "runtime"
                },
                "moduleIds": "deterministic",
                "sideEffects": False,
                "usedExports": True,
                "concatenateModules": True
            },
            "module": {
                "rules": [
                    {
                        "test": "/.jsx?$/",
                        "exclude": "/node_modules/",
                        "use": {
                            "loader": "babel-loader",
                            "options": {
                                "presets": [
                                    ["@babel/preset-env", {
                                        "targets": "> 0.25%, not dead",
                                        "useBuiltIns": "usage",
                                        "corejs": 3
                                    }],
                                    "@babel/preset-react"
                                ],
                                "plugins": [
                                    "@babel/plugin-syntax-dynamic-import",
                                    "@babel/plugin-proposal-class-properties",
                                    "babel-plugin-transform-remove-console"
                                ]
                            }
                        }
                    },
                    {
                        "test": "/.css$/",
                        "use": [
                            "style-loader",
                            {
                                "loader": "css-loader",
                                "options": {
                                    "modules": True,
                                    "importLoaders": 1
                                }
                            },
                            {
                                "loader": "postcss-loader",
                                "options": {
                                    "postcssOptions": {
                                        "plugins": [
                                            "autoprefixer",
                                            "cssnano"
                                        ]
                                    }
                                }
                            }
                        ]
                    },
                    {
                        "test": "/.(png|jpg|jpeg|gif|svg|webp)$/",
                        "type": "asset",
                        "parser": {
                            "dataUrlCondition": {
                                "maxSize": 8192
                            }
                        },
                        "generator": {
                            "filename": "images/[name].[hash:8][ext]"
                        }
                    }
                ]
            },
            "plugins": [
                {
                    "plugin": "HtmlWebpackPlugin",
                    "options": {
                        "template": "./public/index.html",
                        "minify": {
                            "removeComments": True,
                            "collapseWhitespace": True,
                            "removeAttributeQuotes": True,
                            "minifyJS": True,
                            "minifyCSS": True
                        }
                    }
                },
                {
                    "plugin": "CompressionPlugin",
                    "options": {
                        "algorithm": "gzip",
                        "test": "/.(js|css|html|svg)$/",
                        "threshold": 8192,
                        "minRatio": 0.8
                    }
                },
                {
                    "plugin": "BrotliPlugin",
                    "options": {
                        "asset": "[path].br[query]",
                        "test": "/.(js|css|html|svg)$/",
                        "threshold": 10240,
                        "minRatio": 0.8
                    }
                },
                {
                    "plugin": "BundleAnalyzerPlugin",
                    "options": {
                        "analyzerMode": "static",
                        "openAnalyzer": False,
                        "reportFilename": "bundle-report.html"
                    }
                },
                {
                    "plugin": "WorkboxPlugin",
                    "options": {
                        "clientsClaim": True,
                        "skipWaiting": True,
                        "runtimeCaching": [
                            {
                                "urlPattern": "/api/",
                                "handler": "NetworkFirst",
                                "options": {
                                    "cacheName": "api-cache",
                                    "expiration": {
                                        "maxEntries": 100,
                                        "maxAgeSeconds": 300
                                    }
                                }
                            },
                            {
                                "urlPattern": "/.(png|jpg|jpeg|svg|gif|webp)$/",
                                "handler": "CacheFirst",
                                "options": {
                                    "cacheName": "image-cache",
                                    "expiration": {
                                        "maxEntries": 200,
                                        "maxAgeSeconds": 86400
                                    }
                                }
                            }
                        ]
                    }
                }
            ],
            "performance": {
                "hints": "warning",
                "maxEntrypointSize": 512000,
                "maxAssetSize": 512000,
                "assetFilter": lambda assetFilename: not assetFilename.endswith('.map')
            }
        }


def generate_service_worker():
    """Generate optimized service worker for offline functionality"""
    return """
// MARTA Platform Service Worker v1.0.0
const CACHE_NAME = 'marta-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/static/css/main.css',
  '/static/js/bundle.js',
  '/manifest.json'
];

// Install event - cache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(cacheName => cacheName !== CACHE_NAME)
          .map(cacheName => caches.delete(cacheName))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache with fallback
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // API calls - network first, cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(request);
        })
    );
    return;
  }

  // Static assets - cache first, network fallback
  event.respondWith(
    caches.match(request)
      .then(response => response || fetch(request))
      .catch(() => {
        // Offline fallback page
        if (request.mode === 'navigate') {
          return caches.match('/offline.html');
        }
      })
  );
});

// Background sync for offline requests
self.addEventListener('sync', event => {
  if (event.tag === 'sync-requests') {
    event.waitUntil(syncOfflineRequests());
  }
});

async function syncOfflineRequests() {
  const cache = await caches.open('offline-requests');
  const requests = await cache.keys();
  
  for (const request of requests) {
    try {
      const response = await fetch(request);
      if (response.ok) {
        await cache.delete(request);
      }
    } catch (error) {
      console.error('Sync failed for:', request.url);
    }
  }
}

// Push notifications
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : 'MARTA Update',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    }
  };

  event.waitUntil(
    self.registration.showNotification('MARTA Platform', options)
  );
});
"""


def generate_lazy_loading_components():
    """Generate React components with lazy loading"""
    return """
import React, { lazy, Suspense } from 'react';
import { ErrorBoundary } from 'react-error-boundary';

// Lazy load heavy components
const MapContainer = lazy(() => 
  import(/* webpackChunkName: "map" */ './components/map/MapContainer')
);

const Dashboard = lazy(() => 
  import(/* webpackChunkName: "dashboard" */ './components/Dashboard')
);

const Analytics = lazy(() => 
  import(/* webpackChunkName: "analytics" */ './components/Analytics')
);

const RouteOptimizer = lazy(() => 
  import(/* webpackChunkName: "optimizer" */ './components/RouteOptimizer')
);

// Loading component
const Loading = () => (
  <div className="loading-container">
    <div className="spinner" />
    <p>Loading...</p>
  </div>
);

// Error fallback
const ErrorFallback = ({ error, resetErrorBoundary }) => (
  <div className="error-container">
    <h2>Something went wrong</h2>
    <pre>{error.message}</pre>
    <button onClick={resetErrorBoundary}>Try again</button>
  </div>
);

// Main App component with code splitting
export const App = () => {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/map" element={<MapContainer />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/optimize" element={<RouteOptimizer />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
};

// Preload critical components
export const preloadCriticalComponents = () => {
  const critical = [
    () => import('./components/map/MapContainer'),
    () => import('./components/Dashboard')
  ];
  
  critical.forEach(load => load());
};
"""


def generate_performance_monitoring():
    """Generate Core Web Vitals monitoring code"""
    return """
// Core Web Vitals Monitoring
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

class PerformanceMonitor {
  constructor() {
    this.metrics = {
      CLS: null,     // Cumulative Layout Shift
      FID: null,     // First Input Delay
      FCP: null,     // First Contentful Paint
      LCP: null,     // Largest Contentful Paint
      TTFB: null,    // Time to First Byte
      custom: {}
    };
    
    this.initializeMonitoring();
  }
  
  initializeMonitoring() {
    // Core Web Vitals
    getCLS(metric => this.recordMetric('CLS', metric));
    getFID(metric => this.recordMetric('FID', metric));
    getFCP(metric => this.recordMetric('FCP', metric));
    getLCP(metric => this.recordMetric('LCP', metric));
    getTTFB(metric => this.recordMetric('TTFB', metric));
    
    // Navigation timing
    if (window.performance && window.performance.timing) {
      window.addEventListener('load', () => {
        this.recordNavigationTiming();
      });
    }
    
    // Resource timing
    this.observeResources();
    
    // Long tasks
    this.observeLongTasks();
    
    // Memory usage
    this.monitorMemory();
  }
  
  recordMetric(name, metric) {
    this.metrics[name] = {
      value: metric.value,
      rating: this.getRating(name, metric.value),
      timestamp: Date.now()
    };
    
    // Send to analytics
    this.sendToAnalytics(name, metric);
  }
  
  getRating(name, value) {
    const thresholds = {
      CLS: { good: 0.1, poor: 0.25 },
      FID: { good: 100, poor: 300 },
      FCP: { good: 1800, poor: 3000 },
      LCP: { good: 2500, poor: 4000 },
      TTFB: { good: 800, poor: 1800 }
    };
    
    const threshold = thresholds[name];
    if (!threshold) return 'unknown';
    
    if (value <= threshold.good) return 'good';
    if (value <= threshold.poor) return 'needs-improvement';
    return 'poor';
  }
  
  recordNavigationTiming() {
    const timing = window.performance.timing;
    const navigationStart = timing.navigationStart;
    
    this.metrics.custom = {
      ...this.metrics.custom,
      dnsLookup: timing.domainLookupEnd - timing.domainLookupStart,
      tcpConnection: timing.connectEnd - timing.connectStart,
      serverResponse: timing.responseEnd - timing.requestStart,
      domParsing: timing.domInteractive - timing.domLoading,
      domContentLoaded: timing.domContentLoadedEventEnd - navigationStart,
      pageLoad: timing.loadEventEnd - navigationStart
    };
  }
  
  observeResources() {
    if (!window.PerformanceObserver) return;
    
    const observer = new PerformanceObserver(list => {
      list.getEntries().forEach(entry => {
        if (entry.entryType === 'resource') {
          this.trackResource(entry);
        }
      });
    });
    
    observer.observe({ entryTypes: ['resource'] });
  }
  
  trackResource(entry) {
    const duration = entry.responseEnd - entry.startTime;
    const size = entry.transferSize || 0;
    
    // Track slow resources
    if (duration > 1000) {
      console.warn(`Slow resource: ${entry.name} took ${duration}ms`);
    }
    
    // Track large resources
    if (size > 500000) {
      console.warn(`Large resource: ${entry.name} is ${(size / 1024 / 1024).toFixed(2)}MB`);
    }
  }
  
  observeLongTasks() {
    if (!window.PerformanceObserver) return;
    
    const observer = new PerformanceObserver(list => {
      list.getEntries().forEach(entry => {
        if (entry.duration > 50) {
          console.warn(`Long task detected: ${entry.duration}ms`);
          this.metrics.custom.longTasks = (this.metrics.custom.longTasks || 0) + 1;
        }
      });
    });
    
    try {
      observer.observe({ entryTypes: ['longtask'] });
    } catch (e) {
      // Long task API not supported
    }
  }
  
  monitorMemory() {
    if (!performance.memory) return;
    
    setInterval(() => {
      const memory = performance.memory;
      this.metrics.custom.memory = {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit
      };
      
      // Detect memory leaks
      const heapUsagePercent = (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100;
      if (heapUsagePercent > 90) {
        console.error('High memory usage detected:', heapUsagePercent.toFixed(2) + '%');
      }
    }, 10000);
  }
  
  sendToAnalytics(name, metric) {
    // Send to your analytics service
    if (window.gtag) {
      window.gtag('event', name, {
        value: Math.round(metric.value),
        metric_id: metric.id,
        metric_value: metric.value,
        metric_delta: metric.delta
      });
    }
    
    // Also send to custom endpoint
    fetch('/api/metrics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        metric: name,
        value: metric.value,
        timestamp: Date.now(),
        url: window.location.href,
        userAgent: navigator.userAgent
      })
    }).catch(err => console.error('Failed to send metrics:', err));
  }
  
  getReport() {
    return {
      coreWebVitals: {
        CLS: this.metrics.CLS,
        FID: this.metrics.FID,
        FCP: this.metrics.FCP,
        LCP: this.metrics.LCP,
        TTFB: this.metrics.TTFB
      },
      custom: this.metrics.custom,
      recommendations: this.generateRecommendations()
    };
  }
  
  generateRecommendations() {
    const recommendations = [];
    
    // Check Core Web Vitals
    Object.entries(this.metrics).forEach(([key, value]) => {
      if (value && value.rating === 'poor') {
        recommendations.push(this.getRecommendation(key));
      }
    });
    
    // Check custom metrics
    if (this.metrics.custom.pageLoad > 5000) {
      recommendations.push('Page load time exceeds 5 seconds. Consider code splitting and lazy loading.');
    }
    
    if (this.metrics.custom.longTasks > 5) {
      recommendations.push('Multiple long tasks detected. Break up JavaScript execution.');
    }
    
    return recommendations;
  }
  
  getRecommendation(metric) {
    const recommendations = {
      CLS: 'Reduce layout shifts by setting dimensions for images and ads',
      FID: 'Reduce JavaScript execution time and break up long tasks',
      FCP: 'Optimize server response time and eliminate render-blocking resources',
      LCP: 'Optimize images, preload critical resources, and use CDN',
      TTFB: 'Optimize server, use CDN, and implement caching'
    };
    
    return recommendations[metric] || 'Optimize performance';
  }
}

// Initialize monitoring
export const performanceMonitor = new PerformanceMonitor();

// Export for use in components
export const measureComponentPerformance = (componentName) => {
  const startTime = performance.now();
  
  return () => {
    const endTime = performance.now();
    const duration = endTime - startTime;
    
    performanceMonitor.metrics.custom.components = {
      ...performanceMonitor.metrics.custom.components,
      [componentName]: duration
    };
    
    if (duration > 100) {
      console.warn(`Component ${componentName} took ${duration}ms to render`);
    }
  };
};
"""


def generate_optimization_script():
    """Generate optimization script for build process"""
    return """
#!/bin/bash
# MARTA Frontend Optimization Script

echo "Starting frontend optimization..."

# Clean previous builds
rm -rf dist/
rm -rf .cache/

# Install dependencies
npm ci --production

# Run build with optimizations
NODE_ENV=production npm run build

# Analyze bundle size
npx webpack-bundle-analyzer dist/stats.json -m static -r dist/bundle-report.html

# Generate critical CSS
npx critical dist/index.html --base dist --inline --minify > dist/index.critical.html
mv dist/index.critical.html dist/index.html

# Optimize images
find dist/images -type f \\( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \\) -exec npx imagemin {} --out-dir=dist/images \\;

# Generate WebP versions
for img in dist/images/*.{jpg,jpeg,png}; do
  npx cwebp "$img" -o "${img%.*}.webp" -q 80
done

# Compress assets
find dist -type f \\( -name "*.js" -o -name "*.css" -o -name "*.html" \\) -exec gzip -9 -k {} \\;
find dist -type f \\( -name "*.js" -o -name "*.css" -o -name "*.html" \\) -exec brotli -9 -k {} \\;

# Generate service worker
npm run generate-sw

# Run lighthouse audit
npx lighthouse http://localhost:3000 --output=json --output-path=./dist/lighthouse-report.json

echo "Frontend optimization complete!"
echo "Bundle size report: dist/bundle-report.html"
echo "Lighthouse report: dist/lighthouse-report.json"
"""


# Save webpack config
def save_webpack_config():
    """Save optimized webpack configuration"""
    config = WebpackConfig.generate_config()
    
    with open('webpack.config.prod.js', 'w') as f:
        f.write(f"module.exports = {json.dumps(config, indent=2)};")
    
    logger.info("Webpack configuration saved to webpack.config.prod.js")


# Save service worker
def save_service_worker():
    """Save service worker file"""
    sw_content = generate_service_worker()
    
    with open('public/service-worker.js', 'w') as f:
        f.write(sw_content)
    
    logger.info("Service worker saved to public/service-worker.js")


# Save performance monitoring
def save_performance_monitoring():
    """Save performance monitoring code"""
    monitoring_code = generate_performance_monitoring()
    
    with open('src/utils/performance.js', 'w') as f:
        f.write(monitoring_code)
    
    logger.info("Performance monitoring saved to src/utils/performance.js")