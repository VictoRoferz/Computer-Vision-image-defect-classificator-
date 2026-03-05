#!/usr/bin/env bash
# ============================================================
# PCB Defect Classification System - One-Click Launcher
# Works on Mac and Linux
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  PCB Defect Classification System"
echo "============================================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed."
    echo "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running."
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "[OK] Docker is running"

# Check Docker Compose
if ! docker compose version &> /dev/null 2>&1; then
    echo "ERROR: Docker Compose is not available."
    echo "Please update Docker Desktop."
    exit 1
fi

echo "[OK] Docker Compose is available"

# Create .env from template if needed
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "[OK] .env file created (edit it later to set LABELSTUDIO_API_KEY)"
fi

echo ""
echo "Building and starting all services..."
echo "  This may take a few minutes on first run (downloading images + models)."
echo ""

docker compose up --build -d

echo ""
echo "============================================================"
echo "  All services are starting!"
echo "============================================================"
echo ""
echo "  Dashboard:       http://localhost:3000"
echo "  Label Studio:    http://localhost:8080"
echo "  Camera API:      http://localhost:8001/docs"
echo "  Storage API:     http://localhost:8002/docs"
echo "  Inference API:   http://localhost:8003/docs"
echo ""
echo "  First-time setup:"
echo "    1. Open http://localhost:8080"
echo "    2. Login with: admin@example.com / admin123"
echo "    3. Go to Account & Settings > Access Token"
echo "    4. Copy the token into .env as LABELSTUDIO_API_KEY=<token>"
echo "    5. Run: docker compose restart server2"
echo ""
echo "  Then open http://localhost:3000 to use the dashboard!"
echo ""
echo "  Stop all services: docker compose down"
echo "  View logs:         docker compose logs -f"
echo "============================================================"
