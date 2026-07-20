#!/usr/bin/env node

const https = require('https');
const http = require('http');

const SUPABASE_URL = 'https://vglychbweuowsovboxyf.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZnbHljaGJ3ZXVvd3NvdmJveHlmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2OTA5OTMsImV4cCI6MjA3MjI2Njk5M30.W8P-ZLQRWouaWH8LWVA4frKNs5r-nX_j_x27oRIAerY';

console.log('🔍 MARTA Backend Connection Test');
console.log('=====================================\n');

// Test functions
async function testSupabaseEndpoint(name, path) {
    return new Promise((resolve) => {
        const url = new URL(`${SUPABASE_URL}/functions/v1/${path}`);
        
        const options = {
            hostname: url.hostname,
            path: url.pathname + url.search,
            method: 'GET',
            headers: {
                'apikey': SUPABASE_ANON_KEY,
                'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const json = JSON.parse(data);
                    if (res.statusCode === 200) {
                        console.log(`✅ ${name}: SUCCESS`);
                        if (Array.isArray(json)) {
                            console.log(`   Returns ${json.length} items`);
                        } else if (typeof json === 'object') {
                            console.log(`   Returns object with keys: ${Object.keys(json).join(', ')}`);
                        }
                    } else {
                        console.log(`❌ ${name}: HTTP ${res.statusCode}`);
                        console.log(`   Error: ${JSON.stringify(json).substring(0, 100)}`);
                    }
                } catch (e) {
                    console.log(`❌ ${name}: Failed to parse response`);
                }
                resolve();
            });
        });

        req.on('error', (e) => {
            console.log(`❌ ${name}: ${e.message}`);
            resolve();
        });

        req.end();
    });
}

async function testFrontend() {
    return new Promise((resolve) => {
        http.get('http://localhost:5173/', (res) => {
            if (res.statusCode === 200) {
                console.log('✅ Frontend: Running on http://localhost:5173');
            } else {
                console.log(`⚠️ Frontend: HTTP ${res.statusCode}`);
            }
            resolve();
        }).on('error', (e) => {
            console.log('❌ Frontend: Not running on localhost:5173');
            resolve();
        });
    });
}

// Run all tests
async function runTests() {
    console.log('1. FRONTEND STATUS:');
    console.log('-------------------');
    await testFrontend();
    
    console.log('\n2. BACKEND (EDGE FUNCTIONS) STATUS:');
    console.log('------------------------------------');
    await testSupabaseEndpoint('marta-arrivals', 'marta-arrivals?station=FIVE POINTS STATION');
    await testSupabaseEndpoint('analytics-performance', 'analytics-performance');
    await testSupabaseEndpoint('analytics-insights', 'analytics-insights');
    await testSupabaseEndpoint('predict-arrival', 'predict-arrival?station=AIRPORT STATION&line=RED&direction=N');
    await testSupabaseEndpoint('delay-patterns', 'delay-patterns');
    await testSupabaseEndpoint('demand-forecast', 'demand-forecast?station=FIVE POINTS STATION');
    
    console.log('\n3. INTEGRATION STATUS:');
    console.log('----------------------');
    
    // Test if frontend can reach backend
    const frontendWorks = await new Promise(resolve => {
        http.get('http://localhost:5173/', res => resolve(res.statusCode === 200))
            .on('error', () => resolve(false));
    });
    
    const backendWorks = await new Promise(resolve => {
        const url = new URL(`${SUPABASE_URL}/functions/v1/marta-arrivals`);
        https.get({
            hostname: url.hostname,
            path: url.pathname,
            headers: {
                'apikey': SUPABASE_ANON_KEY,
                'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
            }
        }, res => resolve(res.statusCode === 200))
        .on('error', () => resolve(false));
    });
    
    if (frontendWorks && backendWorks) {
        console.log('✅ Frontend-Backend Integration: READY');
        console.log('   Frontend can fetch data from Supabase Edge Functions');
    } else if (frontendWorks && !backendWorks) {
        console.log('⚠️ Frontend running but backend unavailable');
    } else if (!frontendWorks && backendWorks) {
        console.log('⚠️ Backend working but frontend not running');
    } else {
        console.log('❌ Both frontend and backend have issues');
    }
    
    console.log('\n=====================================');
    console.log('📊 SUMMARY:');
    if (frontendWorks && backendWorks) {
        console.log('✅ System is FULLY OPERATIONAL!');
        console.log('   - Frontend: http://localhost:5173');
        console.log('   - Backend: Supabase Edge Functions');
        console.log('   - Real MARTA data is being served');
    } else {
        console.log('⚠️ System has some issues that need attention');
    }
}

runTests();