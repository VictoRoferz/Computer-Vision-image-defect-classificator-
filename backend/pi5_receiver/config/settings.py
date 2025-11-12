"""Configuration settings for PI5 Receiver service.

This module handles all configuration using environment variables,
following the 12-factor app methodology for portability.
"""

import os
from pathlib import Path
from typing import Optional
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Storage Configuration
    DATA_ROOT: Path = Path(os.getenv("DATA_ROOT", "/data"))
    IMAGES_UNLABELED: Path = DATA_ROOT / "images" / "unlabeled"
    IMAGES_LABELED: Path = DATA_ROOT / "images" / "labeled"
    DATABASE_PATH: Path = DATA_ROOT / "pcb_labeling.db"

    # Label Studio Configuration
    LABEL_STUDIO_URL: str = os.getenv("LABEL_STUDIO_URL", "http://label-studio:8080")
    LABEL_STUDIO_API_KEY: str = os.getenv("LABEL_STUDIO_API_KEY", "")
    LABEL_STUDIO_PROJECT_ID: Optional[int] = (
        int(os.getenv("LABEL_STUDIO_PROJECT_ID"))
        if os.getenv("LABEL_STUDIO_PROJECT_ID")
        else None
    )
    LABEL_STUDIO_PROJECT_NAME: str = os.getenv(
        "LABEL_STUDIO_PROJECT_NAME", "PCB Defect Classification"
    )

    # Watcher Configuration
    WATCHER_ENABLED: bool = os.getenv("WATCHER_ENABLED", "true").lower() == "true"
    WATCHER_POLL_INTERVAL: int = int(os.getenv("WATCHER_POLL_INTERVAL", "5"))

    # Image Processing Configuration
    SUPPORTED_FORMATS: tuple = (".jpg", ".jpeg", ".png", ".bmp")
    MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        """Initialize settings and create necessary directories."""
        self.IMAGES_UNLABELED.mkdir(parents=True, exist_ok=True)
        self.IMAGES_LABELED.mkdir(parents=True, exist_ok=True)
        self.DATA_ROOT.mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        """Validate critical configuration settings.

        Returns:
            bool: True if all critical settings are valid

        Raises:
            ValueError: If critical settings are invalid
        """
        if not self.LABEL_STUDIO_URL:
            raise ValueError("LABEL_STUDIO_URL must be set")

        if self.WATCHER_ENABLED and not self.LABEL_STUDIO_API_KEY:
            raise ValueError(
                "LABEL_STUDIO_API_KEY must be set when WATCHER_ENABLED is true"
            )

        return True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Using lru_cache ensures we only create one Settings instance
    throughout the application lifecycle.

    Returns:
        Settings: Singleton settings instance
    """
    settings = Settings()
    settings.validate()
    return settings
