# PCB Labeling Workflow System

A modular, production-ready system for labeling PCB defect images using Label Studio. This system simulates a two-Raspberry-Pi architecture (Pi3 as sender, Pi5 as receiver) on Mac/local development environments using Docker.

## 🎯 Overview

This system automates the workflow for collecting, storing, and labeling PCB images for computer vision defect classification:

```
[Image Source] → [PI3 Sender] → [PI5 Receiver] → [Label Studio] → [Labeled Dataset]
```

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Docker Network                             │
│                                                                     │
│  ┌──────────────┐         ┌──────────────┐      ┌───────────────┐ │
│  │  PI3 Sender  │────────▶│ PI5 Receiver │◀────▶│ Label Studio  │ │
│  │              │  HTTP   │              │ SDK  │               │ │
│  │  - Watcher   │         │  - FastAPI   │      │  - UI (8080)  │ │
│  │  - Camera    │         │  - Storage   │      │  - Projects   │ │
│  │  - Uploader  │         │  - Database  │      │  - Tasks      │ │
│  └──────────────┘         │  - LS Sync   │      └───────────────┘ │
│                           └──────────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   Persistent     │
                    │   Volumes        │
                    │  - Images        │
                    │  - Database      │
                    │  - Annotations   │
                    └─────────────────┘
```

## 🏗️ Architecture Design

### Modular Structure

```
backend/
├── pi3_sender/              # Server 1 - Image source and forwarder
│   ├── config/             # Configuration management
│   ├── services/           # Business logic (camera, sender, watcher)
│   ├── utils/              # Logging and helpers
│   └── main.py             # Entry point
│
├── pi5_receiver/           # Server 2 - Receiver and Label Studio integration
│   ├── config/             # Configuration management
│   ├── api/                # FastAPI routes and models
│   ├── services/           # Business logic (storage, LS, watcher)
│   ├── database/           # Data layer (SQLite)
│   ├── utils/              # Logging and helpers
│   └── main.py             # Entry point
│
├── label_studio_init/      # Label Studio project setup
│   └── init_project.py     # Initialization script
│
└── docker-compose.yml      # Service orchestration
```

### Design Principles

1. **Separation of Concerns**: Configuration, API, services, and data layers are separated
2. **Dependency Injection**: Services receive dependencies through constructors
3. **Repository Pattern**: Database access abstracted through repository layer
4. **12-Factor App**: Configuration via environment variables
5. **Modular Services**: Each service has a single, well-defined responsibility
6. **Error Handling**: Comprehensive error handling with retries and logging

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (for Mac)
- **Docker Compose** v2.0+
- At least **4GB RAM** available for containers
- **10GB disk space** for images and data

### 1. Initial Setup

```bash
# Clone the repository
cd backend

# Copy environment template
cp .env.example .env

# Create required directories
mkdir -p data/watch sample_images

# Build services
docker-compose build
```

### 2. Start the System

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

Services will be available at:
- **Label Studio UI**: http://localhost:8080
- **PI5 Receiver API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 3. Configure Label Studio

**First-time setup:**

1. Open http://localhost:8080
2. Create an account (email: `admin@example.com`, password: choose your own)
3. Go to **Account & Settings** → **Access Token**
4. Copy your API token
5. Update `.env` file:
   ```bash
   LABEL_STUDIO_API_KEY=your_token_here
   ```
6. Restart services:
   ```bash
   docker-compose restart pi5-receiver
   ```

**Initialize Label Studio Project:**

```bash
# Run initialization script (one-time)
docker-compose --profile init up label-studio-init

# Or manually run:
docker-compose run --rm label-studio-init
```

### 4. Test the Workflow

**Option A: Manual Image Upload**

```bash
# Copy a test image to the watch directory
cp /path/to/your/pcb_image.jpg data/watch/

# PI3 Sender will automatically detect and send it
# Check logs: docker-compose logs -f pi3-sender
```

**Option B: Using Sample Images**

```bash
# Add sample images to the sample_images directory
# These will be used when no camera is available
```

**Option C: Using API**

```bash
# Upload directly via API
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@pcb_image.jpg"
```

### 5. Label Images

1. Open Label Studio UI: http://localhost:8080
2. Open "PCB Defect Classification" project
3. Click on a task to start labeling
4. Use brush tool to mark defects
5. Select defect type (Solder Bridge, Cold Joint, etc.)
6. Choose overall quality (Pass/Fail/Needs Review)
7. Click "Submit" when done

### 6. View Results

```bash
# Check database for processed images
curl http://localhost:8000/api/v1/stats

# View specific image status
curl http://localhost:8000/api/v1/images/{sha256}

# List all images
curl http://localhost:8000/api/v1/images
```

## 📊 Data Flow

### 1. Image Arrival (PI3 Sender)

```
New image in watch directory
    ↓
Watcher detects image
    ↓
Send HTTP POST to PI5 Receiver
    ↓
Retry logic (3 attempts with exponential backoff)
    ↓
Success: Mark as processed
```

### 2. Image Storage (PI5 Receiver)

```
Receive HTTP POST
    ↓
Calculate SHA256 hash
    ↓
Check for duplicates
    ↓
Store in content-addressed path
    ↓
Create database record (status: RECEIVED)
    ↓
Trigger Label Studio sync
```

### 3. Label Studio Integration

```
New image in database
    ↓
Create Label Studio task
    ↓
Update status: SENT_TO_LABELSTUDIO
    ↓
User labels in UI
    ↓
Watcher polls for completion
    ↓
Export annotations
    ↓
Move to labeled directory
    ↓
Update status: LABELED
```

## 🗄️ Database Schema

### Images Table

| Column              | Type      | Description                          |
|---------------------|-----------|--------------------------------------|
| id                  | INTEGER   | Primary key                          |
| filename            | TEXT      | Original filename                    |
| sha256              | TEXT      | SHA256 hash (unique)                 |
| file_path           | TEXT      | Full path to image                   |
| status              | TEXT      | Processing status (enum)             |
| received_at         | TIMESTAMP | When image was received              |
| sent_to_ls_at       | TIMESTAMP | When sent to Label Studio            |
| labeled_at          | TIMESTAMP | When labeling completed              |
| labelstudio_task_id | INTEGER   | Label Studio task ID                 |
| error_message       | TEXT      | Error message if failed              |

### Status Values

- `received`: Image received and stored
- `sent_to_labelstudio`: Sent to Label Studio for labeling
- `labeled`: Labeling completed and exported
- `error`: Error occurred during processing

## 🛠️ Configuration

### Environment Variables

#### PI3 Sender

| Variable         | Default                                 | Description                      |
|------------------|-----------------------------------------|----------------------------------|
| USE_CAMERA       | false                                   | Use real camera vs sample images |
| CAMERA_INDEX     | 0                                       | Camera device index              |
| WATCH_DIR        | /data/watch                             | Directory to monitor             |
| WATCH_INTERVAL   | 2                                       | Polling interval (seconds)       |
| UPLOAD_URL       | http://pi5-receiver:8000/api/v1/upload  | Upload endpoint                  |
| RETRY_ATTEMPTS   | 3                                       | Number of upload retries         |
| LOG_LEVEL        | INFO                                    | Logging level                    |

#### PI5 Receiver

| Variable                    | Default                     | Description                        |
|-----------------------------|-----------------------------|------------------------------------|
| HOST                        | 0.0.0.0                     | Server host                        |
| PORT                        | 8000                        | Server port                        |
| DATA_ROOT                   | /data                       | Root data directory                |
| LABEL_STUDIO_URL            | http://label-studio:8080    | Label Studio URL                   |
| LABEL_STUDIO_API_KEY        | (required)                  | Label Studio API key               |
| LABEL_STUDIO_PROJECT_ID     | (auto-created)              | Project ID                         |
| LABEL_STUDIO_PROJECT_NAME   | PCB Defect Classification   | Project name                       |
| WATCHER_ENABLED             | true                        | Enable completion watcher          |
| WATCHER_POLL_INTERVAL       | 5                           | Polling interval (seconds)         |
| MAX_IMAGE_SIZE_MB           | 10                          | Maximum upload size                |
| LOG_LEVEL                   | INFO                        | Logging level                      |

## 📁 Storage Structure

```
backend/
└── data/
    ├── watch/                    # Incoming images (PI3 watches this)
    ├── captured/                 # Camera captures (if using camera)
    ├── images/
    │   ├── unlabeled/           # Unlabeled images (content-addressed)
    │   │   └── ab/cd/[hash]/    # SHA256 sharding
    │   └── labeled/             # Labeled images
    │       ├── annotations/     # JSON annotation files
    │       └── ab/cd/[hash]/    # Labeled images
    ├── pcb_labeling.db          # SQLite database
    └── labelstudio/             # Label Studio data
```

### Content-Addressed Storage

Images are stored using SHA256 hashing:
- **Path format**: `unlabeled/ab/cd/abcdef.../filename.jpg`
- **Benefits**:
  - Automatic deduplication
  - Fast lookups
  - No directory size limitations
  - Content integrity verification

## 🔌 API Endpoints

### POST /api/v1/upload

Upload an image to the system.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@image.jpg"
```

**Response:**
```json
{
  "status": "stored",
  "sha256": "abcdef...",
  "filename": "image.jpg",
  "file_path": "/data/images/unlabeled/ab/cd/.../image.jpg",
  "is_duplicate": false,
  "labelstudio_task_id": 123
}
```

### GET /api/v1/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": true,
  "labelstudio": true,
  "storage": true,
  "timestamp": "2025-01-15T10:30:00"
}
```

### GET /api/v1/images/{sha256}

Get status of a specific image.

### GET /api/v1/images?status={status}&limit={limit}

List images with optional filtering.

### GET /api/v1/stats

Get system statistics.

**Response:**
```json
{
  "total_images": 150,
  "unlabeled": 10,
  "sent_to_labelstudio": 20,
  "labeled": 115,
  "errors": 5
}
```

## 🐛 Troubleshooting

### Label Studio Not Starting

```bash
# Check logs
docker-compose logs label-studio

# Restart service
docker-compose restart label-studio

# Wait for health check
docker-compose ps
```

### PI5 Receiver Can't Connect to Label Studio

```bash
# Verify Label Studio is running
curl http://localhost:8080/health

# Check API key in .env
cat .env | grep LABEL_STUDIO_API_KEY

# Restart receiver
docker-compose restart pi5-receiver
```

### Images Not Appearing in Label Studio

1. Check if image was received:
   ```bash
   curl http://localhost:8000/api/v1/stats
   ```

2. Verify Label Studio project exists:
   - Open http://localhost:8080
   - Check project list

3. Check receiver logs:
   ```bash
   docker-compose logs pi5-receiver | grep "Label Studio"
   ```

4. Manually sync storage:
   - Log into Label Studio UI
   - Go to Project Settings → Cloud Storage
   - Click "Sync Storage"

### PI3 Sender Not Uploading

```bash
# Check logs
docker-compose logs pi3-sender

# Verify receiver is reachable
docker-compose exec pi3-sender ping pi5-receiver

# Test upload manually
docker-compose exec pi3-sender curl http://pi5-receiver:8000/api/v1/health
```

## 🔧 Development

### Running Locally (without Docker)

**PI5 Receiver:**

```bash
cd pi5_receiver
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATA_ROOT=./local_data
export LABEL_STUDIO_URL=http://localhost:8080
export LABEL_STUDIO_API_KEY=your_key

python main.py
```

**PI3 Sender:**

```bash
cd pi3_sender
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export UPLOAD_URL=http://localhost:8000/api/v1/upload
python main.py
```

### Hot Reload for Development

Uncomment volume mounts in `docker-compose.yml`:

```yaml
volumes:
  - ./pi5_receiver:/app  # Code hot reload
```

### Running Tests

```bash
# TODO: Add pytest tests
pytest tests/
```

## 📦 Deployment to Raspberry Pi

### PI3 Setup

```bash
# On Raspberry Pi 3
scp -r pi3_sender/ pi@raspberrypi3:/home/pi/
ssh pi@raspberrypi3

cd /home/pi/pi3_sender
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
export UPLOAD_URL=http://192.168.1.100:8000/api/v1/upload
export USE_CAMERA=true

# Run
python main.py
```

### PI5 Setup

```bash
# On Raspberry Pi 5
scp -r pi5_receiver/ pi@raspberrypi5:/home/pi/
scp docker-compose.yml pi@raspberrypi5:/home/pi/

ssh pi@raspberrypi5
cd /home/pi

# Start Label Studio + Receiver
docker-compose up -d label-studio pi5-receiver
```

## 📝 Best Practices

### For Production

1. **Security**:
   - Change default Label Studio credentials
   - Use strong API keys
   - Enable HTTPS/TLS
   - Restrict network access

2. **Backup**:
   - Regularly backup `data/` directory
   - Export database periodically
   - Version control annotations

3. **Monitoring**:
   - Monitor disk space
   - Track error rates
   - Set up alerts for failures

4. **Performance**:
   - Adjust polling intervals based on load
   - Consider PostgreSQL for high volume
   - Optimize image compression

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Follow PEP 8 style guide
2. Add type hints
3. Write docstrings
4. Include unit tests
5. Update documentation

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **Label Studio**: Open-source annotation platform
- **FastAPI**: Modern web framework
- **Python**: Programming language

---

**Need Help?** Open an issue on GitHub or contact the maintainer.
