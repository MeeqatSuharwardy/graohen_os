"""GrapheneOS Build Download Endpoint

This endpoint checks if a build is available and triggers download.
Used by the frontend to show a download button when the app loads.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.utils.grapheneos.bundles import (
    get_bundle_for_codename,
    download_release,
    find_latest_version,
    index_bundles,
)
from app.config import settings
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/download", tags=["grapheneos"])

# Store download progress in memory (use Redis in production)
download_progress: Dict[str, Dict[str, Any]] = {}


class DownloadCheckRequest(BaseModel):
    """Request to check if download is needed"""
    codename: str


class DownloadRequest(BaseModel):
    """Request to download a build"""
    codename: str
    version: Optional[str] = None  # If None, downloads latest


class DownloadStatusResponse(BaseModel):
    """Download status response"""
    download_id: str
    status: str
    progress: float = 0.0
    downloaded: int = 0
    total: int = 0
    error: Optional[str] = None
    bundle_path: Optional[str] = None


@router.get("/check/{codename}")
async def check_build_availability(codename: str):
    """
    Check if a build is available for download.
    Called when the app loads to determine if download button should be shown.
    
    Returns:
        - available: bool - Whether a build is available
        - has_bundle: bool - Whether a bundle is already downloaded locally
        - latest_version: Optional[str] - Latest available version
        - bundle_path: Optional[str] - Path to existing bundle if available
    """
    try:
        # Check if we already have a bundle locally
        local_bundle = get_bundle_for_codename(codename)
        
        if local_bundle:
            return {
                "available": True,
                "has_bundle": True,
                "latest_version": local_bundle.get("version"),
                "bundle_path": local_bundle.get("path"),
                "message": "Bundle already downloaded",
            }
        
        # Try to find the latest version available online
        try:
            latest_version = await find_latest_version(codename, max_days_back=30)
            if latest_version:
                return {
                    "available": True,
                    "has_bundle": False,
                    "latest_version": latest_version,
                    "bundle_path": None,
                    "message": f"Latest version {latest_version} available for download",
                }
        except Exception as e:
            logger.warning(f"Could not find latest version for {codename}: {e}")
        
        # If no latest version found, still return available=True
        # The frontend can prompt the user to enter a version manually
        return {
            "available": True,
            "has_bundle": False,
            "latest_version": None,
            "bundle_path": None,
            "message": "Build available (version may need to be specified)",
        }
        
    except Exception as e:
        logger.error(f"Error checking build availability for {codename}: {e}", exc_info=True)
        return {
            "available": False,
            "has_bundle": False,
            "latest_version": None,
            "bundle_path": None,
            "error": str(e),
        }


@router.post("/start")
async def start_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start downloading a GrapheneOS build.
    
    If version is not provided, automatically finds the latest version.
    """
    codename = request.codename
    
    # Determine version
    version = request.version
    if not version:
        # Find latest version
        try:
            version = await find_latest_version(codename, max_days_back=30)
            if not version:
                raise HTTPException(
                    status_code=404,
                    detail=f"Could not find latest version for {codename}. Please specify a version."
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to find latest version: {str(e)}"
            )
    
    download_id = f"{codename}-{version}"
    
    # Check if already downloading
    if download_id in download_progress:
        progress_info = download_progress[download_id]
        if progress_info.get("status") == "downloading":
            raise HTTPException(
                status_code=400,
                detail="Download already in progress"
            )
        elif progress_info.get("status") == "completed":
            return {
                "download_id": download_id,
                "status": "completed",
                "message": "Download already completed",
                "bundle_path": progress_info.get("bundle_path"),
            }
    
    # Initialize progress
    download_progress[download_id] = {
        "status": "downloading",
        "progress": 0.0,
        "downloaded": 0,
        "total": 0,
        "error": None,
        "bundle_path": None,
    }
    
    async def download_with_progress():
        """Background task for downloading"""
        try:
            async def progress_cb(progress: float, downloaded: int, total: int):
                download_progress[download_id] = {
                    "status": "downloading",
                    "progress": progress,
                    "downloaded": downloaded,
                    "total": total,
                    "error": None,
                    "bundle_path": None,
                }
            
            result = await download_release(
                codename,
                version,
                progress_callback=progress_cb
            )
            
            download_progress[download_id] = {
                "status": "completed" if result.get("success") else "error",
                "progress": 100.0 if result.get("success") else 0.0,
                "downloaded": download_progress[download_id].get("total", 0),
                "total": download_progress[download_id].get("total", 0),
                "error": None if result.get("success") else ", ".join(result.get("errors", [])),
                "bundle_path": result.get("path"),
            }
        except Exception as e:
            logger.error(f"Download failed: {e}", exc_info=True)
            download_progress[download_id] = {
                "status": "error",
                "progress": 0.0,
                "error": str(e),
            }
    
    # Start download in background
    background_tasks.add_task(download_with_progress)
    
    return {
        "download_id": download_id,
        "status": "started",
        "message": f"Download started for {codename} {version}",
        "codename": codename,
        "version": version,
    }


@router.get("/status/{download_id}")
async def get_download_status(download_id: str):
    """Get download status and progress"""
    if download_id not in download_progress:
        raise HTTPException(status_code=404, detail="Download not found")
    
    return download_progress[download_id]

