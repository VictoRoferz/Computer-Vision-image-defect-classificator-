"""API routes for PI5 Receiver service.

Defines all HTTP endpoints for the receiver service.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List

from .models import (
    UploadResponse,
    HealthResponse,
    ImageStatusResponse,
    StatsResponse
)
from ..config import Settings, get_settings
from ..database import DatabaseRepository, ImageStatus
from ..services import StorageService, LabelStudioService
from ..utils.logger import get_logger
from ..utils.helpers import is_image_file

logger = get_logger(__name__)


def create_router(
    settings: Settings,
    db_repo: DatabaseRepository,
    storage_service: StorageService,
    ls_service: LabelStudioService
) -> APIRouter:
    """Create and configure API router with dependency injection.

    Args:
        settings: Application settings
        db_repo: Database repository instance
        storage_service: Storage service instance
        ls_service: Label Studio service instance

    Returns:
        APIRouter: Configured router
    """
    router = APIRouter()

    @router.post("/upload", response_model=UploadResponse)
    async def upload_image(file: UploadFile = File(...)):
        """Upload an image to the receiver service.

        This endpoint:
        1. Receives the uploaded image
        2. Stores it in content-addressed storage
        3. Creates a database record
        4. Sends to Label Studio (if configured)

        Args:
            file: Uploaded file

        Returns:
            UploadResponse: Upload status and metadata

        Raises:
            HTTPException: If upload fails
        """
        try:
            # Validate file type
            if not is_image_file(file.filename or "", settings.SUPPORTED_FORMATS):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type. Supported: {settings.SUPPORTED_FORMATS}"
                )

            # Validate file size
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to start

            max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Max size: {settings.MAX_IMAGE_SIZE_MB}MB"
                )

            logger.info(f"Receiving upload: {file.filename} ({file_size} bytes)")

            # Save image
            record, is_duplicate = storage_service.save_uploaded_image(
                file.file,
                file.filename or "upload.jpg"
            )

            # Create Label Studio task if not duplicate
            task_id = None
            if not is_duplicate and ls_service.client:
                try:
                    task = ls_service.create_task_for_image(record.sha256)
                    if task:
                        task_id = task.get("id")
                except Exception as e:
                    logger.error(f"Failed to create Label Studio task: {e}")

            return UploadResponse(
                status="already_stored" if is_duplicate else "stored",
                sha256=record.sha256,
                filename=record.filename,
                file_path=record.file_path,
                is_duplicate=is_duplicate,
                labelstudio_task_id=task_id
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload error: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint.

        Returns:
            HealthResponse: Service health status
        """
        # Check database
        db_ok = False
        try:
            db_repo.get_all(limit=1)
            db_ok = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        # Check Label Studio
        ls_ok = ls_service.health_check() if ls_service.client else False

        # Check storage
        storage_ok = settings.IMAGES_UNLABELED.exists() and settings.IMAGES_LABELED.exists()

        overall_status = "healthy" if (db_ok and storage_ok) else "degraded"

        return HealthResponse(
            status=overall_status,
            database=db_ok,
            labelstudio=ls_ok,
            storage=storage_ok
        )

    @router.get("/images/{sha256}", response_model=ImageStatusResponse)
    async def get_image_status(sha256: str):
        """Get status of a specific image by SHA256.

        Args:
            sha256: SHA256 hash of the image

        Returns:
            ImageStatusResponse: Image status

        Raises:
            HTTPException: If image not found
        """
        record = db_repo.get_by_sha256(sha256)
        if not record:
            raise HTTPException(status_code=404, detail="Image not found")

        return ImageStatusResponse(
            sha256=record.sha256,
            filename=record.filename,
            status=record.status.value,
            received_at=record.received_at,
            sent_to_ls_at=record.sent_to_ls_at,
            labeled_at=record.labeled_at,
            labelstudio_task_id=record.labelstudio_task_id,
            error_message=record.error_message
        )

    @router.get("/images", response_model=List[ImageStatusResponse])
    async def list_images(
        status: str = None,
        limit: int = 100
    ):
        """List all images with optional filtering.

        Args:
            status: Optional status filter (received, sent_to_labelstudio, labeled, error)
            limit: Maximum number of results

        Returns:
            List of ImageStatusResponse
        """
        try:
            if status:
                records = db_repo.get_by_status(ImageStatus(status))
            else:
                records = db_repo.get_all(limit=limit)

            return [
                ImageStatusResponse(
                    sha256=r.sha256,
                    filename=r.filename,
                    status=r.status.value,
                    received_at=r.received_at,
                    sent_to_ls_at=r.sent_to_ls_at,
                    labeled_at=r.labeled_at,
                    labelstudio_task_id=r.labelstudio_task_id,
                    error_message=r.error_message
                )
                for r in records
            ]

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    @router.get("/stats", response_model=StatsResponse)
    async def get_statistics():
        """Get system statistics.

        Returns:
            StatsResponse: System statistics
        """
        all_images = db_repo.get_all()

        stats = {
            "total_images": len(all_images),
            "unlabeled": 0,
            "sent_to_labelstudio": 0,
            "labeled": 0,
            "errors": 0
        }

        for img in all_images:
            if img.status == ImageStatus.RECEIVED:
                stats["unlabeled"] += 1
            elif img.status == ImageStatus.SENT_TO_LABELSTUDIO:
                stats["sent_to_labelstudio"] += 1
            elif img.status == ImageStatus.LABELED:
                stats["labeled"] += 1
            elif img.status == ImageStatus.ERROR:
                stats["errors"] += 1

        return StatsResponse(**stats)

    return router
