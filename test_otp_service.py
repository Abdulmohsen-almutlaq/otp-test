import requests
import hmac
import hashlib
import struct
import time
import base64
import json
from typing import Dict, Any

class OTPTester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def test_health_check(self) -> Dict[str, Any]:
        """Test the health endpoint"""
        print("🏥 Testing Health Check...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            result = {
                'status_code': response.status_code,
                'response': response.json() if response.status_code == 200 else response.text,
                'success': response.status_code == 200
            }
            
            if result['success']:
                print("✅ Health check passed!")
                print(f"   Database: {result['response'].get('database', 'Unknown')}")
                print(f"   Status: {result['response'].get('status', 'Unknown')}")
            else:
                print(f"❌ Health check failed! Status: {response.status_code}")
            
            return result
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return {'success': False, 'error': str(e)}
    
    def register_device(self, device_id: str, user_id: str) -> Dict[str, Any]:
        """Register a new device"""
        print(f"📱 Registering device: {device_id}")
        try:
            data = {
                'device_id': device_id,
                'user_id': user_id
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/devices/register",
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            result = {
                'status_code': response.status_code,
                'response': response.json() if response.status_code in [200, 400] else response.text,
                'success': response.status_code == 200
            }
            
            if result['success']:
                print("✅ Device registered successfully!")
                derived_key = result['response']['data']['derived_key']
                print(f"   Derived Key: {derived_key[:20]}...")
                return result
            else:
                print(f"❌ Device registration failed! Status: {response.status_code}")
                print(f"   Error: {result['response']}")
            
            return result
        except Exception as e:
            print(f"❌ Device registration error: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_otp_locally(self, derived_key_b64: str) -> int:
        """Generate OTP locally using derived key"""
        derived_key = base64.b64decode(derived_key_b64)
        time_step = int(time.time() // 30)  # 30 second interval
        msg = struct.pack(">Q", time_step)
        hmac_hash = hmac.new(derived_key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        return code_int % (10 ** 6)  # 6 digits
    
    def verify_otp(self, device_id: str, otp: int) -> Dict[str, Any]:
        """Verify OTP with the server"""
        print(f"🔐 Verifying OTP: {otp:06d}")
        try:
            data = {
                'device_id': device_id,
                'otp': otp
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/otp/verify",
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            result = {
                'status_code': response.status_code,
                'response': response.json() if response.status_code in [200, 400] else response.text,
                'success': response.status_code == 200
            }
            
            if result['success']:
                is_valid = result['response']['data']['valid']
                if is_valid:
                    print("✅ OTP verification PASSED!")
                else:
                    print("❌ OTP verification FAILED - Invalid OTP")
            else:
                print(f"❌ OTP verification error! Status: {response.status_code}")
                print(f"   Error: {result['response']}")
            
            return result
        except Exception as e:
            print(f"❌ OTP verification error: {e}")
            return {'success': False, 'error': str(e)}
    
    def deactivate_device(self, device_id: str) -> Dict[str, Any]:
        """Deactivate a device"""
        print(f"🚫 Deactivating device: {device_id}")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/devices/{device_id}/deactivate",
                headers=self.headers,
                timeout=10
            )
            
            result = {
                'status_code': response.status_code,
                'response': response.json() if response.status_code in [200, 400] else response.text,
                'success': response.status_code == 200
            }
            
            if result['success']:
                print("✅ Device deactivated successfully!")
            else:
                print(f"❌ Device deactivation failed! Status: {response.status_code}")
            
            return result
        except Exception as e:
            print(f"❌ Device deactivation error: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_full_test(self, device_id: str = "TEST-DEVICE-001", user_id: str = "test@example.com"):
        """Run complete test suite"""
        print("=" * 60)
        print("🚀 STARTING OTP SERVICE FULL TEST")
        print("=" * 60)
        
        # Test 1: Health Check
        health = self.test_health_check()
        if not health['success']:
            print("❌ Health check failed - stopping tests")
            return False
        
        print("\n" + "-" * 40)
        
        # Test 2: Register Device
        registration = self.register_device(device_id, user_id)
        if not registration['success']:
            print("❌ Device registration failed - stopping tests")
            return False
        
        derived_key = registration['response']['data']['derived_key']
        
        print("\n" + "-" * 40)
        
        # Test 3: Generate and Verify OTP
        otp = self.generate_otp_locally(derived_key)
        print(f"🔢 Generated OTP locally: {otp:06d}")
        
        verification = self.verify_otp(device_id, otp)
        if not verification['success'] or not verification['response']['data']['valid']:
            print("❌ OTP verification failed")
            return False
        
        print("\n" + "-" * 40)
        
        # Test 4: Test Invalid OTP
        print("🧪 Testing invalid OTP...")
        invalid_otp = 999999
        invalid_verification = self.verify_otp(device_id, invalid_otp)
        if invalid_verification['success'] and not invalid_verification['response']['data']['valid']:
            print("✅ Invalid OTP correctly rejected!")
        else:
            print("⚠️ Invalid OTP test unexpected result")
        
        print("\n" + "-" * 40)
        
        # Test 5: Test Authentication
        print("🔑 Testing without API key...")
        old_headers = self.headers.copy()
        self.headers = {'Content-Type': 'application/json'}
        
        auth_test = self.verify_otp(device_id, otp)
        if auth_test['status_code'] == 401:
            print("✅ Authentication protection working!")
        else:
            print("⚠️ Authentication test unexpected result")
        
        # Restore headers
        self.headers = old_headers
        
        print("\n" + "-" * 40)
        
        # Test 6: Deactivate Device
        deactivation = self.deactivate_device(device_id)
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS COMPLETED!")
        print("=" * 60)
        
        return True


def main():
    """Main testing function"""
    print("🧪 OTP SERVICE TESTER")
    print("Choose testing mode:")
    print("1. Local testing (http://localhost:8000)")
    print("2. Render.com testing (your deployed service)")
    print("3. Custom URL")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        base_url = "http://localhost:8000"
        print("📍 Testing locally at http://localhost:8000")
    elif choice == "2":
        service_name = input("Enter your Render service name (e.g., otp-test-abc123): ").strip()
        base_url = f"https://{service_name}.onrender.com"
        print(f"📍 Testing Render deployment at {base_url}")
    elif choice == "3":
        base_url = input("Enter custom URL: ").strip()
    else:
        print("Invalid choice!")
        return
    
    # Get API key
    print("\n🔑 API Key needed for testing")
    print("Use this generated key: UkFPS1EXdV8SmopIby5TvY2kCTsu228c")
    api_key = input("Enter API key (or press Enter for generated key): ").strip()
    
    if not api_key:
        api_key = "UkFPS1EXdV8SmopIby5TvY2kCTsu228c"
    
    # Initialize tester
    tester = OTPTester(base_url, api_key)
    
    # Run tests
    print(f"\n🎯 Starting tests against: {base_url}")
    tester.run_full_test()


if __name__ == "__main__":
    main()
