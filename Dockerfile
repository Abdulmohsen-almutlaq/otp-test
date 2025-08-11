# Simple single-stage Dockerfile for Render.com
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY migrations/ ./migrations/

# Expose port
EXPOSE $PORT

# Start application
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
