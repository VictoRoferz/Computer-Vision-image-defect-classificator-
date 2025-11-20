"""
Label Studio Service for Server 2 (Raspberry Pi 5)
Handles Label Studio API interactions, project setup, and task management
"""
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from label_studio_sdk import Client
from ..config.settings import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__, level=settings.log_level)


# PCB defect classification labeling interface configuration
LABELING_CONFIG = """
<View>
  <Header value="PCB Joint Defect Classification"/>
  <Image name="image" value="$image" zoom="true" zoomControl="true" rotateControl="true"/>

  <BrushLabels name="defects" toName="image">
    <Label value="Good Joint" background="#2ECC40"/>
    <Label value="Cold Joint" background="#0074D9"/>
    <Label value="Insufficient Solder" background="#FFDC00"/>
    <Label value="Excess Solder" background="#FF851B"/>
    <Label value="Bridging" background="#FF4136"/>
    <Label value="Missing Component" background="#B10DC9"/>
    <Label value="Tombstoning" background="#F012BE"/>
    <Label value="Lifted Pad" background="#85144b"/>
    <Label value="Other Defect" background="#AAAAAA"/>
  </BrushLabels>

  <Choices name="overall_quality" toName="image" choice="single" showInline="true">
    <Choice value="Pass"/>
    <Choice value="Fail"/>
    <Choice value="Needs Review"/>
  </Choices>

  <TextArea name="notes" toName="image"
            placeholder="Additional notes or observations..."
            rows="3"
            maxSubmissions="1"/>
</View>
"""


class LabelStudioService:
    """
    Service for interacting with Label Studio API.
    Handles project creation, task management, and webhook configuration.
    """

    def __init__(self):
        self.ls_url = settings.labelstudio_url
        self.api_key = settings.labelstudio_api_key
        self.project_id = settings.labelstudio_project_id
        self.project_name = settings.labelstudio_project_name

        self.client: Optional[Client] = None
        self.project = None

        logger.info(f"LabelStudioService initialized: url={self.ls_url}")

    def initialize(self, max_retries: int = 10, retry_delay: float = 3.0) -> None:
        """
        Initialize Label Studio client and project with retry logic.
        Creates project if it doesn't exist.

        Retries connection if Label Studio is not ready yet (e.g., still starting up).

        Args:
            max_retries: Maximum number of connection attempts (default: 10)
            retry_delay: Initial delay between retries in seconds (default: 3.0)

        Raises:
            RuntimeError: If initialization fails after all retries
        """
        if not self.api_key:
            logger.warning(
                "Label Studio API key not set. "
                "Please set LABELSTUDIO_API_KEY environment variable."
            )
            raise RuntimeError("Label Studio API key not configured")

        last_error = None

        # Retry loop - Label Studio might still be starting up
        for attempt in range(1, max_retries + 1):
            try:
                # Create client
                logger.info(
                    f"Connecting to Label Studio at {self.ls_url} "
                    f"(attempt {attempt}/{max_retries})"
                )
                self.client = Client(url=self.ls_url, api_key=self.api_key)

                # Get or create project
                if self.project_id:
                    self.project = self._get_project()
                else:
                    self.project = self._create_or_get_project()

                if self.project:
                    logger.info(
                        f"✓ Label Studio connected successfully! "
                        f"Project ready: ID={self.project.id}"
                    )

                    # Configure webhook if enabled
                    if settings.labelstudio_enable_webhooks:
                        self._setup_webhook()

                    return  # Success! Exit the function
                else:
                    raise RuntimeError("Failed to initialize Label Studio project")

            except Exception as e:
                last_error = e

                if attempt < max_retries:
                    # Calculate delay with exponential backoff
                    delay = retry_delay * (1.5 ** (attempt - 1))
                    logger.warning(
                        f"Connection failed (attempt {attempt}/{max_retries}): {str(e)[:100]}"
                    )
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error(
                        f"Label Studio initialization failed after {max_retries} attempts: {e}",
                        exc_info=True
                    )
                    raise RuntimeError(
                        f"Label Studio initialization failed after {max_retries} attempts: {e}"
                    ) from e

    def _get_project(self):
        """
        Get existing project by ID.

        Returns:
            Project instance or None if not found
        """
        try:
            project = self.client.get_project(self.project_id)
            logger.info(f"Found existing project: {project.id} - {project.title}")
            return project
        except Exception as e:
            logger.warning(f"Project {self.project_id} not found: {e}")
            return None

    def _create_or_get_project(self):
        """
        Create new project or get existing by name.

        Returns:
            Project instance

        Raises:
            RuntimeError: If creation fails
        """
        try:
            # Check if project exists by name
            projects = self.client.list_projects()
            for proj in projects:
                if proj.title == self.project_name:
                    logger.info(f"Found existing project: {proj.id} - {proj.title}")
                    # Get full project details
                    fullproject = self.client.get_project(proj.id)
                    # Ensure local storage is configured
                    self._setup_local_storage(proj.id)
                    return fullproject

            # Create new project
            logger.info(f"Creating new project: {self.project_name}")
            project = self.client.create_project(
                title=self.project_name,
                label_config=LABELING_CONFIG,
                description="PCB joint defect classification for computer vision training"
            )

            logger.info(f"Created project: {project.id}")
            # Configure local storage for the project
            self._setup_local_storage(project.id)
            return project

        except Exception as e:
            logger.error(f"Failed to create project: {e}", exc_info=True)
            raise RuntimeError(f"Project creation failed: {e}") from e

    def _setup_local_storage(self, project_id: int) -> None:
        """
        Configure local file storage for the project.
        This allows Label Studio to serve images from /data directory.
        Uses direct API calls since old SDK doesn't have import_storage methods.
        """
        try:
            logger.info(f"Creating local storage for project {project_id}")

            # Check if storage already exists
            list_url = f"{self.ls_url}/api/storages/localfiles?project={project_id}"
            headers = {"Authorization": f"Token {self.api_key}"}
            response = self.client.session.get(list_url, headers=headers)
            response.raise_for_status()

            existing_storages = response.json()
            if existing_storages:
                storage_id = existing_storages[0]['id']
                logger.info(f"Local storage already exists for project {project_id}, ID={storage_id}")
                return

            # Create new storage
            storage_config = {
                "project": project_id,
                "title": "Local Image Storage",
                "description": "PCB images from /data directory",
                "path": "/data",
                "use_blob_urls": False,
                "regex_filter": ".*\\.(jpg|jpeg|png)$"
            }

            create_url = f"{self.ls_url}/api/storages/localfiles"
            response = self.client.session.post(create_url, json=storage_config, headers=headers)
            response.raise_for_status()

            storage = response.json()
            logger.info(f"Local storage configured for project {project_id}, ID={storage['id']}")

        except Exception as e:
            logger.warning(f"Failed to setup local storage: {e}", exc_info=True)

    def _setup_webhook(self) -> None:
        """
        Configure webhook for annotation completion events.
        """
        try:
            webhook_url = settings.labelstudio_webhook_url

            logger.info(f"Setting up webhook: {webhook_url}")

            # Note: Label Studio SDK doesn't have direct webhook API
            # Webhooks need to be configured via UI or direct API call
            # For now, we'll log the information
            logger.info(
                f"Webhook configuration required:\n"
                f"  URL: {webhook_url}\n"
                f"  Events: ANNOTATION_CREATED, ANNOTATION_UPDATED\n"
                f"  Configure via Label Studio UI: Project Settings -> Webhooks"
            )

            # TODO: Implement direct webhook creation via REST API if needed

        except Exception as e:
            logger.warning(f"Webhook setup warning: {e}")

    def create_task_from_image(
        self,
        image_path: Path,
        sha256: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Label Studio task from stored image.

        Args:
            image_path: Path to stored image file
            sha256: SHA256 hash of the image
            metadata: Optional metadata to attach to task

        Returns:
            Dictionary with task information

        Raises:
            RuntimeError: If task creation fails
        """
        if not self.project:
            raise RuntimeError("Label Studio project not initialized")

        try:
            # Construct image URL (accessible from Label Studio container)
            # Using local-files URL format for local storage integration
            relative_path = str(image_path.relative_to(settings.data_root))
            image_url = f"/data/local-files/?d={relative_path}"

            # Prepare task data
            task_data = {
                "image": image_url
            }

            # Prepare metadata
            task_meta = {
                "sha256": sha256,
                "original_filename": image_path.name,
                "upload_timestamp": time.time()
            }
            if metadata:
                task_meta.update(metadata)

            logger.info(f"Creating task for image: {image_path.name}")
            logger.debug(f"Task data: {task_data}")

            # Create task using SDK
            # Note: Using direct API call as SDK's task creation might have different signature
            task_payload = {
                "data": task_data,
                "meta": task_meta,
                "project": self.project.id
            }

            url = f"{self.ls_url}/api/projects/{self.project.id}/tasks"
            headers = {"Authorization": f"Token {self.api_key}"}
            response = self.client.session.post(url, json=task_payload, headers=headers)
            response.raise_for_status()
            task = response.json()

            logger.info(f"Task created: ID={task['id']}")

            return {
                "status": "created",
                "task_id": task["id"],
                "project_id": self.project.id,
                "image_url": image_url,
                "sha256": sha256
            }

        except Exception as e:
            logger.error(f"Failed to create task: {e}", exc_info=True)
            raise RuntimeError(f"Task creation failed: {e}") from e

    def get_task(self, task_id: int) -> Dict[str, Any]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task data dictionary

        Raises:
            RuntimeError: If task retrieval fails
        """
        if not self.project:
            raise RuntimeError("Label Studio project not initialized")

        try:
            task = self.project.get_task(task_id)
            return task
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
            raise RuntimeError(f"Task retrieval failed: {e}") from e

    def get_annotation(self, annotation_id: int) -> Dict[str, Any]:
        """
        Get annotation by ID.

        Args:
            annotation_id: Annotation ID

        Returns:
            Annotation data dictionary

        Raises:
            RuntimeError: If annotation retrieval fails
        """
        try:
            # Note: SDK might not have direct annotation getter
            # May need to use client's session to make direct API call
            url = f"{self.ls_url}/api/annotations/{annotation_id}"
            response = self.client.session.get(url)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Failed to get annotation {annotation_id}: {e}", exc_info=True)
            raise RuntimeError(f"Annotation retrieval failed: {e}") from e

    def list_tasks(
        self,
        limit: int = 100,
        completed_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List tasks in project.

        Args:
            limit: Maximum number of tasks to return
            completed_only: Return only completed tasks

        Returns:
            List of task dictionaries
        """
        if not self.project:
            raise RuntimeError("Label Studio project not initialized")

        try:
            tasks = self.project.get_tasks(
                filters={"only_with_annotations": completed_only} if completed_only else None
            )

            return tasks[:limit] if limit else tasks

        except Exception as e:
            logger.error(f"Failed to list tasks: {e}", exc_info=True)
            return []

    def get_project_stats(self) -> Dict[str, Any]:
        """
        Get project statistics.

        Returns:
            Dictionary with project statistics
        """
        if not self.project:
            return {"error": "Project not initialized"}

        try:
            # Refresh project to get latest data
            self.project = self.client.get_project(self.project.id)

            return {
                "project_id": self.project.id,
                "project_name": self.project.title,
                "total_tasks": self.project.task_number,
                "completed_tasks": getattr(self.project, 'num_tasks_with_annotations', 0),
                "total_annotations": getattr(self.project, 'total_annotations_number', 0)
            }

        except Exception as e:
            logger.error(f"Failed to get project stats: {e}", exc_info=True)
            return {"error": str(e)}

    def is_healthy(self) -> bool:
        """
        Check if Label Studio service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.client:
                return False

            # Try to list projects as health check
            projects = self.client.list_projects()
            return True

        except Exception as e:
            logger.warning(f"Label Studio health check failed: {e}")
            return False


# Global Label Studio service instance
labelstudio_service = LabelStudioService()
