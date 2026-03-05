# Computer-Vision-image-defect-classificator

End-to-end AI-powered defect detection system combining hardware and software to automatically identify and classify PCB product defects using Machine Learning and Computer Vision.

## Quick Start

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running.

```bash
cd App

# Mac/Linux
./start.sh

# Windows
start.bat
```

This builds and starts all services. Open **http://localhost:3000** for the dashboard.

### First-Time Label Studio Setup

1. Open http://localhost:8080
2. Login: `admin@example.com` / `admin123`
3. Go to **Account & Settings > Access Token**
4. Copy the token into `App/.env` as `LABELSTUDIO_API_KEY=<your-token>`
5. Run `docker compose restart server2`

## Architecture

```
┌───────────────────────────────────────────────────────┐
│                  Dashboard (:3000)                     │
│            Label Mode  |  Inference Mode               │
└──────┬─────────────┬──────────────┬───────────────────┘
       │             │              │
┌──────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│ Camera :8001│ │ Storage  │ │ Inference   │
│ (Server 1)  │ │  :8002   │ │   :8003     │
│ webcam /    │ │(Server 2)│ │ YOLOv8      │
│ sample img  │ │          │ │ defect det. │
└──────┬──────┘ └────┬─────┘ └─────────────┘
       │             │
       └──────►──────┘
              │
       ┌──────▼──────┐
       │Label Studio │
       │   :8080     │
       └─────────────┘
```

| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 3000 | Web UI for both workflows |
| Camera (Server 1) | 8001 | Image capture (webcam or sample fallback) |
| Storage (Server 2) | 8002 | Content-addressed image storage + Label Studio integration |
| Inference (Server 3) | 8003 | YOLOv8 defect detection |
| Label Studio | 8080 | Annotation platform |

## Workflows

### Label Mode
1. Click **Capture Image** in the dashboard (or `POST http://localhost:8001/api/v1/capture`)
2. Image is stored in Server 2 and a Label Studio task is created
3. Open Label Studio to annotate defects with brush labels
4. Annotations are saved alongside images automatically

### Inference Mode
1. Upload a PCB image in the dashboard (drag & drop or click)
2. YOLOv8 runs defect detection and returns bounding boxes + classifications
3. Overall quality verdict: Pass / Fail / Needs Review

## Configuration

Copy `App/.env.example` to `App/.env` and edit:

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_CAMERA` | `false` | Set `true` to use laptop webcam |
| `LABELSTUDIO_API_KEY` | (empty) | Required for Label Studio integration |
| `CONFIDENCE_THRESHOLD` | `0.25` | ML detection confidence (0.0-1.0) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

See `.env.example` for all options.

## Useful Commands

```bash
cd App

docker compose up --build -d    # Build & start all services
docker compose down              # Stop all services
docker compose logs -f           # Follow all logs
docker compose logs -f inference # Follow inference logs only
docker compose down -v           # Stop & delete all data
```

## Project Structure

```
App/
├── docker-compose.yml              # Unified Docker configuration
├── .env.example                    # Environment variable template
├── start.sh / start.bat           # One-click launchers
├── dashboard/                      # Web UI
│   ├── app.py                     # FastAPI dashboard server
│   ├── templates/index.html       # Main page
│   └── static/                    # CSS + JS
└── zander-prod-backend/backend/
    ├── server1_camera/            # Camera service
    ├── server2_labelstudio/       # Storage + Label Studio service
    └── server3_inference/         # YOLOv8 inference service
```

## Defect Classes

| Class | Color |
|-------|-------|
| Good Joint | Green |
| Cold Joint | Blue |
| Insufficient Solder | Yellow |
| Excess Solder | Orange |
| Bridging | Red |
| Missing Component | Purple |
| Tombstoning | Pink |
| Lifted Pad | Dark Purple |
| Other Defect | Gray |

## Tech Stack

- **Backend:** FastAPI + Uvicorn
- **ML:** YOLOv8 (ultralytics)
- **Annotation:** Label Studio
- **Frontend:** Vanilla JS + CSS (no build step)
- **Infrastructure:** Docker Compose
- **Language:** Python 3.11
