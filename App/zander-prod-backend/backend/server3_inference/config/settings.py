"""
Configuration for Server 3 (ML Inference Service)
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "inference-service"
    service_version: str = "1.0.0"

    host: str = "0.0.0.0"
    port: int = 8003

    # Model configuration
    model_path: str = "models/yolov8n.pt"
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    max_detections: int = 100
    image_size: int = 640

    # Server 2 connection (for fetching stored images)
    server2_url: str = "http://localhost:8002"

    # Storage
    data_root: Path = Path("/data")

    # Logging
    log_level: str = "INFO"

    # PCB defect class names (maps to YOLOv8 generic classes until fine-tuned)
    defect_classes: list[str] = [
        "Good Joint",
        "Cold Joint",
        "Insufficient Solder",
        "Excess Solder",
        "Bridging",
        "Missing Component",
        "Tombstoning",
        "Lifted Pad",
        "Other Defect"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
