"""
Main application entry point for Server 1 (Camera Service - Raspberry Pi 3)
FastAPI application for PCB image capture and upload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .api.routes import router
from .config.settings import settings
from .utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    logger.info(f"Server 2 URL: {settings.server2_url}")
    logger.info(f"Camera enabled: {settings.use_camera}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}")


# Create FastAPI application
app = FastAPI(
    title="PCB Camera Service (Server 1)",
    description="Raspberry Pi 3 - Camera capture and image upload service",
    version=settings.service_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (for development/testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "description": "PCB Camera Service - Raspberry Pi 3 Simulator",
        "endpoints": {
            "capture": "POST /api/v1/capture - Capture and upload image",
            "status": "GET /api/v1/status - Get service status",
            "health": "GET /api/v1/health - Health check",
            "test_camera": "POST /api/v1/test-camera - Test camera only",
            "test_upload": "POST /api/v1/test-upload - Test Server 2 connection",
            "docs": "GET /docs - Interactive API documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.host}:{settings.port}")

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # Development mode
        log_level=settings.log_level.lower()
    )
