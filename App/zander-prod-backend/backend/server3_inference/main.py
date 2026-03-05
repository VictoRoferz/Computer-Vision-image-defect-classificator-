"""
Main application entry point for Server 3 (ML Inference Service)
FastAPI application for PCB defect detection using YOLOv8
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.routes import router
from config.settings import settings
from services.inference_service import inference_service
from utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    logger.info(f"Model path: {settings.model_path}")
    logger.info(f"Confidence threshold: {settings.confidence_threshold}")

    # Load ML model on startup
    try:
        inference_service.load_model()
        logger.info("ML model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}", exc_info=True)
        logger.warning("Service will start but predictions will be unavailable")

    yield

    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="PCB Inference Service (Server 3)",
    description="YOLOv8-based PCB defect detection service",
    version=settings.service_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "description": "PCB Defect Detection - YOLOv8 Inference Service",
        "model_loaded": inference_service.model_loaded,
        "endpoints": {
            "predict": "POST /api/v1/predict - Upload image for detection",
            "predict_path": "POST /api/v1/predict-path - Detect on stored image",
            "model_info": "GET /api/v1/model/info - Model information",
            "status": "GET /api/v1/status - Service status",
            "health": "GET /api/v1/health - Health check",
            "docs": "GET /docs - API documentation",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
