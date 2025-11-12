# Dockerfile for PI5 Receiver Service
# Optimized for Raspberry Pi 5 (ARM64) but works on any platform

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal for efficiency)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config/ ./config/
COPY database/ ./database/
COPY services/ ./services/
COPY api/ ./api/
COPY utils/ ./utils/
COPY main.py .

# Create data directories
RUN mkdir -p /data/images/unlabeled /data/images/labeled

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_ROOT=/data
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health', timeout=5)" || exit 1

# Run the application
CMD ["python", "main.py"]
