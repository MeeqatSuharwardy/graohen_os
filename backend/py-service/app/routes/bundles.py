from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
import os
import zipfile
import io
import tempfile
import shutil
from ..utils.bundles import (
    index_bundles,
    get_bundle_for_codename,
    verify_bundle,
    get_available_releases,
    download_release,
    find_latest_version,
)

router = APIRouter()

# Store download progress in memory (use Redis in production)
download_progress: Dict[str, Dict[str, Any]] = {}


@router.post("/index")
async def index_bundles_endpoint():
    """Index all available bundles"""
    return index_bundles()


@router.get("/for/{codename}")
async def get_bundle_for_codename_endpoint(codename: str):
    """Get the newest bundle for a codename"""
    bundle = get_bundle_for_codename(codename)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail=f"No bundle found for codename: {codename}"
        )
    
    return bundle


@router.post("/verify")
async def verify_bundle_endpoint(bundle_path: str):
    """Verify bundle integrity"""
    if not bundle_path:
        raise HTTPException(status_code=400, detail="bundle_path is required")
    
    result = verify_bundle(bundle_path)
    return result


@router.get("/releases/{codename}")
async def get_releases_endpoint(codename: str):
    """Get available GrapheneOS releases for a codename"""
    releases = await get_available_releases(codename)
    return {"codename": codename, "releases": releases}


@router.get("/find-latest/{codename}")
async def find_latest_version_endpoint(codename: str):
    """Find the latest available version for a codename"""
    latest_version = await find_latest_version(codename)
    if not latest_version:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any available releases for codename: {codename}"
        )
    return {"codename": codename, "version": latest_version}


class DownloadRequest(BaseModel):
    codename: str
    version: str


async def progress_callback(progress: float, downloaded: int, total: int):
    """Callback for download progress"""
    pass  # Will be handled by the download function


@router.post("/download")
async def download_bundle_endpoint(
    request: DownloadRequest,
    background_tasks: BackgroundTasks
):
    """Download a GrapheneOS factory image bundle"""
    download_id = f"{request.codename}-{request.version}"
    
    # Check if already downloading
    if download_id in download_progress:
        progress_info = download_progress[download_id]
        if progress_info.get("status") == "downloading":
            raise HTTPException(
                status_code=400,
                detail="Download already in progress"
            )
    
    # Initialize progress
    download_progress[download_id] = {
        "status": "downloading",
        "progress": 0.0,
        "downloaded": 0,
        "total": 0,
        "error": None,
    }
    
    async def download_with_progress():
        try:
            async def progress_cb(progress: float, downloaded: int, total: int):
                download_progress[download_id] = {
                    "status": "downloading",
                    "progress": progress,
                    "downloaded": downloaded,
                    "total": total,
                    "error": None,
                }
            
            result = await download_release(
                request.codename,
                request.version,
                progress_callback=progress_cb
            )
            
            download_progress[download_id] = {
                "status": "completed",
                "progress": 100.0,
                "result": result,
                "error": None,
            }
        except Exception as e:
            download_progress[download_id] = {
                "status": "error",
                "error": str(e),
            }
    
    # Start download in background
    background_tasks.add_task(download_with_progress)
    
    return {
        "download_id": download_id,
        "status": "started",
        "message": "Download started",
    }


@router.get("/download/{download_id}/status")
async def get_download_status_endpoint(download_id: str):
    """Get download status and progress"""
    if download_id not in download_progress:
        raise HTTPException(status_code=404, detail="Download not found")
    
    return download_progress[download_id]


def _get_bundle_zip_file(codename: str, version: str) -> Path:
    """
    Helper function to get or create bundle zip file.
    Returns the Path to the zip file.
    """
    bundle = get_bundle_for_codename(codename, version=version)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail=f"Bundle not found for codename: {codename}, version: {version}"
        )
    
    bundle_path = Path(bundle["path"])
    
    if not bundle_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Bundle directory not found: {bundle_path}"
        )
    
    # Look for image.zip in the bundle directory
    image_zip = bundle_path / "image.zip"
    
    # Also check for the factory zip file
    factory_zip = bundle_path / f"{codename}-factory-{version}.zip"
    
    zip_file = None
    if image_zip.exists() and image_zip.is_file():
        zip_file = image_zip
    elif factory_zip.exists() and factory_zip.is_file():
        zip_file = factory_zip
    else:
        # Check if bundle_path itself is a zip file
        if bundle_path.is_file() and bundle_path.suffix == ".zip":
            zip_file = bundle_path
        else:
            # Bundle folder exists but no zip file - create one on-the-fly
            # Create a zip file in the bundle directory (cache it for future use)
            zip_file_path = bundle_path / f"{codename}-factory-{version}.zip"
            
            # Check if we already created it
            if zip_file_path.exists() and zip_file_path.is_file():
                zip_file = zip_file_path
            else:
                # Create zip archive of the bundle folder
                try:
                    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        # Add all files in the bundle directory
                        for root, dirs, files in os.walk(bundle_path):
                            # Skip hidden files and directories
                            dirs[:] = [d for d in dirs if not d.startswith('.')]
                            
                            for file in files:
                                if file.startswith('.') or file.endswith('.zip'):
                                    # Skip hidden files and existing zip files
                                    continue
                                file_path = Path(root) / file
                                # Get relative path from bundle_path
                                try:
                                    arcname = file_path.relative_to(bundle_path)
                                    zipf.write(file_path, arcname)
                                except ValueError:
                                    # Skip if path is outside bundle_path
                                    continue
                    
                    zip_file = zip_file_path
                except Exception as e:
                    # Clean up on error
                    if zip_file_path.exists():
                        try:
                            zip_file_path.unlink()
                        except:
                            pass
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create bundle archive: {str(e)}"
                    )
    
    if not zip_file or not zip_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Bundle file not found: {zip_file}"
        )
    
    return zip_file


@router.head("/releases/{codename}/{version}/download")
@router.get("/releases/{codename}/{version}/download")
async def download_bundle_file(codename: str, version: str, request: Request):
    """
    Download a bundle ZIP file from the bundles folder.
    Supports both HEAD (for checking availability) and GET (for downloading).
    Returns the image.zip file if it exists, or creates a ZIP archive of the bundle folder.
    """
    try:
        zip_file = _get_bundle_zip_file(codename, version)
    except HTTPException:
        raise
    
    # For HEAD requests, just return headers without body
    if request.method == "HEAD":
        file_size = zip_file.stat().st_size
        return Response(
            status_code=200,
            headers={
                "Content-Type": "application/zip",
                "Content-Length": str(file_size),
                "Content-Disposition": f"attachment; filename={codename}-factory-{version}.zip"
            }
        )
    
    # For GET requests, return the file
    return FileResponse(
        path=str(zip_file),
        filename=f"{codename}-factory-{version}.zip",
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={codename}-factory-{version}.zip"
        }
    )


@router.get("/releases/{codename}/{version}/file/{filename}")
async def download_bundle_file_item(codename: str, version: str, filename: str):
    """
    Download a specific file from a bundle (e.g., boot.img, system.img, etc.).
    """
    bundle = get_bundle_for_codename(codename, version=version)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail=f"Bundle not found for codename: {codename}, version: {version}"
        )
    
    bundle_path = Path(bundle["path"])
    
    # Security: Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )
    
    file_path = bundle_path / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}"
        )
    
    # Ensure file is within bundle directory (security check)
    try:
        file_path.resolve().relative_to(bundle_path.resolve())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid file path"
        )
    
    # Determine media type based on file extension
    media_type = "application/octet-stream"
    if filename.endswith(".img"):
        media_type = "application/octet-stream"
    elif filename.endswith(".zip"):
        media_type = "application/zip"
    elif filename.endswith(".sh"):
        media_type = "text/x-shellscript"
    elif filename.endswith(".bat"):
        media_type = "text/plain"
    elif filename.endswith(".json"):
        media_type = "application/json"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )


@router.get("/releases/{codename}/{version}/list")
async def list_bundle_files(codename: str, version: str):
    """
    List all files in a bundle directory.
    """
    bundle = get_bundle_for_codename(codename, version=version)
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail=f"Bundle not found for codename: {codename}, version: {version}"
        )
    
    bundle_path = Path(bundle["path"])
    
    if not bundle_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Bundle directory not found: {bundle_path}"
        )
    
    files = []
    try:
        for item in bundle_path.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "size": item.stat().st_size,
                    "path": f"/bundles/releases/{codename}/{version}/file/{item.name}"
                })
            elif item.is_dir():
                # Recursively list files in subdirectories
                for subitem in item.rglob("*"):
                    if subitem.is_file():
                        relative_path = subitem.relative_to(bundle_path)
                        files.append({
                            "name": str(relative_path),
                            "size": subitem.stat().st_size,
                            "path": f"/bundles/releases/{codename}/{version}/file/{relative_path}"
                        })
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing bundle files: {str(e)}"
        )
    
    return {
        "codename": codename,
        "version": version,
        "bundle_path": str(bundle_path),
        "files": files,
        "total_files": len(files)
    }

