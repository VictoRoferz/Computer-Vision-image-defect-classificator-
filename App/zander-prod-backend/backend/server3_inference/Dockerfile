# Dockerfile for Server 3 (ML Inference Service)
# YOLOv8-based PCB defect detection

FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies for OpenCV and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create models directory
RUN mkdir -p /app/models

ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=models/yolov8n.pt
ENV CONFIDENCE_THRESHOLD=0.25
ENV LOG_LEVEL=INFO

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8003/api/v1/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
