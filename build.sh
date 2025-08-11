#!/bin/bash

# Render.com deployment script
# This script is executed during the build phase

echo "🚀 Starting deployment for Enterprise OTP Service..."

# Install Python dependencies
echo "📦 Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# Run database migrations (if using Alembic)
echo "🗄️ Running database migrations..."
# alembic upgrade head

# Create necessary directories
mkdir -p logs

echo "✅ Build completed successfully!"
echo "🌐 Service will be available at: https://your-service.onrender.com"
echo "📚 API docs: https://your-service.onrender.com/docs (if DEBUG=true)"
echo "❤️ Health check: https://your-service.onrender.com/health"
