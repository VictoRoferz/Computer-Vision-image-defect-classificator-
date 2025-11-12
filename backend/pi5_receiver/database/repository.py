"""Database repository for managing image records.

Provides abstraction layer for database operations using SQLite.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from .models import ImageRecord, ImageStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseRepository:
    """Repository for managing image records in SQLite database.

    This class provides CRUD operations and follows the Repository pattern
    for clean separation between business logic and data access.
    """

    def __init__(self, db_path: Path):
        """Initialize database repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema.

        Creates tables if they don't exist. Safe to call multiple times.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create images table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    sha256 TEXT UNIQUE NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    sent_to_ls_at TEXT,
                    labeled_at TEXT,
                    labelstudio_task_id INTEGER,
                    error_message TEXT
                )
            """)

            # Create index on sha256 for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sha256 ON images(sha256)
            """)

            # Create index on status for filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON images(status)
            """)

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections.

        Ensures connections are properly closed and provides
        automatic transaction management.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like row access
        try:
            yield conn
        finally:
            conn.close()

    def create(self, record: ImageRecord) -> ImageRecord:
        """Create a new image record.

        Args:
            record: ImageRecord to create

        Returns:
            ImageRecord: Created record with generated ID

        Raises:
            sqlite3.IntegrityError: If SHA256 already exists
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO images (
                    filename, sha256, file_path, status,
                    received_at, sent_to_ls_at, labeled_at,
                    labelstudio_task_id, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.filename,
                record.sha256,
                record.file_path,
                record.status.value,
                record.received_at.isoformat(),
                record.sent_to_ls_at.isoformat() if record.sent_to_ls_at else None,
                record.labeled_at.isoformat() if record.labeled_at else None,
                record.labelstudio_task_id,
                record.error_message,
            ))

            conn.commit()
            record.id = cursor.lastrowid

            logger.info(f"Created image record: {record.filename} (ID: {record.id})")
            return record

    def get_by_sha256(self, sha256: str) -> Optional[ImageRecord]:
        """Get image record by SHA256 hash.

        Args:
            sha256: SHA256 hash

        Returns:
            ImageRecord if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM images WHERE sha256 = ?", (sha256,))
            row = cursor.fetchone()

            if row:
                return self._row_to_record(row)
            return None

    def get_by_id(self, record_id: int) -> Optional[ImageRecord]:
        """Get image record by ID.

        Args:
            record_id: Record ID

        Returns:
            ImageRecord if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM images WHERE id = ?", (record_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_record(row)
            return None

    def get_by_status(self, status: ImageStatus) -> List[ImageRecord]:
        """Get all image records with a specific status.

        Args:
            status: ImageStatus to filter by

        Returns:
            List of ImageRecords
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM images WHERE status = ?", (status.value,))
            rows = cursor.fetchall()

            return [self._row_to_record(row) for row in rows]

    def update_status(
        self,
        sha256: str,
        status: ImageStatus,
        **kwargs
    ) -> Optional[ImageRecord]:
        """Update image record status and related fields.

        Args:
            sha256: SHA256 hash of the image
            status: New status
            **kwargs: Additional fields to update (sent_to_ls_at, labeled_at, etc.)

        Returns:
            Updated ImageRecord if found, None otherwise
        """
        record = self.get_by_sha256(sha256)
        if not record:
            logger.warning(f"Cannot update: Image with SHA256 {sha256} not found")
            return None

        # Build dynamic UPDATE query
        update_fields = ["status = ?"]
        values = [status.value]

        for key, value in kwargs.items():
            if hasattr(record, key):
                update_fields.append(f"{key} = ?")
                if isinstance(value, datetime):
                    values.append(value.isoformat())
                else:
                    values.append(value)

        values.append(sha256)
        query = f"UPDATE images SET {', '.join(update_fields)} WHERE sha256 = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()

            logger.info(f"Updated image {sha256} to status {status.value}")

        return self.get_by_sha256(sha256)

    def get_all(self, limit: Optional[int] = None) -> List[ImageRecord]:
        """Get all image records.

        Args:
            limit: Optional limit on number of records

        Returns:
            List of ImageRecords
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if limit:
                cursor.execute(
                    "SELECT * FROM images ORDER BY received_at DESC LIMIT ?",
                    (limit,)
                )
            else:
                cursor.execute("SELECT * FROM images ORDER BY received_at DESC")

            rows = cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> ImageRecord:
        """Convert database row to ImageRecord.

        Args:
            row: SQLite row

        Returns:
            ImageRecord: Converted record
        """
        return ImageRecord(
            id=row["id"],
            filename=row["filename"],
            sha256=row["sha256"],
            file_path=row["file_path"],
            status=ImageStatus(row["status"]),
            received_at=datetime.fromisoformat(row["received_at"]),
            sent_to_ls_at=(
                datetime.fromisoformat(row["sent_to_ls_at"])
                if row["sent_to_ls_at"]
                else None
            ),
            labeled_at=(
                datetime.fromisoformat(row["labeled_at"])
                if row["labeled_at"]
                else None
            ),
            labelstudio_task_id=row["labelstudio_task_id"],
            error_message=row["error_message"],
        )
