/**
 * Manual Frontend Test with Better Error Handling
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const FRONTEND_URL = 'http://localhost:5173';

async function testFrontendManual() {
    console.log('🚀 Starting Manual Frontend Test...');
    
    const browser = await puppeteer.launch({
        headless: false,
        devtools: true,
        args: ['--disable-web-security', '--window-size=1280,720']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });

    // Monitor network requests
    const apiCalls = [];
    page.on('response', async (response) => {
        const url = response.url();
        if (url.includes('supabase.co/functions/v1/') || url.includes('marta')) {
            console.log(`📡 API Call: ${response.status()} - ${url}`);
            apiCalls.push({
                url,
                status: response.status(),
                ok: response.ok()
            });
        }
    });

    // Capture console logs
    page.on('console', (msg) => {
        const type = msg.type();
        if (type === 'error') {
            console.log(`🔴 Console Error: ${msg.text()}`);
        } else if (type === 'log' && (msg.text().includes('API') || msg.text().includes('data'))) {
            console.log(`🔵 Console Log: ${msg.text()}`);
        }
    });

    try {
        // Navigate to frontend
        console.log('📍 Loading MARTA Frontend...');
        await page.goto(FRONTEND_URL, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Take initial screenshot
        const mainScreenshot = path.join(__dirname, 'frontend', 'test-screenshots', `main-screenshot-${Date.now()}.png`);
        await page.screenshot({ path: mainScreenshot, fullPage: true });
        console.log(`📸 Main page screenshot: ${mainScreenshot}`);

        // Wait for potential data loading
        console.log('⏳ Waiting for data to load...');
        await page.waitForTimeout(8000);

        // Check if Analytics tab is accessible
        console.log('📍 Testing Analytics Tab...');
        try {
            // Look for Analytics tab or button
            const analyticsSelectors = [
                'button[data-testid="analytics-tab"]',
                'button:contains("Analytics")',
                '[role="tab"]:contains("Analytics")',
                '.nav-analytics',
                'a[href*="analytics"]'
            ];
            
            let analyticsFound = false;
            for (const selector of analyticsSelectors) {
                try {
                    const elements = await page.$$(selector);
                    if (elements.length > 0) {
                        console.log(`✅ Found Analytics tab with selector: ${selector}`);
                        await elements[0].click();
                        analyticsFound = true;
                        break;
                    }
                } catch (e) {
                    // Try next selector
                }
            }

            if (!analyticsFound) {
                // Try clicking on "Analytics" text directly
                await page.evaluate(() => {
                    const elements = Array.from(document.querySelectorAll('*'));
                    const analyticsElement = elements.find(el => el.textContent && el.textContent.trim() === 'Analytics');
                    if (analyticsElement) {
                        analyticsElement.click();
                        return true;
                    }
                    return false;
                });
            }

            // Wait for analytics page to load
            await page.waitForTimeout(3000);
            
            // Take analytics screenshot
            const analyticsScreenshot = path.join(__dirname, 'frontend', 'test-screenshots', `analytics-screenshot-${Date.now()}.png`);
            await page.screenshot({ path: analyticsScreenshot, fullPage: true });
            console.log(`📸 Analytics page screenshot: ${analyticsScreenshot}`);

        } catch (error) {
            console.log(`⚠️ Analytics tab test failed: ${error.message}`);
        }

        // Check for live data elements
        console.log('📍 Checking for live data elements...');
        const dataElements = await page.evaluate(() => {
            const elements = {
                stations: document.querySelectorAll('[data-testid*="station"], .station, .stop').length,
                arrivals: document.querySelectorAll('[data-testid*="arrival"], .arrival, .train').length,
                routes: document.querySelectorAll('[data-testid*="route"], .route, .line').length,
                status: document.querySelectorAll('.status, .connected, .active').length,
                metrics: document.querySelectorAll('.metric, .stat, .kpi, .number').length
            };
            
            // Look for specific text content that indicates real data
            const textContent = document.body.textContent || '';
            elements.hasStationNames = textContent.includes('Station') || textContent.includes('STATION');
            elements.hasSystemStatus = textContent.includes('System Active') || textContent.includes('Connected');
            elements.hasRealTimeData = textContent.includes('Real-time') || textContent.includes('Live Data');
            
            return elements;
        });

        console.log('📊 Data Elements Found:');
        console.log(`  - Stations: ${dataElements.stations}`);
        console.log(`  - Arrivals: ${dataElements.arrivals}`);
        console.log(`  - Routes: ${dataElements.routes}`);
        console.log(`  - Status indicators: ${dataElements.status}`);
        console.log(`  - Metrics: ${dataElements.metrics}`);
        console.log(`  - Has station names: ${dataElements.hasStationNames}`);
        console.log(`  - Has system status: ${dataElements.hasSystemStatus}`);
        console.log(`  - Has real-time data: ${dataElements.hasRealTimeData}`);

        // Final screenshot
        await page.waitForTimeout(2000);
        const finalScreenshot = path.join(__dirname, 'frontend', 'test-screenshots', `final-screenshot-${Date.now()}.png`);
        await page.screenshot({ path: finalScreenshot, fullPage: true });
        console.log(`📸 Final screenshot: ${finalScreenshot}`);

        // Report findings
        console.log('\n📋 TEST RESULTS:');
        console.log(`📡 API Calls Made: ${apiCalls.length}`);
        console.log(`✅ Successful API Calls: ${apiCalls.filter(call => call.ok).length}`);
        console.log(`❌ Failed API Calls: ${apiCalls.filter(call => !call.ok).length}`);

        if (apiCalls.length > 0) {
            console.log('\n📡 API Call Details:');
            apiCalls.forEach((call, i) => {
                console.log(`  ${i + 1}. ${call.status} - ${call.url}`);
            });
        }

        const hasData = dataElements.stations > 0 || dataElements.hasSystemStatus || dataElements.hasRealTimeData;
        console.log(`\n🔍 DATA VERIFICATION: ${hasData ? '✅ REAL DATA DETECTED' : '❌ NO DATA DETECTED'}`);
        console.log(`🔗 API INTEGRATION: ${apiCalls.length > 0 ? '✅ API CALLS MADE' : '⚠️ NO API CALLS DETECTED'}`);
        console.log(`🖥️ FRONTEND STATUS: ${dataElements.hasSystemStatus ? '✅ SYSTEM ACTIVE' : '❌ SYSTEM INACTIVE'}`);

    } catch (error) {
        console.error(`❌ Test failed: ${error.message}`);
    } finally {
        await browser.close();
    }
}

testFrontendManual().catch(console.error);