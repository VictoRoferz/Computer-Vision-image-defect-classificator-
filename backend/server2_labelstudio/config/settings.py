"""
Configuration management for Server 2 (Label Studio Service - Raspberry Pi 5)
Uses Pydantic Settings for type-safe environment variable handling
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Server 2 configuration settings.
    All values can be overridden via environment variables.
    """

    # Service identification
    service_name: str = "labelstudio-service"
    service_version: str = "1.0.0"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8002

    # Storage configuration
    data_root: Path = Path("/data")
    unlabeled_dir: Path = Path("/data/unlabeled")
    labeled_dir: Path = Path("/data/labeled")

    # Content-addressed storage (from main branch)
    use_content_addressing: bool = True  # SHA256-based deduplication

    # Label Studio configuration
    labelstudio_url: str = "http://localhost:8080"
    labelstudio_api_key: str = ""  # Must be set via environment
    labelstudio_project_id: Optional[int] = None  # Auto-created if None
    labelstudio_project_name: str = "PCB Defect Classification"

    # Label Studio project configuration
    labelstudio_auto_create_project: bool = True
    labelstudio_enable_webhooks: bool = True

    # Webhook configuration
    webhook_secret: Optional[str] = None  # Optional webhook signature verification
    webhook_enabled: bool = True

    # File watching
    enable_file_watcher: bool = True
    file_watcher_recursive: bool = True

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Health check
    health_check_enabled: bool = True

    # Image formats
    allowed_extensions: list[str] = [".jpg", ".jpeg", ".png", ".bmp"]

    # Performance tuning for Raspberry Pi 5
    max_upload_size_mb: int = 50
    cleanup_temp_files: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.unlabeled_dir.mkdir(parents=True, exist_ok=True)
        self.labeled_dir.mkdir(parents=True, exist_ok=True)

    @property
    def labelstudio_webhook_url(self) -> str:
        """Webhook URL for Label Studio to call"""
        return f"http://server2:{self.port}/api/v1/webhook/annotation-created"

    def get_unlabeled_path(self, sha256: str, filename: str) -> Path:
        """
        Get content-addressed path for unlabeled image.

        Args:
            sha256: SHA256 hash of the file
            filename: Original filename

        Returns:
            Path object for the file location
        """
        if self.use_content_addressing:
            # Content-addressed: /data/unlabeled/ab/cd/abcd.../filename.jpg
            sub1, sub2 = sha256[:2], sha256[2:4]
            return self.unlabeled_dir / sub1 / sub2 / sha256 / filename
        else:
            # Simple storage: /data/unlabeled/filename.jpg
            return self.unlabeled_dir / filename

    def get_labeled_path(self, sha256: str, filename: str) -> Path:
        """
        Get path for labeled image.

        Args:
            sha256: SHA256 hash of the file
            filename: Original filename

        Returns:
            Path object for the file location
        """
        # Labeled images use flat structure with hash prefix
        return self.labeled_dir / f"{sha256[:8]}_{filename}"

    def get_annotation_path(self, sha256: str, filename: str) -> Path:
        """
        Get path for annotation JSON file.

        Args:
            sha256: SHA256 hash of the file
            filename: Original filename

        Returns:
            Path object for the annotation JSON file
        """
        # Same location as labeled image, but with .json extension
        base_name = Path(filename).stem
        return self.labeled_dir / f"{sha256[:8]}_{base_name}.json"


# Global settings instance
settings = Settings()
