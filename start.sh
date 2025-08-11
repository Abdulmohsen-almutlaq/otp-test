#!/bin/bash
# Simple startup script for Render.com

echo "Starting OTP Service..."

# Install dependencies
pip install -r requirements.txt

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
