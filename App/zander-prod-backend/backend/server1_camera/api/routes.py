"""
API Routes for Server 1 (Camera Service)
Provides endpoints for camera control, image capture, and capture-to-predict flow.
"""
import io
import requests as http_requests
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from typing import Dict, Any
from services.camera_service import camera_service
from services.upload_service import upload_service
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)

router = APIRouter(prefix="/api/v1", tags=["camera"])


@router.post("/capture", response_model=Dict[str, Any])
async def capture_and_upload(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Capture image from camera and upload to Server 2.

    This endpoint:
    1. Captures image from camera (or uses fallback)
    2. Uploads to Server 2 (Raspberry Pi 5)
    3. Cleans up local file (if configured)

    Returns:
        Dictionary with capture and upload status

    Raises:
        HTTPException: If capture or upload fails
    """
    logger.info("Received capture request")

    try:
        # Step 1: Capture image
        logger.info("Capturing image...")
        image_path = camera_service.capture()

        if not image_path:
            raise HTTPException(
                status_code=500,
                detail="Failed to capture image"
            )

        # Step 2: Upload to Server 2
        logger.info(f"Uploading {image_path.name} to Server 2...")
        upload_response = upload_service.upload_and_cleanup(image_path)

        return {
            "status": "success",
            "message": "Image captured and uploaded successfully",
            "image_name": image_path.name,
            "server2_response": upload_response
        }

    except RuntimeError as e:
        logger.error(f"Capture/upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Operation failed: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_status() -> Dict[str, Any]:
    """
    Get camera service status.

    Returns:
        Dictionary with camera and connection status
    """
    logger.debug("Status check requested")

    try:
        # Get camera status
        camera_status = camera_service.get_status()

        # Test Server 2 connection
        server2_connected = upload_service.test_connection()

        return {
            "service": settings.service_name,
            "version": settings.service_version,
            "camera": camera_status,
            "server2": {
                "url": settings.server2_url,
                "connected": server2_connected
            },
            "status": "healthy" if camera_status.get("camera_available", True) else "degraded"
        }

    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Simple health check endpoint for Docker/Kubernetes.

    Returns:
        Dictionary with health status
    """
    return {
        "status": "healthy",
        "service": settings.service_name
    }


@router.post("/test-camera", response_model=Dict[str, Any])
async def test_camera() -> Dict[str, Any]:
    """
    Test camera capture without uploading to Server 2.
    Useful for debugging camera issues.

    Returns:
        Dictionary with test results

    Raises:
        HTTPException: If capture fails
    """
    logger.info("Camera test requested")

    try:
        image_path = camera_service.capture()

        if not image_path:
            raise HTTPException(
                status_code=500,
                detail="Camera capture failed"
            )

        # Get image info
        file_size_kb = image_path.stat().st_size / 1024

        result = {
            "status": "success",
            "message": "Camera test successful",
            "image_name": image_path.name,
            "image_path": str(image_path),
            "size_kb": round(file_size_kb, 2),
            "note": "Image saved locally but not uploaded to Server 2"
        }

        logger.info(f"Camera test successful: {result}")
        return result

    except Exception as e:
        logger.error(f"Camera test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Camera test failed: {str(e)}"
        )


@router.post("/capture-image")
async def capture_image_only(mode: str = "server") -> Response:
    """
    Capture image from camera and return the raw image bytes.
    Used by the dashboard for the capture-and-predict inference flow.
    Does NOT upload to Server 2.

    Args:
        mode: 'server' to use configured camera, 'test' to force test/fallback image.
    """
    logger.info(f"Capture-image request (mode={mode})")

    try:
        if mode == "test":
            image_path = camera_service.capture_test()
        else:
            image_path = camera_service.capture()

        if not image_path:
            raise HTTPException(status_code=500, detail="Failed to capture image")

        # Read image bytes
        image_bytes = image_path.read_bytes()
        filename = image_path.name

        # Cleanup temp file
        camera_service.cleanup(image_path)

        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={"X-Image-Filename": filename}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Capture-image failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Capture failed: {str(e)}")


@router.post("/test-upload", response_model=Dict[str, Any])
async def test_upload() -> Dict[str, Any]:
    """
    Test connection to Server 2 without capturing new image.
    Uses existing fallback image if available.

    Returns:
        Dictionary with connection test results

    Raises:
        HTTPException: If test fails
    """
    logger.info("Upload test requested")

    try:
        # Test connection
        connected = upload_service.test_connection()

        if not connected:
            raise HTTPException(
                status_code=503,
                detail="Server 2 is not reachable"
            )

        return {
            "status": "success",
            "message": "Connection to Server 2 successful",
            "server2_url": settings.server2_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload test failed: {str(e)}"
        )


@router.post("/button-capture-predict", response_model=Dict[str, Any])
async def button_capture_and_predict() -> Dict[str, Any]:
    """
    Capture image and run inference in one step.
    Used by the GPIO button listener in inference mode.
    Captures locally, sends to the inference service, returns prediction.
    """
    logger.info("Button capture-and-predict triggered")

    try:
        image_path = camera_service.capture()
        if not image_path:
            raise HTTPException(status_code=500, detail="Failed to capture image")

        image_bytes = image_path.read_bytes()
        filename = image_path.name
        camera_service.cleanup(image_path)

        # Forward to inference service
        inference_url = settings.inference_url
        files = {"file": (filename, io.BytesIO(image_bytes), "image/jpeg")}
        r = http_requests.post(
            f"{inference_url}/api/v1/predict", files=files, timeout=60
        )
        r.raise_for_status()

        result = r.json()
        result["source"] = "button_capture"
        result["image_name"] = filename
        return result

    except HTTPException:
        raise
    except http_requests.RequestException as e:
        logger.error(f"Inference request failed: {e}")
        raise HTTPException(status_code=502, detail=f"Inference service error: {e}")
    except Exception as e:
        logger.error(f"Button capture-predict failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")
