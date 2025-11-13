"""
Camera Service for Server 1 (Raspberry Pi 3)
Handles image capture from camera or fallback image
Optimized for low-power embedded systems
"""
import cv2
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)


class CameraService:
    """
    Service for capturing images from camera or fallback source.
    Designed to be memory-efficient for Raspberry Pi 3.
    """

    def __init__(self):
        self.use_camera = settings.use_camera
        self.camera_index = settings.camera_index
        self.fallback_path = Path(settings.fallback_image_path)
        self.temp_dir = settings.temp_dir

        logger.info(
            f"CameraService initialized: use_camera={self.use_camera}, "
            f"index={self.camera_index}"
        )

    def capture(self) -> Optional[Path]:
        """
        Capture image from camera or use fallback.

        Returns:
            Path to captured image, or None if capture failed

        Raises:
            RuntimeError: If capture fails and no fallback available
        """
        if self.use_camera:
            image_path = self._capture_from_camera()
            if image_path:
                logger.info(f"Image captured from camera: {image_path}")
                return image_path
            else:
                logger.warning("Camera capture failed, falling back to sample image")
                return self._use_fallback()
        else:
            logger.info("Camera disabled, using fallback image")
            return self._use_fallback()

    def _capture_from_camera(self) -> Optional[Path]:
        """
        Capture image from camera using OpenCV.

        Returns:
            Path to captured image, or None if failed
        """
        cap = None
        try:
            # Open camera
            cap = cv2.VideoCapture(self.camera_index)

            if not cap.isOpened():
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return None

            # Set resolution (if supported by camera)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.camera_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_height)
            cap.set(cv2.CAP_PROP_FPS, settings.camera_fps)

            # Capture frame
            ret, frame = cap.read()

            if not ret or frame is None:
                logger.error("Failed to capture frame from camera")
                return None

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"capture_{timestamp}.jpg"
            image_path = self.temp_dir / filename

            # Save image as JPEG (space-efficient for PCB images)
            success = cv2.imwrite(
                str(image_path),
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 95]  # High quality for defect detection
            )

            if not success:
                logger.error(f"Failed to save image to {image_path}")
                return None

            # Get actual dimensions
            height, width = frame.shape[:2]
            logger.debug(
                f"Captured {width}x{height} image, size: "
                f"{image_path.stat().st_size / 1024:.1f} KB"
            )

            return image_path

        except Exception as e:
            logger.error(f"Camera capture exception: {e}", exc_info=True)
            return None

        finally:
            # Always release camera resource
            if cap is not None:
                cap.release()
                logger.debug("Camera released")

    def _use_fallback(self) -> Path:
        """
        Use fallback image for testing without camera.

        Returns:
            Path to fallback image

        Raises:
            RuntimeError: If fallback image doesn't exist and can't be created
        """
        if not self.fallback_path.exists():
            # Create a minimal test image if fallback doesn't exist
            logger.warning(
                f"Fallback image not found at {self.fallback_path}, "
                "creating test image"
            )
            self._create_test_image()

        if not self.fallback_path.exists():
            raise RuntimeError(
                f"Fallback image not available at {self.fallback_path}"
            )

        logger.info(f"Using fallback image: {self.fallback_path}")
        return self.fallback_path

    def _create_test_image(self) -> None:
        """
        Create a minimal test image for development/testing.
        Creates a simple colored rectangle with text.
        """
        try:
            import numpy as np

            # Create 1920x1080 test image (typical PCB inspection resolution)
            width, height = 1920, 1080
            image = np.zeros((height, width, 3), dtype=np.uint8)

            # Dark background (simulating PCB)
            image[:] = (20, 40, 20)  # BGR: dark greenish

            # Add text
            text = f"TEST IMAGE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(
                image,
                text,
                (50, height // 2),
                font,
                2,
                (255, 255, 255),
                3,
                cv2.LINE_AA
            )

            # Save
            cv2.imwrite(str(self.fallback_path), image)
            logger.info(f"Created test image at {self.fallback_path}")

        except Exception as e:
            logger.error(f"Failed to create test image: {e}", exc_info=True)

    def cleanup(self, image_path: Path) -> None:
        """
        Clean up temporary captured image.

        Args:
            image_path: Path to image file to delete
        """
        try:
            if image_path.exists() and image_path.parent == self.temp_dir:
                image_path.unlink()
                logger.debug(f"Cleaned up temporary image: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {image_path}: {e}")

    def get_status(self) -> dict:
        """
        Get camera service status.

        Returns:
            Dictionary with camera status information
        """
        status = {
            "use_camera": self.use_camera,
            "camera_index": self.camera_index,
            "fallback_available": self.fallback_path.exists(),
            "temp_dir": str(self.temp_dir),
            "temp_dir_exists": self.temp_dir.exists(),
        }

        # Test camera availability if enabled
        if self.use_camera:
            cap = cv2.VideoCapture(self.camera_index)
            status["camera_available"] = cap.isOpened()
            cap.release()

        return status


# Global camera service instance
camera_service = CameraService()
