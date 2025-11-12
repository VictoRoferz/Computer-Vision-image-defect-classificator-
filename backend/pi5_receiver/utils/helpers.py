"""Helper utilities for PI5 Receiver service.

Provides reusable utility functions for file operations.
"""

import hashlib
from pathlib import Path
from typing import BinaryIO


def calculate_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate SHA256 hash of a file.

    Uses chunked reading to handle large files efficiently on Raspberry Pi.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read (default: 1MB)

    Returns:
        str: Hexadecimal SHA256 hash

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def calculate_sha256_from_stream(stream: BinaryIO, chunk_size: int = 1024 * 1024) -> str:
    """Calculate SHA256 hash from a binary stream.

    Args:
        stream: Binary stream (e.g., uploaded file)
        chunk_size: Size of chunks to read (default: 1MB)

    Returns:
        str: Hexadecimal SHA256 hash
    """
    sha256_hash = hashlib.sha256()
    stream.seek(0)  # Ensure we're at the start

    for chunk in iter(lambda: stream.read(chunk_size), b""):
        sha256_hash.update(chunk)

    stream.seek(0)  # Reset for future reads
    return sha256_hash.hexdigest()


def create_shard_path(root: Path, sha256_hex: str, filename: str) -> Path:
    """Create a content-addressed file path using SHA256 sharding.

    Sharding scheme: root/ab/cd/abcd...xyz/filename
    - First 2 chars: Level 1 directory
    - Next 2 chars: Level 2 directory
    - Full hash: Level 3 directory
    - Filename: Original filename preserved

    This approach:
    - Avoids file system limitations (too many files in one directory)
    - Enables deduplication (same hash = same file)
    - Improves lookup performance

    Args:
        root: Root directory path
        sha256_hex: SHA256 hash in hexadecimal format
        filename: Original filename

    Returns:
        Path: Sharded file path

    Example:
        >>> create_shard_path(Path("/data"), "abcd1234...", "image.jpg")
        Path("/data/ab/cd/abcd1234.../image.jpg")
    """
    # Extract first 4 characters for sharding
    shard1 = sha256_hex[:2]  # First 2 chars
    shard2 = sha256_hex[2:4]  # Next 2 chars

    # Create full path: root/ab/cd/full_hash/filename
    return root / shard1 / shard2 / sha256_hex / filename


def is_image_file(filename: str, supported_formats: tuple = (".jpg", ".jpeg", ".png", ".bmp")) -> bool:
    """Check if a file is a supported image format.

    Args:
        filename: Name of the file
        supported_formats: Tuple of supported extensions

    Returns:
        bool: True if file extension is supported
    """
    return filename.lower().endswith(supported_formats)
