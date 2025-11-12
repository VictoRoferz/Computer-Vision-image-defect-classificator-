"""Data models for image tracking.

Defines the structure of data stored in the database.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ImageStatus(Enum):
    """Enum for tracking image processing status."""

    RECEIVED = "received"  # Image received, stored in unlabeled directory
    SENT_TO_LABELSTUDIO = "sent_to_labelstudio"  # Sent to Label Studio for labeling
    LABELED = "labeled"  # Labeling completed, exported to labeled directory
    ERROR = "error"  # Error occurred during processing


@dataclass
class ImageRecord:
    """Data model for an image record in the database.

    Attributes:
        id: Auto-generated primary key
        filename: Original filename
        sha256: SHA256 hash for content addressing
        file_path: Full path to the image file
        status: Current processing status
        received_at: Timestamp when image was received
        sent_to_ls_at: Timestamp when sent to Label Studio
        labeled_at: Timestamp when labeling was completed
        labelstudio_task_id: Label Studio task ID
        error_message: Error message if status is ERROR
    """

    id: Optional[int] = None
    filename: str = ""
    sha256: str = ""
    file_path: str = ""
    status: ImageStatus = ImageStatus.RECEIVED
    received_at: datetime = None
    sent_to_ls_at: Optional[datetime] = None
    labeled_at: Optional[datetime] = None
    labelstudio_task_id: Optional[int] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.received_at is None:
            self.received_at = datetime.now()

        # Convert string to enum if necessary
        if isinstance(self.status, str):
            self.status = ImageStatus(self.status)

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            dict: Dictionary with all fields
        """
        return {
            "id": self.id,
            "filename": self.filename,
            "sha256": self.sha256,
            "file_path": self.file_path,
            "status": self.status.value if isinstance(self.status, ImageStatus) else self.status,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "sent_to_ls_at": self.sent_to_ls_at.isoformat() if self.sent_to_ls_at else None,
            "labeled_at": self.labeled_at.isoformat() if self.labeled_at else None,
            "labelstudio_task_id": self.labelstudio_task_id,
            "error_message": self.error_message,
        }
