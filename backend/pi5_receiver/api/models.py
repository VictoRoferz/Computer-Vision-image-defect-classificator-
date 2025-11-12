"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response model for image upload endpoint."""

    status: str = Field(
        ...,
        description="Status of upload (stored, already_stored, error)"
    )
    sha256: str = Field(..., description="SHA256 hash of the image")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Storage path")
    is_duplicate: bool = Field(
        ...,
        description="True if image was already in database"
    )
    labelstudio_task_id: Optional[int] = Field(
        None,
        description="Label Studio task ID if created"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Overall service status")
    database: bool = Field(..., description="Database connection status")
    labelstudio: bool = Field(..., description="Label Studio connection status")
    storage: bool = Field(..., description="Storage availability status")
    timestamp: datetime = Field(default_factory=datetime.now)


class ImageStatusResponse(BaseModel):
    """Response model for image status endpoint."""

    sha256: str
    filename: str
    status: str
    received_at: datetime
    sent_to_ls_at: Optional[datetime] = None
    labeled_at: Optional[datetime] = None
    labelstudio_task_id: Optional[int] = None
    error_message: Optional[str] = None


class StatsResponse(BaseModel):
    """Response model for statistics endpoint."""

    total_images: int
    unlabeled: int
    sent_to_labelstudio: int
    labeled: int
    errors: int
