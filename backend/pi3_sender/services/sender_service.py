"""Sender service for uploading images to PI5 Receiver.

Handles HTTP file uploads with retry logic.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from ..config import Settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SenderService:
    """Service for sending images to PI5 Receiver.

    This service provides:
    - HTTP file upload
    - Retry logic with exponential backoff
    - Error handling and logging
    """

    def __init__(self, settings: Settings):
        """Initialize sender service.

        Args:
            settings: Application settings
        """
        self.settings = settings

    def send_image(
        self,
        image_path: Path,
        mime_type: str = "image/jpeg"
    ) -> Optional[Dict[str, Any]]:
        """Send an image to the PI5 Receiver service.

        Args:
            image_path: Path to the image file
            mime_type: MIME type of the image

        Returns:
            Dict with response data, or None if all retries failed

        Raises:
            FileNotFoundError: If image file doesn't exist
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        logger.info(f"Sending image {image_path.name} to {self.settings.UPLOAD_URL}")

        for attempt in range(self.settings.RETRY_ATTEMPTS):
            try:
                with open(image_path, "rb") as f:
                    files = {
                        "file": (image_path.name, f, mime_type)
                    }

                    response = requests.post(
                        self.settings.UPLOAD_URL,
                        files=files,
                        timeout=self.settings.UPLOAD_TIMEOUT
                    )

                    response.raise_for_status()
                    result = response.json()

                    logger.info(
                        f"Successfully uploaded {image_path.name}: "
                        f"Status={result.get('status')}, "
                        f"SHA256={result.get('sha256', 'N/A')[:8]}..."
                    )

                    return result

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Upload timeout (attempt {attempt + 1}/{self.settings.RETRY_ATTEMPTS})"
                )
            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"Connection error (attempt {attempt + 1}/{self.settings.RETRY_ATTEMPTS}): {e}"
                )
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error during upload: {e}")
                return None  # Don't retry on HTTP errors
            except Exception as e:
                logger.error(f"Unexpected error during upload: {e}")
                return None

            # Exponential backoff before retry
            if attempt < self.settings.RETRY_ATTEMPTS - 1:
                delay = self.settings.RETRY_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)

        logger.error(f"Failed to upload {image_path.name} after all retries")
        return None

    def health_check(self) -> bool:
        """Check if the PI5 Receiver service is reachable.

        Returns:
            bool: True if service is reachable
        """
        try:
            # Try to reach the health endpoint
            health_url = self.settings.UPLOAD_URL.replace("/upload", "/health")
            response = requests.get(health_url, timeout=5)
            response.raise_for_status()

            logger.info("PI5 Receiver service is reachable")
            return True

        except Exception as e:
            logger.warning(f"PI5 Receiver health check failed: {e}")
            return False
