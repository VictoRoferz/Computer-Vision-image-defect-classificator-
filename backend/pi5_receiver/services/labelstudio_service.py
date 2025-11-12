"""Label Studio integration service.

Handles all interactions with Label Studio including:
- Project initialization
- Task creation
- Annotation export
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests

from label_studio_sdk import Client as LabelStudioClient
from label_studio_sdk.label_interface import LabelInterface
from label_studio_sdk.label_interface.objects import PredictionValue

from ..config import Settings
from ..database import DatabaseRepository, ImageStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LabelStudioService:
    """Service for managing Label Studio integration.

    This service handles:
    - Project setup and configuration
    - Creating tasks from new images
    - Exporting completed annotations
    """

    def __init__(self, settings: Settings, db_repo: DatabaseRepository):
        """Initialize Label Studio service.

        Args:
            settings: Application settings
            db_repo: Database repository instance
        """
        self.settings = settings
        self.db_repo = db_repo
        self.client: Optional[LabelStudioClient] = None
        self.project_id: Optional[int] = settings.LABEL_STUDIO_PROJECT_ID

        if settings.LABEL_STUDIO_API_KEY:
            self._init_client()

    def _init_client(self) -> None:
        """Initialize Label Studio SDK client with retry logic."""
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.client = LabelStudioClient(
                    url=self.settings.LABEL_STUDIO_URL,
                    api_key=self.settings.LABEL_STUDIO_API_KEY
                )
                # Test connection
                self.client.check_connection()
                logger.info("Connected to Label Studio successfully")
                return
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} to connect to "
                    f"Label Studio failed: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Failed to connect to Label Studio after all retries")
                    raise

    def ensure_project_exists(self) -> int:
        """Ensure Label Studio project exists, create if not.

        Returns:
            int: Project ID

        Raises:
            RuntimeError: If project cannot be created or found
        """
        if not self.client:
            raise RuntimeError("Label Studio client not initialized")

        # If project ID is set, verify it exists
        if self.project_id:
            try:
                project = self.client.get_project(self.project_id)
                logger.info(f"Using existing project: {project.title} (ID: {self.project_id})")
                return self.project_id
            except Exception as e:
                logger.warning(f"Project {self.project_id} not found: {e}")

        # Search for project by name
        try:
            projects = self.client.list_projects()
            for project in projects:
                if project.title == self.settings.LABEL_STUDIO_PROJECT_NAME:
                    self.project_id = project.id
                    logger.info(f"Found existing project: {project.title} (ID: {self.project_id})")
                    return self.project_id
        except Exception as e:
            logger.warning(f"Error listing projects: {e}")

        # Create new project
        logger.info(f"Creating new project: {self.settings.LABEL_STUDIO_PROJECT_NAME}")
        project = self._create_project()
        self.project_id = project.id
        return self.project_id

    def _create_project(self):
        """Create a new Label Studio project for PCB defect classification.

        Returns:
            Project object
        """
        # Label config for brush-based segmentation with defect classification
        label_config = """
        <View>
          <Header value="PCB Defect Classification"/>
          <Image name="image" value="$image" zoom="true" zoomControl="true"/>

          <BrushLabels name="defects" toName="image">
            <Label value="Solder Bridge" background="#FF0000"/>
            <Label value="Insufficient Solder" background="#FFA500"/>
            <Label value="Cold Joint" background="#FFFF00"/>
            <Label value="Component Damage" background="#00FF00"/>
            <Label value="Missing Component" background="#0000FF"/>
            <Label value="Wrong Component" background="#FF00FF"/>
            <Label value="Misalignment" background="#00FFFF"/>
            <Label value="Contamination" background="#808080"/>
            <Label value="Other Defect" background="#000000"/>
            <Label value="Good" background="#90EE90"/>
          </BrushLabels>

          <Choices name="overall_quality" toName="image" choice="single">
            <Choice value="Pass"/>
            <Choice value="Fail"/>
            <Choice value="Needs Review"/>
          </Choices>

          <TextArea name="notes" toName="image" placeholder="Additional notes..." rows="3"/>
        </View>
        """

        project = self.client.create_project(
            title=self.settings.LABEL_STUDIO_PROJECT_NAME,
            label_config=label_config,
            description="PCB joint image defect classification using brush annotations"
        )

        logger.info(f"Created project: {project.title} (ID: {project.id})")
        return project

    def create_task_for_image(self, sha256: str) -> Optional[Dict[str, Any]]:
        """Create a Label Studio task for an image.

        Args:
            sha256: SHA256 hash of the image

        Returns:
            Dict with task information, or None if failed

        Raises:
            RuntimeError: If Label Studio client not initialized
        """
        if not self.client:
            raise RuntimeError("Label Studio client not initialized")

        # Get image record
        record = self.db_repo.get_by_sha256(sha256)
        if not record:
            logger.error(f"Image with SHA256 {sha256} not found in database")
            return None

        # Ensure project exists
        if not self.project_id:
            self.ensure_project_exists()

        try:
            # Construct file path relative to Label Studio's data root
            # Label Studio expects paths relative to LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT
            image_path = Path(record.file_path)

            # The path should be relative to /labelstudio/data
            # Format: /data/local-files/?d=images/unlabeled/xx/yy/hash/filename.jpg
            relative_path = str(image_path.relative_to(self.settings.IMAGES_UNLABELED.parent))

            task_data = {
                "image": f"/data/local-files/?d={relative_path}"
            }

            # Create task
            project = self.client.get_project(self.project_id)
            task = project.create_task(task_data)

            # Update database record
            self.db_repo.update_status(
                sha256,
                ImageStatus.SENT_TO_LABELSTUDIO,
                sent_to_ls_at=datetime.now(),
                labelstudio_task_id=task["id"]
            )

            logger.info(
                f"Created Label Studio task {task['id']} for image {record.filename}"
            )

            return task

        except Exception as e:
            logger.error(f"Error creating Label Studio task: {e}")
            self.db_repo.update_status(
                sha256,
                ImageStatus.ERROR,
                error_message=str(e)
            )
            return None

    def get_completed_annotations(self) -> List[Dict[str, Any]]:
        """Get all completed annotations from Label Studio.

        Returns:
            List of completed tasks with annotations
        """
        if not self.client or not self.project_id:
            logger.warning("Cannot fetch annotations: client or project not initialized")
            return []

        try:
            project = self.client.get_project(self.project_id)

            # Get all tasks
            tasks = project.get_tasks()

            # Filter completed tasks (those with annotations)
            completed = [
                task for task in tasks
                if task.get("annotations") and len(task["annotations"]) > 0
            ]

            logger.info(f"Found {len(completed)} completed annotations")
            return completed

        except Exception as e:
            logger.error(f"Error fetching completed annotations: {e}")
            return []

    def export_annotation(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Export a specific annotation.

        Args:
            task_id: Label Studio task ID

        Returns:
            Dict with annotation data, or None if failed
        """
        if not self.client or not self.project_id:
            return None

        try:
            project = self.client.get_project(self.project_id)
            task = project.get_task(task_id)

            if not task.get("annotations"):
                logger.warning(f"Task {task_id} has no annotations")
                return None

            logger.info(f"Exported annotation for task {task_id}")
            return task

        except Exception as e:
            logger.error(f"Error exporting annotation for task {task_id}: {e}")
            return None

    def health_check(self) -> bool:
        """Check if Label Studio is reachable.

        Returns:
            bool: True if Label Studio is healthy
        """
        try:
            if self.client:
                self.client.check_connection()
                return True
        except Exception as e:
            logger.error(f"Label Studio health check failed: {e}")

        return False
