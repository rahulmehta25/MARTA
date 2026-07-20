#!/usr/bin/env node

/**
 * Simple Deployed MARTA Application Test
 * Basic connectivity and structure test using Node.js built-ins
 */

import https from 'https';
import url from 'url';
import fs from 'fs';
import path from 'path';

const DEPLOYED_URL = 'https://marta-eta.vercel.app';

class SimpleAppTester {
  constructor() {
    this.results = {
      timestamp: new Date().toISOString(),
      url: DEPLOYED_URL,
      tests: [],
      summary: { total: 0, passed: 0, failed: 0 }
    };
  }

  async runTests() {
    console.log('🚀 Running Simple MARTA Application Test');
    console.log(`📍 Testing URL: ${DEPLOYED_URL}`);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    await this.testConnectivity();
    await this.testHeaders();
    await this.testContent();

    this.printSummary();
    this.generateReport();
  }

  async testConnectivity() {
    console.log('\n🔍 Testing Basic Connectivity...');
    
    return new Promise((resolve) => {
      const parsedUrl = url.parse(DEPLOYED_URL);
      
      const req = https.request({
        hostname: parsedUrl.hostname,
        path: parsedUrl.path,
        method: 'GET',
        timeout: 10000,
        headers: {
          'User-Agent': 'MARTA-Test-Agent/1.0'
        }
      }, (res) => {
        const statusOk = res.statusCode >= 200 && res.statusCode < 300;
        this.addResult('Connectivity', 'HTTP Response', statusOk, 
          `Status: ${res.statusCode} ${res.statusMessage}`);

        // Check response time
        const responseTime = Date.now() - startTime;
        this.addResult('Performance', 'Response Time', responseTime < 5000,
          `Response time: ${responseTime}ms`);

        // Check for redirect handling
        if (res.statusCode >= 300 && res.statusCode < 400) {
          this.addResult('Connectivity', 'Redirect Handling', true,
            `Redirected to: ${res.headers.location}`);
        }

        resolve();
      });

      req.on('timeout', () => {
        this.addResult('Connectivity', 'HTTP Response', false, 'Request timeout');
        req.destroy();
        resolve();
      });

      req.on('error', (error) => {
        this.addResult('Connectivity', 'HTTP Response', false, error.message);
        resolve();
      });

      const startTime = Date.now();
      req.end();
    });
  }

  async testHeaders() {
    console.log('\n🔧 Testing Response Headers...');
    
    return new Promise((resolve) => {
      const req = https.request(DEPLOYED_URL, { method: 'HEAD' }, (res) => {
        // Check content type
        const contentType = res.headers['content-type'] || '';
        const isHTML = contentType.includes('text/html');
        this.addResult('Headers', 'Content Type', isHTML,
          `Content-Type: ${contentType}`);

        // Check security headers
        const securityHeaders = [
          'x-frame-options',
          'x-content-type-options',
          'strict-transport-security'
        ];

        securityHeaders.forEach(header => {
          const hasHeader = !!res.headers[header];
          this.addResult('Security', `${header} Header`, hasHeader,
            hasHeader ? `${header}: ${res.headers[header]}` : `Missing ${header}`);
        });

        // Check caching headers
        const cacheControl = res.headers['cache-control'];
        this.addResult('Caching', 'Cache Control', !!cacheControl,
          cacheControl ? `cache-control: ${cacheControl}` : 'No cache control');

        resolve();
      });

      req.on('error', (error) => {
        this.addResult('Headers', 'Header Check', false, error.message);
        resolve();
      });

      req.end();
    });
  }

  async testContent() {
    console.log('\n📄 Testing Content Structure...');
    
    return new Promise((resolve) => {
      const req = https.request(DEPLOYED_URL, (res) => {
        let data = '';

        res.on('data', (chunk) => {
          data += chunk;
        });

        res.on('end', () => {
          // Test for basic HTML structure
          const hasDoctype = data.includes('<!DOCTYPE html>') || data.includes('<!doctype html>');
          this.addResult('Content', 'HTML Doctype', hasDoctype,
            hasDoctype ? 'Valid HTML doctype found' : 'Missing or invalid doctype');

          // Test for title containing MARTA
          const titleMatch = data.match(/<title[^>]*>([^<]*)<\/title>/i);
          const hasTitle = titleMatch && titleMatch[1].toLowerCase().includes('marta');
          this.addResult('Content', 'Page Title', hasTitle,
            titleMatch ? `Title: "${titleMatch[1]}"` : 'No title found');

          // Test for meta viewport (responsive design)
          const hasViewport = data.includes('name="viewport"');
          this.addResult('Content', 'Viewport Meta', hasViewport,
            hasViewport ? 'Viewport meta tag found' : 'Missing viewport meta tag');

          // Test for React/JavaScript
          const hasReactScripts = data.includes('react') || data.includes('js') || data.includes('script');
          this.addResult('Content', 'JavaScript/React', hasReactScripts,
            hasReactScripts ? 'JavaScript/React detected' : 'No JavaScript detected');

          // Test for CSS/Styles
          const hasStyles = data.includes('<style') || data.includes('.css') || data.includes('tailwind');
          this.addResult('Content', 'Styling', hasStyles,
            hasStyles ? 'CSS/Styling detected' : 'No styling detected');

          // Test for app container
          const hasAppContainer = data.includes('id="root"') || data.includes('class="App"') || 
                                  data.includes('data-reactroot');
          this.addResult('Content', 'App Container', hasAppContainer,
            hasAppContainer ? 'React app container found' : 'No app container detected');

          // Check content size (should be substantial for a real app)
          const contentSize = data.length;
          const hasSubstantialContent = contentSize > 1000; // At least 1KB
          this.addResult('Content', 'Content Size', hasSubstantialContent,
            `Content size: ${(contentSize / 1024).toFixed(2)}KB`);

          // Test for common SPA patterns
          const isSPA = data.includes('history') || data.includes('router') || 
                       data.includes('single-page') || data.includes('app.js');
          this.addResult('Content', 'SPA Pattern', isSPA,
            isSPA ? 'SPA patterns detected' : 'Static content (not SPA)');

          resolve();
        });
      });

      req.on('error', (error) => {
        this.addResult('Content', 'Content Check', false, error.message);
        resolve();
      });

      req.end();
    });
  }

  addResult(category, test, passed, details) {
    this.results.tests.push({
      category,
      test,
      passed,
      details,
      timestamp: new Date().toISOString()
    });

    this.results.summary.total++;
    if (passed) {
      this.results.summary.passed++;
      console.log(`  ✅ ${test}: ${details}`);
    } else {
      this.results.summary.failed++;
      console.log(`  ❌ ${test}: ${details}`);
    }
  }

  printSummary() {
    const { total, passed, failed } = this.results.summary;
    const passRate = total > 0 ? ((passed / total) * 100).toFixed(1) : 0;

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 Test Summary:');
    console.log(`   Total Tests: ${total}`);
    console.log(`   ✅ Passed: ${passed}`);
    console.log(`   ❌ Failed: ${failed}`);
    console.log(`   📈 Pass Rate: ${passRate}%`);
    console.log(`\n🎯 Overall Status: ${passRate >= 80 ? '✅ EXCELLENT' : passRate >= 60 ? '⚠️  GOOD' : passRate >= 40 ? '🔄 NEEDS WORK' : '❌ CRITICAL ISSUES'}`);
  }

  generateReport() {
    const reportPath = '/Users/rahulmehta/Desktop/MARTA/frontend/test-results/simple-test-report.json';

    try {
      // Create directory if it doesn't exist
      const dir = path.dirname(reportPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      fs.writeFileSync(reportPath, JSON.stringify(this.results, null, 2));
      console.log(`\n📄 Test report saved: ${reportPath}`);
    } catch (error) {
      console.log(`\n⚠️  Could not save report: ${error.message}`);
    }
  }
}

// Run the test
async function main() {
  const tester = new SimpleAppTester();
  await tester.runTests();
  
  // Exit with appropriate code
  process.exit(tester.results.summary.failed === 0 ? 0 : 1);
}

main().catch(error => {
  console.error('Test runner failed:', error);
  process.exit(1);
});

export { SimpleAppTester };