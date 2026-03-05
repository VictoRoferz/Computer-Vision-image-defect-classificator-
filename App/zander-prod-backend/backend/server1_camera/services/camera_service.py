"""
Camera Service for Server 1 (Camera Service)
Handles image capture from camera or fallback image.
Supports: laptop webcam (MacBook), USB cameras, or fallback test image.
"""
import cv2
from pathlib import Path
from datetime import datetime
from typing import Optional
from config.settings import settings
from utils.logger import setup_logger


logger = setup_logger(__name__, level=settings.log_level)


class CameraService:
    """
    Service for capturing images from camera or fallback source.
    Works with laptop webcam (USE_CAMERA=true) or generates test images (USE_CAMERA=false).
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
        Works with laptop webcam (index 0) or external USB cameras.
        """
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_index)

            if not cap.isOpened():
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return None

            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.camera_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_height)
            cap.set(cv2.CAP_PROP_FPS, settings.camera_fps)

            # Allow camera to warm up (important for webcams)
            for _ in range(5):
                cap.read()

            ret, frame = cap.read()

            if not ret or frame is None:
                logger.error("Failed to capture frame from camera")
                return None

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"capture_{timestamp}.jpg"
            image_path = self.temp_dir / filename

            # Save as JPEG (high quality for defect detection)
            success = cv2.imwrite(
                str(image_path),
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 95]
            )

            if not success:
                logger.error(f"Failed to save image to {image_path}")
                return None

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
            if cap is not None:
                cap.release()
                logger.debug("Camera released")

    def _use_fallback(self) -> Path:
        """
        Use fallback image for testing without camera.
        Creates a test image if none exists.
        """
        if not self.fallback_path.exists():
            logger.warning(
                f"Fallback image not found at {self.fallback_path}, "
                "creating test image"
            )
            self._create_test_image()

        if not self.fallback_path.exists():
            raise RuntimeError(
                f"Fallback image not available at {self.fallback_path}"
            )

        # Copy fallback to temp dir with unique name so uploads don't conflict
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"capture_{timestamp}.jpg"
        dest = self.temp_dir / filename

        import shutil
        shutil.copy2(str(self.fallback_path), str(dest))

        logger.info(f"Using fallback image: {self.fallback_path} -> {dest}")
        return dest

    def _create_test_image(self) -> None:
        """
        Create a minimal test image for development/testing.
        Simulates a PCB board appearance.
        """
        try:
            import numpy as np

            width, height = 1920, 1080
            image = np.zeros((height, width, 3), dtype=np.uint8)

            # Dark green background (simulating PCB)
            image[:] = (20, 40, 20)

            # Add some rectangles to simulate components
            cv2.rectangle(image, (200, 200), (400, 350), (60, 60, 60), -1)
            cv2.rectangle(image, (500, 300), (800, 450), (50, 50, 80), -1)
            cv2.rectangle(image, (1000, 400), (1200, 550), (40, 70, 40), -1)
            cv2.rectangle(image, (1400, 200), (1700, 400), (70, 50, 50), -1)

            # Add text
            text = f"PCB TEST IMAGE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(image, text, (50, height - 50), font, 1.5, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.imwrite(str(self.fallback_path), image)
            logger.info(f"Created test image at {self.fallback_path}")

        except Exception as e:
            logger.error(f"Failed to create test image: {e}", exc_info=True)

    def capture_bytes(self) -> Optional[bytes]:
        """
        Capture image and return as bytes (useful for direct inference).
        """
        image_path = self.capture()
        if image_path is None:
            return None
        try:
            with open(image_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read captured image: {e}")
            return None

    def cleanup(self, image_path: Path) -> None:
        """Clean up temporary captured image."""
        try:
            if image_path.exists() and image_path.parent == self.temp_dir:
                image_path.unlink()
                logger.debug(f"Cleaned up temporary image: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {image_path}: {e}")

    def get_status(self) -> dict:
        """Get camera service status."""
        status = {
            "use_camera": self.use_camera,
            "camera_index": self.camera_index,
            "fallback_available": self.fallback_path.exists(),
            "temp_dir": str(self.temp_dir),
            "temp_dir_exists": self.temp_dir.exists(),
        }

        if self.use_camera:
            try:
                cap = cv2.VideoCapture(self.camera_index)
                status["camera_available"] = cap.isOpened()
                cap.release()
            except Exception:
                status["camera_available"] = False

        return status


# Global camera service instance
camera_service = CameraService()
