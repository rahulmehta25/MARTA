// frontend/src/services/sentryConfig.ts

import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';
import { CaptureConsole } from '@sentry/integrations';

interface SentryConfigOptions {
  dsn?: string;
  environment?: string;
  release?: string;
  tracesSampleRate?: number;
}

class SentryService {
  private initialized: boolean = false;
  private dsn: string | undefined;
  private environment: string;

  constructor() {
    this.dsn = import.meta.env.VITE_SENTRY_DSN;
    this.environment = import.meta.env.VITE_ENVIRONMENT || 'development';
  }

  /**
   * Initialize Sentry for error and performance monitoring
   */
  initialize(options?: SentryConfigOptions): boolean {
    // Use provided DSN or fall back to environment variable
    const dsn = options?.dsn || this.dsn;

    if (!dsn) {
      console.warn('Sentry DSN not configured - monitoring disabled');
      return false;
    }

    if (this.initialized) {
      console.info('Sentry already initialized');
      return true;
    }

    try {
      Sentry.init({
        dsn,
        environment: options?.environment || this.environment,
        release: options?.release || import.meta.env.VITE_APP_VERSION || '1.0.0',

        // Performance Monitoring
        integrations: [
          new BrowserTracing({
            // Set sampling rate for performance monitoring
            tracingOrigins: [
              'localhost',
              /^https:\/\/marta-eta\.vercel\.app/,
              /^https:\/\/.*\.supabase\.co/,
            ],
            // Capture interactions
            routingInstrumentation: Sentry.reactRouterV6Instrumentation(
              React.useEffect,
              useLocation,
              useNavigationType,
              createRoutesFromChildren,
              matchRoutes
            ),
          }),
          // Capture console errors
          new CaptureConsole({
            levels: ['error', 'warn'],
          }),
        ],

        // Performance sampling
        tracesSampleRate: options?.tracesSampleRate || 0.1,

        // Session replay
        replaysSessionSampleRate: 0.1,
        replaysOnErrorSampleRate: 1.0,

        // Error filtering
        beforeSend: (event, hint) => {
          // Filter out certain errors
          if (event.exception) {
            const error = hint.originalException;

            // Don't send network errors in development
            if (this.environment === 'development' && error?.name === 'NetworkError') {
              return null;
            }

            // Filter out expected errors
            if (error?.message?.includes('ResizeObserver loop limit exceeded')) {
              return null;
            }
          }

          // Remove sensitive data
          if (event.request) {
            // Remove authorization headers
            if (event.request.headers) {
              delete event.request.headers['Authorization'];
              delete event.request.headers['Cookie'];
            }
          }

          return event;
        },

        // Don't send personally identifiable information
        sendClientReports: false,

        // Breadcrumb configuration
        maxBreadcrumbs: 50,

        // Ignore certain errors
        ignoreErrors: [
          // Browser extensions
          'top.GLOBALS',
          // Random network errors
          'Network request failed',
          'NetworkError',
          'Failed to fetch',
          // Resize observer errors
          'ResizeObserver loop limit exceeded',
          // Non-error promise rejections
          'Non-Error promise rejection captured',
        ],

        // Ignore transactions from certain URLs
        ignoreTransactions: [
          '/health',
          '/metrics',
        ],
      });

      this.initialized = true;
      console.info(`Sentry initialized for ${this.environment} environment`);
      return true;
    } catch (error) {
      console.error('Failed to initialize Sentry:', error);
      return false;
    }
  }

  /**
   * Capture an exception with optional context
   */
  captureException(error: Error, context?: Record<string, any>): void {
    if (!this.initialized) return;

    if (context) {
      Sentry.withScope((scope) => {
        Object.keys(context).forEach((key) => {
          scope.setContext(key, context[key]);
        });
        Sentry.captureException(error);
      });
    } else {
      Sentry.captureException(error);
    }
  }

  /**
   * Capture a message with optional context
   */
  captureMessage(
    message: string,
    level: Sentry.SeverityLevel = 'info',
    context?: Record<string, any>
  ): void {
    if (!this.initialized) return;

    if (context) {
      Sentry.withScope((scope) => {
        Object.keys(context).forEach((key) => {
          scope.setContext(key, context[key]);
        });
        Sentry.captureMessage(message, level);
      });
    } else {
      Sentry.captureMessage(message, level);
    }
  }

  /**
   * Add breadcrumb for tracking user actions
   */
  addBreadcrumb(breadcrumb: Sentry.Breadcrumb): void {
    if (!this.initialized) return;
    Sentry.addBreadcrumb(breadcrumb);
  }

  /**
   * Set user context
   */
  setUser(user: Sentry.User | null): void {
    if (!this.initialized) return;
    Sentry.setUser(user);
  }

  /**
   * Set additional context
   */
  setContext(key: string, context: any): void {
    if (!this.initialized) return;
    Sentry.setContext(key, context);
  }

  /**
   * Set tags for categorization
   */
  setTag(key: string, value: string): void {
    if (!this.initialized) return;
    Sentry.setTag(key, value);
  }

  /**
   * Start a transaction for performance monitoring
   */
  startTransaction(name: string, op: string = 'navigation'): any {
    if (!this.initialized) return null;
    return Sentry.startTransaction({ name, op });
  }

  /**
   * Profile a React component
   */
  profileComponent<P extends object>(
    Component: React.ComponentType<P>,
    name?: string
  ): React.ComponentType<P> {
    if (!this.initialized) return Component;
    return Sentry.withProfiler(Component, { name });
  }

  /**
   * Create error boundary component
   */
  createErrorBoundary(fallback: React.ComponentType<any>, showDialog: boolean = false) {
    return Sentry.ErrorBoundary({ fallback, showDialog });
  }
}

// Create singleton instance
export const sentryService = new SentryService();

// React hooks for Sentry
export const useSentryUser = (user: any) => {
  React.useEffect(() => {
    if (user) {
      sentryService.setUser({
        id: user.id,
        email: user.email,
        username: user.username,
      });
    } else {
      sentryService.setUser(null);
    }
  }, [user]);
};

export const useSentryError = () => {
  return {
    captureException: (error: Error, context?: Record<string, any>) =>
      sentryService.captureException(error, context),
    captureMessage: (message: string, level?: Sentry.SeverityLevel, context?: Record<string, any>) =>
      sentryService.captureMessage(message, level, context),
  };
};

// Error boundary wrapper component
export const SentryErrorBoundary: React.FC<{
  children: React.ReactNode;
  fallback?: React.ComponentType<any>;
}> = ({ children, fallback }) => {
  const ErrorBoundary = sentryService.createErrorBoundary(
    fallback || DefaultErrorFallback,
    false
  );

  return <ErrorBoundary>{children}</ErrorBoundary>;
};

// Default error fallback component
const DefaultErrorFallback: React.FC<{ error?: Error }> = ({ error }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-100">
    <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full">
      <h2 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h2>
      <p className="text-gray-600 mb-4">
        We're sorry, but something unexpected happened. The error has been reported to our team.
      </p>
      {error && (
        <details className="mb-4">
          <summary className="cursor-pointer text-sm text-gray-500">Error details</summary>
          <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto">
            {error.message}
          </pre>
        </details>
      )}
      <button
        onClick={() => window.location.reload()}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700"
      >
        Reload Page
      </button>
    </div>
  </div>
);

// Import required React Router dependencies
import React from 'react';
import {
  useLocation,
  useNavigationType,
  createRoutesFromChildren,
  matchRoutes,
} from 'react-router-dom';

export default sentryService;