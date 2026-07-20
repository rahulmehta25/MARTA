#!/usr/bin/env node

const https = require('https');

function checkDeployment() {
  console.log('🧪 Testing MARTA deployment at https://marta-eta.vercel.app\n');
  
  https.get('https://marta-eta.vercel.app', (res) => {
    console.log('✅ Status Code:', res.statusCode);
    console.log('✅ Headers:', {
      'content-type': res.headers['content-type'],
      'cache-control': res.headers['cache-control']
    });
    
    let data = '';
    res.on('data', (chunk) => {
      data += chunk;
    });
    
    res.on('end', () => {
      // Check for critical elements
      const checks = [
        { test: data.includes('<div id="root">'), name: 'React root element' },
        { test: data.includes('MARTA Analytics'), name: 'Page title' },
        { test: data.includes('/assets/index-'), name: 'JavaScript bundle' },
        { test: data.includes('</html>'), name: 'Complete HTML' },
        { test: res.statusCode === 200, name: 'HTTP 200 status' }
      ];
      
      console.log('\n📋 Component Checks:');
      checks.forEach(check => {
        console.log(check.test ? `✅ ${check.name}` : `❌ ${check.name}`);
      });
      
      const passed = checks.every(c => c.test);
      console.log('\n' + (passed ? '🎉 Deployment successful!' : '❌ Deployment has issues'));
      console.log('\n🌐 Visit: https://marta-eta.vercel.app');
    });
  }).on('error', (err) => {
    console.error('❌ Error:', err.message);
  });
}

checkDeployment();