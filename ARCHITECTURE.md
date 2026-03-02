# Code & Workflow Overview

## Project Summary

This repository implements a **PCB (Printed Circuit Board) Defect Detection and Classification System** — a distributed data collection and annotation platform built on two Raspberry Pi microservices. It captures images of PCB solder joints via camera, stores them with content-addressed deduplication, and integrates with [Label Studio](https://labelstud.io/) for human annotation of defect types.

---

## Architecture

```
┌──────────────────────────┐         HTTP POST          ┌──────────────────────────────┐
│   Raspberry Pi 3         │  ───────────────────────►   │   Raspberry Pi 5             │
│   (Server 1 - Camera)    │    multipart/form-data      │   (Server 2 - Label Studio)  │
│                          │                             │                              │
│  ┌────────────────────┐  │                             │  ┌────────────────────────┐  │
│  │  FastAPI :8001     │  │                             │  │  FastAPI :8002         │  │
│  │  - /api/v1/capture │  │                             │  │  - /api/v1/upload      │  │
│  │  - /api/v1/status  │  │                             │  │  - /api/v1/images/*    │  │
│  │  - /api/v1/health  │  │                             │  │  - /api/v1/stats       │  │
│  └────────────────────┘  │                             │  │  - /api/v1/webhook/*   │  │
│                          │                             │  └────────────────────────┘  │
│  ┌────────────────────┐  │                             │                              │
│  │  Camera Service    │  │                             │  ┌────────────────────────┐  │
│  │  (OpenCV)          │  │                             │  │  Label Studio :8080    │  │
│  └────────────────────┘  │                             │  │  (annotation UI)       │  │
│                          │                             │  └────────────────────────┘  │
└──────────────────────────┘                             └──────────────────────────────┘
```

Both services are containerized with Docker and orchestrated via Docker Compose.

---

## Directory Structure

```
App/zander-prod-backend/backend/
├── docker-compose.pi3.yml          # Compose for Raspberry Pi 3 (camera)
├── docker-compose.pi5.yml          # Compose for Raspberry Pi 5 (labeling)
│
├── server1_camera/                 # Camera microservice
│   ├── main.py                     # FastAPI app entry point
│   ├── Dockerfile                  # Python 3.11-slim + OpenCV deps
│   ├── requirements.txt            # fastapi, uvicorn, opencv, requests
│   ├── api/
│   │   └── routes.py               # REST endpoints (capture, status, health)
│   ├── config/
│   │   └── settings.py             # Pydantic settings (camera, upload, logging)
│   ├── services/
│   │   ├── camera_service.py       # OpenCV image capture logic
│   │   └── upload_service.py       # HTTP upload with retry/backoff
│   └── utils/
│       └── logger.py               # Structured logging utility
│
└── server2_labelstudio/            # Label Studio integration microservice
    ├── main.py                     # FastAPI app entry point
    ├── Dockerfile                  # Python 3.11-slim
    ├── requirements.txt            # fastapi, uvicorn, label-studio-sdk
    ├── api/
    │   ├── routes.py               # REST endpoints (upload, images, stats)
    │   └── webhooks.py             # Label Studio webhook handlers
    ├── config/
    │   └── settings.py             # Pydantic settings (storage paths, LS config)
    ├── models/
    │   └── schemas.py              # Pydantic request/response schemas
    ├── services/
    │   ├── labelstudio_service.py  # Label Studio SDK integration
    │   └── storage_service.py      # Content-addressed file storage
    └── utils/
        └── logger.py               # Structured logging utility
```

---

## End-to-End Workflow

### Stage 1: Image Capture (Server 1)

**File:** `server1_camera/services/camera_service.py`

- A Raspberry Pi 3 camera (or USB camera at `/dev/video0`) captures a JPEG image using OpenCV.
- Resolution defaults to 1920×1080 (configurable via env vars).
- A fallback `sample.jpg` is used when no hardware camera is available (for testing).
- Captured images are saved temporarily to `/tmp/camera_captures/`.

**Trigger:** `POST /api/v1/capture` (defined in `server1_camera/api/routes.py`)

### Stage 2: Image Upload (Server 1 → Server 2)

**File:** `server1_camera/services/upload_service.py`

- The captured image is uploaded to Server 2 via HTTP `POST /api/v1/upload` as `multipart/form-data`.
- Built-in resilience: exponential backoff retry logic (3 attempts, starting at 2s delay).
- 30-second timeout per attempt.
- Local temporary file is cleaned up after successful upload.

### Stage 3: Content-Addressed Storage (Server 2)

**File:** `server2_labelstudio/services/storage_service.py`

- On receipt, the image's **SHA256 hash** is calculated (using memory-efficient chunked reading).
- If the hash already exists, the image is deduplicated (not stored again).
- Otherwise, the image is stored at a content-addressed path:
  ```
  /data/unlabeled/{hash[0:2]}/{hash[2:4]}/{full_hash}/{filename}
  ```
- File extension validation restricts uploads to `jpg`, `jpeg`, `png`, `bmp`.

### Stage 4: Label Studio Task Creation (Server 2)

**File:** `server2_labelstudio/services/labelstudio_service.py`

- A Label Studio task is automatically created containing:
  - The image URL (served via Label Studio's local file storage)
  - Metadata: SHA256 hash, original filename, upload timestamp
- The annotation interface (XML config) provides:
  - **Brush labels** for marking defect regions on the image
  - **Quality assessment** radio buttons (Pass / Fail / Needs Review)
  - **Notes** text field

### Stage 5: Human Annotation (Label Studio UI)

- Annotators access Label Studio at `http://<pi5-ip>:8080`.
- They view PCB images and mark defect regions using brush tools for these categories:

| Defect Type          | Color     |
|----------------------|-----------|
| Good Joint           | Green     |
| Cold Joint           | Blue      |
| Insufficient Solder  | Yellow    |
| Excess Solder        | Orange    |
| Bridging             | Red       |
| Missing Component    | Purple    |
| Tombstoning          | Pink      |
| Lifted Pad           | Dark Red  |
| Other Defect         | Gray      |

- They select an overall quality rating and optionally add notes.
- On submission, Label Studio fires a webhook.

### Stage 6: Webhook Processing (Server 2)

**File:** `server2_labelstudio/api/webhooks.py`

- Label Studio sends a `POST /api/v1/webhook/annotation-created` callback.
- Server 2 processes the webhook:
  1. Extracts annotation data and task metadata (SHA256, filename).
  2. Copies the image from `unlabeled/` to `labeled/` directory.
  3. Saves the annotation as a JSON file alongside the labeled image:
     ```
     /data/labeled/{hash8}_{filename}
     /data/labeled/{hash8}_{basename}.json
     ```

### Stage 7: Dataset Monitoring

**File:** `server2_labelstudio/api/routes.py`

Several endpoints provide visibility into the dataset:

| Endpoint                      | Purpose                                    |
|-------------------------------|--------------------------------------------|
| `GET /api/v1/images/unlabeled`| List unlabeled images (with pagination)    |
| `GET /api/v1/images/labeled`  | List labeled images with annotation status |
| `GET /api/v1/stats`           | Storage statistics (counts, sizes in MB)   |
| `GET /api/v1/labelstudio/stats`| Label Studio project stats               |

---

## Deployment

### Raspberry Pi 3 (Camera Service)

```bash
docker compose -f docker-compose.pi3.yml up --build
```

- Runs `server1_camera` on port **8001**.
- Requires privileged mode for camera/GPIO access.
- Mounts `/dev/video0` for camera input.

### Raspberry Pi 5 (Label Studio Service)

```bash
docker compose -f docker-compose.pi5.yml up --build
```

- Runs `server2_labelstudio` on port **8002**.
- Runs Label Studio on port **8080**.
- Persistent storage via Docker volumes for `/data` and Label Studio data.
- Default Label Studio credentials: `admin@example.com` / `admin123`.

---

## Key Environment Variables

### Server 1

| Variable          | Description                    | Default             |
|-------------------|--------------------------------|---------------------|
| `USE_CAMERA`      | Enable hardware camera         | `true`              |
| `CAMERA_INDEX`    | Camera device index            | `0`                 |
| `CAMERA_WIDTH`    | Capture width                  | `1920`              |
| `CAMERA_HEIGHT`   | Capture height                 | `1080`              |
| `SERVER2_URL`     | Server 2 base URL              | `http://server2:8002`|
| `UPLOAD_TIMEOUT`  | Upload timeout (seconds)       | `30`                |
| `UPLOAD_RETRIES`  | Max retry attempts             | `3`                 |
| `LOG_LEVEL`       | Logging level                  | `INFO`              |

### Server 2

| Variable                         | Description                    | Default                    |
|----------------------------------|--------------------------------|----------------------------|
| `DATA_ROOT`                      | Root storage path              | `/data`                    |
| `LABELSTUDIO_URL`                | Label Studio service URL       | `http://labelstudio:8080`  |
| `LABELSTUDIO_API_KEY`            | Label Studio API key (required)| —                          |
| `LABELSTUDIO_PROJECT_NAME`       | Project name                   | `PCB Defect Classification`|
| `LABELSTUDIO_AUTO_CREATE_PROJECT`| Auto-create project            | `true`                     |
| `WEBHOOK_ENABLED`                | Enable webhook handling        | `true`                     |
| `MAX_UPLOAD_SIZE_MB`             | Max upload file size           | `50`                       |
| `LOG_LEVEL`                      | Logging level                  | `INFO`                     |

---

## Design Decisions

- **Content-addressed storage**: SHA256 hashing prevents duplicate images from consuming disk space — critical on resource-constrained Raspberry Pis.
- **Microservice separation**: Camera capture (Pi 3) is decoupled from storage/annotation (Pi 5), allowing independent scaling and hardware-appropriate resource allocation.
- **Exponential backoff retries**: Network communication between Pis uses retry logic with increasing delays to handle transient failures gracefully.
- **Label Studio integration**: Leverages an established open-source annotation platform rather than building a custom UI, providing a full-featured brush labeling tool for defect marking.
- **Webhook-driven pipeline**: Annotation completion triggers automatic file organization, keeping the labeled dataset current without polling.

---

## What's Not Yet Included

This repository focuses on **data collection and annotation infrastructure**. The following ML pipeline stages are not yet present:

- Model architecture definition (e.g., CNN for defect classification)
- Data preprocessing and augmentation pipelines
- Training loop and optimization
- Evaluation metrics (accuracy, precision, recall, confusion matrix)
- Inference/prediction service
- Model deployment and serving
