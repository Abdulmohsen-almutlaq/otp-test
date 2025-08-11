# Minimal Dockerfile for Render.com
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements_simple.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_simple.txt

# Copy application
COPY simple_app.py .

# Expose port
EXPOSE $PORT

# Run the application
CMD uvicorn simple_app:app --host 0.0.0.0 --port $PORT
