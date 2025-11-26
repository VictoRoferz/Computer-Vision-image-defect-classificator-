# PCB Defect Classification - Labeling System

A modular, production-ready system for labeling PCB (Printed Circuit Board) joint defects using computer vision. Built with FastAPI, Docker, and Label Studio, optimized for embedded systems (Raspberry Pi 3 & 5).

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Workflow](#workflow)
- [Development](#development)
- [Deployment to Raspberry Pi](#deployment-to-raspberry-pi)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## 🎯 Overview

This system enables automated PCB defect labeling for training computer vision models. It simulates a two-Raspberry-Pi setup on your Mac:

- **Server 1 (RPi3 Simulator)**: Camera capture and image upload service
- **Server 2 (RPi5 Simulator)**: Storage, Label Studio integration, and webhook handling
- **Label Studio**: Web-based annotation interface

The system automatically:
1. Captures images from a camera (or uses test images)
2. Uploads to Server 2 for storage
3. Creates Label Studio tasks
4. Displays images in the UI for labeling
5. Saves labeled images and annotations via webhooks

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          YOUR MAC / RASPBERRY PIs                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────┐  ┌─────────────────────────┐  │
│  │  SERVER 1 (Port 8001)       │  │  SERVER 2 (Port 8002)    │  │
│  │  Raspberry Pi 3 Simulator   │  │  Raspberry Pi 5 Simulator│  │
│  ├─────────────────────────────┤  ├─────────────────────────┤  │
│  │ ✓ Camera Service (OpenCV)   │  │ ✓ Storage Service       │  │
│  │ ✓ FastAPI REST API          │──▶│ ✓ Label Studio API     │  │
│  │ ✓ Auto-capture & Upload     │  │ ✓ Webhook Handler       │  │
│  │ ✓ Retry Logic               │  │ ✓ Content-Addressed DB  │  │
│  └─────────────────────────────┘  └───────┬─────────────────┘  │
│                                             │                    │
│                                     ┌───────▼─────────────────┐  │
│                                     │ Label Studio (Port 8080)│  │
│                                     │ Docker Container        │  │
│                                     │ UI: localhost:8080      │  │
│                                     └─────────────────────────┘  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │             DATA STORAGE (Server 2)                     │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  /data/unlabeled/  →  Raw captured images              │    │
│  │  /data/labeled/    →  Labeled images + JSON annotations│    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### **Server 1: Camera Service**
- **Technology**: FastAPI + OpenCV
- **Port**: 8001
- **Responsibilities**:
  - Capture images from camera (or use fallback)
  - Upload to Server 2 with retry logic (exponential backoff)
  - Cleanup local temporary files
- **Optimizations**: Headless OpenCV, minimal dependencies

#### **Server 2: Label Studio Service**
- **Technology**: FastAPI + Label Studio SDK
- **Port**: 8002
- **Responsibilities**:
  - Receive and store images (content-addressed with SHA256)
  - Manage two databases: unlabeled and labeled
  - Auto-create Label Studio tasks
  - Handle webhooks for annotation completion
  - Save labeled images + annotations
- **Optimizations**: Content deduplication, efficient file storage

#### **Label Studio**
- **Technology**: Official Label Studio Docker image
- **Port**: 8080
- **Features**:
  - Brush tool for pixel-level defect marking
  - Multi-class labeling (9 defect types)
  - Quality classification (Pass/Fail)
  - Notes/comments support
  - Webhook integration

---

## ✨ Features

### Modular Architecture
- **Separation of Concerns**: Each service has a single responsibility
- **Service Independence**: Services can be deployed/scaled separately
- **Clean Code**: Type hints, docstrings, logging throughout

### Content-Addressed Storage
- **Deduplication**: SHA256-based to prevent duplicate storage
- **Organized**: Sharded directory structure (`/ab/cd/abcd.../image.jpg`)
- **Idempotent**: Safe to upload same image multiple times

### Robust Networking
- **Retry Logic**: Exponential backoff for network failures (2s, 4s, 8s)
- **Health Checks**: Docker health monitoring for all services
- **Error Handling**: Comprehensive exception handling and logging

### Automatic Workflow
- **Zero Manual Steps**: Images flow automatically through the pipeline
- **Webhook Integration**: Labeled data saved automatically
- **Task Creation**: New images appear in Label Studio instantly

### Production-Ready
- **Structured Logging**: Timestamp, level, module, message
- **Type Safety**: Pydantic models for validation
- **Docker Compose**: One-command deployment
- **Environment Config**: 12-factor app principles

### Embedded-Optimized
- **Lightweight**: Minimal Docker images (Python 3.11-slim)
- **Memory Efficient**: Headless OpenCV, no GUI dependencies
- **Low Bandwidth**: Efficient image transfer, compression

---

## 📦 Prerequisites

- **Docker Desktop** (Mac) or **Docker + Docker Compose** (RPi)
- **8GB RAM minimum** (for running all 3 services)
- **10GB free disk space** (for images and Docker volumes)
- **Optional**: USB camera or webcam (for actual capture)

### Mac Setup
```bash
# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker compose version
```

### Raspberry Pi Setup
```bash
# Install Docker (Raspberry Pi OS)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install docker-compose

# Reboot
sudo reboot
```

---

## 🚀 Quick Start

### 1. Clone and Navigate
```bash
cd backend
```

### 2. Run Setup Script
```bash
./setup.sh
```

This script:
- Checks Docker installation
- Creates `.env` file from template
- Shows next steps

### 3. Start Services
```bash
docker-compose up --build
```

Wait for all services to start (30-60 seconds). You'll see:
```
✓ server1 started
✓ server2 started
✓ labelstudio started
```

### 4. Configure Label Studio

**First time only:**

1. Open http://localhost:8080
2. Create account:
   - Email: `admin@example.com`
   - Password: `admin123`
   - Or use your own credentials
3. After login, go to **Account & Settings** → **Access Token**
4. Copy the API token
5. Edit `.env` file:
   ```bash
   LABELSTUDIO_API_KEY=your_token_here
   ```
6. Restart Server 2:
   ```bash
   docker-compose restart server2
   ```

### 5. Test the System

**Capture and upload an image:**
```bash
curl -X POST http://localhost:8001/api/v1/capture
```

**Expected response:**
```json
{
  "status": "success",
  "message": "Image captured and uploaded successfully",
  "image_name": "capture_20250113_143022_123456.jpg",
  "server2_response": {
    "status": "stored",
    "sha256": "abc123...",
    "task_id": 1
  }
}
```

### 6. Label in UI

1. Open http://localhost:8080
2. Click on **PCB Defect Classification** project
3. You'll see the new image task
4. Click **Label** to start
5. Use brush tool to mark defects:
   - Good Joint (green)
   - Cold Joint (blue)
   - Insufficient Solder (yellow)
   - Excess Solder (orange)
   - Bridging (red)
   - Missing Component (purple)
   - Tombstoning (magenta)
   - Lifted Pad (brown)
   - Other Defect (gray)
6. Select overall quality: Pass/Fail/Needs Review
7. Add notes if needed
8. Click **Submit**

The labeled image is automatically saved to `/data/labeled/` on Server 2!

---

## ⚙️ Configuration

### Environment Variables

All configuration is in `.env` file. See `.env.example` for all options.

#### Key Settings:

**Server 1 (Camera):**
```bash
SERVER1_USE_CAMERA=false       # true to use real camera
SERVER1_CAMERA_INDEX=0         # Camera device index
SERVER1_CAMERA_WIDTH=1920      # Resolution
SERVER1_CAMERA_HEIGHT=1080
SERVER1_UPLOAD_RETRIES=3       # Retry attempts
```

**Server 2 (Storage):**
```bash
SERVER2_USE_CONTENT_ADDRESSING=true  # SHA256 deduplication
MAX_UPLOAD_SIZE_MB=50               # Max file size
```

**Label Studio:**
```bash
LABELSTUDIO_API_KEY=              # REQUIRED: Get from UI
LABELSTUDIO_PROJECT_NAME=PCB Defect Classification
LABELSTUDIO_AUTO_CREATE_PROJECT=true
```

**Logging:**
```bash
LOG_LEVEL=INFO  # DEBUG for verbose logs
```

---

## 📚 API Documentation

### Server 1 (Camera Service)

**Base URL**: `http://localhost:8001`

**Interactive Docs**: http://localhost:8001/docs

#### Endpoints:

**POST /api/v1/capture**
- Capture image and upload to Server 2
- Returns: Upload status and task ID

**GET /api/v1/status**
- Get camera and connection status
- Returns: Service health information

**GET /api/v1/health**
- Simple health check
- Returns: `{"status": "healthy"}`

**POST /api/v1/test-camera**
- Test camera without uploading
- Returns: Captured image info

**POST /api/v1/test-upload**
- Test Server 2 connection
- Returns: Connection status

### Server 2 (Label Studio Service)

**Base URL**: `http://localhost:8002`

**Interactive Docs**: http://localhost:8002/docs

#### Endpoints:

**POST /api/v1/upload**
- Upload image (called by Server 1)
- Returns: Storage info and task ID

**GET /api/v1/images/unlabeled**
- List unlabeled images
- Query params: `limit`, `offset`

**GET /api/v1/images/labeled**
- List labeled images with annotations
- Query params: `limit`, `offset`

**GET /api/v1/stats**
- Get storage statistics
- Returns: Counts and sizes

**GET /api/v1/labelstudio/stats**
- Get Label Studio project stats
- Returns: Task counts, annotations

**GET /api/v1/status**
- Comprehensive service status
- Returns: Storage + Label Studio info

**GET /api/v1/health**
- Simple health check

**POST /api/v1/webhook/annotation-created**
- Label Studio webhook (automatic)
- Saves labeled images + annotations

---

## 🔄 Workflow

### Complete End-to-End Flow

```
1. USER ACTION
   ├─> POST /api/v1/capture
   │
2. SERVER 1: Camera Service
   ├─> Capture image (OpenCV)
   ├─> Save to /tmp/camera_captures/
   │
3. SERVER 1: Upload Service
   ├─> POST /api/v1/upload to Server 2
   ├─> Retry on failure (3x, exponential backoff)
   ├─> Cleanup local file
   │
4. SERVER 2: Storage Service
   ├─> Calculate SHA256 hash
   ├─> Store in /data/unlabeled/<hash>/
   ├─> Check for duplicates
   │
5. SERVER 2: Label Studio Service
   ├─> Create task via SDK
   ├─> Task appears in UI instantly
   │
6. USER: Label in UI
   ├─> Open localhost:8080
   ├─> Use brush tool to mark defects
   ├─> Select quality (Pass/Fail)
   ├─> Submit annotation
   │
7. LABEL STUDIO: Trigger Webhook
   ├─> POST /api/v1/webhook/annotation-created
   │
8. SERVER 2: Webhook Handler
   ├─> Receive annotation data
   ├─> Copy image to /data/labeled/
   ├─> Save annotation JSON
   │
9. RESULT
   └─> Two databases on Server 2:
       ├─> /data/unlabeled/ (raw images)
       └─> /data/labeled/   (images + annotations)
```

### Data Flow Diagram

```
┌─────────┐   capture   ┌──────────┐   upload   ┌──────────┐
│ Camera  │────────────▶│ Server 1 │───────────▶│ Server 2 │
└─────────┘             └──────────┘            └────┬─────┘
                                                      │
                                                      │ create_task
                                                      ▼
┌─────────┐   webhook   ┌──────────┐   UI/API  ┌──────────┐
│ Server 2│◀────────────│  Label   │◀──────────│   User   │
│(labeled)│             │  Studio  │           │ (browser)│
└─────────┘             └──────────┘           └──────────┘
```

---

## 🛠️ Development

### Project Structure

```
backend/
├── server1_camera/              # Server 1 (Camera Service)
│   ├── config/
│   │   └── settings.py         # Configuration management
│   ├── services/
│   │   ├── camera_service.py   # Camera capture logic
│   │   └── upload_service.py   # Upload to Server 2
│   ├── api/
│   │   └── routes.py           # REST API endpoints
│   ├── utils/
│   │   └── logger.py           # Logging setup
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
│
├── server2_labelstudio/         # Server 2 (Label Studio Service)
│   ├── config/
│   │   └── settings.py         # Configuration management
│   ├── services/
│   │   ├── storage_service.py  # Image storage logic
│   │   └── labelstudio_service.py  # Label Studio integration
│   ├── api/
│   │   ├── routes.py           # REST API endpoints
│   │   └── webhooks.py         # Webhook handlers
│   ├── models/
│   │   └── schemas.py          # Pydantic data models
│   ├── utils/
│   │   └── logger.py           # Logging setup
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml           # Orchestration
├── .env.example                 # Configuration template
├── setup.sh                     # Setup script
└── README.md                    # This file
```

### Adding New Features

#### Example: Add New Defect Type

1. **Update Label Studio config** in `server2_labelstudio/services/labelstudio_service.py`:
```python
LABELING_CONFIG = """
<View>
  ...
  <BrushLabels name="defects" toName="image">
    ...
    <Label value="Your New Defect" background="#HEXCOLOR"/>
  </BrushLabels>
  ...
</View>
"""
```

2. **Rebuild and restart**:
```bash
docker-compose up --build
```

3. **Recreate project** (if needed):
   - Delete old project in Label Studio UI
   - Set `LABELSTUDIO_PROJECT_ID=` in `.env`
   - Restart: `docker-compose restart server2`

### Running Tests

```bash
# Server 1 tests
cd server1_camera
pytest tests/

# Server 2 tests
cd server2_labelstudio
pytest tests/
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f server1
docker-compose logs -f server2
docker-compose logs -f labelstudio

# Last 100 lines
docker-compose logs --tail=100 server2
```

### Debugging

**Enable debug logs:**
```bash
# Edit .env
LOG_LEVEL=DEBUG

# Restart
docker-compose restart
```

**Access container:**
```bash
docker exec -it pcb-server1-camera bash
docker exec -it pcb-server2-labelstudio bash
```

**Inspect volumes:**
```bash
docker volume ls
docker volume inspect pcb_server2_data
```

---

## 🚀 Deployment to Raspberry Pi

### Prerequisites on Raspberry Pi

**Raspberry Pi 3 (Server 1):**
- Raspberry Pi OS Lite (64-bit recommended)
- USB camera or Pi Camera Module
- Docker + Docker Compose installed
- Network connectivity

**Raspberry Pi 5 (Server 2):**
- Raspberry Pi OS (with Desktop for Label Studio UI)
- Docker + Docker Compose installed
- Tablet connected via WiFi (for Label Studio UI)

### Step 1: Install Docker on Both RPis

```bash
# On both RPi3 and RPi5
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo apt-get install docker-compose

# Enable camera (RPi3 only, if using Pi Camera)
sudo raspi-config
# Interface Options -> Camera -> Enable

sudo reboot
```

### Step 2: Configure Network

**On RPi5**, get IP address:
```bash
ip addr show | grep 'inet '
# Note the IP, e.g., 192.168.1.100
```

### Step 3: Deploy to RPi3 (Server 1)

```bash
# Copy files to RPi3
scp -r backend/server1_camera pi@raspberrypi3:/home/pi/

# SSH to RPi3
ssh pi@raspberrypi3

# Edit .env
nano server1_camera/.env
```

**RPi3 .env:**
```bash
SERVER1_USE_CAMERA=true
SERVER1_CAMERA_INDEX=0        # Or 1 for USB camera
SERVER2_URL=http://192.168.1.100:8002  # RPi5 IP!
LOG_LEVEL=INFO
```

**Start Server 1:**
```bash
cd server1_camera
docker-compose up -d
```

### Step 4: Deploy to RPi5 (Server 2 + Label Studio)

```bash
# Copy files to RPi5
scp -r backend/server2_labelstudio backend/docker-compose.yml backend/.env pi@raspberrypi5:/home/pi/

# SSH to RPi5
ssh pi@raspberrypi5

cd /home/pi

# Edit .env
nano .env
```

**RPi5 .env:**
```bash
LABELSTUDIO_API_KEY=<get-from-ui>
LOG_LEVEL=INFO
```

**Start Server 2 + Label Studio:**
```bash
docker-compose up -d
```

### Step 5: Access Label Studio from Tablet

**On your tablet's browser:**
```
http://192.168.1.100:8080
```

(Replace with actual RPi5 IP)

### Step 6: Test the System

**From any device on the network:**
```bash
curl -X POST http://<rpi3-ip>:8001/api/v1/capture
```

### Production Optimizations for RPi

**1. Reduce camera resolution** (RPi3 .env):
```bash
SERVER1_CAMERA_WIDTH=1280
SERVER1_CAMERA_HEIGHT=720
```

**2. Enable log rotation** (both RPis):
```bash
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

**3. Monitor resources:**
```bash
docker stats
htop
```

**4. Autostart on boot:**
```bash
# Add to /etc/rc.local (before 'exit 0')
cd /home/pi && docker-compose up -d
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "Label Studio not initialized"

**Cause**: API key not set or invalid

**Solution**:
```bash
# Get new API key from Label Studio UI
# Update .env
LABELSTUDIO_API_KEY=your_valid_token

# Restart
docker-compose restart server2
```

#### 2. "Server 2 is not reachable"

**Cause**: Network issue or Server 2 not running

**Solution**:
```bash
# Check Server 2 status
docker-compose ps

# Check logs
docker-compose logs server2

# Test connection
curl http://localhost:8002/api/v1/health
```

#### 3. "Camera not found"

**Cause**: Camera not connected or wrong index

**Solution**:
```bash
# List cameras (Mac)
system_profiler SPCameraDataType

# Test different index
SERVER1_CAMERA_INDEX=1  # Try 0, 1, 2

# Use fallback for testing
SERVER1_USE_CAMERA=false
```

#### 4. "Port already in use"

**Cause**: Another service using 8001/8002/8080

**Solution**:
```bash
# Find process
lsof -i :8001

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8011:8001"  # Use 8011 externally
```

#### 5. "Webhook not working"

**Cause**: Webhook not configured in Label Studio

**Solution**:
1. Open Label Studio UI
2. Go to Project Settings
3. Click **Webhooks** tab
4. Add webhook:
   - URL: `http://server2:8000/api/v1/webhook/annotation-created`
   - Events: `ANNOTATION_CREATED`, `ANNOTATION_UPDATED`
5. Save and test

#### 6. "Out of disk space"

**Cause**: Too many images stored

**Solution**:
```bash
# Check volume usage
docker system df

# Clean up old images (be careful!)
docker volume prune

# Or manually delete from /data/labeled/
```

### Debug Checklist

- [ ] All containers running: `docker-compose ps`
- [ ] No errors in logs: `docker-compose logs`
- [ ] `.env` file configured correctly
- [ ] Label Studio API key set
- [ ] Network connectivity between services
- [ ] Sufficient disk space: `df -h`
- [ ] Ports not blocked by firewall

### Getting Help

**Check logs:**
```bash
docker-compose logs --tail=100 -f
```

**Restart everything:**
```bash
docker-compose down
docker-compose up --build
```

**Clean slate (deletes all data!):**
```bash
docker-compose down -v
docker system prune -a
docker-compose up --build
```

---

## 📊 Performance Tips

### For Raspberry Pi 3

- Use camera resolution ≤ 1280x720
- Set `LOG_LEVEL=WARNING` (less disk I/O)
- Disable hot reload in production
- Monitor CPU/RAM: `docker stats`

### For Raspberry Pi 5

- Can handle 1920x1080 resolution
- Enable swap if needed: `sudo dphys-swapfile setup`
- Use SSD instead of SD card for `/data`

### For Mac Development

- Allocate more resources to Docker Desktop:
  - CPU: 4+ cores
  - RAM: 8+ GB
  - Disk: 20+ GB

---

## 🔒 Security Considerations

For production deployment:

1. **Change default credentials**
2. **Use HTTPS** (reverse proxy with nginx)
3. **Restrict CORS** origins in FastAPI
4. **Set firewall rules** on Raspberry Pis
5. **Enable Label Studio authentication**
6. **Use strong API keys**
7. **Regular security updates**: `sudo apt update && sudo apt upgrade`

---

## 📝 License

This project is part of the PCB Defect Classification system. See main repository for license information.

---

## 🙏 Acknowledgments

- **FastAPI**: Modern Python web framework
- **Label Studio**: Open-source annotation platform
- **OpenCV**: Computer vision library
- **Docker**: Containerization platform

---

## 📞 Support

For issues, questions, or contributions, please see the main project repository.

---

**Built with ❤️ for PCB quality assurance**
