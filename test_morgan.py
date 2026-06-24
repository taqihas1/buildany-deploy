#!/usr/bin/env python3
"""
Quick test Morgan chat API
"""
import requests, json

BASE_URL = "http://localhost:3000"

def test_morgan():
    print("🧪 Testing Morgan Chat...")
    try:
        res = requests.post(f"{BASE_URL}/api/morgan-chat", json={
            "messages": [{"role": "user", "content": "hi"}],
            "projectContext": {"projectId": "test", "description": "test"}
        }, timeout=30)
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Response: {data.get('content', 'NO CONTENT')[:200]}")
        print(f"Model: {data.get('model', 'unknown')}")
    except Exception as e:
        print(f"Error: {e}")

test_morgan()
