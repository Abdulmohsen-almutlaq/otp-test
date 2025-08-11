"""
Simple OTP Generator for Testing (No external dependencies)
Use this to generate OTPs for manual testing
"""

import hmac
import hashlib
import struct
import time
import base64

def generate_otp_from_key(derived_key_b64: str, digits: int = 6, interval: int = 30) -> int:
    """Generate OTP from base64 derived key"""
    try:
        derived_key = base64.b64decode(derived_key_b64)
        time_step = int(time.time() // interval)
        msg = struct.pack(">Q", time_step)
        hmac_hash = hmac.new(derived_key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        truncated_hash = hmac_hash[offset:offset + 4]
        code_int = struct.unpack(">I", truncated_hash)[0] & 0x7FFFFFFF
        return code_int % (10 ** digits)
    except Exception as e:
        print(f"Error generating OTP: {e}")
        return None

def main():
    print("🔢 OTP Generator for Testing")
    print("=" * 40)
    
    print("\n📝 TESTING INSTRUCTIONS:")
    print("1. Deploy your service to Render.com")
    print("2. Register a device using curl or HTTP client")
    print("3. Copy the derived_key from registration response")
    print("4. Use this script to generate current OTP")
    print("5. Test verification with the generated OTP")
    
    print("\n🔑 Your API Key: UkFPS1EXdV8SmopIby5TvY2kCTsu228c")
    print("🌐 Service URL: https://otp-test-YOUR-ID.onrender.com")
    
    print("\n" + "=" * 40)
    
    # Interactive OTP generation
    while True:
        print("\nOptions:")
        print("1. Generate OTP from derived key")
        print("2. Show test curl commands")
        print("3. Exit")
        
        choice = input("\nChoose option (1-3): ").strip()
        
        if choice == "1":
            derived_key = input("\nEnter derived key (base64): ").strip()
            if derived_key:
                otp = generate_otp_from_key(derived_key)
                if otp is not None:
                    print(f"\n🔢 Current OTP: {otp:06d}")
                    print(f"⏰ Valid for next {30 - (int(time.time()) % 30)} seconds")
                else:
                    print("❌ Failed to generate OTP")
            else:
                print("❌ Invalid derived key")
        
        elif choice == "2":
            print("\n📋 CURL TEST COMMANDS:")
            print("Replace YOUR-SERVICE-URL with your actual Render URL")
            print("\n1. Health Check:")
            print("curl https://YOUR-SERVICE-URL.onrender.com/health")
            
            print("\n2. Register Device:")
            print('curl -X POST "https://YOUR-SERVICE-URL.onrender.com/api/v1/devices/register" \\')
            print('  -H "Authorization: Bearer UkFPS1EXdV8SmopIby5TvY2kCTsu228c" \\')
            print('  -H "Content-Type: application/json" \\')
            print('  -d \'{"device_id": "TEST-001", "user_id": "test@example.com"}\'')
            
            print("\n3. Verify OTP (replace 123456 with actual OTP):")
            print('curl -X POST "https://YOUR-SERVICE-URL.onrender.com/api/v1/otp/verify" \\')
            print('  -H "Authorization: Bearer UkFPS1EXdV8SmopIby5TvY2kCTsu228c" \\')
            print('  -H "Content-Type: application/json" \\')
            print('  -d \'{"device_id": "TEST-001", "otp": 123456}\'')
        
        elif choice == "3":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
