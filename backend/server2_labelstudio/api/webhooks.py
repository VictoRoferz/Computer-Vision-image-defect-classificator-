"""
Webhook handlers for Server 2 (Label Studio Service)
Handles callbacks from Label Studio when annotations are created/updated
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from typing import Dict, Any
from pathlib import Path
from models.schemas import WebhookPayload, WebhookResponse
from services.storage_service import storage_service
from services.labelstudio_service import labelstudio_service
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)

router = APIRouter(prefix="/api/v1/webhook", tags=["webhooks"])


@router.post("/annotation-created", response_model=WebhookResponse)
async def handle_annotation_created(
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Handle ANNOTATION_CREATED webhook from Label Studio.

    This endpoint is called by Label Studio when a user completes labeling an image.
    It:
    1. Receives the annotation data
    2. Copies the image to labeled directory
    3. Saves the annotation JSON alongside

    Args:
        request: FastAPI request object
        background_tasks: Background task handler

    Returns:
        WebhookResponse with processing status

    Raises:
        HTTPException: If processing fails
    """
    logger.info("Received ANNOTATION_CREATED webhook")

    try:
        # Parse webhook payload
        payload = await request.json()
        logger.debug(f"Webhook payload: {payload}")

        # Extract key information
        action = payload.get("action")
        annotation = payload.get("annotation", {})
        task = payload.get("task", {})

        if not annotation:
            raise HTTPException(
                status_code=400,
                detail="Missing annotation data in webhook payload"
            )

        # Get task metadata (contains SHA256 and filename)
        task_meta = task.get("meta", {})
        sha256 = task_meta.get("sha256")
        original_filename = task_meta.get("original_filename")

        if not sha256 or not original_filename:
            logger.error(f"Missing metadata in task: {task_meta}")
            raise HTTPException(
                status_code=400,
                detail="Missing SHA256 or filename in task metadata"
            )

        logger.info(
            f"Processing annotation for: {original_filename} (SHA256: {sha256[:8]}...)"
        )

        # Store labeled image and annotation
        result = storage_service.store_labeled_image(
            sha256=sha256,
            filename=original_filename,
            annotation_data=annotation
        )

        logger.info(
            f"Labeled image stored: {result['image_path']}, "
            f"annotation: {result['annotation_path']}"
        )

        return {
            "status": "success",
            "message": f"Annotation processed for {original_filename}",
            "labeled_image_path": result["image_path"],
            "annotation_path": result["annotation_path"]
        }

    except HTTPException:
        raise

    except FileNotFoundError as e:
        logger.error(f"Source image not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Source image not found: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process annotation: {str(e)}"
        )


@router.post("/annotation-updated", response_model=WebhookResponse)
async def handle_annotation_updated(
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Handle ANNOTATION_UPDATED webhook from Label Studio.

    This endpoint is called when an existing annotation is modified.
    It updates the stored annotation JSON.

    Args:
        request: FastAPI request object
        background_tasks: Background task handler

    Returns:
        WebhookResponse with processing status

    Raises:
        HTTPException: If processing fails
    """
    logger.info("Received ANNOTATION_UPDATED webhook")

    try:
        # Parse webhook payload
        payload = await request.json()
        logger.debug(f"Webhook payload: {payload}")

        # Extract key information
        annotation = payload.get("annotation", {})
        task = payload.get("task", {})

        if not annotation:
            raise HTTPException(
                status_code=400,
                detail="Missing annotation data in webhook payload"
            )

        # Get task metadata
        task_meta = task.get("meta", {})
        sha256 = task_meta.get("sha256")
        original_filename = task_meta.get("original_filename")

        if not sha256 or not original_filename:
            raise HTTPException(
                status_code=400,
                detail="Missing SHA256 or filename in task metadata"
            )

        logger.info(
            f"Updating annotation for: {original_filename} (SHA256: {sha256[:8]}...)"
        )

        # Update labeled image and annotation
        result = storage_service.store_labeled_image(
            sha256=sha256,
            filename=original_filename,
            annotation_data=annotation
        )

        logger.info(f"Annotation updated: {result['annotation_path']}")

        return {
            "status": "success",
            "message": f"Annotation updated for {original_filename}",
            "labeled_image_path": result["image_path"],
            "annotation_path": result["annotation_path"]
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update annotation: {str(e)}"
        )


@router.post("/test")
async def test_webhook(request: Request) -> Dict[str, Any]:
    """
    Test endpoint for webhook configuration.

    Returns:
        Simple acknowledgment response
    """
    logger.info("Received webhook test request")

    try:
        payload = await request.json()
        logger.debug(f"Test payload: {payload}")

        return {
            "status": "success",
            "message": "Webhook endpoint is working",
            "received": payload
        }

    except Exception as e:
        logger.error(f"Test webhook failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
