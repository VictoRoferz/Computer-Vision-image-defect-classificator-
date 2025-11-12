# System Architecture - PCB Labeling Workflow

## Overview

This document describes the architectural design, patterns, and rationale behind the PCB labeling workflow system.

## System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Production System                          │
│                                                                     │
│  ┌──────────────┐         ┌──────────────┐      ┌───────────────┐ │
│  │ Raspberry Pi3│────────▶│ Raspberry Pi5│◀────▶│     Tablet    │ │
│  │              │  WiFi   │              │ WLAN │   (Browser)   │ │
│  │  + Camera    │         │  + Storage   │      │  Label Studio │ │
│  │              │         │  + Database  │      │      UI       │ │
│  └──────────────┘         └──────────────┘      └───────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

                               ↕ (Simulated by)

┌─────────────────────────────────────────────────────────────────────┐
│                      Development System (Mac)                       │
│                                                                     │
│  ┌──────────────┐         ┌──────────────┐      ┌───────────────┐ │
│  │ pi3-sender   │────────▶│ pi5-receiver │◀────▶│ label-studio  │ │
│  │  container   │  Docker │  container   │ SDK  │   container   │ │
│  │              │ Network │              │      │               │ │
│  └──────────────┘         └──────────────┘      └───────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Architectural Principles

### 1. Separation of Concerns

Each module has a **single responsibility**:

- **Config**: Environment-based configuration
- **API**: HTTP interface and request/response handling
- **Services**: Business logic
- **Database**: Data persistence
- **Utils**: Cross-cutting concerns (logging, helpers)

### 2. Layered Architecture

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │  ← HTTP Interface
├─────────────────────────────────────┤
│       Service Layer (Business)      │  ← Business Logic
├─────────────────────────────────────┤
│      Data Layer (Repository)        │  ← Data Access
├─────────────────────────────────────┤
│        Storage (File System)        │  ← Persistence
└─────────────────────────────────────┘
```

**Benefits:**
- **Testability**: Each layer can be tested independently
- **Maintainability**: Changes in one layer don't affect others
- **Flexibility**: Easy to swap implementations (e.g., SQLite → PostgreSQL)

### 3. Dependency Injection

Services receive dependencies through constructors:

```python
class StorageService:
    def __init__(self, settings: Settings, db_repo: DatabaseRepository):
        self.settings = settings
        self.db_repo = db_repo
```

**Benefits:**
- **Loose coupling**: Services don't create their dependencies
- **Testability**: Easy to inject mocks for testing
- **Flexibility**: Easy to change implementations

### 4. Repository Pattern

Database access is abstracted through a repository:

```python
class DatabaseRepository:
    def get_by_sha256(self, sha256: str) -> Optional[ImageRecord]:
        # Database-specific implementation hidden
        pass
```

**Benefits:**
- **Abstraction**: Business logic doesn't know about SQL
- **Testability**: Easy to mock the repository
- **Portability**: Easy to switch databases

### 5. 12-Factor App

All configuration via environment variables:

```python
class Settings:
    LABEL_STUDIO_URL: str = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
```

**Benefits:**
- **Portability**: Same code runs in dev, staging, production
- **Security**: Secrets not in code
- **Flexibility**: Easy to configure for different environments

## Component Design

### PI3 Sender (Server 1)

**Purpose**: Image source and forwarder

```
┌─────────────────────────────────────────┐
│           PI3 Sender Service            │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────────────────────┐  │
│  │     CameraService                │  │
│  │  - Capture from camera           │  │
│  │  - Fallback to sample images     │  │
│  └──────────────────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │     WatcherService               │  │
│  │  - Monitor watch directory       │  │
│  │  - Detect new images             │  │
│  │  - Track processed files         │  │
│  └──────────────────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │     SenderService                │  │
│  │  - HTTP upload                   │  │
│  │  - Retry logic                   │  │
│  │  - Error handling                │  │
│  └──────────────────────────────────┘  │
│              ↓                          │
│         PI5 Receiver                    │
└─────────────────────────────────────────┘
```

**Design Decisions:**

1. **Watcher vs Event-Driven**:
   - **Choice**: Polling-based watcher
   - **Rationale**: Simpler, more portable, works on all platforms
   - **Trade-off**: Slight delay (configurable via `WATCH_INTERVAL`)

2. **Retry Logic**:
   - **Exponential backoff**: 2s, 4s, 8s
   - **Rationale**: Network hiccups are common in IoT environments
   - **Configurable**: Via `RETRY_ATTEMPTS` and `RETRY_DELAY`

3. **Fallback Images**:
   - **Rationale**: Development without physical camera
   - **Production**: Set `USE_CAMERA=true`

### PI5 Receiver (Server 2)

**Purpose**: Storage, database, Label Studio integration

```
┌─────────────────────────────────────────────────────────┐
│              PI5 Receiver Service                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │         API Layer (FastAPI)                    │    │
│  │  /upload    /health    /images    /stats       │    │
│  └────────────────────────────────────────────────┘    │
│                    ↓                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │            Service Layer                       │    │
│  │                                                │    │
│  │  ┌──────────────────┐  ┌──────────────────┐   │    │
│  │  │ StorageService   │  │ LabelStudioSvc   │   │    │
│  │  │ - Save images    │  │ - Create tasks   │   │    │
│  │  │ - SHA256 hash    │  │ - Export labels  │   │    │
│  │  │ - Deduplication  │  │ - Sync storage   │   │    │
│  │  └──────────────────┘  └──────────────────┘   │    │
│  │                                                │    │
│  │  ┌──────────────────────────────────────────┐ │    │
│  │  │      CompletionWatcherService            │ │    │
│  │  │  - Poll Label Studio                     │ │    │
│  │  │  - Detect completed tasks                │ │    │
│  │  │  - Export annotations                    │ │    │
│  │  │  - Move to labeled directory             │ │    │
│  │  └──────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────┘    │
│                    ↓                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │         Data Layer (Repository)                │    │
│  │  - CRUD operations                             │    │
│  │  - Status tracking                             │    │
│  │  - Transaction management                      │    │
│  └────────────────────────────────────────────────┘    │
│                    ↓                                    │
│  ┌────────────────────────────────────────────────┐    │
│  │            Storage Layer                       │    │
│  │  ┌──────────────┐         ┌──────────────┐    │    │
│  │  │   SQLite DB  │         │ File System  │    │    │
│  │  │  Metadata    │         │   Images     │    │    │
│  │  └──────────────┘         └──────────────┘    │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Design Decisions:**

1. **Content-Addressed Storage**:
   - **Path format**: `unlabeled/ab/cd/abcdef.../filename.jpg`
   - **Rationale**:
     - Automatic deduplication (same SHA256 = same file)
     - Fast lookups (indexed by hash)
     - No directory size limits (sharding prevents millions of files in one dir)
   - **Trade-off**: Slightly more complex path structure

2. **SQLite vs PostgreSQL**:
   - **Choice**: SQLite
   - **Rationale**:
     - Lightweight (perfect for Raspberry Pi)
     - No separate server process
     - Built into Python
     - Sufficient for single-node deployment
   - **When to upgrade**:
     - Multiple Pi5 instances
     - > 100k images
     - Concurrent write operations

3. **Async/Await Architecture**:
   - **FastAPI**: Async request handling
   - **Rationale**: Non-blocking I/O for better throughput on limited hardware
   - **Example**: While uploading one image, can process other requests

4. **Two-Database Approach**:
   - **Logical separation**: `unlabeled` vs `labeled` tables
   - **Physical separation**: Separate directories
   - **Rationale**:
     - Clear separation of concerns
     - Easy backup strategies
     - Simple data lifecycle management

### Label Studio Integration

**Architecture**:

```
┌─────────────────────────────────────────────┐
│          Label Studio (Container)           │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         Web UI (Port 8080)          │   │
│  └─────────────────────────────────────┘   │
│              ↕ REST API                     │
│  ┌─────────────────────────────────────┐   │
│  │        Project Management           │   │
│  │  - Create/Update projects           │   │
│  │  - Manage tasks                     │   │
│  │  - Export annotations               │   │
│  └─────────────────────────────────────┘   │
│              ↕                              │
│  ┌─────────────────────────────────────┐   │
│  │         Storage Backend             │   │
│  │  - Local file storage               │   │
│  │  - Serve images to UI               │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
         ↕ (Label Studio SDK)
┌─────────────────────────────────────────────┐
│         PI5 Receiver Service                │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │    LabelStudioService               │   │
│  │  - Create tasks on image arrival    │   │
│  │  - Update project                   │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  CompletionWatcherService           │   │
│  │  - Poll for completed annotations   │   │
│  │  - Export to labeled directory      │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

**Design Decisions:**

1. **Polling vs Webhooks**:
   - **Choice**: Polling
   - **Rationale**:
     - Simpler setup (no webhook endpoint needed)
     - Works in local development
     - Configurable interval
   - **Production Improvement**: Could use webhooks for real-time updates

2. **Label Configuration**:
   - **Brush-based annotation**: Best for PCB defects (irregular shapes)
   - **Multiple defect types**: 10 predefined labels
   - **Overall quality**: Pass/Fail/Needs Review
   - **Notes field**: Optional additional context

3. **Storage Integration**:
   - **Local file storage**: Images stored on filesystem, served by Label Studio
   - **Path mapping**: `/labelstudio/data/images` → shared volume
   - **Benefit**: No image duplication

## Data Flow

### Image Upload Flow

```
1. Image arrives at Pi3
      ↓
2. Watcher detects file
      ↓
3. Send POST /upload to Pi5
      ↓
4. Pi5 calculates SHA256
      ↓
5. Check for duplicate
      ↓ (if new)
6. Store in content-addressed path
      ↓
7. Create database record (status: RECEIVED)
      ↓
8. Create Label Studio task
      ↓
9. Update status: SENT_TO_LABELSTUDIO
      ↓
10. Return success response
```

### Labeling Flow

```
1. User opens Label Studio UI
      ↓
2. Select task from project
      ↓
3. Annotate image with brush
      ↓
4. Submit annotation
      ↓
5. Completion Watcher polls LS
      ↓
6. Detect completed task
      ↓
7. Export annotations (JSON)
      ↓
8. Copy image to labeled directory
      ↓
9. Update status: LABELED
      ↓
10. Save annotations alongside image
```

## Technology Stack

### Why These Technologies?

| Technology | Purpose | Rationale |
|------------|---------|-----------|
| **Python 3.11** | Programming language | - Wide ML/CV ecosystem<br>- Raspberry Pi support<br>- Async/await support |
| **FastAPI** | Web framework | - Fast (async)<br>- Type hints<br>- Auto documentation<br>- Low overhead |
| **SQLite** | Database | - Lightweight<br>- No separate process<br>- Perfect for RPi<br>- ACID compliant |
| **Label Studio** | Annotation platform | - Open source<br>- Brush tool support<br>- API/SDK<br>- Active development |
| **Docker** | Containerization | - Consistent environments<br>- Easy deployment<br>- Resource isolation |
| **Pydantic** | Validation | - Type safety<br>- Auto validation<br>- JSON serialization |

## Performance Considerations

### For Raspberry Pi

1. **Memory Usage**:
   - SQLite: ~5MB
   - FastAPI: ~50MB
   - Python process: ~100MB
   - **Total**: ~200MB (comfortable for RPi3/5)

2. **Disk I/O**:
   - Content-addressed storage reduces writes
   - SQLite uses write-ahead logging (WAL)
   - Async I/O prevents blocking

3. **Network**:
   - Small payloads (multipart form data)
   - Retry logic handles WiFi hiccups
   - Configurable timeouts

### Scalability

**Current System** (Single Pi5):
- Handles: ~10 images/minute
- Storage: ~1TB (10,000 images @ 100MB each)
- Database: ~100k records

**Scaling Options**:
1. **Vertical**: Upgrade Pi5 → More powerful hardware
2. **Horizontal**: Multiple Pi5 instances → Load balancer
3. **Database**: SQLite → PostgreSQL
4. **Storage**: Local → NAS/S3

## Security Considerations

### Current System

1. **API Key**: Label Studio API key via environment variable
2. **Local Network**: Docker network isolation
3. **No Authentication**: API endpoints are open (add auth for production)

### Production Recommendations

1. **Add API Authentication**:
   ```python
   from fastapi.security import HTTPBearer
   ```

2. **HTTPS/TLS**:
   - Use reverse proxy (nginx)
   - Let's Encrypt certificates

3. **Rate Limiting**:
   ```python
   from slowapi import Limiter
   ```

4. **Input Validation**:
   - Already using Pydantic
   - Add file type validation
   - Size limits

## Testing Strategy

### Unit Tests

```python
def test_storage_service_deduplication():
    # Test that duplicate images are detected
    pass

def test_database_repository_create():
    # Test database CRUD operations
    pass
```

### Integration Tests

```python
def test_upload_workflow():
    # Test complete upload → storage → database flow
    pass
```

### End-to-End Tests

```
1. Upload image via API
2. Verify in database
3. Check Label Studio task created
4. Simulate labeling completion
5. Verify export to labeled directory
```

## Future Improvements

### Near-Term

1. **Webhook support**: Replace polling with webhooks
2. **Batch operations**: Upload multiple images
3. **Image preprocessing**: Auto-resize, quality adjustment
4. **Monitoring**: Prometheus metrics, Grafana dashboards

### Long-Term

1. **ML Integration**:
   - Auto-labeling with pre-trained models
   - Active learning (prioritize uncertain images)

2. **Multi-Node**:
   - Multiple Pi3 senders
   - Multiple Pi5 receivers
   - Load balancing

3. **Cloud Sync**:
   - Optional cloud backup
   - Collaborative labeling

4. **Advanced UI**:
   - Custom Label Studio plugins
   - Real-time statistics dashboard

## Conclusion

This architecture balances:
- **Simplicity**: Easy to understand and deploy
- **Modularity**: Easy to modify and extend
- **Efficiency**: Optimized for Raspberry Pi constraints
- **Best Practices**: Industry-standard patterns and tools

The system is production-ready for small-scale deployments and provides a solid foundation for future scaling.
