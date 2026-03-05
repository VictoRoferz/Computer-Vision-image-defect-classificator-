@echo off
REM ============================================================
REM PCB Defect Classification System - One-Click Launcher
REM Works on Windows
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo   PCB Defect Classification System
echo ============================================================
echo.

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed.
    echo Install Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker daemon is not running.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [OK] Docker is running

docker compose version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Compose is not available.
    echo Please update Docker Desktop.
    pause
    exit /b 1
)

echo [OK] Docker Compose is available

REM Create .env from template if needed
if not exist .env (
    echo.
    echo Creating .env file from template...
    copy .env.example .env >nul
    echo [OK] .env file created
)

echo.
echo Building and starting all services...
echo   This may take a few minutes on first run.
echo.

docker compose up --build -d

echo.
echo ============================================================
echo   All services are starting!
echo ============================================================
echo.
echo   Dashboard:       http://localhost:3000
echo   Label Studio:    http://localhost:8080
echo   Camera API:      http://localhost:8001/docs
echo   Storage API:     http://localhost:8002/docs
echo   Inference API:   http://localhost:8003/docs
echo.
echo   First-time setup:
echo     1. Open http://localhost:8080
echo     2. Login with: admin@example.com / admin123
echo     3. Go to Account ^& Settings ^> Access Token
echo     4. Copy the token into .env as LABELSTUDIO_API_KEY=^<token^>
echo     5. Run: docker compose restart server2
echo.
echo   Then open http://localhost:3000 to use the dashboard!
echo.
echo   Stop all services: docker compose down
echo ============================================================
echo.
pause
