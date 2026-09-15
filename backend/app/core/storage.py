"""
Cloudinary storage utility.

All file I/O (uploads and downloads) for datasets and synthetic outputs
goes through this module instead of the local filesystem.
"""
import io
import tempfile
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests

from app.core.config import settings
from app.core.logging import logger


def _configure():
    """Configure Cloudinary with credentials from environment variables."""
    # Validate credentials are set
    if (settings.CLOUDINARY_API_KEY == "placeholder_cloudinary_api_key" or 
        settings.CLOUDINARY_API_SECRET == "placeholder_cloudinary_api_secret" or
        not settings.CLOUDINARY_CLOUD_NAME or
        settings.CLOUDINARY_CLOUD_NAME == "placeholder_cloud_name"):
        raise ValueError(
            "Cloudinary credentials not configured. Please set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables. "
            "Get these from https://cloudinary.com/console"
        )
    
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_file(file_bytes: bytes, public_id: str, folder: str = "synthetix") -> str:
    """
    Upload raw bytes to Cloudinary.

    Args:
        file_bytes: The file content as bytes.
        public_id:  Unique identifier for the asset (without folder prefix).
        folder:     Cloudinary folder to store the file in.

    Returns:
        The secure HTTPS URL of the uploaded file.
    
    Raises:
        ValueError: If Cloudinary credentials are not configured.
        Exception: If upload fails (network, quota, authentication, etc.)
    """
    try:
        _configure()
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=public_id,
            folder=folder,
            resource_type="raw",   # required for non-image files (CSV, JSON, etc.)
            overwrite=True,
        )
        url: str = result["secure_url"]
        logger.info(f"Uploaded to Cloudinary: {url}")
        return url
    except ValueError as ve:
        # Credentials not configured
        logger.error(f"Cloudinary configuration error: {ve}")
        raise
    except Exception as e:
        logger.error(f"Cloudinary upload failed for {public_id}: {e}", exc_info=True)
        raise Exception(f"File upload failed: {str(e)}") from e


def download_to_temp(url: str, suffix: str = ".csv") -> str:
    """
    Download a Cloudinary (or any HTTPS) URL to a named temporary file.

    Args:
        url:    The Cloudinary secure URL.
        suffix: File extension for the temp file.

    Returns:
        Absolute path of the temporary file. Caller is responsible for deletion.
    """
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(response.content)
    tmp.flush()
    tmp.close()

    logger.info(f"Downloaded {url} → {tmp.name}")
    return tmp.name


def delete_file(public_id_with_folder: str):
    """
    Delete a file from Cloudinary by its full public_id (folder/name).
    Silently logs errors so callers are not blocked.
    """
    _configure()
    try:
        cloudinary.uploader.destroy(public_id_with_folder, resource_type="raw")
        logger.info(f"Deleted from Cloudinary: {public_id_with_folder}")
    except Exception as e:
        logger.warning(f"Failed to delete Cloudinary asset {public_id_with_folder}: {e}")
