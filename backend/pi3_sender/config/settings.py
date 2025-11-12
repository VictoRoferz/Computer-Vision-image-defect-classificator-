"""Configuration settings for PI3 Sender service.

This module handles all configuration using environment variables.
"""

import os
from pathlib import Path
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    # Camera Configuration
    USE_CAMERA: bool = os.getenv("USE_CAMERA", "false").lower() == "true"
    CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))
    FALLBACK_IMAGE_DIR: Path = Path(os.getenv("FALLBACK_IMAGE_DIR", "/app/sample_images"))

    # Watch Directory Configuration (for simulating incoming images)
    WATCH_DIR: Path = Path(os.getenv("WATCH_DIR", "/data/watch"))
    WATCH_INTERVAL: int = int(os.getenv("WATCH_INTERVAL", "2"))

    # Upload Configuration
    UPLOAD_URL: str = os.getenv("UPLOAD_URL", "http://pi5-receiver:8000/api/v1/upload")
    UPLOAD_TIMEOUT: int = int(os.getenv("UPLOAD_TIMEOUT", "30"))
    RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "2"))

    # Output Configuration
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "/data/captured"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        """Initialize settings and create necessary directories."""
        self.WATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.FALLBACK_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        """Validate critical configuration settings.

        Returns:
            bool: True if all critical settings are valid

        Raises:
            ValueError: If critical settings are invalid
        """
        if not self.UPLOAD_URL:
            raise ValueError("UPLOAD_URL must be set")

        return True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Singleton settings instance
    """
    settings = Settings()
    settings.validate()
    return settings
