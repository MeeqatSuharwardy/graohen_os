from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
from ..utils.flash import start_flash_job, get_flash_job, cancel_flash_job, flash_jobs
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


class FlashStartRequest(BaseModel):
    device_serial: str
    bundle_path: str
    dry_run: bool = False
    confirmation_token: Optional[str] = None


@router.post("/start")
async def start_flash(request: FlashStartRequest):
    """Start a flash job"""
    try:
        job_id = start_flash_job(
            device_serial=request.device_serial,
            bundle_path=request.bundle_path,
            dry_run=request.dry_run,
            confirmation_token=request.confirmation_token,
        )
        return {"job_id": job_id, "status": "started"}
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

