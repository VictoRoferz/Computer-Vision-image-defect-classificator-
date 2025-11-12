# Dockerfile for PI3 Sender Service
# Optimized for Raspberry Pi 3 (ARM) but works on any platform

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV (optional, for camera support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config/ ./config/
COPY services/ ./services/
COPY utils/ ./utils/
COPY main.py .

# Create directories
RUN mkdir -p /data/watch /data/captured /app/sample_images

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV WATCH_DIR=/data/watch
ENV OUTPUT_DIR=/data/captured
ENV FALLBACK_IMAGE_DIR=/app/sample_images

# Run the application
CMD ["python", "main.py"]
