"""Main entry point for PI5 Receiver service.

This module initializes all components and starts the FastAPI application.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import DatabaseRepository
from services import StorageService, LabelStudioService, CompletionWatcherService
from api import create_router
from utils.logger import get_logger

logger = get_logger(__name__)


# Global service instances
watcher_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting PI5 Receiver service...")

    settings = get_settings()
    db_repo = app.state.db_repo
    ls_service = app.state.ls_service
    storage_service = app.state.storage_service

    # Ensure Label Studio project exists
    if ls_service.client:
        try:
            project_id = ls_service.ensure_project_exists()
            logger.info(f"Label Studio project ready (ID: {project_id})")
        except Exception as e:
            logger.error(f"Failed to initialize Label Studio project: {e}")

    # Start watcher service
    global watcher_service
    watcher_service = CompletionWatcherService(
        settings, db_repo, ls_service, storage_service
    )

    # Start watcher in background
    if settings.WATCHER_ENABLED:
        asyncio.create_task(watcher_service.start())

    logger.info("PI5 Receiver service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down PI5 Receiver service...")

    if watcher_service:
        watcher_service.stop()

    logger.info("PI5 Receiver service stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    # Configure logging
    from utils.logger import setup_logger
    setup_logger(__name__, settings.LOG_LEVEL)

    app = FastAPI(
        title="PI5 Receiver Service",
        description="PCB Labeling Workflow - Raspberry Pi 5 Receiver & Label Studio Integration",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize services
    db_repo = DatabaseRepository(settings.DATABASE_PATH)
    storage_service = StorageService(settings, db_repo)
    ls_service = LabelStudioService(settings, db_repo)

    # Store in app state for access in lifespan
    app.state.settings = settings
    app.state.db_repo = db_repo
    app.state.storage_service = storage_service
    app.state.ls_service = ls_service

    # Create and include router
    router = create_router(settings, db_repo, storage_service, ls_service)
    app.include_router(router, prefix="/api/v1", tags=["receiver"])

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "PI5 Receiver",
            "version": "1.0.0",
            "status": "running"
        }

    logger.info("FastAPI application created")
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # Set to True for development
        log_level=settings.LOG_LEVEL.lower()
    )
