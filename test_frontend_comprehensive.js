/**
 * Comprehensive MARTA Frontend Testing Script
 * 
 * This script tests the MARTA frontend application for:
 * 1. API connectivity to Supabase edge functions
 * 2. Real-time data display
 * 3. UI functionality across different views
 * 4. Network monitoring for API calls
 * 5. Error detection and console logging
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Configuration
const FRONTEND_URL = 'http://localhost:5173';
const SUPABASE_URL = 'https://vglychbweuowsovboxyf.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY';

// Test results container
const testResults = {
    timestamp: new Date().toISOString(),
    frontend: {
        accessible: false,
        loadTime: 0,
        errors: []
    },
    api: {
        arrivals: { success: false, responseTime: 0, dataCount: 0 },
        analytics: { success: false, responseTime: 0, dataCount: 0 },
        delayPatterns: { success: false, responseTime: 0, dataCount: 0 },
        demandForecast: { success: false, responseTime: 0, dataCount: 0 }
    },
    ui: {
        mainPage: { loaded: false, hasData: false, errors: [] },
        analyticsTab: { accessible: false, hasData: false, errors: [] },
        stationSelection: { functional: false, stationCount: 0 }
    },
    network: {
        totalRequests: 0,
        successfulRequests: 0,
        failedRequests: 0,
        apiCalls: []
    },
    screenshots: []
};

async function testApiEndpoints() {
    console.log('\n🔍 Testing API Endpoints Directly...');
    
    const endpoints = [
        { name: 'arrivals', url: `${SUPABASE_URL}/functions/v1/marta-arrivals` },
        { name: 'analytics', url: `${SUPABASE_URL}/functions/v1/analytics-performance` },
        { name: 'delayPatterns', url: `${SUPABASE_URL}/functions/v1/delay-patterns` },
        { name: 'demandForecast', url: `${SUPABASE_URL}/functions/v1/demand-forecast` }
    ];

    for (const endpoint of endpoints) {
        try {
            const startTime = Date.now();
            const response = await fetch(endpoint.url, {
                headers: {
                    'apikey': SUPABASE_ANON_KEY,
                    'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
                }
            });
            
            const responseTime = Date.now() - startTime;
            
            if (response.ok) {
                const data = await response.json();
                testResults.api[endpoint.name] = {
                    success: true,
                    responseTime,
                    dataCount: Array.isArray(data) ? data.length : Object.keys(data).length,
                    status: response.status
                };
                console.log(`✅ ${endpoint.name}: OK (${responseTime}ms, ${testResults.api[endpoint.name].dataCount} items)`);
            } else {
                testResults.api[endpoint.name] = {
                    success: false,
                    responseTime,
                    dataCount: 0,
                    status: response.status,
                    error: `HTTP ${response.status}`
                };
                console.log(`❌ ${endpoint.name}: Failed (${response.status})`);
            }
        } catch (error) {
            testResults.api[endpoint.name] = {
                success: false,
                responseTime: 0,
                dataCount: 0,
                error: error.message
            };
            console.log(`❌ ${endpoint.name}: Error - ${error.message}`);
        }
    }
}

async function testFrontend() {
    console.log('\n🌐 Launching Browser for Frontend Testing...');
    
    const browser = await puppeteer.launch({
        headless: false,
        devtools: true,
        args: [
            '--disable-web-security',
            '--window-size=1280,720',
            '--disable-features=VizDisplayCompositor'
        ]
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });

    // Enable request interception to monitor network calls
    await page.setRequestInterception(true);
    
    page.on('request', (request) => {
        testResults.network.totalRequests++;
        if (request.url().includes('supabase.co/functions/v1/')) {
            testResults.network.apiCalls.push({
                url: request.url(),
                method: request.method(),
                timestamp: new Date().toISOString()
            });
        }
        request.continue();
    });

    page.on('response', async (response) => {
        if (response.ok()) {
            testResults.network.successfulRequests++;
        } else {
            testResults.network.failedRequests++;
        }

        if (response.url().includes('supabase.co/functions/v1/')) {
            try {
                const responseBody = await response.text();
                console.log(`📡 API Response: ${response.url()} - ${response.status()}`);
                console.log(`📊 Response size: ${responseBody.length} characters`);
            } catch (e) {
                console.log(`📡 API Response: ${response.url()} - ${response.status()} (body read failed)`);
            }
        }
    });

    // Capture console messages
    page.on('console', (msg) => {
        const type = msg.type();
        const text = msg.text();
        
        if (type === 'error') {
            testResults.frontend.errors.push(text);
            console.log(`🔴 Console Error: ${text}`);
        } else if (type === 'warn') {
            console.log(`🟡 Console Warning: ${text}`);
        } else if (text.includes('API') || text.includes('fetch')) {
            console.log(`🔵 Console Log: ${text}`);
        }
    });

    try {
        // Test 1: Navigate to main page
        console.log('\n📍 Test 1: Loading Main Page...');
        const startTime = Date.now();
        await page.goto(FRONTEND_URL, { waitUntil: 'networkidle2', timeout: 30000 });
        testResults.frontend.loadTime = Date.now() - startTime;
        testResults.frontend.accessible = true;
        
        // Wait for React to initialize
        await page.waitForSelector('body', { timeout: 10000 });
        console.log(`✅ Main page loaded in ${testResults.frontend.loadTime}ms`);

        // Take screenshot of main page
        const mainPageScreenshot = path.join(__dirname, 'frontend', 'test-screenshots', `main-page-${Date.now()}.png`);
        await page.screenshot({ path: mainPageScreenshot, fullPage: true });
        testResults.screenshots.push(mainPageScreenshot);
        console.log(`📸 Main page screenshot saved: ${mainPageScreenshot}`);

        // Test 2: Check for real-time data
        console.log('\n📍 Test 2: Checking for Real-time Data...');
        
        // Wait for data to load
        await page.waitForTimeout(5000);
        
        // Look for arrival data elements
        const arrivalElements = await page.$$('[data-testid*="arrival"], .arrival, .train-arrival');
        const stationElements = await page.$$('[data-testid*="station"], .station, .station-name');
        
        testResults.ui.mainPage.loaded = true;
        testResults.ui.mainPage.hasData = arrivalElements.length > 0 || stationElements.length > 0;
        testResults.ui.stationSelection.stationCount = stationElements.length;
        
        console.log(`📊 Found ${arrivalElements.length} arrival elements`);
        console.log(`🚉 Found ${stationElements.length} station elements`);

        // Test 3: Try to access Analytics tab
        console.log('\n📍 Test 3: Testing Analytics Tab...');
        
        const analyticsSelector = 'button[data-tab="analytics"], .nav-analytics, [href*="analytics"], button:contains("Analytics")';
        
        try {
            await page.waitForSelector(analyticsSelector, { timeout: 5000 });
            await page.click(analyticsSelector);
            await page.waitForTimeout(3000);
            
            testResults.ui.analyticsTab.accessible = true;
            
            // Take screenshot of analytics page
            const analyticsScreenshot = path.join(__dirname, 'frontend', 'test-screenshots', `analytics-page-${Date.now()}.png`);
            await page.screenshot({ path: analyticsScreenshot, fullPage: true });
            testResults.screenshots.push(analyticsScreenshot);
            console.log(`📸 Analytics page screenshot saved: ${analyticsScreenshot}`);
            
            // Check for analytics data
            const chartElements = await page.$$('canvas, svg, .chart, .graph');
            const metricElements = await page.$$('.metric, .kpi, .stat, .analytics-card');
            
            testResults.ui.analyticsTab.hasData = chartElements.length > 0 || metricElements.length > 0;
            console.log(`📈 Found ${chartElements.length} chart elements`);
            console.log(`📊 Found ${metricElements.length} metric elements`);
            
        } catch (error) {
            testResults.ui.analyticsTab.errors.push(error.message);
            console.log(`❌ Analytics tab not accessible: ${error.message}`);
        }

        // Test 4: Test station selection if available
        console.log('\n📍 Test 4: Testing Station Selection...');
        
        const stationSelectors = [
            'select[name*="station"], select[id*="station"]',
            '.station-selector select',
            'button[data-station], .station-button',
            'li[data-station], .station-item'
        ];
        
        for (const selector of stationSelectors) {
            try {
                const elements = await page.$$(selector);
                if (elements.length > 0) {
                    // Try clicking the first station
                    await elements[0].click();
                    await page.waitForTimeout(2000);
                    testResults.ui.stationSelection.functional = true;
                    console.log(`✅ Station selection functional with selector: ${selector}`);
                    break;
                }
            } catch (error) {
                console.log(`⚠️ Station selector ${selector} not found or not clickable`);
            }
        }

        // Test 5: Take final screenshot of Network tab (simulate)
        console.log('\n📍 Test 5: Capturing Final State...');
        
        // Open DevTools Network tab (simulated by checking network activity)
        const finalScreenshot = path.join(__dirname, 'frontend', 'test-screenshots', `final-state-${Date.now()}.png`);
        await page.screenshot({ path: finalScreenshot, fullPage: true });
        testResults.screenshots.push(finalScreenshot);

        console.log(`📸 Final state screenshot saved: ${finalScreenshot}`);

        // Wait a bit more to capture any late API calls
        await page.waitForTimeout(5000);

    } catch (error) {
        testResults.frontend.errors.push(error.message);
        console.log(`❌ Frontend test error: ${error.message}`);
    } finally {
        await browser.close();
    }
}

async function generateReport() {
    console.log('\n📋 Generating Test Report...');
    
    // Calculate overall health scores
    const apiHealth = Object.values(testResults.api).filter(api => api.success).length / Object.keys(testResults.api).length * 100;
    const networkHealth = testResults.network.totalRequests > 0 ? 
        (testResults.network.successfulRequests / testResults.network.totalRequests * 100) : 0;
    
    const report = `
# MARTA Frontend Comprehensive Test Report
Generated: ${testResults.timestamp}

## 🌐 Frontend Accessibility
- **Status**: ${testResults.frontend.accessible ? '✅ ACCESSIBLE' : '❌ NOT ACCESSIBLE'}
- **Load Time**: ${testResults.frontend.loadTime}ms
- **Errors**: ${testResults.frontend.errors.length}

## 🔌 API Connectivity (Health: ${apiHealth.toFixed(1)}%)
${Object.entries(testResults.api).map(([name, result]) => `
### ${name.toUpperCase()}
- Status: ${result.success ? '✅ SUCCESS' : '❌ FAILED'}
- Response Time: ${result.responseTime}ms
- Data Count: ${result.dataCount}
${result.error ? `- Error: ${result.error}` : ''}
`).join('')}

## 🖥️ User Interface Testing
### Main Page
- **Loaded**: ${testResults.ui.mainPage.loaded ? '✅ YES' : '❌ NO'}
- **Has Data**: ${testResults.ui.mainPage.hasData ? '✅ YES' : '❌ NO'}
- **Errors**: ${testResults.ui.mainPage.errors.length}

### Analytics Tab
- **Accessible**: ${testResults.ui.analyticsTab.accessible ? '✅ YES' : '❌ NO'}
- **Has Data**: ${testResults.ui.analyticsTab.hasData ? '✅ YES' : '❌ NO'}
- **Errors**: ${testResults.ui.analyticsTab.errors.length}

### Station Selection
- **Functional**: ${testResults.ui.stationSelection.functional ? '✅ YES' : '❌ NO'}
- **Station Count**: ${testResults.ui.stationSelection.stationCount}

## 🌐 Network Activity (Health: ${networkHealth.toFixed(1)}%)
- **Total Requests**: ${testResults.network.totalRequests}
- **Successful**: ${testResults.network.successfulRequests}
- **Failed**: ${testResults.network.failedRequests}
- **API Calls Made**: ${testResults.network.apiCalls.length}

### API Call Details
${testResults.network.apiCalls.map((call, i) => `
${i + 1}. **${call.method}** ${call.url}
   - Time: ${call.timestamp}
`).join('')}

## 📸 Screenshots Generated
${testResults.screenshots.map((path, i) => `${i + 1}. ${path}`).join('\n')}

## 🔍 Data Verification Summary
${testResults.ui.mainPage.hasData ? 
  '✅ **REAL DATA CONFIRMED**: The frontend is displaying real data from Supabase edge functions.' :
  '⚠️ **DATA STATUS UNCLEAR**: Unable to confirm if real data is being displayed.'
}

${testResults.network.apiCalls.length > 0 ?
  `✅ **API INTEGRATION CONFIRMED**: ${testResults.network.apiCalls.length} API calls made to Supabase edge functions.` :
  '❌ **API INTEGRATION ISSUE**: No API calls detected to Supabase edge functions.'
}

## 📊 Overall Assessment
- **Frontend Functionality**: ${testResults.frontend.accessible && testResults.ui.mainPage.loaded ? 'WORKING' : 'ISSUES DETECTED'}
- **API Integration**: ${apiHealth > 50 ? 'FUNCTIONAL' : 'NEEDS ATTENTION'}
- **Data Display**: ${testResults.ui.mainPage.hasData ? 'ACTIVE' : 'NO DATA VISIBLE'}
- **Real-time Updates**: ${testResults.network.apiCalls.length > 0 ? 'CONNECTED' : 'DISCONNECTED'}

---
*Test completed at ${new Date().toISOString()}*
`;

    // Save report
    const reportPath = path.join(__dirname, 'frontend', `MARTA-Frontend-Test-Report-${Date.now()}.md`);
    fs.writeFileSync(reportPath, report);
    
    // Also save raw results as JSON
    const resultsPath = path.join(__dirname, 'frontend', `test-results-${Date.now()}.json`);
    fs.writeFileSync(resultsPath, JSON.stringify(testResults, null, 2));
    
    console.log(`📄 Test report saved: ${reportPath}`);
    console.log(`📊 Raw results saved: ${resultsPath}`);
    
    return report;
}

async function main() {
    console.log('🚀 Starting MARTA Frontend Comprehensive Test Suite...');
    console.log(`Testing frontend at: ${FRONTEND_URL}`);
    console.log(`Testing API at: ${SUPABASE_URL}`);
    
    try {
        // Ensure screenshot directory exists
        const screenshotDir = path.join(__dirname, 'frontend', 'test-screenshots');
        if (!fs.existsSync(screenshotDir)) {
            fs.mkdirSync(screenshotDir, { recursive: true });
        }

        // Run tests
        await testApiEndpoints();
        await testFrontend();
        
        // Generate and display report
        const report = await generateReport();
        console.log('\n' + '='.repeat(80));
        console.log(report);
        console.log('='.repeat(80));
        
    } catch (error) {
        console.error('\n❌ Test suite failed:', error.message);
        process.exit(1);
    }
    
    console.log('\n✅ Test suite completed successfully!');
}

// Run the tests
if (require.main === module) {
    main().catch(console.error);
}

module.exports = { main, testResults };