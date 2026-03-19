import subprocess
import os
import platform
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.config import settings

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
    
    # Create job FIRST before starting thread
    job = {
        "id": job_id,
        "device_serial": device_serial,
        "bundle_path": bundle_path,
        "dry_run": dry_run,
        "status": "starting",
        "logs": [],
        "process": None,
    }
    
    # Store job immediately so it can be queried
    flash_jobs[job_id] = job
    
    # Start flashing process (in a thread to avoid blocking)
    import threading
    thread = threading.Thread(target=_run_flash, args=(job,))
    thread.daemon = True
    thread.start()
    
    return job_id


def _run_flash(job: Dict[str, Any]):
    """Run the flash process"""
    # Ensure job persists in flash_jobs dict
    job_id = job.get("id")
    if job_id:
        flash_jobs[job_id] = job
    
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
        import traceback
        job["logs"].append(f"Traceback: {traceback.format_exc()}")
    finally:
        if job["process"]:
            job["process"] = None
        # Ensure job persists in flash_jobs dict
        job_id = job.get("id")
        if job_id:
            flash_jobs[job_id] = job


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


async def execute_flash_direct(
    device_serial: str,
    bundle_path: str,
    dry_run: bool = False,
    confirmation_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute flash directly and return result with logs"""
    # Safety check: require typed confirmation
    if settings.REQUIRE_TYPED_CONFIRMATION:
        expected_token = f"FLASH {device_serial}"
        if confirmation_token != expected_token:
            raise ValueError(f"Invalid confirmation token. Expected: {expected_token}")
    
    # Verify bundle
    from .bundles import verify_bundle
    verification = verify_bundle(bundle_path)
    
    # Only fail on actual errors, not warnings
    if verification["errors"]:
        raise ValueError(f"Bundle verification failed: {verification['errors']}")
    
    bundle_path_obj = Path(bundle_path)
    is_windows = platform.system() == "Windows"
    flash_script = bundle_path_obj / ("flash-all.bat" if is_windows else "flash-all.sh")
    
    if not flash_script.exists():
        raise ValueError(f"Flash script not found at: {flash_script}")
    
    logs: List[str] = []
    logs.append(f"Starting flash process for device: {device_serial}")
    logs.append(f"Using bundle: {bundle_path}")
    
    if dry_run:
        logs.append(f"[DRY RUN] Would execute: bash {flash_script}")
        return {
            "success": True,
            "dry_run": True,
            "logs": logs,
            "message": "Dry run completed"
        }
    
    # Prepare command
    if is_windows:
        cmd = [str(flash_script)]
    else:
        cmd = ["bash", str(flash_script)]
    
    # Set environment variables
    env = os.environ.copy()
    env["ANDROID_SERIAL"] = device_serial
    fastboot_dir = os.path.dirname(settings.FASTBOOT_PATH)
    current_path = env.get("PATH", "")
    if fastboot_dir not in current_path:
        env["PATH"] = f"{fastboot_dir}:{current_path}"
    
    logs.append(f"Command: {' '.join(cmd)}")
    logs.append(f"Fastboot path: {settings.FASTBOOT_PATH}")
    logs.append("Flash process starting...")
    
    try:
        # Execute in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _run_flash_sync,
            cmd,
            str(bundle_path_obj),
            env,
            logs
        )
        
        return {
            "success": result["success"],
            "logs": result["logs"],
            "exit_code": result.get("exit_code"),
            "message": result.get("message", "Flash completed" if result["success"] else "Flash failed")
        }
    except Exception as e:
        error_msg = str(e)
        logs.append(f"ERROR: {error_msg}")
        import traceback
        traceback_str = traceback.format_exc()
        logs.append(f"Traceback: {traceback_str}")
        return {
            "success": False,
            "logs": logs,
            "message": f"Flash failed: {error_msg}",
            "error": error_msg,
            "traceback": traceback_str
        }


def _run_flash_sync(cmd: List[str], cwd: str, env: Dict[str, str], logs: List[str]) -> Dict[str, Any]:
    """Run flash synchronously (called from thread pool)"""
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,  # Unbuffered for real-time output
            universal_newlines=True,
            env=env,
        )
        
        logs.append("Flash process started, streaming output...")
        
        # Stream output in real-time
        import select
        
        if hasattr(select, 'select'):
            # Unix: use select for non-blocking read
            while True:
                if process.poll() is not None:
                    remaining = process.stdout.read()
                    if remaining:
                        for line in remaining.splitlines():
                            if line.strip():
                                logs.append(line.strip())
                    break
                
                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line:
                            logs.append(line)
        else:
            # Windows: fallback
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.strip()
                    if line:
                        logs.append(line)
                if process.poll() is not None:
                    break
        
        return_code = process.poll()
        
        if return_code == 0:
            logs.append("✓ Flash completed successfully!")
            return {"success": True, "exit_code": return_code, "logs": logs, "message": "Flash completed successfully"}
        else:
            error_msg = f"Flash failed with exit code: {return_code}"
            logs.append(f"✗ {error_msg}")
            return {
                "success": False,
                "exit_code": return_code,
                "logs": logs,
                "message": error_msg
            }
            
    except Exception as e:
        error_msg = str(e)
        logs.append(f"ERROR: {error_msg}")
        import traceback
        traceback_str = traceback.format_exc()
        logs.append(f"Traceback: {traceback_str}")
        return {
            "success": False,
            "logs": logs,
            "message": f"Flash execution error: {error_msg}",
            "error": error_msg
        }
