# Dockerfile for Server 2 (Label Studio Service - Raspberry Pi 5)
# Optimized for ARM architecture and efficient operation

FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies (minimal set + git for SDK installation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
# Upgrade pip first to ensure we get the latest packages
RUN pip install --upgrade pip
# Install dependencies with no cache and upgrade flag
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application code
COPY . .

# Create directories for data storage
RUN mkdir -p /data/unlabeled /data/labeled /data/__temp__

# Environment variables (can be overridden in docker-compose)
ENV PYTHONUNBUFFERED=1
ENV DATA_ROOT=/data
ENV UNLABELED_DIR=/data/unlabeled
ENV LABELED_DIR=/data/labeled
ENV LABELSTUDIO_URL=http://labelstudio:8080
ENV LOG_LEVEL=INFO

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/api/v1/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
