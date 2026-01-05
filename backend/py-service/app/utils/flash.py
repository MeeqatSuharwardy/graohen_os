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
    
    # Only fail on actual errors, not warnings (like SHA256 mismatch for renamed files)
    if verification["errors"]:
        raise ValueError(f"Bundle verification failed: {verification['errors']}")
    
    # Log warnings but don't fail
    if verification["warnings"]:
        import logging
        logger = logging.getLogger(__name__)
        for warning in verification["warnings"]:
            logger.warning(f"Bundle verification warning: {warning}")
    
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
        # Set environment variables for device serial and fastboot path
        env = os.environ.copy()
        env["ANDROID_SERIAL"] = device_serial
        # Ensure fastboot is in PATH
        fastboot_dir = os.path.dirname(settings.FASTBOOT_PATH)
        current_path = env.get("PATH", "")
        if fastboot_dir not in current_path:
            env["PATH"] = f"{fastboot_dir}:{current_path}"
        
        job["status"] = "running"
        job["logs"].append(f"Starting flash process for device: {device_serial}")
        job["logs"].append(f"Using bundle: {bundle_path}")
        job["logs"].append(f"Command: {' '.join(cmd)}")
        job["logs"].append(f"Fastboot path: {settings.FASTBOOT_PATH}")
        
        process = subprocess.Popen(
            cmd,
            cwd=str(bundle_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,  # Unbuffered for real-time output
            universal_newlines=True,
            env=env,
        )
        
        job["process"] = process
        job["logs"].append("Flash process started, streaming output...")
        
        # Stream output in real-time (non-blocking)
        import select
        import sys
        
        # Use select for non-blocking read (Unix only)
        if hasattr(select, 'select'):
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    # Process finished, read remaining output
                    remaining = process.stdout.read()
                    if remaining:
                        for line in remaining.splitlines():
                            if line.strip():
                                job["logs"].append(line.strip())
                    break
                
                # Check if there's data to read (non-blocking)
                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line:  # Only add non-empty lines
                            job["logs"].append(line)
        else:
            # Fallback for Windows or systems without select
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.strip()
                    if line:
                        job["logs"].append(line)
                if process.poll() is not None:
                    break
        
        return_code = process.poll()
        
        if return_code == 0:
            job["status"] = "completed"
            job["logs"].append("✓ Flash completed successfully!")
        else:
            job["status"] = "failed"
            job["logs"].append(f"✗ Flash failed with exit code: {return_code}")
            
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
