# Dockerfile for Label Studio Initialization
# Used to initialize Label Studio project on first run

FROM python:3.11-slim

WORKDIR /app

# Copy requirements and script
COPY requirements.txt .
COPY init_project.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run initialization script
CMD ["python", "init_project.py"]
