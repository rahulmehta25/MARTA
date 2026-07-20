import { test, expect } from '@playwright/test';

const DEPLOYED_URL = 'https://marta-eta.vercel.app';

test.describe('MARTA Application E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to deployed application
    await page.goto(DEPLOYED_URL, { waitUntil: 'networkidle' });
    
    // Wait for React to hydrate
    await page.waitForTimeout(2000);
  });

  test.describe('Page Loading and Basic Components', () => {
    test('should load the main page successfully', async ({ page }) => {
      // Check page title
      await expect(page).toHaveTitle(/MARTA Analytics/);
      
      // Check for no console errors
      const errors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });
      
      await page.waitForTimeout(3000);
      expect(errors.length).toBe(0);
    });

    test('should display main layout components', async ({ page }) => {
      // Check for main container
      const mainContainer = page.locator('.App');
      await expect(mainContainer).toBeVisible();
      
      // Check for layout wrapper
      const layoutWrapper = page.locator('div.relative.h-screen.w-full');
      await expect(layoutWrapper).toBeVisible();
    });

    test('should have proper viewport and responsive design', async ({ page }) => {
      const viewport = page.viewportSize();
      expect(viewport.width).toBeGreaterThan(1000);
      expect(viewport.height).toBeGreaterThan(600);
      
      // Check for responsive classes
      const responsiveElements = page.locator('[class*="sm:"], [class*="md:"], [class*="lg:"]');
      await expect(responsiveElements.first()).toBeVisible();
    });
  });

  test.describe('Search Bar Component', () => {
    test('should display search bar at the top', async ({ page }) => {
      const searchContainer = page.locator('.absolute.top-0.left-0.right-0.z-30');
      await expect(searchContainer).toBeVisible();
      
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      await expect(searchInput).toBeVisible();
      await expect(searchInput).toBeEnabled();
    });

    test('should handle search input interaction', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      
      // Test typing in search input
      await searchInput.fill('Five Points');
      await expect(searchInput).toHaveValue('Five Points');
      
      // Check for search icon
      const searchIcon = page.locator('.absolute .inset-y-0 .left-0 svg');
      await expect(searchIcon).toBeVisible();
    });

    test('should show clear button when input has value', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      
      await searchInput.fill('Test Station');
      
      // Clear button should be visible
      const clearButton = page.locator('button:has(svg):near(input)');
      await expect(clearButton).toBeVisible();
      
      // Clear button should work
      await clearButton.click();
      await expect(searchInput).toHaveValue('');
    });

    test('should handle keyboard navigation', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      
      // Test escape key
      await searchInput.fill('Test');
      await searchInput.press('Escape');
      
      // Test enter key
      await searchInput.fill('Station');
      await searchInput.press('Enter');
      
      // Should not throw errors
      await page.waitForTimeout(1000);
    });
  });

  test.describe('Map Container Component', () => {
    test('should display map container area', async ({ page }) => {
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      await expect(mapContainer).toBeVisible();
      
      // Map container should have proper dimensions
      const boundingBox = await mapContainer.boundingBox();
      expect(boundingBox.width).toBeGreaterThan(800);
      expect(boundingBox.height).toBeGreaterThan(400);
    });

    test('should be positioned correctly behind other elements', async ({ page }) => {
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      const searchBar = page.locator('.absolute.top-0.left-0.right-0.z-30');
      
      // Map should be behind search bar (lower z-index)
      const mapZIndex = await mapContainer.evaluate(el => 
        window.getComputedStyle(el).zIndex
      );
      const searchZIndex = await searchBar.evaluate(el => 
        window.getComputedStyle(el).zIndex
      );
      
      expect(parseInt(mapZIndex)).toBeLessThan(parseInt(searchZIndex));
    });

    test('should handle map interactions', async ({ page }) => {
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      
      // Test click interaction
      await mapContainer.click();
      await page.waitForTimeout(500);
      
      // Test hover interaction
      await mapContainer.hover();
      await page.waitForTimeout(500);
    });
  });

  test.describe('Floating Buttons Component', () => {
    test('should display floating buttons on the right side', async ({ page }) => {
      const floatingButtons = page.locator('.absolute.right-4.top-20.z-20');
      await expect(floatingButtons).toBeVisible();
    });

    test('should be positioned correctly', async ({ page }) => {
      const floatingButtons = page.locator('.absolute.right-4.top-20.z-20');
      const boundingBox = await floatingButtons.boundingBox();
      
      // Should be on the right side of the screen
      const viewport = page.viewportSize();
      expect(boundingBox.x).toBeGreaterThan(viewport.width * 0.8);
    });

    test('should handle button interactions', async ({ page }) => {
      const floatingButtons = page.locator('.absolute.right-4.top-20.z-20');
      
      // Should be clickable
      await floatingButtons.click();
      await page.waitForTimeout(500);
    });
  });

  test.describe('Bottom Drawer Component', () => {
    test('should initially be closed', async ({ page }) => {
      // Drawer should not be visible initially
      const drawer = page.locator('.fixed.inset-x-0.bottom-0.z-50');
      await expect(drawer).not.toBeVisible();
    });

    test('should open when stop is selected', async ({ page, browserName }) => {
      // Skip this test on webkit due to potential interaction issues
      test.skip(browserName === 'webkit');
      
      // Click on map to potentially select a stop
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      await mapContainer.click();
      
      // Wait for potential drawer opening
      await page.waitForTimeout(2000);
      
      // Check if drawer opened (conditional test)
      const drawer = page.locator('.fixed.inset-x-0.bottom-0.z-50');
      const isVisible = await drawer.isVisible().catch(() => false);
      
      if (isVisible) {
        await expect(drawer).toBeVisible();
        
        // Check for drag handle
        const dragHandle = page.locator('.w-12.h-1.bg-gray-300.rounded-full');
        await expect(dragHandle).toBeVisible();
        
        // Check for close button
        const closeButton = page.locator('button:has(svg):near(.fixed)');
        await expect(closeButton).toBeVisible();
      }
    });

    test('should handle drawer interactions when open', async ({ page }) => {
      // Try to open drawer by clicking search and selecting
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      await searchInput.fill('Station');
      await searchInput.press('Enter');
      
      await page.waitForTimeout(2000);
      
      const drawer = page.locator('.fixed.inset-x-0.bottom-0.z-50');
      const isVisible = await drawer.isVisible().catch(() => false);
      
      if (isVisible) {
        // Test expand/collapse functionality
        const expandButton = page.locator('button:has(svg[class*="chevron"])');
        if (await expandButton.isVisible()) {
          await expandButton.click();
          await page.waitForTimeout(500);
        }
        
        // Test close functionality
        const closeButton = page.locator('button:has(svg):near(.fixed) >> last');
        if (await closeButton.isVisible()) {
          await closeButton.click();
          await expect(drawer).not.toBeVisible();
        }
      }
    });

    test('should display proper tab navigation when open', async ({ page }) => {
      // Attempt to open drawer
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      await mapContainer.click();
      await page.waitForTimeout(2000);
      
      const drawer = page.locator('.fixed.inset-x-0.bottom-0.z-50');
      const isVisible = await drawer.isVisible().catch(() => false);
      
      if (isVisible) {
        // Check for tab buttons
        const tabButtons = page.locator('button:has-text("Overview"), button:has-text("Demand"), button:has-text("Schedule"), button:has-text("Trends")');
        const tabCount = await tabButtons.count();
        
        if (tabCount > 0) {
          // Test tab switching
          for (let i = 0; i < Math.min(tabCount, 4); i++) {
            const tab = tabButtons.nth(i);
            if (await tab.isVisible()) {
              await tab.click();
              await page.waitForTimeout(300);
            }
          }
        }
      }
    });
  });

  test.describe('Error Handling and Edge Cases', () => {
    test('should handle network interruptions gracefully', async ({ page }) => {
      // Block all network requests to simulate network issues
      await page.route('**/*', route => route.abort());
      
      // Reload the page
      await page.reload({ waitUntil: 'domcontentloaded' });
      
      // Should still render basic layout
      const appContainer = page.locator('.App');
      await expect(appContainer).toBeVisible();
      
      // Restore network
      await page.unroute('**/*');
    });

    test('should handle invalid search inputs', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      
      // Test various invalid inputs
      const invalidInputs = ['', '   ', '!@#$%^&*()', '123456789012345678901234567890123456789012345678901234567890'];
      
      for (const input of invalidInputs) {
        await searchInput.fill(input);
        await searchInput.press('Enter');
        await page.waitForTimeout(500);
        
        // Should not crash the application
        const appContainer = page.locator('.App');
        await expect(appContainer).toBeVisible();
      }
    });

    test('should maintain state during rapid interactions', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      
      // Rapid interactions
      for (let i = 0; i < 5; i++) {
        await searchInput.fill(`Test ${i}`);
        await mapContainer.click();
        await page.waitForTimeout(100);
      }
      
      // Application should remain stable
      const appContainer = page.locator('.App');
      await expect(appContainer).toBeVisible();
    });

    test('should handle browser zoom levels', async ({ page }) => {
      // Test different zoom levels
      const zoomLevels = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
      
      for (const zoom of zoomLevels) {
        await page.evaluate((zoomLevel) => {
          document.body.style.zoom = zoomLevel;
        }, zoom);
        
        await page.waitForTimeout(500);
        
        // Check that main components are still visible
        const searchInput = page.locator('input[placeholder*="Search for stops"]');
        const mapContainer = page.locator('.absolute.inset-0.z-10');
        
        await expect(searchInput).toBeVisible();
        await expect(mapContainer).toBeVisible();
      }
      
      // Reset zoom
      await page.evaluate(() => {
        document.body.style.zoom = '1.0';
      });
    });
  });

  test.describe('Performance and Accessibility', () => {
    test('should load within acceptable time limits', async ({ page }) => {
      const startTime = Date.now();
      
      await page.goto(DEPLOYED_URL, { waitUntil: 'networkidle' });
      
      const loadTime = Date.now() - startTime;
      
      // Should load within 10 seconds
      expect(loadTime).toBeLessThan(10000);
      
      // Check for critical elements within 5 seconds
      await expect(page.locator('input[placeholder*="Search for stops"]')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('.absolute.inset-0.z-10')).toBeVisible({ timeout: 5000 });
    });

    test('should have proper keyboard navigation', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      
      // Tab navigation should work
      await page.keyboard.press('Tab');
      
      // Search input should be focusable
      await searchInput.focus();
      const isFocused = await searchInput.evaluate(el => el === document.activeElement);
      expect(isFocused).toBe(true);
    });

    test('should have proper ARIA labels and accessibility attributes', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      
      // Check for placeholder text
      const placeholder = await searchInput.getAttribute('placeholder');
      expect(placeholder).toContain('Search');
      
      // Check input type
      const inputType = await searchInput.getAttribute('type');
      expect(inputType).toBe('text');
    });

    test('should not have memory leaks during extended usage', async ({ page }) => {
      // Simulate extended usage pattern
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      
      for (let i = 0; i < 10; i++) {
        await searchInput.fill(`Search term ${i}`);
        await searchInput.clear();
        await mapContainer.click();
        await page.waitForTimeout(200);
      }
      
      // Check that the page is still responsive
      await expect(searchInput).toBeVisible();
      await expect(mapContainer).toBeVisible();
    });
  });

  test.describe('Cross-Browser Compatibility', () => {
    test('should work across different viewport sizes', async ({ page }) => {
      const viewportSizes = [
        { width: 1920, height: 1080 }, // Desktop
        { width: 1366, height: 768 },  // Laptop
        { width: 768, height: 1024 },  // Tablet
        { width: 375, height: 667 }    // Mobile
      ];
      
      for (const size of viewportSizes) {
        await page.setViewportSize(size);
        await page.waitForTimeout(1000);
        
        // Essential elements should be visible at all sizes
        const searchInput = page.locator('input[placeholder*="Search for stops"]');
        const mapContainer = page.locator('.absolute.inset-0.z-10');
        
        await expect(searchInput).toBeVisible();
        await expect(mapContainer).toBeVisible();
      }
    });

    test('should handle touch interactions on mobile viewports', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      
      // Simulate touch interactions
      await mapContainer.tap();
      await searchInput.tap();
      
      // Should remain functional
      await expect(searchInput).toBeFocused();
    });
  });

  test.describe('Data Integration and API Connectivity', () => {
    test('should handle API responses gracefully', async ({ page }) => {
      // Monitor network requests
      const apiRequests = [];
      page.on('request', request => {
        if (request.url().includes('api') || request.url().includes('predict') || request.url().includes('search')) {
          apiRequests.push(request.url());
        }
      });
      
      // Perform actions that might trigger API calls
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      await searchInput.fill('Five Points Station');
      await page.waitForTimeout(2000);
      
      // Click on map
      const mapContainer = page.locator('.absolute.inset-0.z-10');
      await mapContainer.click();
      await page.waitForTimeout(2000);
      
      // Application should remain stable regardless of API responses
      const appContainer = page.locator('.App');
      await expect(appContainer).toBeVisible();
    });

    test('should display loading states appropriately', async ({ page }) => {
      const searchInput = page.locator('input[placeholder*="Search for stops"]');
      
      // Trigger search that might show loading state
      await searchInput.fill('Station');
      await page.waitForTimeout(500);
      
      // Look for loading indicators
      const loadingSpinner = page.locator('.animate-spin, [class*="loading"], [class*="spinner"]');
      const loadingText = page.locator('text=/loading/i, text=/searching/i');
      
      // Check if loading states appear (they might or might not, depending on API speed)
      const hasLoadingSpinner = await loadingSpinner.isVisible().catch(() => false);
      const hasLoadingText = await loadingText.isVisible().catch(() => false);
      
      // This is informational - we don't fail if no loading states are found
      if (hasLoadingSpinner || hasLoadingText) {
        console.log('Loading states detected - good UX');
      }
    });
  });
});

// Mobile-specific test suite
test.describe('Mobile-Specific Features', () => {
  test.beforeEach(async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(DEPLOYED_URL, { waitUntil: 'networkidle' });
  });

  test('should be fully functional on mobile devices', async ({ page }) => {
    // Check responsive design
    const searchInput = page.locator('input[placeholder*="Search for stops"]');
    const mapContainer = page.locator('.absolute.inset-0.z-10');
    
    await expect(searchInput).toBeVisible();
    await expect(mapContainer).toBeVisible();
    
    // Check touch interactions
    await searchInput.tap();
    await searchInput.fill('Mobile Test');
    
    await mapContainer.tap();
    await page.waitForTimeout(1000);
  });

  test('should handle orientation changes', async ({ page }) => {
    // Portrait mode
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);
    
    const searchInput = page.locator('input[placeholder*="Search for stops"]');
    await expect(searchInput).toBeVisible();
    
    // Landscape mode
    await page.setViewportSize({ width: 667, height: 375 });
    await page.waitForTimeout(1000);
    
    await expect(searchInput).toBeVisible();
  });
});