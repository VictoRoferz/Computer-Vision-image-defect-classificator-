#!/bin/bash

# ============================================================
# PCB Defect Classification System - Setup Script
# ============================================================
# This script helps you set up the system on any laptop (Mac/Linux/Windows WSL)

set -e

echo "============================================================"
echo "PCB Defect Classification System - Setup"
echo "============================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "[OK] Docker is installed"

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not available"
    echo "Please install Docker Compose or update Docker Desktop"
    exit 1
fi

echo "[OK] Docker Compose is available"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "[OK] .env file created"
    echo ""
    echo "NOTE: You need to configure Label Studio API key after first start!"
    echo "  1. Start the services: ./start.sh"
    echo "  2. Open http://localhost:8080 in your browser"
    echo "  3. Login with admin@example.com / admin123"
    echo "  4. Go to Account & Settings > Access Token"
    echo "  5. Copy the token"
    echo "  6. Edit .env file and set LABELSTUDIO_API_KEY=<your-token>"
    echo "  7. Restart: docker compose restart server2"
    echo ""
else
    echo "[OK] .env file already exists"
    echo ""
fi

# Check if LABELSTUDIO_API_KEY is set
if grep -q "LABELSTUDIO_API_KEY=$" .env 2>/dev/null; then
    echo "WARNING: LABELSTUDIO_API_KEY is not set in .env"
    echo "  Label Studio integration will not work until you set it"
    echo ""
fi

echo "============================================================"
echo "Quick Start:"
echo "============================================================"
echo ""
echo "  ./start.sh          # Mac/Linux: build & start everything"
echo "  start.bat            # Windows: double-click to start"
echo ""
echo "Access services:"
echo "  Dashboard:       http://localhost:3000"
echo "  Label Studio:    http://localhost:8080"
echo "  Camera API:      http://localhost:8001/docs"
echo "  Storage API:     http://localhost:8002/docs"
echo "  Inference API:   http://localhost:8003/docs"
echo ""
echo "Useful Commands:"
echo "  docker compose up --build -d    # Build & start"
echo "  docker compose down             # Stop"
echo "  docker compose logs -f          # View logs"
echo "  docker compose down -v          # Stop & delete data"
echo ""
echo "============================================================"
echo "Ready! Run ./start.sh to launch."
echo "============================================================"
