"""
Pydantic models for Server 2 (Label Studio Service)
Data validation and serialization schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UploadResponse(BaseModel):
    """Response model for image upload"""
    status: str = Field(..., description="Upload status: stored, already_stored, error")
    sha256: str = Field(..., description="SHA256 hash of the image")
    path: str = Field(..., description="Storage path")
    filename: str = Field(..., description="Original filename")
    size_bytes: int = Field(..., description="File size in bytes")
    task_id: Optional[int] = Field(None, description="Label Studio task ID")
    message: Optional[str] = Field(None, description="Additional information")


class ImageInfo(BaseModel):
    """Information about a stored image"""
    filename: str
    path: str
    size_bytes: int
    modified: float
    sha256: Optional[str] = None


class LabeledImageInfo(ImageInfo):
    """Information about a labeled image"""
    annotation_path: Optional[str] = None
    has_annotation: bool = False


class StorageStats(BaseModel):
    """Storage statistics"""
    unlabeled: Dict[str, Any]
    labeled: Dict[str, Any]
    total: Dict[str, Any]


class WebhookPayload(BaseModel):
    """Label Studio webhook payload"""
    action: str = Field(..., description="Webhook action: ANNOTATION_CREATED, ANNOTATION_UPDATED, etc.")
    project: Dict[str, Any] = Field(..., description="Project information")
    annotation: Optional[Dict[str, Any]] = Field(None, description="Annotation data")
    task: Optional[Dict[str, Any]] = Field(None, description="Task data")


class WebhookResponse(BaseModel):
    """Response for webhook processing"""
    status: str = Field(..., description="Processing status: success, error")
    message: str = Field(..., description="Status message")
    labeled_image_path: Optional[str] = Field(None, description="Path to labeled image")
    annotation_path: Optional[str] = Field(None, description="Path to annotation JSON")


class TaskCreateRequest(BaseModel):
    """Request to create Label Studio task"""
    image_path: str = Field(..., description="Path to image file")
    sha256: str = Field(..., description="SHA256 hash")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TaskCreateResponse(BaseModel):
    """Response for task creation"""
    status: str
    task_id: int
    project_id: int
    image_url: str
    sha256: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    components: Optional[Dict[str, bool]] = Field(None, description="Component health status")


class StatusResponse(BaseModel):
    """Service status response"""
    service: str
    version: str
    storage: StorageStats
    labelstudio: Dict[str, Any]
    status: str
