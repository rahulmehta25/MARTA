import puppeteer from 'puppeteer';
import fs from 'fs';

async function assessMartaFrontend() {
    let browser;
    try {
        console.log('🚀 Starting MARTA Frontend Assessment...');
        
        browser = await puppeteer.launch({ 
            headless: false, 
            devtools: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security']
        });
        
        const page = await browser.newPage();
        await page.setViewport({ width: 1280, height: 720 });
        
        // Capture console logs
        const consoleLogs = [];
        page.on('console', msg => {
            const logEntry = `[${msg.type()}] ${msg.text()}`;
            consoleLogs.push(logEntry);
            console.log(`Console: ${logEntry}`);
        });
        
        // Capture network errors
        const networkErrors = [];
        page.on('response', response => {
            if (!response.ok()) {
                const errorEntry = `Network Error: ${response.status()} ${response.url()}`;
                networkErrors.push(errorEntry);
                console.log(`❌ ${errorEntry}`);
            }
        });
        
        // Navigate to the application
        console.log('📱 Navigating to http://localhost:5174...');
        await page.goto('http://localhost:5174', { 
            waitUntil: 'networkidle0',
            timeout: 15000 
        });
        
        console.log('✅ Page loaded successfully');
        
        // Wait for React to render
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Take initial screenshot
        await page.screenshot({ path: 'marta-initial.png', fullPage: true });
        console.log('📸 Initial screenshot saved as marta-initial.png');
        
        // Check page title
        const title = await page.title();
        console.log(`📄 Page Title: ${title}`);
        
        // Check for main content
        const bodyContent = await page.$eval('body', el => el.textContent);
        if (bodyContent.includes('MARTA')) {
            console.log('✅ MARTA content found on page');
        } else {
            console.log('⚠️ No MARTA content detected');
        }
        
        // Check for specific API-related elements or errors
        try {
            await page.waitForSelector('.loading, .error, .data-container, main', { timeout: 5000 });
            console.log('✅ Main UI elements found');
        } catch (e) {
            console.log('⚠️ Main UI elements not found within 5 seconds');
        }
        
        // Test PWA functionality
        console.log('🔍 Testing PWA features...');
        
        // Check for service worker registration
        const swRegistered = await page.evaluate(() => {
            return 'serviceWorker' in navigator;
        });
        console.log(`PWA - Service Worker Support: ${swRegistered ? '✅' : '❌'}`);
        
        // Check for manifest
        const manifestExists = await page.$('link[rel="manifest"]');
        console.log(`PWA - Manifest Link: ${manifestExists ? '✅' : '❌'}`);
        
        // Wait a bit more for any async operations
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Take final screenshot
        await page.screenshot({ path: 'marta-final.png', fullPage: true });
        console.log('📸 Final screenshot saved as marta-final.png');
        
        // Analyze console logs
        console.log('\n📋 CONSOLE LOGS ANALYSIS:');
        console.log(`Total logs: ${consoleLogs.length}`);
        
        const errors = consoleLogs.filter(log => log.includes('[error]'));
        const warnings = consoleLogs.filter(log => log.includes('[warning]'));
        const apiErrors = consoleLogs.filter(log => 
            log.toLowerCase().includes('api') || 
            log.toLowerCase().includes('fetch') || 
            log.toLowerCase().includes('getstops') ||
            log.toLowerCase().includes('getroutes')
        );
        
        console.log(`❌ Errors: ${errors.length}`);
        if (errors.length > 0) {
            errors.slice(0, 3).forEach(error => console.log(`  ${error}`));
        }
        
        console.log(`⚠️ Warnings: ${warnings.length}`);
        if (warnings.length > 0) {
            warnings.slice(0, 2).forEach(warning => console.log(`  ${warning}`));
        }
        
        console.log(`🌐 API-related logs: ${apiErrors.length}`);
        if (apiErrors.length > 0) {
            apiErrors.slice(0, 3).forEach(log => console.log(`  ${log}`));
        }
        
        console.log(`🌐 Network errors: ${networkErrors.length}`);
        if (networkErrors.length > 0) {
            networkErrors.slice(0, 3).forEach(error => console.log(`  ${error}`));
        }
        
        // Summary
        console.log('\n📊 ASSESSMENT SUMMARY:');
        console.log(`✅ Page loads: ${title ? 'YES' : 'NO'}`);
        console.log(`✅ MARTA content: ${bodyContent.includes('MARTA') ? 'YES' : 'NO'}`);
        console.log(`❌ Console errors: ${errors.length}`);
        console.log(`🌐 Network errors: ${networkErrors.length}`);
        console.log(`📱 PWA ready: ${swRegistered && manifestExists ? 'YES' : 'PARTIAL'}`);
        
        const assessment = {
            status: errors.length === 0 && networkErrors.length === 0 ? 'HEALTHY' : 'ISSUES_FOUND',
            errors: errors.length,
            warnings: warnings.length,
            networkErrors: networkErrors.length,
            apiIssues: apiErrors.length,
            pwaReady: swRegistered && manifestExists
        };
        
        // Save assessment to file
        fs.writeFileSync('marta-assessment.json', JSON.stringify(assessment, null, 2));
        console.log('📄 Assessment saved to marta-assessment.json');
        
    } catch (error) {
        console.error('❌ Assessment failed:', error);
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

async function testAnalyticsTab() {
    let browser;
    try {
        console.log('🔍 Testing Analytics Tab...');
        
        browser = await puppeteer.launch({ 
            headless: false, 
            devtools: false,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        
        const page = await browser.newPage();
        await page.setViewport({ width: 1280, height: 720 });
        
        // Navigate to the app
        await page.goto('http://localhost:5174', { 
            waitUntil: 'networkidle2',
            timeout: 15000 
        });
        
        console.log('✅ Page loaded, waiting for content...');
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Click Analytics tab
        try {
            // Wait for tab buttons to be available
            await page.waitForSelector('nav button', { timeout: 5000 });
            
            // Find and click Analytics tab
            const analyticsTab = await page.$x("//button[contains(text(), 'Analytics')]");
            if (analyticsTab.length > 0) {
                await analyticsTab[0].click();
                console.log('✅ Clicked Analytics tab');
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                await page.screenshot({ path: 'assessment-analytics.png', fullPage: true });
                console.log('📸 Analytics screenshot saved');
            } else {
                console.log('⚠️ Analytics tab not found, trying alternative selector');
                // Try clicking the 4th tab (Analytics is usually the last one)
                const tabs = await page.$$('nav button');
                if (tabs.length >= 4) {
                    await tabs[3].click();
                    console.log('✅ Clicked Analytics tab (by position)');
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    await page.screenshot({ path: 'assessment-analytics.png', fullPage: true });
                    console.log('📸 Analytics screenshot saved');
                }
            }
        } catch (error) {
            console.log('❌ Failed to click Analytics tab:', error.message);
            // Still take a screenshot of whatever is currently visible
            await page.screenshot({ path: 'assessment-analytics.png', fullPage: true });
            console.log('📸 Analytics screenshot saved (current state)');
        }
        
        // Test mobile view
        await page.setViewport({ width: 375, height: 667 });
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.screenshot({ path: 'assessment-mobile.png', fullPage: true });
        console.log('📸 Mobile screenshot saved');
        
        // Test tablet view
        await page.setViewport({ width: 768, height: 1024 });
        await new Promise(resolve => setTimeout(resolve, 1000));
        await page.screenshot({ path: 'assessment-tablet.png', fullPage: true });
        console.log('📸 Tablet screenshot saved');
        
        // Back to desktop and main page
        await page.setViewport({ width: 1280, height: 720 });
        try {
            const overviewTab = await page.$x("//button[contains(text(), 'Overview')]");
            if (overviewTab.length > 0) {
                await overviewTab[0].click();
                console.log('✅ Clicked Overview tab');
            } else {
                // Try clicking the first tab
                const tabs = await page.$$('nav button');
                if (tabs.length > 0) {
                    await tabs[0].click();
                    console.log('✅ Clicked Overview tab (by position)');
                }
            }
        } catch (error) {
            console.log('⚠️ Could not click Overview tab:', error.message);
        }
        await new Promise(resolve => setTimeout(resolve, 2000));
        await page.screenshot({ path: 'assessment-main-page.png', fullPage: true });
        console.log('📸 Main page screenshot saved');
        
    } catch (error) {
        console.error('❌ Analytics test failed:', error);
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

// Run both assessments
assessMartaFrontend().then(() => {
    return testAnalyticsTab();
});