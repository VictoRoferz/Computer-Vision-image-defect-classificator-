"""Camera service for capturing images.

Handles image capture from camera or fallback to sample images.
"""

import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from ..config import Settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CameraService:
    """Service for capturing images from camera or fallback sources.

    This service provides:
    - Camera capture (if available)
    - Fallback to sample images (for simulation)
    - Image timestamping and naming
    """

    def __init__(self, settings: Settings):
        """Initialize camera service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.camera = None

        if settings.USE_CAMERA:
            self._init_camera()

    def _init_camera(self) -> None:
        """Initialize camera (OpenCV).

        Falls back to sample images if camera is not available.
        """
        try:
            import cv2
            self.camera = cv2.VideoCapture(self.settings.CAMERA_INDEX)

            if not self.camera.isOpened():
                logger.warning(
                    f"Camera {self.settings.CAMERA_INDEX} could not be opened. "
                    "Falling back to sample images."
                )
                self.camera = None
            else:
                logger.info(f"Camera {self.settings.CAMERA_INDEX} initialized successfully")

        except ImportError:
            logger.warning("OpenCV not available. Falling back to sample images.")
            self.camera = None
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            self.camera = None

    def capture_image(self) -> Optional[Tuple[Path, str]]:
        """Capture an image from camera or use fallback.

        Returns:
            Tuple of (image_path, mime_type) or None if capture failed

        Raises:
            RuntimeError: If capture fails and no fallback available
        """
        if self.camera:
            return self._capture_from_camera()
        else:
            return self._get_fallback_image()

    def _capture_from_camera(self) -> Optional[Tuple[Path, str]]:
        """Capture image from camera using OpenCV.

        Returns:
            Tuple of (image_path, mime_type) or None if failed
        """
        try:
            import cv2

            ret, frame = self.camera.read()
            if not ret:
                logger.warning("Failed to capture frame from camera")
                return None

            # Generate timestamped filename
            timestamp = datetime.now().strftime("%d%m%Y_%H-%M-%S")
            filename = f"pcb_{timestamp}.jpg"
            output_path = self.settings.OUTPUT_DIR / filename

            # Save image
            cv2.imwrite(str(output_path), frame)
            logger.info(f"Captured image from camera: {output_path}")

            return output_path, "image/jpeg"

        except Exception as e:
            logger.error(f"Error capturing from camera: {e}")
            return None

    def _get_fallback_image(self) -> Optional[Tuple[Path, str]]:
        """Get a random sample image as fallback.

        Returns:
            Tuple of (image_path, mime_type) or None if no samples available
        """
        # Look for sample images in fallback directory
        sample_images = list(self.settings.FALLBACK_IMAGE_DIR.glob("*.jpg"))
        sample_images.extend(self.settings.FALLBACK_IMAGE_DIR.glob("*.jpeg"))
        sample_images.extend(self.settings.FALLBACK_IMAGE_DIR.glob("*.png"))

        if not sample_images:
            logger.error(f"No sample images found in {self.settings.FALLBACK_IMAGE_DIR}")
            return None

        # Select random sample
        sample_path = random.choice(sample_images)
        logger.info(f"Using fallback image: {sample_path}")

        # Determine mime type
        mime_type = "image/jpeg"
        if sample_path.suffix.lower() == ".png":
            mime_type = "image/png"

        return sample_path, mime_type

    def release(self) -> None:
        """Release camera resources."""
        if self.camera:
            self.camera.release()
            logger.info("Camera resources released")
