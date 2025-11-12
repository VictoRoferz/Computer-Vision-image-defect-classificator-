# PCB Defect Classification - Computer Vision System

This project involves the development of an end-to-end AI-powered defect detection system for PCB (Printed Circuit Board) joints, combining hardware and software to automatically identify and classify product defects using Machine Learning (ML) and Artificial Intelligence (AI) techniques.

## 🎯 Project Overview

A production-ready system for collecting, labeling, and classifying PCB defect images using:
- **Raspberry Pi 3**: Image capture and forwarding
- **Raspberry Pi 5**: Storage, database, and Label Studio integration
- **Label Studio**: Web-based annotation platform
- **Docker**: Containerized deployment

## 🚀 Quick Start

### For Development (Mac/Local)

```bash
# Navigate to backend directory
cd backend

# Copy environment template
cp .env.example .env

# Start all services
docker-compose up -d

# Access Label Studio
open http://localhost:8080

# Access API
open http://localhost:8000/docs
```

**Full setup guide**: [backend/SETUP.md](backend/SETUP.md)

### For Production (Raspberry Pi)

See deployment instructions in [backend/README.md](backend/README.md)

## 📁 Project Structure

```
.
├── backend/                      # New modular backend system
│   ├── pi3_sender/              # Raspberry Pi 3 sender service
│   ├── pi5_receiver/            # Raspberry Pi 5 receiver service
│   ├── label_studio_init/       # Label Studio initialization
│   ├── docker-compose.yml       # Service orchestration
│   ├── README.md                # Complete documentation
│   ├── SETUP.md                 # Step-by-step setup guide
│   └── ARCHITECTURE.md          # Architectural design docs
│
├── pi3_sender-main/             # Legacy sender code (reference)
└── pi5_storage-main/            # Legacy storage code (reference)
```

## 🏗️ System Architecture

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
└─────────────────────────────────────────────────────────────────────┘
```

**Full architecture**: [backend/ARCHITECTURE.md](backend/ARCHITECTURE.md)

## ✨ Features

### Current Implementation

- ✅ **Modular Architecture**: Clean separation of concerns
- ✅ **Automated Workflow**: Image arrives → Auto-labeled → Exported
- ✅ **Content-Addressed Storage**: SHA256-based deduplication
- ✅ **SQLite Database**: Lightweight metadata tracking
- ✅ **Label Studio Integration**: Web-based annotation
- ✅ **Docker Deployment**: Containerized services
- ✅ **Health Monitoring**: API health checks
- ✅ **Retry Logic**: Robust error handling
- ✅ **Comprehensive Logging**: Structured logging

### Workflow

1. **Image Capture**: Pi3 captures PCB image or receives from camera
2. **Upload**: Image sent to Pi5 via HTTP POST
3. **Storage**: Content-addressed storage with deduplication
4. **Database**: Metadata tracked in SQLite
5. **Label Studio**: Auto-created task for labeling
6. **Annotation**: User labels defects with brush tool
7. **Export**: Labeled images moved to separate directory
8. **Training**: Ready for ML model training

## 🛠️ Technology Stack

- **Language**: Python 3.11
- **Web Framework**: FastAPI (async)
- **Database**: SQLite
- **Annotation**: Label Studio
- **Containerization**: Docker & Docker Compose
- **Validation**: Pydantic
- **HTTP Client**: Requests
- **Logging**: Python logging

## 📚 Documentation

- [Complete Documentation](backend/README.md) - Full system documentation
- [Setup Guide](backend/SETUP.md) - Step-by-step installation
- [Architecture](backend/ARCHITECTURE.md) - Design and rationale
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (after starting services)

## 🎨 Defect Types

The system supports labeling these PCB defects:
- Solder Bridge
- Insufficient Solder
- Cold Joint
- Component Damage
- Missing Component
- Wrong Component
- Misalignment
- Contamination
- Other Defect
- Good (no defect)

## 🧪 Testing

```bash
# Test image upload
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@test_image.jpg"

# Check system health
curl http://localhost:8000/api/v1/health

# View statistics
curl http://localhost:8000/api/v1/stats
```

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Follow code style (PEP 8)
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 👤 Author

**Victor Roferz**

## 🙏 Acknowledgments

- Label Studio team for the annotation platform
- FastAPI team for the web framework
- Python community for excellent libraries
