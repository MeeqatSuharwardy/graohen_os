import subprocess
import os
import platform
from pathlib import Path
from typing import Optional, Dict, Any
from ..config import settings

# Job storage (in production, use a proper job queue)
flash_jobs: Dict[str, Dict[str, Any]] = {}


def start_flash_job(
    device_serial: str,
    bundle_path: str,
    dry_run: bool = False,
    confirmation_token: Optional[str] = None,
) -> str:
    """Start a flash job"""
    import uuid
    job_id = str(uuid.uuid4())
    
    # Safety check: require typed confirmation
    if settings.REQUIRE_TYPED_CONFIRMATION:
        expected_token = f"FLASH {device_serial}"
        if confirmation_token != expected_token:
            raise ValueError(f"Invalid confirmation token. Expected: {expected_token}")
    
    # Verify bundle
    from .bundles import verify_bundle
    verification = verify_bundle(bundle_path)
    if not verification["valid"]:
        raise ValueError(f"Bundle verification failed: {verification['errors']}")
    
    # Create job
    job = {
        "id": job_id,
        "device_serial": device_serial,
        "bundle_path": bundle_path,
        "dry_run": dry_run,
        "status": "starting",
        "logs": [],
        "process": None,
    }
    flash_jobs[job_id] = job
    
    # Start flashing process (in a thread to avoid blocking)
    import threading
    thread = threading.Thread(target=_run_flash, args=(job,))
    thread.daemon = True
    thread.start()
    
    return job_id


def _run_flash(job: Dict[str, Any]):
    """Run the flash process"""
    bundle_path = Path(job["bundle_path"])
    device_serial = job["device_serial"]
    dry_run = job["dry_run"]
    
    # Determine flash script
    is_windows = platform.system() == "Windows"
    flash_script = bundle_path / ("flash-all.bat" if is_windows else "flash-all.sh")
    
    if not flash_script.exists():
        job["status"] = "failed"
        job["logs"].append("ERROR: Flash script not found")
        return
    
    # Prepare command
    if is_windows:
        cmd = [str(flash_script)]
    else:
        cmd = ["bash", str(flash_script)]
    
    if dry_run:
        job["status"] = "completed"
        job["logs"].append(f"[DRY RUN] Would execute: {' '.join(cmd)}")
        job["logs"].append(f"[DRY RUN] Device: {device_serial}")
        return
    
    # Execute flash script
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(bundle_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        
        job["process"] = process
        job["status"] = "running"
        
        # Stream output
        for line in iter(process.stdout.readline, ''):
            if line:
                job["logs"].append(line.strip())
        
        process.wait()
        
        if process.returncode == 0:
            job["status"] = "completed"
        else:
            job["status"] = "failed"
            job["logs"].append(f"Process exited with code {process.returncode}")
            
    except Exception as e:
        job["status"] = "failed"
        job["logs"].append(f"ERROR: {str(e)}")
    finally:
        if job["process"]:
            job["process"] = None


def get_flash_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get flash job status"""
    return flash_jobs.get(job_id)


def cancel_flash_job(job_id: str) -> bool:
    """Cancel a flash job"""
    job = flash_jobs.get(job_id)
    if not job:
        return False
    
    if job["process"]:
        try:
            job["process"].terminate()
            job["status"] = "cancelled"
            return True
        except Exception:
            pass
    
    return False
