#!/usr/bin/env python3
"""
Test script for MARTA Analytics API endpoints
Verifies that all analytics features are working correctly
"""
import httpx
import json
from datetime import datetime
import sys

# Configuration
BASE_URL = "http://localhost:8000"  # Change to production URL when deployed
ENDPOINTS = [
    ("/health", "GET", None),
    ("/api/v1/analytics/performance", "GET", None),
    ("/api/v1/analytics/system", "GET", None),
    ("/api/v1/analytics/station/FIVE POINTS STATION", "GET", None),
    ("/api/v1/analytics/predictions/FIVE POINTS STATION?line=RED", "GET", None),
    ("/api/v1/analytics/delay-patterns", "GET", None),
    ("/api/v1/analytics/demand/FIVE POINTS STATION", "GET", None),
    ("/api/v1/analytics/insights", "GET", None),
]

def test_endpoint(client, path, method, data=None):
    """Test a single endpoint"""
    try:
        url = f"{BASE_URL}{path}"
        
        if method == "GET":
            response = client.get(url)
        elif method == "POST":
            response = client.post(url, json=data)
        else:
            return False, f"Unsupported method: {method}"
        
        # Check status code
        if response.status_code != 200:
            return False, f"Status {response.status_code}: {response.text[:200]}"
        
        # Try to parse JSON
        try:
            data = response.json()
            return True, data
        except:
            return False, "Invalid JSON response"
            
    except httpx.ConnectError:
        return False, "Connection failed - is the server running?"
    except Exception as e:
        return False, str(e)

def main():
    """Run all API tests"""
    print("🧪 Testing MARTA Analytics API Endpoints")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    with httpx.Client(timeout=30.0) as client:
        for endpoint, method, data in ENDPOINTS:
            print(f"\nTesting: {method} {endpoint}")
            success, result = test_endpoint(client, endpoint, method, data)
            
            if success:
                print(f"  ✅ PASSED")
                
                # Show key metrics for important endpoints
                if "performance" in endpoint:
                    if isinstance(result, dict):
                        health = result.get('health_status', 'unknown')
                        score = result.get('health_score', 0)
                        print(f"     Health: {health} (score: {score})")
                
                elif "predictions" in endpoint:
                    if isinstance(result, dict):
                        seconds = result.get('predicted_seconds')
                        confidence = result.get('confidence', 0)
                        method = result.get('method', 'unknown')
                        if seconds:
                            print(f"     Prediction: {seconds}s (confidence: {confidence:.0%}, method: {method})")
                
                elif "insights" in endpoint:
                    if isinstance(result, dict):
                        count = result.get('insights_count', 0)
                        print(f"     Insights: {count} generated")
                
                elif "delay-patterns" in endpoint:
                    if isinstance(result, dict):
                        count = result.get('patterns_count', 0)
                        print(f"     Patterns: {count} identified")
                
                passed += 1
            else:
                print(f"  ❌ FAILED: {result}")
                failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Analytics API is working correctly.")
        return 0
    else:
        print(f"⚠️  {failed} test(s) failed. Check the server logs.")
        return 1

if __name__ == "__main__":
    sys.exit(main())