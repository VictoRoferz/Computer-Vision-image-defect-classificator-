# Setup Guide - PCB Labeling Workflow System

Step-by-step guide to set up and run the PCB labeling workflow system on your Mac.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [First Run](#first-run)
5. [Testing the Workflow](#testing-the-workflow)
6. [Next Steps](#next-steps)

---

## 1. Prerequisites

### Required Software

- **Docker Desktop for Mac** (v4.0+)
  - Download: https://www.docker.com/products/docker-desktop
  - Ensure Docker Desktop is running before proceeding

- **Git** (for cloning the repository)
  ```bash
  # Check if installed
  git --version
  ```

### System Requirements

- **macOS**: 10.15 (Catalina) or newer
- **RAM**: Minimum 4GB free (8GB recommended)
- **Disk**: 10GB free space
- **CPU**: Intel or Apple Silicon (M1/M2)

### Verify Docker Installation

```bash
# Check Docker is running
docker --version
docker-compose --version

# Test Docker
docker run hello-world
```

---

## 2. Installation

### Step 2.1: Navigate to Backend Directory

```bash
cd backend
```

### Step 2.2: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your preferred editor
nano .env
# or
vim .env
# or
code .env  # if you have VS Code
```

**For now, leave the API key empty** - we'll get it after Label Studio starts.

### Step 2.3: Create Required Directories

```bash
# Create data directories
mkdir -p data/watch
mkdir -p data/captured
mkdir -p data/images/unlabeled
mkdir -p data/images/labeled
mkdir -p data/labelstudio

# Create sample images directory
mkdir -p sample_images
```

### Step 2.4: Add Sample Images (Optional)

If you have sample PCB images for testing:

```bash
# Copy your sample images
cp /path/to/your/pcb_images/*.jpg sample_images/
```

Or download sample images from your dataset.

### Step 2.5: Build Docker Images

```bash
# Build all services (this may take 5-10 minutes)
docker-compose build

# Expected output: Successfully built images for:
# - pi3-sender
# - pi5-receiver
# - label-studio-init
```

---

## 3. Configuration

### Step 3.1: Start Label Studio First

```bash
# Start only Label Studio
docker-compose up -d label-studio

# Wait for Label Studio to be ready (about 30-60 seconds)
docker-compose logs -f label-studio
```

**Wait for this message**: `"Label Studio is running..."`

Press `Ctrl+C` to stop viewing logs.

### Step 3.2: Access Label Studio UI

1. Open your browser: http://localhost:8080
2. You'll see the Label Studio sign-up page

### Step 3.3: Create Label Studio Account

1. Click **Sign Up**
2. Enter your details:
   - **Email**: `admin@example.com` (or your preferred email)
   - **Password**: Choose a strong password
   - **Name**: Your name
3. Click **Create Account**

### Step 3.4: Get API Token

1. After logging in, click your profile icon (top right)
2. Go to **Account & Settings**
3. Click **Access Token** tab
4. Click **Copy Token** button
5. Keep this token safe - you'll need it next

### Step 3.5: Update Environment File

```bash
# Edit .env file
nano .env

# Add your API token (paste the token you copied)
LABEL_STUDIO_API_KEY=your_copied_token_here

# Save and exit (Ctrl+X, then Y, then Enter)
```

---

## 4. First Run

### Step 4.1: Start All Services

```bash
# Start all services
docker-compose up -d

# Check all containers are running
docker-compose ps
```

You should see all services as **healthy** (may take 30-60 seconds):
```
NAME                STATUS
label-studio        Up (healthy)
pi5-receiver        Up (healthy)
pi3-sender          Up
```

### Step 4.2: Initialize Label Studio Project

```bash
# Run the initialization script
docker-compose --profile init up label-studio-init

# Expected output:
# "Initialization Complete!"
# "Project ID: 1"
```

If initialization succeeds, you'll see a new project in Label Studio UI.

### Step 4.3: Verify Services

**Check PI5 Receiver API:**
```bash
curl http://localhost:8000/api/v1/health

# Expected output:
# {"status":"healthy","database":true,"labelstudio":true,...}
```

**Check Label Studio:**
```bash
curl http://localhost:8080/health

# Expected output: OK
```

**View Logs:**
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f pi5-receiver
docker-compose logs -f pi3-sender
docker-compose logs -f label-studio
```

---

## 5. Testing the Workflow

### Test 1: Upload via Watch Directory

This simulates a new image arriving at the PI3 Sender.

```bash
# Copy a test image to the watch directory
cp sample_images/test_image.jpg data/watch/

# Or create a dummy test image
echo "test" > data/watch/test.jpg

# Watch the logs
docker-compose logs -f pi3-sender
```

**Expected log output:**
```
pi3-sender | New image detected: test.jpg
pi3-sender | Sending image...
pi3-sender | Successfully uploaded test.jpg: Status=stored
```

### Test 2: Verify in Database

```bash
# Check statistics
curl http://localhost:8000/api/v1/stats

# Expected output:
# {"total_images":1,"unlabeled":0,"sent_to_labelstudio":1,"labeled":0,"errors":0}

# List all images
curl http://localhost:8000/api/v1/images | jq
```

### Test 3: Check Label Studio

1. Open Label Studio: http://localhost:8080
2. Click on **"PCB Defect Classification"** project
3. You should see 1 task (your uploaded image)
4. Click on the task to view the image

### Test 4: Label an Image

1. In Label Studio, click on a task
2. Select the **Brush** tool
3. Draw on defect areas
4. Select defect type from the labels:
   - Solder Bridge
   - Cold Joint
   - Missing Component
   - etc.
5. Select **Overall Quality**: Pass/Fail/Needs Review
6. (Optional) Add notes
7. Click **Submit**

### Test 5: Verify Labeled Image

After labeling, the completion watcher should detect it (wait ~5-10 seconds):

```bash
# Check statistics again
curl http://localhost:8000/api/v1/stats

# Expected output:
# {"total_images":1,"unlabeled":0,"sent_to_labelstudio":0,"labeled":1,"errors":0}

# Check labeled directory
ls -la data/images/labeled/
```

---

## 6. Next Steps

### Add More Images

**Method 1: Watch Directory**
```bash
# Copy images to watch directory
cp /path/to/pcb_images/*.jpg data/watch/

# PI3 Sender will automatically detect and upload them
```

**Method 2: Direct API Upload**
```bash
# Upload directly via API
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@/path/to/image.jpg"
```

### Monitor the System

**View real-time logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f pi5-receiver
```

**Check system health:**
```bash
# API health
curl http://localhost:8000/api/v1/health

# Statistics
curl http://localhost:8000/api/v1/stats
```

**View database:**
```bash
# Access SQLite database
docker-compose exec pi5-receiver sqlite3 /data/pcb_labeling.db

# Run queries
sqlite> SELECT * FROM images;
sqlite> .exit
```

### Stop the System

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

### Restart the System

```bash
# Start all services
docker-compose up -d

# View startup logs
docker-compose logs -f
```

---

## 🎉 Success!

You now have a fully functional PCB labeling workflow system running on your Mac!

**What you've accomplished:**
- ✅ Set up Docker environment
- ✅ Configured Label Studio
- ✅ Started PI3 Sender and PI5 Receiver
- ✅ Uploaded and labeled your first image
- ✅ Verified the complete workflow

### Recommended Next Steps

1. **Add more sample images** to `sample_images/`
2. **Create labeling guidelines** for consistent annotations
3. **Batch upload images** using the watch directory
4. **Export labeled data** from Label Studio
5. **Train your ML model** using the labeled dataset

---

## 🐛 Troubleshooting

### Issue: Label Studio won't start

**Solution:**
```bash
# Check logs
docker-compose logs label-studio

# Try restarting
docker-compose restart label-studio

# Check port availability
lsof -i :8080
```

### Issue: PI5 Receiver can't connect to Label Studio

**Solution:**
```bash
# Verify Label Studio is running
docker-compose ps label-studio

# Check API key in .env
cat .env | grep LABEL_STUDIO_API_KEY

# Restart receiver
docker-compose restart pi5-receiver
```

### Issue: Images not showing in Label Studio

**Solution:**
1. Check if image was uploaded:
   ```bash
   curl http://localhost:8000/api/v1/stats
   ```

2. Check receiver logs:
   ```bash
   docker-compose logs pi5-receiver | grep "Label Studio"
   ```

3. Manually initialize project:
   ```bash
   docker-compose --profile init up label-studio-init
   ```

### Issue: Out of disk space

**Solution:**
```bash
# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune -a

# Remove old volumes
docker volume prune
```

### Issue: Port already in use

**Solution:**
```bash
# Check what's using the port
lsof -i :8080  # Label Studio
lsof -i :8000  # PI5 Receiver

# Stop the conflicting service
# Or change port in docker-compose.yml
```

---

## 📚 Additional Resources

- [Full README](README.md) - Complete documentation
- [Label Studio Documentation](https://labelstud.io/guide/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)

---

**Need more help?** Check the [Troubleshooting](#troubleshooting) section or open an issue on GitHub.
