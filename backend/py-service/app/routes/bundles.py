from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..utils.bundles import (
    index_bundles,
    get_bundle_for_codename,
    verify_bundle,
    get_available_releases,
    download_release,
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

