from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
from ..utils.flash import start_flash_job, get_flash_job, cancel_flash_job, flash_jobs
from ..utils.tools import identify_device
from ..utils.bundles import get_bundle_for_codename, index_bundles
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


class FlashStartRequest(BaseModel):
    device_serial: str
    bundle_path: Optional[str] = None
    dry_run: bool = False
    confirmation_token: Optional[str] = None


@router.post("/start")
async def start_flash(request: FlashStartRequest):
    """Start a flash job - auto-detects bundle if bundle_path not provided"""
    try:
        # If bundle_path is not provided, try to find it automatically
        bundle_path = request.bundle_path
        
        if not bundle_path:
            # Identify device codename from serial
            device_info = identify_device(request.device_serial)
            
            if not device_info:
                # If identification fails, try to find any bundle and use the first one
                # This allows flashing even if device identification fails
                all_bundles = index_bundles()
                if not all_bundles:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not identify device codename for serial: {request.device_serial} "
                               f"and no bundles found. Please ensure the device is connected and in ADB or Fastboot mode, "
                               f"or download a bundle first."
                    )
                
                # Use the first available bundle (user should ensure it's correct)
                first_codename = list(all_bundles.keys())[0]
                bundle = get_bundle_for_codename(first_codename)
                if bundle:
                    bundle_path = bundle["path"]
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Could not identify device and no valid bundles found. "
                               f"Please download a bundle for your device first."
                    )
            else:
                codename = device_info["codename"]
                
                # Find the latest bundle for this codename
                bundle = get_bundle_for_codename(codename)
                if not bundle:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No bundle found for device codename: {codename}. "
                               f"Please download a bundle first or specify bundle_path."
                    )
                
                bundle_path = bundle["path"]
        
        job_id = start_flash_job(
            device_serial=request.device_serial,
            bundle_path=bundle_path,
            dry_run=request.dry_run,
            confirmation_token=request.confirmation_token,
        )
        return {"job_id": job_id, "status": "started", "bundle_path": bundle_path}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_flash_jobs():
    """List all flash jobs"""
    return {
        "jobs": [
            {
                "id": job["id"],
                "device_serial": job["device_serial"],
                "status": job["status"],
                "dry_run": job["dry_run"],
            }
            for job in flash_jobs.values()
        ]
    }


@router.get("/jobs/{job_id}")
async def get_flash_job_endpoint(job_id: str):
    """Get flash job status"""
    job = get_flash_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job["id"],
        "device_serial": job["device_serial"],
        "status": job["status"],
        "dry_run": job["dry_run"],
        "log_count": len(job["logs"]),
    }


@router.get("/jobs/{job_id}/stream")
async def stream_flash_job(job_id: str):
    """Stream flash job logs via SSE"""
    job = get_flash_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def event_generator():
        last_log_count = 0
        while True:
            job = get_flash_job(job_id)
            if not job:
                yield {"event": "error", "data": json.dumps({"message": "Job not found"})}
                break
            
            # Send new logs
            if len(job["logs"]) > last_log_count:
                for log_line in job["logs"][last_log_count:]:
                    yield {"event": "log", "data": json.dumps({"line": log_line})}
                last_log_count = len(job["logs"])
            
            # Send status updates
            if job["status"] in ["completed", "failed", "cancelled"]:
                yield {"event": "status", "data": json.dumps({"status": job["status"]})}
                yield {"event": "close", "data": json.dumps({})}
                break
            
            yield {"event": "heartbeat", "data": json.dumps({})}
            
            import asyncio
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())


@router.post("/jobs/{job_id}/cancel")
async def cancel_flash_job_endpoint(job_id: str):
    """Cancel a flash job"""
    success = cancel_flash_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    
    return {"success": True, "message": "Job cancelled"}

