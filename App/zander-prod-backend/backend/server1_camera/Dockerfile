# Dockerfile for Server 1 (Camera Service)
# Supports laptop webcam and sample-image fallback

FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/camera_captures

ENV PYTHONUNBUFFERED=1
ENV USE_CAMERA=false
ENV CAMERA_INDEX=0
ENV SERVER2_URL=http://server2:8002
ENV INFERENCE_URL=http://pcb-inference:8003
ENV TEMP_DIR=/tmp/camera_captures
ENV LOG_LEVEL=INFO

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/api/v1/health', timeout=5)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
