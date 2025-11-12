"""Completion watcher service for monitoring Label Studio annotations.

Monitors Label Studio for completed annotations and processes them.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import Settings
from ..database import DatabaseRepository, ImageStatus
from ..services.labelstudio_service import LabelStudioService
from ..services.storage_service import StorageService
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CompletionWatcherService:
    """Service for watching Label Studio for completed annotations.

    This service:
    - Polls Label Studio for completed tasks
    - Exports annotations
    - Moves labeled images to the labeled directory
    - Updates database records
    """

    def __init__(
        self,
        settings: Settings,
        db_repo: DatabaseRepository,
        ls_service: LabelStudioService,
        storage_service: StorageService
    ):
        """Initialize completion watcher service.

        Args:
            settings: Application settings
            db_repo: Database repository instance
            ls_service: Label Studio service instance
            storage_service: Storage service instance
        """
        self.settings = settings
        self.db_repo = db_repo
        self.ls_service = ls_service
        self.storage_service = storage_service
        self.running = False

    async def start(self) -> None:
        """Start the watcher service.

        Runs in a continuous loop, polling Label Studio for completed tasks.
        """
        if not self.settings.WATCHER_ENABLED:
            logger.info("Watcher service disabled in configuration")
            return

        self.running = True
        logger.info(
            f"Starting completion watcher "
            f"(poll interval: {self.settings.WATCHER_POLL_INTERVAL}s)"
        )

        while self.running:
            try:
                await self._check_for_completed_tasks()
            except Exception as e:
                logger.error(f"Error in watcher loop: {e}")

            # Wait before next poll
            await asyncio.sleep(self.settings.WATCHER_POLL_INTERVAL)

    def stop(self) -> None:
        """Stop the watcher service."""
        logger.info("Stopping completion watcher")
        self.running = False

    async def _check_for_completed_tasks(self) -> None:
        """Check Label Studio for completed tasks and process them."""
        try:
            # Get completed annotations from Label Studio
            completed_tasks = self.ls_service.get_completed_annotations()

            if not completed_tasks:
                return

            logger.info(f"Processing {len(completed_tasks)} completed tasks")

            for task in completed_tasks:
                await self._process_completed_task(task)

        except Exception as e:
            logger.error(f"Error checking for completed tasks: {e}")

    async def _process_completed_task(self, task: dict) -> None:
        """Process a single completed task.

        Args:
            task: Task data from Label Studio
        """
        task_id = task.get("id")

        try:
            # Find corresponding image record by task_id
            records = self.db_repo.get_by_status(ImageStatus.SENT_TO_LABELSTUDIO)
            matching_record = None

            for record in records:
                if record.labelstudio_task_id == task_id:
                    matching_record = record
                    break

            if not matching_record:
                logger.warning(f"No matching image record for task {task_id}")
                return

            # Check if already processed
            if matching_record.status == ImageStatus.LABELED:
                logger.debug(f"Task {task_id} already processed")
                return

            logger.info(f"Processing completed task {task_id} for image {matching_record.filename}")

            # Extract annotations
            annotations = task.get("annotations", [])
            if not annotations:
                logger.warning(f"Task {task_id} has no annotations")
                return

            # Save annotations to file
            annotations_file = self._save_annotations(matching_record.sha256, annotations)

            # Move image to labeled directory
            labeled_path = self.storage_service.move_to_labeled(
                matching_record.sha256,
                annotations_filename=annotations_file.name if annotations_file else None
            )

            # Update database
            self.db_repo.update_status(
                matching_record.sha256,
                ImageStatus.LABELED,
                labeled_at=datetime.now()
            )

            logger.info(
                f"Successfully processed completed annotation for "
                f"{matching_record.filename} (moved to {labeled_path})"
            )

        except Exception as e:
            logger.error(f"Error processing completed task {task_id}: {e}")

            # Update record with error
            if matching_record:
                self.db_repo.update_status(
                    matching_record.sha256,
                    ImageStatus.ERROR,
                    error_message=f"Error processing completion: {str(e)}"
                )

    def _save_annotations(self, sha256: str, annotations: list) -> Optional[Path]:
        """Save annotations to JSON file.

        Args:
            sha256: SHA256 hash of the image
            annotations: List of annotation data

        Returns:
            Path to saved annotations file, or None if failed
        """
        try:
            # Create annotations directory in labeled images
            annotations_dir = self.settings.IMAGES_LABELED / "annotations"
            annotations_dir.mkdir(parents=True, exist_ok=True)

            # Save as JSON
            annotations_file = annotations_dir / f"{sha256}.json"

            with open(annotations_file, "w") as f:
                json.dump(annotations, f, indent=2)

            logger.info(f"Saved annotations to {annotations_file}")
            return annotations_file

        except Exception as e:
            logger.error(f"Error saving annotations for {sha256}: {e}")
            return None

    async def process_pending_images(self) -> None:
        """Process any images that haven't been sent to Label Studio yet.

        This is useful for batch processing or recovering from errors.
        """
        try:
            pending_records = self.db_repo.get_by_status(ImageStatus.RECEIVED)

            if not pending_records:
                logger.debug("No pending images to process")
                return

            logger.info(f"Processing {len(pending_records)} pending images")

            for record in pending_records:
                try:
                    self.ls_service.create_task_for_image(record.sha256)
                    logger.info(f"Created task for pending image: {record.filename}")

                    # Small delay to avoid overwhelming Label Studio
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error processing pending image {record.filename}: {e}")

        except Exception as e:
            logger.error(f"Error in process_pending_images: {e}")
