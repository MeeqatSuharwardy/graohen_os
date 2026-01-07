from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import subprocess
import asyncio
import os
import sys
from pathlib import Path
from sse_starlette.sse import EventSourceResponse
from ..utils.tools import identify_device
from ..utils.bundles import get_bundle_for_codename, index_bundles
from ..utils.flash import execute_flash_direct, flash_jobs, start_flash_job, get_flash_job, cancel_flash_job
from ..config import settings

router = APIRouter()


class FlashRequest(BaseModel):
    device_serial: str
    bundle_path: Optional[str] = None
    dry_run: bool = False
    confirmation_token: Optional[str] = None


class UnlockAndFlashRequest(BaseModel):
    device_serial: str
    bundle_path: Optional[str] = None
    skip_unlock: bool = False


@router.post("/execute")
async def execute_flash(request: FlashRequest):
    """Execute flash directly - auto-detects bundle if bundle_path not provided"""
    try:
        # If bundle_path is not provided, try to find it automatically
        bundle_path = request.bundle_path
        
        if not bundle_path:
            # Identify device codename from serial
            device_info = identify_device(request.device_serial)
            
            if not device_info:
                # If identification fails, try to find any bundle and use the first one
                all_bundles = index_bundles()
                if not all_bundles:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not identify device codename for serial: {request.device_serial} "
                               f"and no bundles found. Please ensure the device is connected and in ADB or Fastboot mode, "
                               f"or download a bundle first."
                    )
                
                # Use the first available bundle
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
        
        # Execute flash directly
        result = await execute_flash_direct(
            device_serial=request.device_serial,
            bundle_path=bundle_path,
            dry_run=request.dry_run,
            confirmation_token=request.confirmation_token,
        )
        
        return result
        
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
    """Get flash job status and logs"""
    job = get_flash_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job["id"],
        "device_serial": job["device_serial"],
        "status": job["status"],
        "dry_run": job.get("dry_run", False),
        "log_count": len(job.get("logs", [])),
        "logs": job.get("logs", []),  # Include logs in response
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


@router.post("/unlock-and-flash")
async def unlock_and_flash(request: UnlockAndFlashRequest):
    """
    Unlock bootloader and flash GrapheneOS in one operation.
    This endpoint uses the flasher.py script which handles the complete workflow:
    1. Preflight checks (OEM unlock verification, reboot to bootloader)
    2. Bootloader unlock (with user confirmation)
    3. Flash GrapheneOS
    4. Reboot device
    """
    try:
        # Find bundle path if not provided
        bundle_path = request.bundle_path
        
        if not bundle_path:
            # Try to identify device to get codename
            device_info = identify_device(request.device_serial)
            
            if device_info:
                # Device identified successfully - use its codename
                codename = device_info["codename"]
                
                # Find the latest bundle for this codename
                bundle = get_bundle_for_codename(codename)
                if bundle:
                    bundle_path = bundle["path"]
                else:
                    # Device identified but no bundle found - check for any bundles
                    all_bundles = index_bundles()
                    if all_bundles:
                        # Use the first available bundle as fallback
                        first_codename = list(all_bundles.keys())[0]
                        bundle = get_bundle_for_codename(first_codename)
                        if bundle:
                            bundle_path = bundle["path"]
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Device identified as {codename} but no bundle found. "
                                   f"Please download a bundle first or specify bundle_path."
                        )
            else:
                # Device identification failed (may be rebooting or timing out)
                # Try to use any available bundle as fallback
                all_bundles = index_bundles()
                if not all_bundles:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not identify device codename for serial: {request.device_serial} "
                               f"and no bundles found. Please ensure the device is connected and in fastboot mode, "
                               f"or download a bundle first, or provide bundle_path."
                    )
                
                # Use the first available bundle as fallback
                first_codename = list(all_bundles.keys())[0]
                bundle = get_bundle_for_codename(first_codename)
                if bundle:
                    bundle_path = bundle["path"]
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Could not identify device and no valid bundles found. "
                               f"Please download a bundle first or specify bundle_path."
                    )
        
        # Find extracted bundle directory (handle both zip and extracted)
        bundle_path_obj = Path(bundle_path)
        
        # Check if it's a zip file or already extracted
        extracted_dir = bundle_path_obj
        if bundle_path_obj.is_file() and bundle_path_obj.suffix == ".zip":
            # If it's a zip, look for extracted directory with same name
            extracted_name = bundle_path_obj.stem
            parent_dir = bundle_path_obj.parent
            extracted_dir = parent_dir / extracted_name
            if not extracted_dir.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Bundle appears to be a zip file but extracted directory not found: {extracted_dir}. "
                           f"Please extract the bundle first."
                )
        elif bundle_path_obj.is_dir():
            # Check for panther-install-* subdirectory
            panther_dirs = list(bundle_path_obj.glob("panther-install-*"))
            if panther_dirs:
                extracted_dir = panther_dirs[0]
        
        # Verify flasher.py exists
        # __file__ is at: backend/py-service/app/routes/flash.py
        # flasher.py is at: backend/flasher.py
        # So we need to go up 3 levels: routes -> app -> py-service -> backend
        flasher_script = Path(__file__).parent.parent.parent.parent / "flasher.py"
        
        # Alternative: check relative to backend directory
        if not flasher_script.exists():
            # Try from backend directory
            backend_dir = Path(__file__).parent.parent.parent.parent
            flasher_script = backend_dir / "flasher.py"
        
        if not flasher_script.exists():
            # Last resort: try absolute path from project root
            import os
            project_root = Path(__file__).parent.parent.parent.parent.parent
            flasher_script = project_root / "graohen_os" / "backend" / "flasher.py"
        
        if not flasher_script.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Flasher script not found. Searched: {flasher_script}. "
                       f"Please ensure flasher.py exists in the backend directory."
            )
        
        # Create job for tracking
        import uuid
        job_id = str(uuid.uuid4())
        
        job = {
            "id": job_id,
            "device_serial": request.device_serial,
            "bundle_path": str(extracted_dir),
            "status": "starting",
            "logs": [],
            "process": None,
        }
        
        flash_jobs[job_id] = job
        
        # Start the unlock and flash process in background
        import threading
        thread = threading.Thread(
            target=_run_unlock_and_flash,
            args=(job, flasher_script, extracted_dir, request.device_serial, request.skip_unlock)
        )
        thread.daemon = True
        thread.start()
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "Unlock and flash process started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start unlock and flash: {str(e)}")


def _run_unlock_and_flash(job: dict, flasher_script: Path, bundle_path: Path, device_serial: str, skip_unlock: bool):
    """Run the unlock and flash process using flasher.py"""
    import sys
    import logging
    
    # Set up logging
    logger = logging.getLogger(__name__)
    
    job_id = job.get("id")
    try:
        logger.info(f"Starting unlock and flash for job {job_id}, device {device_serial}")
        logger.info(f"Flasher script: {flasher_script}")
        logger.info(f"Bundle path: {bundle_path}")
        logger.info(f"Skip unlock: {skip_unlock}")
        
        job["status"] = "running"
        initial_logs = [
            f"Starting unlock and flash process for device: {device_serial}",
            f"Using bundle: {bundle_path}",
            f"Flasher script: {flasher_script}",
        ]
        job["logs"].extend(initial_logs)
        # Ensure job is saved
        if job_id:
            flash_jobs[job_id] = job
        
        # Build command
        import sys
        python_cmd = sys.executable
        
        # Use -u flag to run Python in unbuffered mode (immediate output)
        cmd = [
            python_cmd,
            "-u",  # Unbuffered output
            str(flasher_script),
            "--fastboot-path", settings.FASTBOOT_PATH,
            "--adb-path", settings.ADB_PATH,
            "--bundle-path", str(bundle_path),
            "--device-serial", device_serial,
            "--confirm",
        ]
        
        if skip_unlock:
            cmd.append("--skip-unlock")
        
        cmd_str = ' '.join(cmd)
        logger.info(f"Executing command: {cmd_str}")
        job["logs"].append(f"Command: {cmd_str}")
        if job_id:
            flash_jobs[job_id] = job
        
        try:
            # Set environment to ensure unbuffered output
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                text=True,
                bufsize=0,  # Unbuffered for immediate output
                universal_newlines=True,
                env=env,  # Pass environment with PYTHONUNBUFFERED
            )
        except Exception as e:
            job["status"] = "failed"
            job["logs"].append(f"❌ Failed to start process: {str(e)}")
            import traceback
            job["logs"].append(f"Traceback: {traceback.format_exc()}")
            if job_id:
                flash_jobs[job_id] = job
            return
        
        job["process"] = process
        logger.info(f"Process started successfully with PID: {process.pid}")
        job["logs"].append(f"Process started (PID: {process.pid})")
        if job_id:
            flash_jobs[job_id] = job
        
        # Read output line by line (both stdout and stderr are combined)
        # Use a loop that handles both live streaming and final output
        import select
        
        output_lines = []
        
        # Simple approach: read all output in real-time
        # Use readline() with a loop that checks if process is alive
        import threading
        
        def read_output():
            """Read output in a separate thread"""
            try:
                logger.info("Starting output reader thread")
                line_count = 0
                # Give process a moment to start producing output
                import time
                time.sleep(0.1)
                
                # Check if process is still alive
                if process.poll() is not None:
                    logger.warning(f"Process already exited with code {process.poll()} before reading output")
                
                for line in iter(process.stdout.readline, ''):
                    if line:
                        line_stripped = line.rstrip()
                        output_lines.append(line_stripped)
                        line_count += 1
                        logger.info(f"Received line {line_count}: {line_stripped[:100]}...")  # Changed to INFO for debugging
                        # Process immediately for real-time updates
                        _process_flasher_output(job, line_stripped, job_id)
                
                logger.info(f"Output reader thread finished. Total lines read: {line_count}")
                if line_count == 0:
                    logger.warning("No output lines were read from process!")
                    # Try to read any remaining data
                    try:
                        remaining = process.stdout.read()
                        if remaining:
                            logger.info(f"Found remaining output: {remaining[:200]}")
                            for line in remaining.splitlines():
                                if line.strip():
                                    output_lines.append(line.strip())
                                    _process_flasher_output(job, line.strip(), job_id)
                    except:
                        pass
                
                process.stdout.close()
            except Exception as e:
                logger.error(f"Error in output reader thread: {e}", exc_info=True)
                job["logs"].append(f"❌ Error reading output: {str(e)}")
                if job_id:
                    flash_jobs[job_id] = job
        
        # Start reader thread
        reader_thread = threading.Thread(target=read_output, daemon=True)
        reader_thread.start()
        
        # Wait for process to complete and get return code
        logger.info("Waiting for process to complete...")
        return_code = process.wait()
        logger.info(f"Process completed with return code: {return_code}")
        
        # Process finished, wait for reader thread to finish (with timeout)
        logger.info("Waiting for output reader thread to finish...")
        reader_thread.join(timeout=2.0)
        logger.info(f"Reader thread finished. Total output lines: {len(output_lines)}")
        
        # Read any remaining output
        try:
            remaining = process.stdout.read()
            if remaining:
                for line in remaining.splitlines():
                    if line.strip():
                        output_lines.append(line.strip())
                        _process_flasher_output(job, line.strip(), job_id)
        except:
            pass
        
        # Output has already been processed in real-time by the reader thread
        # Just ensure job state is saved
        if job_id:
            flash_jobs[job_id] = job
        
        # If we got no output but process exited, that's suspicious
        if not output_lines and return_code != 0:
            error_msg = f"Process exited with code {return_code} but produced no output"
            logger.error(error_msg)
            logger.error(f"Python version: {sys.version}")
            logger.error(f"Command was: {cmd_str}")
            job["status"] = "failed"
            job["logs"].append(f"❌ ERROR: {error_msg}")
            job["logs"].append("This indicates the script failed to start or crashed immediately")
            job["logs"].append(f"Python version: {sys.version.split()[0]}")
            job["logs"].append(f"Possible causes:")
            job["logs"].append(f"  - Python version mismatch")
            job["logs"].append(f"  - Missing dependencies")
            job["logs"].append(f"  - Syntax error in flasher.py")
            job["logs"].append(f"  - Path/permission issues")
            if job_id:
                flash_jobs[job_id] = job
        elif not output_lines and return_code == 0:
            warning_msg = "Process completed with no output"
            logger.warning(warning_msg)
            job["logs"].append(f"⚠️ {warning_msg}")
            if job_id:
                flash_jobs[job_id] = job
        
        # Check final status
        if return_code != 0:
            job["status"] = "failed"
            if not any("failed" in log.lower() or "error" in log.lower() for log in job["logs"]):
                job["logs"].append(f"✗ Process exited with error code: {return_code}")
        elif job["status"] != "failed" and job["status"] != "completed":
            # Process completed successfully but status wasn't set
            job["status"] = "completed"
            if not any("completed successfully" in log.lower() for log in job["logs"]):
                job["logs"].append("✓ Unlock and flash completed successfully!")
            
    except Exception as e:
        job["status"] = "failed"
        error_msg = f"ERROR: {str(e)}"
        job["logs"].append(error_msg)
        import traceback
        job["logs"].append(f"Traceback: {traceback.format_exc()}")
    finally:
        if job.get("process"):
            job["process"] = None
        # Ensure job persists with final state
        if job_id:
            flash_jobs[job_id] = job


def _process_flasher_output(job: dict, line: str, job_id: str):
    """Process a line of output from flasher.py"""
    import logging
    logger = logging.getLogger(__name__)
    
    if not line:
        return
    
    # Always append the line first (so we don't lose any output)
    try:
        # Try to parse as JSON log
        log_data = json.loads(line)
        if "message" in log_data:
            status = log_data.get("status", "info")
            step = log_data.get("step", "unknown")
            partition = log_data.get("partition")
            message = log_data["message"]
            
            # Format log message
            log_line = f"[{step}]"
            if partition:
                log_line += f" [{partition}]"
            log_line += f" {message}"
            
            job["logs"].append(log_line)
            if job_id:
                flash_jobs[job_id] = job
        elif "success" in log_data:
            # Final result
            if log_data.get("success"):
                job["status"] = "completed"
                job["logs"].append("✓ Unlock and flash completed successfully!")
            else:
                job["status"] = "failed"
                job["logs"].append(f"✗ Failed: {log_data.get('message', 'Unknown error')}")
            if job_id:
                flash_jobs[job_id] = job
        elif "status" in log_data and log_data.get("status") == "error":
            # Error log
            error_msg = log_data.get("message", line)
            logger.error(f"Error from flasher.py: {error_msg}")
            job["status"] = "failed"
            job["logs"].append(f"❌ ERROR: {error_msg}")
            if job_id:
                flash_jobs[job_id] = job
        elif "step" in log_data:
            # Any log with a step field
            step = log_data.get("step", "unknown")
            message = log_data.get("message", line)
            status = log_data.get("status", "info")
            log_line = f"[{step}] {message}"
            job["logs"].append(log_line)
            if job_id:
                flash_jobs[job_id] = job
    except json.JSONDecodeError:
        # Not JSON - could be Python traceback, stderr output, or other text
        # Always show it, but mark errors appropriately
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ['error', 'failed', 'fail', 'unable', 'cannot', 'traceback', 'exception']):
            job["logs"].append(f"❌ {line}")
            # If it looks like a fatal error, mark job as failed
            if any(keyword in line_lower for keyword in ['traceback', 'exception', 'fatal']):
                job["status"] = "failed"
        elif line.strip().startswith("File ") and "line" in line and "in" in line:
            # Python traceback line
            job["logs"].append(f"   {line}")
        else:
            # Regular output
            job["logs"].append(line)
        if job_id:
            flash_jobs[job_id] = job
        
        # Check final status
        if return_code != 0:
            job["status"] = "failed"
            if not any("failed" in log.lower() or "error" in log.lower() for log in job["logs"]):
                job["logs"].append(f"✗ Process exited with error code: {return_code}")
        elif job["status"] != "failed" and job["status"] != "completed":
            # Process completed successfully but status wasn't set
            job["status"] = "completed"
            if not any("completed successfully" in log.lower() for log in job["logs"]):
                job["logs"].append("✓ Unlock and flash completed successfully!")
            
    except Exception as e:
        job["status"] = "failed"
        error_msg = f"ERROR: {str(e)}"
        job["logs"].append(error_msg)
        import traceback
        job["logs"].append(f"Traceback: {traceback.format_exc()}")
    finally:
        if job.get("process"):
            job["process"] = None
        # Ensure job persists with final state
        if job_id:
            flash_jobs[job_id] = job

