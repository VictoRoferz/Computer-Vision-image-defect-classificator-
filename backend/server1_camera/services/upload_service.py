"""
Upload Service for Server 1 (Raspberry Pi 3)
Handles uploading captured images to Server 2 (Raspberry Pi 5)
Includes retry logic with exponential backoff
"""
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)


class UploadService:
    """
    Service for uploading images to Server 2.
    Implements retry logic for network resilience.
    """

    def __init__(self):
        self.upload_url = settings.server2_upload_url
        self.timeout = settings.upload_timeout
        self.max_retries = settings.upload_retries
        self.retry_delay = settings.upload_retry_delay

        logger.info(
            f"UploadService initialized: url={self.upload_url}, "
            f"retries={self.max_retries}, timeout={self.timeout}s"
        )

    def upload_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Upload image to Server 2 with retry logic.

        Args:
            image_path: Path to image file to upload

        Returns:
            Response dictionary from Server 2

        Raises:
            RuntimeError: If upload fails after all retries
            FileNotFoundError: If image file doesn't exist
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Get file size for logging
        file_size_kb = image_path.stat().st_size / 1024

        logger.info(
            f"Starting upload: {image_path.name} ({file_size_kb:.1f} KB) "
            f"to {self.upload_url}"
        )

        # Retry loop with exponential backoff
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response_data = self._attempt_upload(image_path, attempt)
                logger.info(
                    f"Upload successful on attempt {attempt}: "
                    f"{response_data.get('status', 'unknown')}"
                )
                return response_data

            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(
                    f"Upload attempt {attempt}/{self.max_retries} failed: {e}"
                )

                # Don't sleep after last attempt
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)

            except Exception as e:
                # Non-network errors shouldn't be retried
                logger.error(f"Upload failed with non-recoverable error: {e}", exc_info=True)
                raise RuntimeError(f"Upload failed: {e}") from e

        # All retries exhausted
        error_msg = (
            f"Upload failed after {self.max_retries} attempts. "
            f"Last error: {last_exception}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from last_exception

    def _attempt_upload(self, image_path: Path, attempt: int) -> Dict[str, Any]:
        """
        Single upload attempt.

        Args:
            image_path: Path to image file
            attempt: Current attempt number (for logging)

        Returns:
            Response dictionary from Server 2

        Raises:
            requests.exceptions.RequestException: On network/HTTP errors
        """
        with open(image_path, 'rb') as f:
            # Prepare multipart form data
            files = {
                'file': (
                    image_path.name,
                    f,
                    'image/jpeg'  # Assuming JPEG; adjust if needed
                )
            }

            # Send POST request
            logger.debug(f"Attempt {attempt}: Sending POST to {self.upload_url}")
            response = requests.post(
                self.upload_url,
                files=files,
                timeout=self.timeout
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            logger.debug(f"Response: {response_data}")

            return response_data

    def upload_and_cleanup(self, image_path: Path) -> Dict[str, Any]:
        """
        Upload image and cleanup local file if successful.

        Args:
            image_path: Path to image file

        Returns:
            Response dictionary from Server 2

        Raises:
            RuntimeError: If upload fails
        """
        try:
            # Upload
            response = self.upload_image(image_path)

            # Cleanup if configured
            if settings.cleanup_after_upload:
                self._cleanup_image(image_path)

            return response

        except Exception as e:
            logger.error(f"Upload and cleanup failed: {e}")
            raise

    def _cleanup_image(self, image_path: Path) -> None:
        """
        Delete local image file after successful upload.

        Args:
            image_path: Path to image file to delete
        """
        try:
            if image_path.exists():
                image_path.unlink()
                logger.debug(f"Cleaned up local image: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {image_path}: {e}")

    def test_connection(self) -> bool:
        """
        Test connection to Server 2.

        Returns:
            True if Server 2 is reachable, False otherwise
        """
        try:
            # Try to reach Server 2's health endpoint
            health_url = f"{settings.server2_url}/api/v1/health"
            response = requests.get(health_url, timeout=5)
            response.raise_for_status()

            logger.info(f"Connection test successful: {health_url}")
            return True

        except requests.exceptions.RequestException as e:
            logger.warning(f"Connection test failed: {e}")
            return False


# Global upload service instance
upload_service = UploadService()
