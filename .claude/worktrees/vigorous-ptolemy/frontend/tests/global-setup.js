import { chromium } from '@playwright/test';

/**
 * Global setup for Playwright tests
 * Runs once before all test files
 */
async function globalSetup() {
  console.log('🚀 Starting MARTA Application E2E Test Suite');
  console.log('📍 Testing deployed application at: https://marta-eta.vercel.app');
  
  // Create a browser instance to test basic connectivity
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    console.log('🔍 Checking application availability...');
    
    // Basic connectivity check
    const response = await page.goto('https://marta-eta.vercel.app', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    
    if (response.ok()) {
      console.log('✅ Application is accessible and responding');
      
      // Check for basic React hydration
      await page.waitForTimeout(3000);
      
      const hasReactElements = await page.locator('.App, [data-reactroot]').count();
      if (hasReactElements > 0) {
        console.log('⚛️ React application detected and hydrated');
      }
      
      // Check for critical elements
      const hasSearchBar = await page.locator('input[placeholder*="Search"]').count();
      const hasMapContainer = await page.locator('.absolute.inset-0').count();
      
      console.log(`🔎 Found ${hasSearchBar} search elements`);
      console.log(`🗺️ Found ${hasMapContainer} map container elements`);
      
    } else {
      console.error('❌ Application is not responding properly');
      console.error(`Status: ${response.status()} ${response.statusText()}`);
    }
    
  } catch (error) {
    console.error('❌ Failed to access application:', error.message);
    console.error('This may affect test results - some tests may fail');
  } finally {
    await browser.close();
  }
  
  console.log('🎯 Global setup complete - starting test execution');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  return {};
}

export default globalSetup;