"""Watcher service for monitoring directory for new images.

Monitors a directory for new images and triggers sending them.
"""

import time
from pathlib import Path
from typing import Set

from ..config import Settings
from ..services.sender_service import SenderService
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WatcherService:
    """Service for watching directory for new images.

    This service:
    - Monitors a directory for new images
    - Automatically sends new images to PI5 Receiver
    - Tracks processed images to avoid duplicates
    """

    def __init__(self, settings: Settings, sender_service: SenderService):
        """Initialize watcher service.

        Args:
            settings: Application settings
            sender_service: Sender service instance
        """
        self.settings = settings
        self.sender_service = sender_service
        self.processed_files: Set[str] = set()
        self.running = False

    def start(self) -> None:
        """Start watching the directory.

        Runs in a continuous loop, checking for new images.
        """
        self.running = True
        logger.info(f"Starting directory watcher: {self.settings.WATCH_DIR}")

        # Process any existing files first
        self._process_existing_files()

        while self.running:
            try:
                self._check_for_new_images()
            except Exception as e:
                logger.error(f"Error in watcher loop: {e}")

            time.sleep(self.settings.WATCH_INTERVAL)

    def stop(self) -> None:
        """Stop the watcher service."""
        logger.info("Stopping directory watcher")
        self.running = False

    def _process_existing_files(self) -> None:
        """Process any existing files in the watch directory."""
        existing_files = self._get_image_files()

        if existing_files:
            logger.info(f"Found {len(existing_files)} existing images to process")

            for image_path in existing_files:
                self._process_image(image_path)

    def _check_for_new_images(self) -> None:
        """Check for new images in the watch directory."""
        current_files = self._get_image_files()

        for image_path in current_files:
            file_key = str(image_path.absolute())

            if file_key not in self.processed_files:
                logger.info(f"New image detected: {image_path.name}")
                self._process_image(image_path)

    def _process_image(self, image_path: Path) -> None:
        """Process a single image file.

        Args:
            image_path: Path to the image file
        """
        file_key = str(image_path.absolute())

        try:
            # Determine mime type
            mime_type = "image/jpeg"
            if image_path.suffix.lower() == ".png":
                mime_type = "image/png"

            # Send image
            result = self.sender_service.send_image(image_path, mime_type)

            if result:
                # Mark as processed
                self.processed_files.add(file_key)
                logger.info(f"Successfully processed {image_path.name}")

                # Optionally delete or move the file
                # For now, we just mark it as processed
            else:
                logger.error(f"Failed to process {image_path.name}")

        except Exception as e:
            logger.error(f"Error processing {image_path.name}: {e}")

    def _get_image_files(self) -> list[Path]:
        """Get all image files in the watch directory.

        Returns:
            List of image file paths
        """
        image_files = []

        if not self.settings.WATCH_DIR.exists():
            logger.warning(f"Watch directory does not exist: {self.settings.WATCH_DIR}")
            return image_files

        # Supported image formats
        for pattern in ["*.jpg", "*.jpeg", "*.png", "*.bmp"]:
            image_files.extend(self.settings.WATCH_DIR.glob(pattern))

        return sorted(image_files)
