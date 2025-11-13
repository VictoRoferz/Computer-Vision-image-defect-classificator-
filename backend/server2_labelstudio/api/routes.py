"""
API Routes for Server 2 (Label Studio Service - Raspberry Pi 5)
Provides endpoints for image storage, Label Studio integration, and data management
"""
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Optional, List, Dict, Any
from models.schemas import (
    UploadResponse,
    ImageInfo,
    LabeledImageInfo,
    StorageStats,
    StatusResponse,
    HealthResponse
)
from services.storage_service import storage_service
from services.labelstudio_service import labelstudio_service
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)

router = APIRouter(prefix="/api/v1", tags=["storage"])


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload image from Server 1 (Camera).

    This endpoint:
    1. Receives image file
    2. Stores in unlabeled directory with content-addressing
    3. Creates Label Studio task automatically

    Args:
        file: Uploaded image file

    Returns:
        UploadResponse with storage and task information

    Raises:
        HTTPException: If upload or processing fails
    """
    logger.info(f"Received upload: {file.filename} ({file.content_type})")

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Create temporary file
    temp_dir = settings.data_root / "__temp__"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename

    try:
        # Save uploaded file temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Saved temporary file: {temp_path}")

        # Store in unlabeled directory
        storage_result = storage_service.store_unlabeled_image(
            source_path=temp_path,
            filename=file.filename
        )

        sha256 = storage_result["sha256"]
        stored_path = Path(storage_result["path"])

        logger.info(f"Image stored: {stored_path}")

        # Create Label Studio task
        task_result = None
        if labelstudio_service.project:
            try:
                task_result = labelstudio_service.create_task_from_image(
                    image_path=stored_path,
                    sha256=sha256
                )
                logger.info(f"Label Studio task created: ID={task_result['task_id']}")

            except Exception as e:
                logger.error(f"Failed to create Label Studio task: {e}", exc_info=True)
                # Don't fail the upload if task creation fails
                task_result = {"error": str(e)}

        # Prepare response
        response = {
            **storage_result,
            "task_id": task_result.get("task_id") if task_result else None,
            "message": "Image uploaded and task created successfully" if task_result else "Image uploaded (task creation failed)"
        }

        return response

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except IOError as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage failed: {str(e)}")

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    finally:
        # Cleanup temp file
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")


@router.get("/images/unlabeled", response_model=List[ImageInfo])
async def list_unlabeled_images(
    limit: Optional[int] = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    List unlabeled images.

    Args:
        limit: Maximum number of results (1-1000)
        offset: Number of results to skip

    Returns:
        List of unlabeled image information
    """
    logger.debug(f"Listing unlabeled images: limit={limit}, offset={offset}")

    try:
        images = storage_service.list_unlabeled_images(limit=limit, offset=offset)
        return images

    except Exception as e:
        logger.error(f"Failed to list unlabeled images: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list images: {str(e)}"
        )


@router.get("/images/labeled", response_model=List[LabeledImageInfo])
async def list_labeled_images(
    limit: Optional[int] = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> List[Dict[str, Any]]:
    """
    List labeled images with annotations.

    Args:
        limit: Maximum number of results (1-1000)
        offset: Number of results to skip

    Returns:
        List of labeled image information
    """
    logger.debug(f"Listing labeled images: limit={limit}, offset={offset}")

    try:
        images = storage_service.list_labeled_images(limit=limit, offset=offset)
        return images

    except Exception as e:
        logger.error(f"Failed to list labeled images: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list images: {str(e)}"
        )


@router.get("/stats", response_model=StorageStats)
async def get_storage_stats() -> Dict[str, Any]:
    """
    Get storage statistics.

    Returns:
        StorageStats with counts and sizes for unlabeled/labeled images
    """
    logger.debug("Getting storage statistics")

    try:
        stats = storage_service.get_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/labelstudio/stats")
async def get_labelstudio_stats() -> Dict[str, Any]:
    """
    Get Label Studio project statistics.

    Returns:
        Dictionary with Label Studio project stats
    """
    logger.debug("Getting Label Studio statistics")

    try:
        if not labelstudio_service.project:
            raise HTTPException(
                status_code=503,
                detail="Label Studio not initialized"
            )

        stats = labelstudio_service.get_project_stats()
        return stats

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get Label Studio stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.get("/status", response_model=StatusResponse)
async def get_status() -> Dict[str, Any]:
    """
    Get comprehensive service status.

    Returns:
        StatusResponse with service, storage, and Label Studio status
    """
    logger.debug("Status check requested")

    try:
        # Get storage stats
        storage_stats = storage_service.get_statistics()

        # Get Label Studio stats
        ls_stats = labelstudio_service.get_project_stats()
        ls_healthy = labelstudio_service.is_healthy()

        # Determine overall status
        overall_status = "healthy"
        if not ls_healthy:
            overall_status = "degraded"

        return {
            "service": settings.service_name,
            "version": settings.service_version,
            "storage": storage_stats,
            "labelstudio": {
                **ls_stats,
                "healthy": ls_healthy,
                "url": settings.labelstudio_url
            },
            "status": overall_status
        }

    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> Dict[str, Any]:
    """
    Simple health check endpoint for Docker/Kubernetes.

    Returns:
        HealthResponse with health status
    """
    try:
        # Check components
        storage_healthy = settings.unlabeled_dir.exists() and settings.labeled_dir.exists()
        ls_healthy = labelstudio_service.is_healthy() if labelstudio_service.client else False

        overall_status = "healthy"
        if not storage_healthy:
            overall_status = "unhealthy"
        elif not ls_healthy:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "service": settings.service_name,
            "version": settings.service_version,
            "components": {
                "storage": storage_healthy,
                "labelstudio": ls_healthy
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": settings.service_name,
            "version": settings.service_version,
            "components": {
                "storage": False,
                "labelstudio": False
            }
        }
