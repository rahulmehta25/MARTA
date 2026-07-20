import { useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "@/components/Layout/AppShell";
import { MainLayout } from "@/components/Layout/MainLayout";
import { ArrivalsPage } from "@/pages/ArrivalsPage";
import { PlanPage } from "@/pages/PlanPage";
import { AlertsPage } from "@/pages/AlertsPage";
import { SavedRoutesPage } from "@/pages/SavedRoutesPage";
import Dashboard from "./pages/Dashboard";
import NotFound from "./pages/NotFound";
import { InstallPrompt } from "./components/PWA/InstallPrompt";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
});

const App = () => {
  useEffect(() => {
    // Register service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/service-worker.js')
        .then((registration) => {
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  console.log('New MARTA app version available — refresh to update');
                }
              });
            }
          });
        })
        .catch((err) => {
          console.warn('ServiceWorker registration failed:', err);
        });
    }

    // Request notification permission on first interaction
    if ('Notification' in window && Notification.permission === 'default') {
      const requestPermission = () => {
        Notification.requestPermission();
        document.removeEventListener('click', requestPermission);
      };
      document.addEventListener('click', requestPermission);
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* All main routes share the AppShell (header + bottom nav) */}
            <Route element={<AppShell />}>
              <Route path="/" element={<MainLayout />} />
              <Route path="/arrivals" element={<ArrivalsPage />} />
              <Route path="/plan" element={<PlanPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/saved" element={<SavedRoutesPage />} />
              <Route path="/dashboard" element={<Dashboard />} />
            </Route>

            {/* Legacy analytics route */}
            <Route path="/analytics" element={<AppShell />}>
              <Route index element={<ArrivalsPage />} />
            </Route>

            {/* 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
          <InstallPrompt />
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
