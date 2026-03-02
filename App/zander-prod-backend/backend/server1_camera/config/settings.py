"""
Configuration management for Server 1 (Camera Service - Raspberry Pi 3)
Uses Pydantic Settings for type-safe environment variable handling
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Server 1 configuration settings.
    All values can be overridden via environment variables.
    """

    # Service identification
    service_name: str = "camera-service"
    service_version: str = "1.0.0"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8001

    # Camera configuration
    use_camera: bool = True
    camera_index: int = 0  # 0 = default camera, 1+ = external USB cameras
    camera_width: int = 1920
    camera_height: int = 1080
    camera_fps: int = 30

    # Fallback image (for testing without camera)
    fallback_image_path: str = "sample.jpg"

    # Server 2 (Raspberry Pi 5) connection
    server2_url: str = "http://localhost:8002"
    server2_upload_endpoint: str = "/api/v1/upload"
    upload_timeout: int = 30  # seconds
    upload_retries: int = 3
    upload_retry_delay: float = 2.0  # seconds (exponential backoff)

    # Local storage (temporary)
    temp_dir: Path = Path("/tmp/camera_captures")
    cleanup_after_upload: bool = True

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Health check
    health_check_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def server2_upload_url(self) -> str:
        """Full upload URL for Server 2"""
        return f"{self.server2_url}{self.server2_upload_endpoint}"


# Global settings instance
settings = Settings()
