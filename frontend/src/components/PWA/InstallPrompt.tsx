import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { X, Download, Smartphone, Bell, Wifi } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export const InstallPrompt: React.FC = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [showBenefits, setShowBenefits] = useState(false);

  useEffect(() => {
    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
      return;
    }

    // Listen for install prompt
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      
      // Show prompt after 30 seconds or on third visit
      const visits = parseInt(localStorage.getItem('marta_visits') || '0') + 1;
      localStorage.setItem('marta_visits', visits.toString());
      
      if (visits >= 3) {
        setTimeout(() => setShowPrompt(true), 2000);
      } else {
        setTimeout(() => setShowPrompt(true), 30000);
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // Check if installed via app
    window.addEventListener('appinstalled', () => {
      setIsInstalled(true);
      setShowPrompt(false);
    });

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    // Show browser install prompt
    await deferredPrompt.prompt();
    
    // Wait for user choice
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      console.log('PWA installed');
      setIsInstalled(true);
      
      // Track installation
      if ('gtag' in window) {
        (window as any).gtag('event', 'pwa_install', {
          event_category: 'PWA',
          event_label: 'Install accepted'
        });
      }
    }
    
    setDeferredPrompt(null);
    setShowPrompt(false);
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    
    // Don't show again for 7 days
    localStorage.setItem('marta_prompt_dismissed', Date.now().toString());
  };

  // Don't show if already installed or recently dismissed
  if (isInstalled || !showPrompt) {
    return null;
  }

  const dismissedTime = localStorage.getItem('marta_prompt_dismissed');
  if (dismissedTime && Date.now() - parseInt(dismissedTime) < 7 * 24 * 60 * 60 * 1000) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 100 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 100 }}
        className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 z-50"
      >
        <Card className="shadow-2xl border-primary/20 bg-gradient-to-br from-card to-card/95 backdrop-blur">
          <CardContent className="p-4">
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-primary to-primary/80 rounded-xl flex items-center justify-center">
                  <Smartphone className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Install MARTA App</h3>
                  <p className="text-sm text-muted-foreground">
                    Quick access from your home screen
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleDismiss}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Benefits */}
            {!showBenefits ? (
              <div className="space-y-2 mb-4">
                <div className="flex items-center gap-2 text-sm">
                  <Bell className="h-4 w-4 text-primary" />
                  <span>Real-time delay notifications</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Wifi className="h-4 w-4 text-primary" />
                  <span>Works offline with cached data</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Download className="h-4 w-4 text-primary" />
                  <span>Instant access, no app store needed</span>
                </div>
              </div>
            ) : (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="space-y-2 mb-4"
              >
                <p className="text-sm text-muted-foreground">
                  Get the full app experience with:
                </p>
                <ul className="text-sm space-y-1 ml-4">
                  <li>• Push notifications for delays</li>
                  <li>• Offline trip planning</li>
                  <li>• Home screen widget</li>
                  <li>• Faster loading times</li>
                  <li>• Background updates</li>
                </ul>
              </motion.div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                onClick={handleInstall}
                className="flex-1 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70"
              >
                <Download className="h-4 w-4 mr-2" />
                Install App
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowBenefits(!showBenefits)}
                className="px-3"
              >
                {showBenefits ? 'Less' : 'More'}
              </Button>
            </div>

            {/* iOS Instructions */}
            {/iPhone|iPad|iPod/.test(navigator.userAgent) && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-3 pt-3 border-t"
              >
                <p className="text-xs text-muted-foreground">
                  iOS: Tap the share button <span className="inline-block w-4 h-4 align-middle">⬆️</span> then 
                  "Add to Home Screen"
                </p>
              </motion.div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
};

export default InstallPrompt;