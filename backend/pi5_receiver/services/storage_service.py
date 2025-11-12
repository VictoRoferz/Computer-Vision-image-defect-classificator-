"""Storage service for managing image files.

Handles file storage operations including:
- Saving uploaded images
- Content-addressed storage (deduplication)
- Moving labeled images to separate directory
"""

import shutil
from pathlib import Path
from typing import Tuple, BinaryIO, Optional

from ..config import Settings
from ..database import DatabaseRepository, ImageRecord, ImageStatus
from ..utils.helpers import calculate_sha256, create_shard_path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """Service for managing image file storage operations.

    This service handles:
    - Storing uploaded images in content-addressed storage
    - Deduplication using SHA256 hashing
    - Moving images between unlabeled and labeled directories
    """

    def __init__(self, settings: Settings, db_repo: DatabaseRepository):
        """Initialize storage service.

        Args:
            settings: Application settings
            db_repo: Database repository instance
        """
        self.settings = settings
        self.db_repo = db_repo

    def save_uploaded_image(
        self,
        file_stream: BinaryIO,
        filename: str
    ) -> Tuple[ImageRecord, bool]:
        """Save an uploaded image to storage.

        Args:
            file_stream: Binary stream of the uploaded file
            filename: Original filename

        Returns:
            Tuple of (ImageRecord, is_duplicate)
            - ImageRecord: Database record for the image
            - is_duplicate: True if image already existed (deduplicated)

        Raises:
            IOError: If file cannot be saved
        """
        # Create temporary file to calculate hash
        temp_dir = self.settings.DATA_ROOT / "__incoming__"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / filename

        try:
            # Write uploaded file to temp location
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(file_stream, f)

            # Calculate SHA256 hash
            sha256 = calculate_sha256(temp_path)
            logger.info(f"Calculated SHA256: {sha256} for {filename}")

            # Check if image already exists
            existing_record = self.db_repo.get_by_sha256(sha256)
            if existing_record:
                logger.info(f"Duplicate image detected: {sha256}")
                temp_path.unlink(missing_ok=True)
                return existing_record, True

            # Create content-addressed path
            dest_path = create_shard_path(
                self.settings.IMAGES_UNLABELED,
                sha256,
                filename
            )
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file to final location (atomic operation)
            shutil.move(str(temp_path), str(dest_path))
            logger.info(f"Saved image to: {dest_path}")

            # Create database record
            record = ImageRecord(
                filename=filename,
                sha256=sha256,
                file_path=str(dest_path),
                status=ImageStatus.RECEIVED
            )
            record = self.db_repo.create(record)

            return record, False

        except Exception as e:
            logger.error(f"Error saving image: {e}")
            temp_path.unlink(missing_ok=True)
            raise

    def move_to_labeled(
        self,
        sha256: str,
        annotations_filename: Optional[str] = None
    ) -> Optional[Path]:
        """Move an image from unlabeled to labeled directory.

        Args:
            sha256: SHA256 hash of the image
            annotations_filename: Optional filename for annotations file

        Returns:
            Path: New path in labeled directory, or None if not found

        Raises:
            FileNotFoundError: If source image doesn't exist
            IOError: If file cannot be moved
        """
        record = self.db_repo.get_by_sha256(sha256)
        if not record:
            logger.warning(f"Cannot move: Image with SHA256 {sha256} not found")
            return None

        source_path = Path(record.file_path)
        if not source_path.exists():
            logger.error(f"Source file not found: {source_path}")
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Create destination path in labeled directory
        dest_path = create_shard_path(
            self.settings.IMAGES_LABELED,
            sha256,
            record.filename
        )
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy (not move) to preserve original
        shutil.copy2(str(source_path), str(dest_path))
        logger.info(f"Copied labeled image to: {dest_path}")

        # If annotations file provided, save it alongside
        if annotations_filename:
            annotations_dest = dest_path.parent / annotations_filename
            # Note: Actual annotations content would be provided by caller
            logger.info(f"Annotations would be saved to: {annotations_dest}")

        return dest_path

    def get_image_path(self, sha256: str) -> Optional[Path]:
        """Get the file system path for an image by SHA256.

        Args:
            sha256: SHA256 hash

        Returns:
            Path if found, None otherwise
        """
        record = self.db_repo.get_by_sha256(sha256)
        if record:
            return Path(record.file_path)
        return None

    def cleanup_temp_files(self) -> int:
        """Clean up temporary files in the incoming directory.

        Returns:
            int: Number of files cleaned up
        """
        temp_dir = self.settings.DATA_ROOT / "__incoming__"
        if not temp_dir.exists():
            return 0

        count = 0
        for temp_file in temp_dir.iterdir():
            if temp_file.is_file():
                temp_file.unlink()
                count += 1

        logger.info(f"Cleaned up {count} temporary files")
        return count
