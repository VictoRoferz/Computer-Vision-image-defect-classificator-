"""
Main application entry point for Server 2 (Label Studio Service - Raspberry Pi 5)
FastAPI application for PCB image storage and Label Studio integration
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .api.routes import router as api_router
from .api.webhooks import router as webhook_router
from .services.labelstudio_service import labelstudio_service
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
    logger.info(f"Storage: unlabeled={settings.unlabeled_dir}, labeled={settings.labeled_dir}")
    logger.info(f"Label Studio URL: {settings.labelstudio_url}")

    # Initialize Label Studio service
    if settings.labelstudio_api_key:
        try:
            logger.info("Initializing Label Studio service...")
            labelstudio_service.initialize()
            logger.info("Label Studio service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Label Studio: {e}", exc_info=True)
            logger.warning("Service will continue without Label Studio integration")
    else:
        logger.warning("Label Studio API key not set - Label Studio integration disabled")
        logger.warning("Set LABELSTUDIO_API_KEY environment variable to enable")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}")


# Create FastAPI application
app = FastAPI(
    title="PCB Label Studio Service (Server 2)",
    description="Raspberry Pi 5 - Image storage and Label Studio integration service",
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
app.include_router(api_router)
app.include_router(webhook_router)


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "description": "PCB Label Studio Service - Raspberry Pi 5 Simulator",
        "endpoints": {
            "upload": "POST /api/v1/upload - Upload image from Server 1",
            "list_unlabeled": "GET /api/v1/images/unlabeled - List unlabeled images",
            "list_labeled": "GET /api/v1/images/labeled - List labeled images",
            "stats": "GET /api/v1/stats - Storage statistics",
            "labelstudio_stats": "GET /api/v1/labelstudio/stats - Label Studio statistics",
            "status": "GET /api/v1/status - Service status",
            "health": "GET /api/v1/health - Health check",
            "webhook_annotation": "POST /api/v1/webhook/annotation-created - Webhook endpoint",
            "docs": "GET /docs - Interactive API documentation"
        },
        "labelstudio": {
            "url": settings.labelstudio_url,
            "initialized": labelstudio_service.project is not None,
            "project_id": labelstudio_service.project.id if labelstudio_service.project else None
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
