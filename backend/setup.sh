#!/bin/bash

# ============================================================
# PCB Defect Classification System - Setup Script
# ============================================================
# This script helps you set up the system on Mac or Raspberry Pi

set -e  # Exit on error

echo "============================================================"
echo "PCB Defect Classification System - Setup"
echo "============================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✅ Docker is installed"

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not available"
    echo "Please install Docker Compose or update Docker Desktop"
    exit 1
fi

echo "✅ Docker Compose is available"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: You need to configure Label Studio API key!"
    echo "   1. Start the services: docker-compose up"
    echo "   2. Open http://localhost:8080 in your browser"
    echo "   3. Create an account or login"
    echo "   4. Go to Account & Settings > Access Token"
    echo "   5. Copy the token"
    echo "   6. Edit .env file and set LABELSTUDIO_API_KEY=<your-token>"
    echo "   7. Restart services: docker-compose restart server2"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Check if LABELSTUDIO_API_KEY is set
if grep -q "LABELSTUDIO_API_KEY=$" .env; then
    echo "⚠️  Warning: LABELSTUDIO_API_KEY is not set in .env"
    echo "   Label Studio integration will not work until you set it"
    echo ""
fi

echo "============================================================"
echo "Setup Steps:"
echo "============================================================"
echo ""
echo "1. Build and start services:"
echo "   cd backend"
echo "   docker-compose up --build"
echo ""
echo "2. Access services:"
echo "   - Label Studio UI:  http://localhost:8080"
echo "   - Server 1 API:     http://localhost:8001/docs"
echo "   - Server 2 API:     http://localhost:8002/docs"
echo ""
echo "3. Configure Label Studio (first time only):"
echo "   a. Open http://localhost:8080"
echo "   b. Create account (default: admin@example.com / admin123)"
echo "   c. Get API token: Account & Settings > Access Token"
echo "   d. Update .env: LABELSTUDIO_API_KEY=<your-token>"
echo "   e. Restart Server 2: docker-compose restart server2"
echo ""
echo "4. Test the workflow:"
echo "   curl -X POST http://localhost:8001/api/v1/capture"
echo ""
echo "   This will:"
echo "   - Capture/generate a test image on Server 1"
echo "   - Upload it to Server 2"
echo "   - Create a Label Studio task"
echo "   - Image appears in Label Studio UI for labeling"
echo ""
echo "5. Label an image:"
echo "   a. Open http://localhost:8080"
echo "   b. Open the project 'PCB Defect Classification'"
echo "   c. Click on a task to start labeling"
echo "   d. Use brush tool to mark defects"
echo "   e. Select overall quality (Pass/Fail)"
echo "   f. Submit annotation"
echo "   g. Labeled image automatically saved to Server 2"
echo ""
echo "============================================================"
echo "Useful Commands:"
echo "============================================================"
echo ""
echo "Start services:"
echo "  docker-compose up -d"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo "  docker-compose logs -f server1  # Only Server 1 logs"
echo "  docker-compose logs -f server2  # Only Server 2 logs"
echo ""
echo "Rebuild after code changes:"
echo "  docker-compose up --build"
echo ""
echo "Clean up everything (including data!):"
echo "  docker-compose down -v"
echo ""
echo "============================================================"
echo "Ready to start!"
echo "============================================================"
echo ""
echo "Run: docker-compose up --build"
echo ""
