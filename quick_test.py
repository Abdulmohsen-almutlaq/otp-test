#!/usr/bin/env python3
"""
Quick OTP Service Test Script
Run this after deploying to Render.com
"""

import requests
import hmac
import hashlib
import struct
import time
import base64

# Configuration
RENDER_URL = "https://otp-test-YOUR-ID.onrender.com"  # Replace with your actual URL
API_KEY = "UkFPS1EXdV8SmopIby5TvY2kCTsu228c"  # Your generated API key

def test_service_quick():
    """Quick test of the OTP service"""
    
    print("🚀 QUICK OTP SERVICE TEST")
    print("=" * 40)
    
    # Update URL
    url = input(f"Enter your Render URL (or press Enter for {RENDER_URL}): ").strip()
    if not url:
        url = RENDER_URL
    
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Test 1: Health Check
    print("\n1️⃣ Testing Health Check...")
    try:
        response = requests.get(f"{url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health: {data['status']}")
            print(f"✅ Database: {data['database']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return
    
    # Test 2: Register Device
    print("\n2️⃣ Registering test device...")
    device_data = {
        'device_id': 'TEST-DEVICE-123',
        'user_id': 'test@example.com'
    }
    
    try:
        response = requests.post(f"{url}/api/v1/devices/register", json=device_data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            derived_key = data['data']['derived_key']
            print(f"✅ Device registered!")
            print(f"📱 Device ID: {device_data['device_id']}")
            print(f"🔑 Derived Key: {derived_key[:20]}...")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"Error: {response.text}")
            return
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return
    
    # Test 3: Generate OTP
    print("\n3️⃣ Generating OTP...")
    
    def generate_otp(derived_key_b64):
        derived_key = base64.b64decode(derived_key_b64)
        time_step = int(time.time() // 30)
        msg = struct.pack(">Q", time_step)
        hmac_hash = hmac.new(derived_key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        return code_int % (10 ** 6)
    
    otp = generate_otp(derived_key)
    print(f"🔢 Generated OTP: {otp:06d}")
    
    # Test 4: Verify OTP
    print("\n4️⃣ Verifying OTP...")
    verify_data = {
        'device_id': 'TEST-DEVICE-123',
        'otp': otp
    }
    
    try:
        response = requests.post(f"{url}/api/v1/otp/verify", json=verify_data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['data']['valid']:
                print("✅ OTP verification SUCCESSFUL!")
            else:
                print("❌ OTP verification FAILED!")
        else:
            print(f"❌ Verification failed: {response.status_code}")
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"❌ Verification error: {e}")
    
    print("\n🎉 Test completed!")
    print(f"🌐 Your service is running at: {url}")
    print(f"📚 API docs: {url}/docs (if DEBUG=true)")

if __name__ == "__main__":
    test_service_quick()
