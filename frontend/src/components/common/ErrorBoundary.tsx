import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex h-full min-h-[400px] flex-col items-center justify-center p-8">
          <div className="flex flex-col items-center text-center">
            <div className="mb-4 rounded-full bg-red-50 p-3">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <h2 className="mb-2 text-lg font-semibold text-foreground">
              Something went wrong
            </h2>
            <p className="mb-6 max-w-sm text-sm text-muted-foreground">
              An unexpected error occurred. Please try refreshing the page or contact
              support if the problem persists.
            </p>
            <Button onClick={this.handleReset} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Try again
            </Button>
            {this.state.error && (
              <details className="mt-6 max-w-md text-left">
                <summary className="cursor-pointer text-sm text-muted-foreground">
                  Error details
                </summary>
                <pre className="mt-2 overflow-auto rounded bg-muted p-3 text-xs">
                  {this.state.error.message}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
