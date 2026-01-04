from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import platform
import json
from ..config import settings
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

# Job storage (in production, use a proper job queue)
build_jobs: dict = {}


@router.post("/start")
async def start_build():
    """Start a build job (Linux only)"""
    if platform.system() != "Linux":
        raise HTTPException(
            status_code=400,
            detail="Build feature is only available on Linux"
        )
    
    if not settings.BUILD_ENABLE:
        raise HTTPException(
            status_code=400,
            detail="Build feature is disabled (BUILD_ENABLE=false)"
        )
    
    # TODO: Implement actual build logic
    import uuid
    job_id = str(uuid.uuid4())
    
    build_jobs[job_id] = {
        "id": job_id,
        "status": "not_implemented",
        "logs": ["Build feature not yet implemented"],
    }
    
    return {"job_id": job_id, "status": "started", "message": "Build feature placeholder"}


@router.get("/jobs/{build_job_id}/stream")
async def stream_build_job(build_job_id: str):
    """Stream build job logs via SSE"""
    job = build_jobs.get(build_job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def event_generator():
        for log_line in job.get("logs", []):
            yield {"event": "log", "data": json.dumps({"line": log_line})}
        yield {"event": "status", "data": json.dumps({"status": job["status"]})}
        yield {"event": "close", "data": json.dumps({})}
    
    return EventSourceResponse(event_generator())


@router.post("/jobs/{build_job_id}/cancel")
async def cancel_build_job(build_job_id: str):
    """Cancel a build job"""
    if build_job_id not in build_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    build_jobs[build_job_id]["status"] = "cancelled"
    return {"success": True, "message": "Job cancelled"}

