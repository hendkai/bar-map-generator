"""
File storage utilities for BAR Community Map Sharing Portal.
Handles file uploads, validation, and storage management.
"""

import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status

from config import settings


# =============================================================================
# File Storage Utilities
# =============================================================================

def get_upload_dir() -> Path:
    """
    Get the upload directory path, creating it if it doesn't exist.

    Returns:
        Path: Upload directory path
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename while preserving the original extension.

    Args:
        original_filename: Original filename

    Returns:
        Unique filename with UUID prefix
    """
    # Extract file extension
    _, ext = os.path.splitext(original_filename)

    # Generate unique filename with UUID
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{ext}"


def validate_file_extension(filename: str) -> bool:
    """
    Validate that the file has an allowed extension.

    Args:
        filename: Filename to validate

    Returns:
        True if extension is allowed, False otherwise
    """
    _, ext = os.path.splitext(filename.lower())
    return ext in settings.ALLOWED_FILE_EXTENSIONS


async def save_uploaded_file(
    file: UploadFile,
    subdirectory: Optional[str] = None
) -> tuple[str, str]:
    """
    Save an uploaded file to disk.

    Args:
        file: FastAPI UploadFile object
        subdirectory: Optional subdirectory within upload dir

    Returns:
        Tuple of (relative_path, full_path)

    Raises:
        HTTPException: If file validation fails or save operation fails
    """
    # Validate file extension
    if not validate_file_extension(file.filename or ""):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid file type. Allowed types: {', '.join(settings.ALLOWED_FILE_EXTENSIONS)}"
        )

    # Get upload directory
    upload_dir = get_upload_dir()

    # Create subdirectory if specified
    if subdirectory:
        target_dir = upload_dir / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = upload_dir

    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename or "upload.sd7")
    file_path = target_dir / unique_filename

    # Save file to disk
    try:
        content = await file.read()

        # Validate file size
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.0f}MB"
            )

        # Write file
        with open(file_path, "wb") as f:
            f.write(content)

        # Calculate relative path for storage in database
        if subdirectory:
            relative_path = f"{subdirectory}/{unique_filename}"
        else:
            relative_path = unique_filename

        return relative_path, str(file_path)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle any other errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


async def save_preview_image(
    image_data: bytes,
    map_id: int,
    extension: str = "png"
) -> str:
    """
    Save a preview image for a map.

    Args:
        image_data: Image binary data
        map_id: Map ID for organizing images
        extension: Image file extension (default: png)

    Returns:
        Relative path to saved image

    Raises:
        HTTPException: If save operation fails
    """
    # Get upload directory
    upload_dir = get_upload_dir()

    # Create previews subdirectory
    previews_dir = upload_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = f"map_{map_id}.{extension}"
    file_path = previews_dir / filename

    # Save image
    try:
        with open(file_path, "wb") as f:
            f.write(image_data)

        return f"previews/{filename}"

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save preview image: {str(e)}"
        )


def delete_file(file_path: str) -> bool:
    """
    Delete a file from storage.

    Args:
        file_path: Relative path to file within upload directory

    Returns:
        True if file was deleted, False otherwise
    """
    try:
        upload_dir = get_upload_dir()
        full_path = upload_dir / file_path

        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            return True

        return False

    except Exception:
        return False


def get_file_url(file_path: str) -> str:
    """
    Generate a URL for accessing a stored file.

    Args:
        file_path: Relative path to file within upload directory

    Returns:
        URL path for file download
    """
    return f"/api/maps/files/{file_path}"
