"""
Label Studio Service for Server 2 (Raspberry Pi 5)
Handles Label Studio API interactions, project setup, and task management
"""
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

# Import the v1 Client
from label_studio_sdk import LabelStudio
from config.settings import settings
from utils.logger import setup_logger

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

        # v1 Client Type Hinting
        self.client: Optional[LabelStudio] = None
        self.project = None

        logger.info(f"LabelStudioService initialized: url={self.ls_url}")

    def initialize(self, max_retries: int = 10, retry_delay: float = 3.0) -> None:
        """
        Initialize Label Studio client and project with retry logic.
        """
        if not self.api_key:
            logger.warning("Label Studio API key not set.")
            raise RuntimeError("Label Studio API key not configured")

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Connecting to Label Studio at {self.ls_url} (attempt {attempt}/{max_retries})")
                
                # Initialize v1 Client
                self.client = LabelStudio(base_url=self.ls_url, api_key=self.api_key)

                # Get or Create Project
                if self.project_id:
                    self.project = self.client.projects.get(id=self.project_id)
                else:
                    self.project = self._create_or_get_project()

                if self.project:
                    logger.info(f"✓ Label Studio connected! Project ready: ID={self.project.id}")
                    if settings.labelstudio_enable_webhooks:
                        self._setup_webhook()
                    return
                else:
                    raise RuntimeError("Failed to initialize Label Studio project")

            except Exception as e:
                if attempt < max_retries:
                    delay = retry_delay * (1.5 ** (attempt - 1))
                    logger.warning(f"Connection failed: {str(e)[:100]}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Initialization failed: {e}", exc_info=True)
                    raise RuntimeError(f"Label Studio initialization failed: {e}") from e

    def _create_or_get_project(self):
        """
        Create new project or get existing by name.
        """
        try:
            # List projects using v1 SDK
            projects_page = self.client.projects.list()
            # Handle pagination if present (SDK specific)
            projects = getattr(projects_page, 'results', projects_page)
            
            # Use property access (.title) instead of dict access (['title'])
            for proj in projects:
                if proj.title == self.project_name:
                    logger.info(f"Found existing project: {proj.id} - {proj.title}")
                    # Fetch full details
                    fullproject = self.client.projects.get(id=proj.id)
                    self._setup_local_storage(proj.id)
                    return fullproject

            # Create new project
            logger.info(f"Creating new project: {self.project_name}")
            project = self.client.projects.create(
                title=self.project_name,
                label_config=LABELING_CONFIG,
                description="PCB joint defect classification for computer vision training"
            )

            logger.info(f"Created project: {project.id}")
            self._setup_local_storage(project.id)
            return project

        except Exception as e:
            logger.error(f"Failed to create project: {e}", exc_info=True)
            raise RuntimeError(f"Project creation failed: {e}") from e

    def _setup_local_storage(self, project_id: int) -> None:
        """
        Configure local file storage for the project using v1 SDK.
        """
        try:    
            logger.info(f"Creating local storage for project {project_id}")
            # Use the v1 API for storage creation
            storage = self.client.import_storage.local.create(
                project=project_id,
                path="/data/unlabeled",  # Path inside the container
                use_blob_urls=False,
                regex_filter=".*\\.(jpg|jpeg|png)$",
                title="Local Storage"
            )
            # Sync to index existing files
            self.client.import_storage.local.sync(id=storage.id)
            
            logger.info(f"Local storage configured for project {project_id}, ID={storage.id}")
        except Exception as e:
            # It's possible storage already exists, which might throw an error.
            logger.warning(f"Failed to setup local storage (may already exist): {e}")

    def _setup_webhook(self) -> None:
        """
        Configure webhook (informational only as v1 SDK might not strictly automate this yet).
        """
        webhook_url = settings.labelstudio_webhook_url
        logger.info(f"Webhook configuration required: {webhook_url}")

    def create_task_from_image(
        self,
        image_path: Path,
        sha256: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create Label Studio task from stored image using v1 SDK.
        """
        if not self.project:
            raise RuntimeError("Label Studio project not initialized")

        try:
            # Construct image URL (path query for local files)
            relative_path = str(image_path.relative_to(settings.data_root))
            image_url = f"/data/local-files/?d={relative_path}"

            # Prepare data and meta
            task_data = {"image": image_url}
            task_meta = {
                "sha256": sha256,
                "original_filename": image_path.name,
                "upload_timestamp": time.time()
            }
            if metadata:
                task_meta.update(metadata)

            logger.info(f"Creating task for image: {image_path.name}")

            # --- CORRECTED v1 SDK USAGE ---
            task = self.client.tasks.create(
                project=self.project.id,
                data=task_data,
                meta=task_meta
            )

            # Note: `task` is an object, access ID via .id
            logger.info(f"Task created: ID={task.id}")

            return {
                "status": "created",
                "task_id": task.id,
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
        """
        if not self.project:
            raise RuntimeError("Label Studio project not initialized")

        try:
            task = self.client.tasks.get(id=task_id)
            # Convert object to dict for consistency
            return task.model_dump() if hasattr(task, 'model_dump') else task.__dict__
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
            raise RuntimeError(f"Task retrieval failed: {e}") from e

    def get_annotation(self, annotation_id: int) -> Dict[str, Any]:
        """
        Get annotation by ID using v1 SDK.
        """
        try:
            # Use .annotations.get
            annotation = self.client.annotations.get(id=annotation_id)
            return annotation.model_dump() if hasattr(annotation, 'model_dump') else annotation.__dict__

        except Exception as e:
            logger.error(f"Failed to get annotation {annotation_id}: {e}", exc_info=True)
            raise RuntimeError(f"Annotation retrieval failed: {e}") from e

    def list_tasks(self, limit: int = 100, completed_only: bool = False) -> List[Dict[str, Any]]:
        """
        List tasks in project.
        """
        if not self.project:
            raise RuntimeError("Label Studio project not initialized")

        try:
            # v1 SDK list tasks
            tasks_page = self.client.tasks.list(
                project=self.project.id,
                page_size=limit
            )
            tasks = getattr(tasks_page, 'results', tasks_page)
            
            # Convert objects to dicts
            return [t.model_dump() if hasattr(t, 'model_dump') else t.__dict__ for t in tasks]

        except Exception as e:
            logger.error(f"Failed to list tasks: {e}", exc_info=True)
            return []

    def get_project_stats(self) -> Dict[str, Any]:
        """
        Get project statistics.
        """
        if not self.project:
            return {"error": "Project not initialized"}

        try:
            # Refresh project object
            self.project = self.client.projects.get(id=self.project.id)

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
        """
        try:
            if not self.client:
                return False
            # Simple list call to check connection
            self.client.projects.list(page_size=1)
            return True
        except Exception as e:
            logger.warning(f"Label Studio health check failed: {e}")
            return False


# Global Label Studio service instance
labelstudio_service = LabelStudioService()