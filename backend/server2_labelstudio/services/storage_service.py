"""
Storage Service for Server 2 (Raspberry Pi 5)
Handles content-addressed storage for unlabeled and labeled images
Based on the main branch implementation with enhancements
"""
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)


class StorageService:
    """
    Service for managing image storage with content-addressed deduplication.
    Maintains separate databases for unlabeled and labeled images.
    """

    def __init__(self):
        self.unlabeled_dir = settings.unlabeled_dir
        self.labeled_dir = settings.labeled_dir
        self.use_content_addressing = settings.use_content_addressing

        logger.info(
            f"StorageService initialized: "
            f"unlabeled={self.unlabeled_dir}, "
            f"labeled={self.labeled_dir}, "
            f"content_addressing={self.use_content_addressing}"
        )

    def store_unlabeled_image(
        self,
        source_path: Path,
        filename: str
    ) -> Dict[str, Any]:
        """
        Store uploaded image in unlabeled database.

        Args:
            source_path: Path to temporary uploaded file
            filename: Original filename

        Returns:
            Dictionary with storage information

        Raises:
            ValueError: If file extension not allowed
            IOError: If storage operation fails
        """
        # Validate file extension
        ext = Path(filename).suffix.lower()
        if ext not in settings.allowed_extensions:
            raise ValueError(
                f"File extension {ext} not allowed. "
                f"Allowed: {settings.allowed_extensions}"
            )

        # Calculate SHA256 hash
        sha256 = self._calculate_sha256(source_path)
        logger.info(f"File hash: {sha256}")

        # Get destination path
        dest_path = settings.get_unlabeled_path(sha256, filename)

        # Check if already exists (deduplication)
        if dest_path.exists():
            logger.info(f"Image already exists: {dest_path}")
            # Clean up source
            if source_path.exists():
                source_path.unlink()

            return {
                "status": "already_stored",
                "sha256": sha256,
                "path": str(dest_path),
                "filename": filename,
                "size_bytes": dest_path.stat().st_size
            }

        # Create parent directories
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file to destination (atomic operation)
        try:
            shutil.move(str(source_path), str(dest_path))
            logger.info(f"Image stored: {dest_path}")

            return {
                "status": "stored",
                "sha256": sha256,
                "path": str(dest_path),
                "filename": filename,
                "size_bytes": dest_path.stat().st_size
            }

        except Exception as e:
            logger.error(f"Failed to store image: {e}", exc_info=True)
            raise IOError(f"Storage failed: {e}") from e

    def store_labeled_image(
        self,
        sha256: str,
        filename: str,
        annotation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store labeled image and its annotation.

        Args:
            sha256: SHA256 hash of the original image
            filename: Original filename
            annotation_data: Label Studio annotation data

        Returns:
            Dictionary with storage information

        Raises:
            FileNotFoundError: If source image not found in unlabeled dir
            IOError: If storage operation fails
        """
        # Find source image in unlabeled directory
        source_path = settings.get_unlabeled_path(sha256, filename)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Source image not found: {source_path}"
            )

        # Get destination paths
        dest_image_path = settings.get_labeled_path(sha256, filename)
        dest_annotation_path = settings.get_annotation_path(sha256, filename)

        # Check if already exists
        if dest_image_path.exists():
            logger.info(f"Labeled image already exists: {dest_image_path}")
            # Update annotation even if image exists
            self._save_annotation(dest_annotation_path, annotation_data)

            return {
                "status": "updated",
                "sha256": sha256,
                "image_path": str(dest_image_path),
                "annotation_path": str(dest_annotation_path),
                "filename": filename
            }

        # Copy image to labeled directory (keep original in unlabeled)
        try:
            shutil.copy2(str(source_path), str(dest_image_path))
            logger.info(f"Labeled image stored: {dest_image_path}")

            # Save annotation JSON
            self._save_annotation(dest_annotation_path, annotation_data)
            logger.info(f"Annotation stored: {dest_annotation_path}")

            return {
                "status": "stored",
                "sha256": sha256,
                "image_path": str(dest_image_path),
                "annotation_path": str(dest_annotation_path),
                "filename": filename,
                "size_bytes": dest_image_path.stat().st_size
            }

        except Exception as e:
            logger.error(f"Failed to store labeled image: {e}", exc_info=True)
            # Cleanup on failure
            if dest_image_path.exists():
                dest_image_path.unlink()
            if dest_annotation_path.exists():
                dest_annotation_path.unlink()
            raise IOError(f"Labeled storage failed: {e}") from e

    def _calculate_sha256(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal SHA256 hash string
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def _save_annotation(self, path: Path, data: Dict[str, Any]) -> None:
        """
        Save annotation data as JSON.

        Args:
            path: Path to save JSON file
            data: Annotation data dictionary
        """
        import json

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_unlabeled_images(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List unlabeled images.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of image information dictionaries
        """
        images = []

        # Find all image files
        for ext in settings.allowed_extensions:
            for image_path in self.unlabeled_dir.rglob(f"*{ext}"):
                if image_path.is_file():
                    images.append({
                        "filename": image_path.name,
                        "path": str(image_path),
                        "size_bytes": image_path.stat().st_size,
                        "modified": image_path.stat().st_mtime
                    })

        # Sort by modification time (newest first)
        images.sort(key=lambda x: x["modified"], reverse=True)

        # Apply offset and limit
        if limit:
            return images[offset:offset + limit]
        else:
            return images[offset:]

    def list_labeled_images(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List labeled images with their annotations.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of labeled image information dictionaries
        """
        images = []

        # Find all image files in labeled directory
        for ext in settings.allowed_extensions:
            for image_path in self.labeled_dir.glob(f"*{ext}"):
                if image_path.is_file():
                    # Check for corresponding annotation
                    annotation_path = image_path.with_suffix('.json')

                    images.append({
                        "filename": image_path.name,
                        "image_path": str(image_path),
                        "annotation_path": str(annotation_path) if annotation_path.exists() else None,
                        "has_annotation": annotation_path.exists(),
                        "size_bytes": image_path.stat().st_size,
                        "modified": image_path.stat().st_mtime
                    })

        # Sort by modification time (newest first)
        images.sort(key=lambda x: x["modified"], reverse=True)

        # Apply offset and limit
        if limit:
            return images[offset:offset + limit]
        else:
            return images[offset:]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        unlabeled_images = self.list_unlabeled_images()
        labeled_images = self.list_labeled_images()

        unlabeled_size = sum(img["size_bytes"] for img in unlabeled_images)
        labeled_size = sum(img["size_bytes"] for img in labeled_images)

        return {
            "unlabeled": {
                "count": len(unlabeled_images),
                "total_size_bytes": unlabeled_size,
                "total_size_mb": round(unlabeled_size / (1024 * 1024), 2)
            },
            "labeled": {
                "count": len(labeled_images),
                "total_size_bytes": labeled_size,
                "total_size_mb": round(labeled_size / (1024 * 1024), 2),
                "with_annotations": sum(1 for img in labeled_images if img["has_annotation"])
            },
            "total": {
                "images": len(unlabeled_images) + len(labeled_images),
                "size_mb": round((unlabeled_size + labeled_size) / (1024 * 1024), 2)
            }
        }


# Global storage service instance
storage_service = StorageService()
