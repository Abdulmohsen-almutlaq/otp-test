# OTP Service Testing Commands

## Replace YOUR_SERVICE_URL with your actual Render.com URL
## Replace YOUR_API_KEY with: UkFPS1EXdV8SmopIby5TvY2kCTsu228c

# 1. Health Check
curl -X GET "https://otp-test-YOUR-ID.onrender.com/health"

# 2. Register Device
curl -X POST "https://otp-test-YOUR-ID.onrender.com/api/v1/devices/register" \
  -H "Authorization: Bearer UkFPS1EXdV8SmopIby5TvY2kCTsu228c" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST-DEVICE-001",
    "user_id": "test@example.com"
  }'

# 3. Verify OTP (replace 123456 with actual OTP)
curl -X POST "https://otp-test-YOUR-ID.onrender.com/api/v1/otp/verify" \
  -H "Authorization: Bearer UkFPS1EXdV8SmopIby5TvY2kCTsu228c" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST-DEVICE-001",
    "otp": 123456
  }'

# 4. Deactivate Device
curl -X POST "https://otp-test-YOUR-ID.onrender.com/api/v1/devices/TEST-DEVICE-001/deactivate" \
  -H "Authorization: Bearer UkFPS1EXdV8SmopIby5TvY2kCTsu228c"

# 5. Test without API key (should fail with 401)
curl -X GET "https://otp-test-YOUR-ID.onrender.com/api/v1/devices/register" \
  -H "Content-Type: application/json"
