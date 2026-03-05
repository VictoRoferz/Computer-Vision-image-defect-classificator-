"""
API Routes for Server 3 (ML Inference Service)
Provides endpoints for PCB defect detection using YOLOv8
"""
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from services.inference_service import inference_service
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)

router = APIRouter(prefix="/api/v1", tags=["inference"])


@router.post("/predict", response_model=Dict[str, Any])
async def predict_upload(
    file: UploadFile = File(...),
    confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    """
    Run defect detection on an uploaded image.

    Args:
        file: Image file (JPEG/PNG)
        confidence: Override confidence threshold

    Returns:
        Detection results with bounding boxes and classifications
    """
    logger.info(f"Predict request: {file.filename}")

    if not inference_service.model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    try:
        image_bytes = await file.read()
        result = inference_service.predict_bytes(
            image_bytes=image_bytes,
            filename=file.filename or "upload.jpg",
            confidence=confidence,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/predict-path", response_model=Dict[str, Any])
async def predict_path(
    image_path: str,
    confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    """
    Run defect detection on an image by file path (for images already stored in server2).

    Args:
        image_path: Absolute path to image file
        confidence: Override confidence threshold

    Returns:
        Detection results
    """
    logger.info(f"Predict-path request: {image_path}")

    if not inference_service.model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    try:
        result = inference_service.predict_image(
            image_path=image_path,
            confidence=confidence,
        )
        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/model/info")
async def model_info() -> Dict[str, Any]:
    """Get information about the loaded model."""
    return inference_service.get_status()


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get service status."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "healthy" if inference_service.model_loaded else "loading",
        "model": inference_service.get_status(),
    }


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy" if inference_service.model_loaded else "loading",
        "service": settings.service_name,
    }
