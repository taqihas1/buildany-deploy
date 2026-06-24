#!/usr/bin/env python3
"""
Test Morgan Chat API - Diagnose why Morgan returns "No response"
"""
import requests, json, sys

BASE_URL = "http://localhost:3000"

def test_morgan_chat():
    print("=" * 60)
    print("🔍 Testing Morgan Chat API")
    print("=" * 60)
    
    # Test 1: Simple message
    print("\n1. Testing with simple message...")
    try:
        res = requests.post(f"{BASE_URL}/api/morgan-chat", json={
            "messages": [{"role": "user", "content": "hi"}],
            "projectContext": {"projectId": "test", "description": "test app"}
        }, timeout=30)
        print(f"   Status: {res.status_code}")
        print(f"   Response: {res.text[:200]}")
        if res.status_code == 200:
            data = res.json()
            print(f"   ✅ Morgan says: {data.get('content', 'No content')[:100]}")
        else:
            print(f"   ❌ Error: {res.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 2: Check if API is reachable
    print("\n2. Testing API reachability...")
    try:
        res = requests.get(f"{BASE_URL}/api/morgan-chat", timeout=5)
        print(f"   Status: {res.status_code} (GET should be 405)")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 3: Check if route exists in build output
    print("\n3. Checking build output...")
    import os
    route_file = "/root/buildany/.next/server/app/api/morgan-chat/route.js"
    if os.path.exists(route_file):
        print(f"   ✅ Route compiled: {route_file}")
    else:
        print(f"   ❌ Route not found in build output!")
    
    # Test 4: Check DeepSeek API key
    print("\n4. Checking DeepSeek API key...")
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        print(f"   ✅ Key present (len={len(key)})")
    else:
        print(f"   ❌ DEEPSEEK_API_KEY not set!")

if __name__ == "__main__":
    test_morgan_chat()
