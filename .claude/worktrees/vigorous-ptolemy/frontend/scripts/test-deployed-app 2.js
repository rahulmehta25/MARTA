#!/usr/bin/env node

/**
 * Test Deployed MARTA Application
 * Comprehensive testing script for the deployed application
 */

const { chromium, firefox, webkit } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

const DEPLOYED_URL = 'https://marta-eta.vercel.app';
const RESULTS_DIR = path.join(__dirname, '..', 'test-results');

// Test configuration
const TEST_CONFIG = {
  timeout: 30000,
  browsers: ['chromium', 'firefox', 'webkit'],
  viewports: [
    { name: 'Desktop', width: 1280, height: 720 },
    { name: 'Tablet', width: 768, height: 1024 },
    { name: 'Mobile', width: 375, height: 667 }
  ],
  retries: 2
};

class DeployedAppTester {
  constructor() {
    this.results = {
      summary: {
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        startTime: new Date(),
        endTime: null
      },
      tests: [],
      errors: []
    };
  }

  async init() {
    // Create results directory
    try {
      await fs.mkdir(RESULTS_DIR, { recursive: true });
      console.log('📁 Test results directory created');
    } catch (error) {
      console.error('Failed to create results directory:', error.message);
    }
  }

  async runAllTests() {
    console.log('🚀 Starting comprehensive deployed application testing...');
    console.log(`📍 Testing URL: ${DEPLOYED_URL}`);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    await this.init();

    // Test basic connectivity first
    await this.testConnectivity();

    // Run tests for each browser
    for (const browserName of TEST_CONFIG.browsers) {
      await this.testBrowser(browserName);
    }

    // Generate final report
    await this.generateReport();

    this.results.summary.endTime = new Date();
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 Testing Complete!');
    this.printSummary();
  }

  async testConnectivity() {
    console.log('\n🔍 Testing basic connectivity...');
    
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    try {
      const response = await page.goto(DEPLOYED_URL, { 
        waitUntil: 'networkidle', 
        timeout: TEST_CONFIG.timeout 
      });

      if (response.ok()) {
        this.addTestResult('connectivity', 'Basic connectivity', true, 'Application accessible');
        console.log('✅ Application is accessible');
      } else {
        this.addTestResult('connectivity', 'Basic connectivity', false, 
          `HTTP ${response.status()}: ${response.statusText()}`);
        console.log(`❌ Application returned ${response.status()}`);
      }

      // Test for React hydration
      await page.waitForTimeout(3000);
      const reactElements = await page.locator('.App, [data-reactroot]').count();
      
      if (reactElements > 0) {
        this.addTestResult('connectivity', 'React hydration', true, 'React app detected');
        console.log('⚛️ React application detected and hydrated');
      } else {
        this.addTestResult('connectivity', 'React hydration', false, 'No React elements found');
        console.log('⚠️ React application not detected');
      }

    } catch (error) {
      this.addTestResult('connectivity', 'Basic connectivity', false, error.message);
      console.error('❌ Connectivity test failed:', error.message);
    } finally {
      await browser.close();
    }
  }

  async testBrowser(browserName) {
    console.log(`\n🌐 Testing with ${browserName}...`);
    
    let browser;
    try {
      browser = await this.launchBrowser(browserName);
      
      for (const viewport of TEST_CONFIG.viewports) {
        await this.testViewport(browser, browserName, viewport);
      }
      
    } catch (error) {
      console.error(`❌ Browser ${browserName} failed:`, error.message);
      this.addError(`Browser ${browserName}`, error.message);
    } finally {
      if (browser) {
        await browser.close();
      }
    }
  }

  async launchBrowser(browserName) {
    const browsers = { chromium, firefox, webkit };
    return await browsers[browserName].launch({
      headless: true,
      args: browserName === 'chromium' ? [
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor'
      ] : []
    });
  }

  async testViewport(browser, browserName, viewport) {
    console.log(`  📱 Testing ${viewport.name} (${viewport.width}x${viewport.height})`);
    
    const page = await browser.newPage();
    await page.setViewportSize(viewport);
    
    const testName = `${browserName}-${viewport.name}`;
    
    try {
      // Navigate to application
      await page.goto(DEPLOYED_URL, { 
        waitUntil: 'networkidle', 
        timeout: TEST_CONFIG.timeout 
      });

      // Test suite for this viewport
      await this.testPageLoad(page, testName);
      await this.testUIComponents(page, testName);
      await this.testInteractions(page, testName);
      await this.testResponsiveness(page, testName, viewport);
      await this.testPerformance(page, testName);
      await this.testAccessibility(page, testName);
      
    } catch (error) {
      console.error(`    ❌ ${testName} failed:`, error.message);
      this.addError(testName, error.message);
    } finally {
      await page.close();
    }
  }

  async testPageLoad(page, testName) {
    try {
      // Test page title
      const title = await page.title();
      const hasCorrectTitle = title.includes('MARTA');
      this.addTestResult(testName, 'Page title', hasCorrectTitle, 
        hasCorrectTitle ? `Title: "${title}"` : `Unexpected title: "${title}"`);

      // Test for critical elements
      const searchInput = await page.locator('input[placeholder*="Search"]').count();
      this.addTestResult(testName, 'Search bar presence', searchInput > 0, 
        `Found ${searchInput} search elements`);

      const mapContainer = await page.locator('.absolute.inset-0, [class*="map"]').count();
      this.addTestResult(testName, 'Map container presence', mapContainer > 0, 
        `Found ${mapContainer} map elements`);

      // Check for console errors
      const errors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.waitForTimeout(2000);
      this.addTestResult(testName, 'Console errors', errors.length === 0, 
        errors.length === 0 ? 'No console errors' : `${errors.length} console errors`);

    } catch (error) {
      this.addTestResult(testName, 'Page load test', false, error.message);
    }
  }

  async testUIComponents(page, testName) {
    try {
      // Test search bar functionality
      const searchInput = page.locator('input[placeholder*="Search"]').first();
      const searchVisible = await searchInput.isVisible().catch(() => false);
      this.addTestResult(testName, 'Search bar visibility', searchVisible, 
        searchVisible ? 'Search bar visible' : 'Search bar not found');

      if (searchVisible) {
        // Test search input interaction
        await searchInput.fill('Test Station');
        const value = await searchInput.inputValue();
        this.addTestResult(testName, 'Search input functionality', value === 'Test Station',
          `Input value: "${value}"`);

        await searchInput.clear();
      }

      // Test layout containers
      const layoutElements = await page.locator('.relative, .absolute, .fixed').count();
      this.addTestResult(testName, 'Layout structure', layoutElements > 0,
        `Found ${layoutElements} layout elements`);

    } catch (error) {
      this.addTestResult(testName, 'UI components test', false, error.message);
    }
  }

  async testInteractions(page, testName) {
    try {
      // Test clickable elements
      const buttons = await page.locator('button, [role="button"]').count();
      this.addTestResult(testName, 'Interactive elements', buttons > 0,
        `Found ${buttons} interactive elements`);

      // Test map interaction (if map container exists)
      const mapContainer = page.locator('.absolute.inset-0, [class*="map"]').first();
      const mapExists = await mapContainer.isVisible().catch(() => false);
      
      if (mapExists) {
        await mapContainer.click().catch(() => {});
        this.addTestResult(testName, 'Map interaction', true, 'Map container clickable');
      } else {
        this.addTestResult(testName, 'Map interaction', false, 'Map container not found');
      }

    } catch (error) {
      this.addTestResult(testName, 'Interactions test', false, error.message);
    }
  }

  async testResponsiveness(page, testName, viewport) {
    try {
      // Test element visibility at different viewport sizes
      const searchInput = page.locator('input[placeholder*="Search"]').first();
      const searchVisible = await searchInput.isVisible().catch(() => false);

      const mapContainer = page.locator('.absolute.inset-0').first();
      const mapVisible = await mapContainer.isVisible().catch(() => false);

      this.addTestResult(testName, `${viewport.name} search visibility`, searchVisible,
        searchVisible ? 'Search visible on ' + viewport.name : 'Search not visible');

      this.addTestResult(testName, `${viewport.name} map visibility`, mapVisible,
        mapVisible ? 'Map visible on ' + viewport.name : 'Map not visible');

      // Test touch interactions on mobile
      if (viewport.name === 'Mobile') {
        if (searchVisible) {
          await searchInput.tap().catch(() => {});
          const isFocused = await searchInput.evaluate(el => el === document.activeElement).catch(() => false);
          this.addTestResult(testName, 'Mobile touch interaction', isFocused,
            isFocused ? 'Touch interaction works' : 'Touch interaction failed');
        }
      }

    } catch (error) {
      this.addTestResult(testName, 'Responsiveness test', false, error.message);
    }
  }

  async testPerformance(page, testName) {
    try {
      // Measure load time
      const startTime = Date.now();
      await page.reload({ waitUntil: 'networkidle' });
      const loadTime = Date.now() - startTime;

      this.addTestResult(testName, 'Load time', loadTime < 10000,
        `Load time: ${loadTime}ms`);

      // Test for performance best practices
      const scripts = await page.locator('script').count();
      const stylesheets = await page.locator('link[rel="stylesheet"]').count();

      this.addTestResult(testName, 'Resource count', scripts < 50 && stylesheets < 20,
        `Scripts: ${scripts}, Stylesheets: ${stylesheets}`);

    } catch (error) {
      this.addTestResult(testName, 'Performance test', false, error.message);
    }
  }

  async testAccessibility(page, testName) {
    try {
      // Basic accessibility checks
      const focusableElements = await page.locator('input, button, a, [tabindex]').count();
      this.addTestResult(testName, 'Focusable elements', focusableElements > 0,
        `Found ${focusableElements} focusable elements`);

      // Test keyboard navigation
      await page.keyboard.press('Tab');
      const activeElement = await page.locator(':focus').count();
      this.addTestResult(testName, 'Keyboard navigation', activeElement > 0,
        activeElement > 0 ? 'Focus management works' : 'No focus detected');

      // Check for alt text on images
      const images = await page.locator('img').count();
      const imagesWithAlt = await page.locator('img[alt]').count();
      this.addTestResult(testName, 'Image accessibility', images === 0 || imagesWithAlt === images,
        `Images: ${images}, With alt text: ${imagesWithAlt}`);

    } catch (error) {
      this.addTestResult(testName, 'Accessibility test', false, error.message);
    }
  }

  addTestResult(category, testName, passed, details) {
    this.results.tests.push({
      category,
      name: testName,
      passed,
      details,
      timestamp: new Date().toISOString()
    });

    this.results.summary.total++;
    if (passed) {
      this.results.summary.passed++;
      console.log(`    ✅ ${testName}: ${details}`);
    } else {
      this.results.summary.failed++;
      console.log(`    ❌ ${testName}: ${details}`);
    }
  }

  addError(context, message) {
    this.results.errors.push({
      context,
      message,
      timestamp: new Date().toISOString()
    });
  }

  async generateReport() {
    const reportData = {
      ...this.results,
      config: TEST_CONFIG,
      url: DEPLOYED_URL,
      generatedAt: new Date().toISOString()
    };

    // Generate JSON report
    const jsonPath = path.join(RESULTS_DIR, 'deployed-app-test-results.json');
    await fs.writeFile(jsonPath, JSON.stringify(reportData, null, 2));

    // Generate HTML report
    const htmlReport = this.generateHTMLReport(reportData);
    const htmlPath = path.join(RESULTS_DIR, 'deployed-app-test-report.html');
    await fs.writeFile(htmlPath, htmlReport);

    // Generate summary text
    const summaryPath = path.join(RESULTS_DIR, 'test-summary.txt');
    await fs.writeFile(summaryPath, this.generateSummaryText());

    console.log(`\n📄 Reports generated:`);
    console.log(`   JSON: ${jsonPath}`);
    console.log(`   HTML: ${htmlPath}`);
    console.log(`   Summary: ${summaryPath}`);
  }

  generateHTMLReport(data) {
    const passRate = data.summary.total > 0 ? 
      ((data.summary.passed / data.summary.total) * 100).toFixed(1) : 0;

    return `
<!DOCTYPE html>
<html>
<head>
    <title>MARTA App Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2196F3; color: white; padding: 20px; border-radius: 8px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .metric { background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }
        .metric.passed { background: #e8f5e8; }
        .metric.failed { background: #ffeaea; }
        .test-result { padding: 10px; margin: 5px 0; border-radius: 4px; }
        .test-result.passed { background: #e8f5e8; }
        .test-result.failed { background: #ffeaea; }
        .category { margin: 20px 0; }
        .category h3 { color: #1976D2; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚄 MARTA Application Test Report</h1>
        <p>Deployed Application: <strong>${data.url}</strong></p>
        <p>Generated: ${data.generatedAt}</p>
    </div>

    <div class="summary">
        <div class="metric">
            <h3>${data.summary.total}</h3>
            <p>Total Tests</p>
        </div>
        <div class="metric passed">
            <h3>${data.summary.passed}</h3>
            <p>Passed</p>
        </div>
        <div class="metric failed">
            <h3>${data.summary.failed}</h3>
            <p>Failed</p>
        </div>
        <div class="metric">
            <h3>${passRate}%</h3>
            <p>Pass Rate</p>
        </div>
    </div>

    <div class="category">
        <h2>📊 Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                ${data.tests.map(test => `
                    <tr class="${test.passed ? 'passed' : 'failed'}">
                        <td>${test.category}</td>
                        <td>${test.name}</td>
                        <td>${test.passed ? '✅ PASS' : '❌ FAIL'}</td>
                        <td>${test.details}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    </div>

    ${data.errors.length > 0 ? `
    <div class="category">
        <h2>⚠️ Errors</h2>
        ${data.errors.map(error => `
            <div class="test-result failed">
                <strong>${error.context}:</strong> ${error.message}
            </div>
        `).join('')}
    </div>
    ` : ''}

    <div class="category">
        <h2>🔧 Test Configuration</h2>
        <ul>
            <li>Browsers: ${data.config.browsers.join(', ')}</li>
            <li>Viewports: ${data.config.viewports.map(v => v.name).join(', ')}</li>
            <li>Timeout: ${data.config.timeout}ms</li>
            <li>Retries: ${data.config.retries}</li>
        </ul>
    </div>
</body>
</html>`;
  }

  generateSummaryText() {
    const passRate = this.results.summary.total > 0 ? 
      ((this.results.summary.passed / this.results.summary.total) * 100).toFixed(1) : 0;

    return `
MARTA Application Test Summary
=============================

URL: ${DEPLOYED_URL}
Generated: ${new Date().toISOString()}

RESULTS:
- Total Tests: ${this.results.summary.total}
- Passed: ${this.results.summary.passed}
- Failed: ${this.results.summary.failed}
- Pass Rate: ${passRate}%

BROWSERS TESTED: ${TEST_CONFIG.browsers.join(', ')}
VIEWPORTS: ${TEST_CONFIG.viewports.map(v => `${v.name} (${v.width}x${v.height})`).join(', ')}

${this.results.errors.length > 0 ? `
ERRORS:
${this.results.errors.map(e => `- ${e.context}: ${e.message}`).join('\n')}
` : 'No errors encountered.'}

Test completed successfully.
`;
  }

  printSummary() {
    const passRate = this.results.summary.total > 0 ? 
      ((this.results.summary.passed / this.results.summary.total) * 100).toFixed(1) : 0;

    console.log(`\n📈 Test Summary:`);
    console.log(`   Total Tests: ${this.results.summary.total}`);
    console.log(`   ✅ Passed: ${this.results.summary.passed}`);
    console.log(`   ❌ Failed: ${this.results.summary.failed}`);
    console.log(`   📊 Pass Rate: ${passRate}%`);
    
    if (this.results.errors.length > 0) {
      console.log(`   ⚠️  Errors: ${this.results.errors.length}`);
    }

    console.log(`\n🎯 Overall Status: ${passRate >= 80 ? '✅ GOOD' : passRate >= 60 ? '⚠️  NEEDS ATTENTION' : '❌ CRITICAL ISSUES'}`);
  }
}

// Main execution
async function main() {
  const tester = new DeployedAppTester();
  
  try {
    await tester.runAllTests();
    process.exit(tester.results.summary.failed === 0 ? 0 : 1);
  } catch (error) {
    console.error('❌ Test runner failed:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { DeployedAppTester };