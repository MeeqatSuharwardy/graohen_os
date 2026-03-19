import subprocess
import os
import logging
from typing import List, Dict, Optional
from ..config import settings

logger = logging.getLogger(__name__)


def check_tool_availability(tool_path: str) -> bool:
    """Check if a tool is available at the given path"""
    if not tool_path or not os.path.exists(tool_path):
        return False
    try:
        result = subprocess.run(
            [tool_path, "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def run_adb_command(args: List[str], serial: Optional[str] = None, timeout: int = 30) -> Optional[subprocess.CompletedProcess]:
    """Run an ADB command with timeout handling"""
    cmd = [settings.ADB_PATH]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(args)
    
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        logger.warning(f"ADB command timed out after {timeout}s: {' '.join(cmd)}")
        # Return a mock result object with timeout indication
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds (device may be rebooting or unresponsive)"
        )
        return result
    except Exception as e:
        logger.error(f"Error running ADB command {' '.join(cmd)}: {e}")
        return None


def run_fastboot_command(args: List[str], serial: Optional[str] = None, timeout: int = 30) -> Optional[subprocess.CompletedProcess]:
    """Run a Fastboot command with timeout handling"""
    cmd = [settings.FASTBOOT_PATH]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(args)
    
    try:
        # Run fastboot command
        # Note: fastboot often outputs to stderr, even for successful commands
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            # Don't fail on non-zero return codes - fastboot can return non-zero on warnings
        )
        
        # Log command execution for debugging (only in debug mode)
        logger.debug(f"Fastboot command: {' '.join(cmd)}, returncode: {result.returncode}")
        if result.stdout:
            logger.debug(f"Fastboot stdout: {result.stdout[:200]}")
        if result.stderr:
            logger.debug(f"Fastboot stderr: {result.stderr[:200]}")
        
        # Fastboot sometimes returns non-zero exit codes even on success
        # Always return the result so caller can check output
        return result
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Fastboot command timed out after {timeout}s: {' '.join(cmd)}")
        # Return a mock result object with timeout indication
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds (device may be rebooting)"
        )
        return result
    except FileNotFoundError:
        logger.error(f"Fastboot not found at path: {settings.FASTBOOT_PATH}")
        return None
    except PermissionError:
        logger.error(f"Permission denied running fastboot: {settings.FASTBOOT_PATH}. May need USB permissions or sudo.")
        return None
    except Exception as e:
        logger.error(f"Error running fastboot command {' '.join(cmd)}: {e}", exc_info=True)
        return None


def get_devices() -> List[Dict[str, str]]:
    """Get list of connected devices"""
    devices = []
    
    # Get ADB devices
    try:
        result = run_adb_command(["devices"], timeout=10)
        if result:
            # ADB outputs to stdout, but check both for robustness
            output = result.stdout.strip() if result.stdout else ""
            if not output and result.stderr:
                output = result.stderr.strip()
            
            if output:
                lines = output.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("List of devices") or line.startswith("* daemon"):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 2:
                        serial = parts[0].strip()
                        state = parts[1].strip()
                        if serial and len(serial) > 3:  # Valid serial numbers are longer
                            devices.append({
                                "id": serial,
                                "serial": serial,
                                "state": state,
                            })
    except Exception as e:
        logger.warning(f"Error getting ADB devices: {e}")
    
    # Get Fastboot devices
    try:
        # Fastboot devices command - don't use serial flag when listing all devices
        result = run_fastboot_command(["devices"], timeout=15)
        
        if result is None:
            logger.debug("Fastboot devices command returned None")
        else:
            # Fastboot outputs can be in stdout, stderr, or both
            # Also, fastboot may return non-zero exit codes even when it succeeds
            stdout = result.stdout.strip() if result.stdout else ""
            stderr = result.stderr.strip() if result.stderr else ""
            
            # Log raw output for debugging
            logger.debug(f"Fastboot devices - returncode: {result.returncode}, stdout: {repr(stdout)}, stderr: {repr(stderr)}")
            
            # Combine outputs - fastboot often uses stderr for device list
            # Standard format: "SERIAL\tfastboot" or "SERIAL\tfastboot\n"
            combined_output = ""
            if stdout:
                combined_output = stdout
            if stderr:
                # If stdout exists, append stderr; otherwise use stderr
                if combined_output:
                    combined_output = f"{combined_output}\n{stderr}"
                else:
                    combined_output = stderr
            
            # Also check if command succeeded even with non-zero returncode
            # (fastboot can return non-zero for warnings but still list devices)
            if combined_output or result.returncode == 0:
                # Fastboot doesn't have a header line like ADB
                # Format examples:
                # "SERIAL\tfastboot"
                # "SERIAL\tfastboot\n"
                # "SERIAL  fastboot" (space-separated)
                # Sometimes just: "SERIAL"
                
                lines = combined_output.split("\n") if combined_output else []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Filter out common non-device lines
                    # But first check if it looks like a device line (has tab separator with serial)
                    is_device_line = "\t" in line and len(line.split("\t")) >= 2
                    
                    if not is_device_line:
                        line_lower = line.lower()
                        skip_keywords = [
                            "waiting", "finished", "total time", "error", 
                            "sending", "okay", "booting", "rebooting",
                            "usage:", "unknown command", "command not found",
                            "fastboot:", "fastboot.exe", "fastboot version"
                        ]
                        # Skip lines that are clearly status/error messages
                        if any(keyword in line_lower for keyword in skip_keywords):
                            continue
                        # Also skip lines that start with these patterns
                        if line_lower.startswith(("error", "usage", "unknown")):
                            continue
                    
                    serial = None
                    state = "fastboot"
                    
                    # Try tab-separated format first (most common): "SERIAL\tfastboot"
                    if "\t" in line:
                        parts = line.split("\t")
                        if len(parts) >= 1:
                            serial = parts[0].strip()
                            if len(parts) >= 2:
                                state_part = parts[1].strip().lower()
                                if state_part and state_part != "fastboot":
                                    # Might have additional info, still valid
                                    pass
                    else:
                        # Try space-separated format: "SERIAL fastboot" or just "SERIAL"
                        parts = line.split()
                        if len(parts) >= 1:
                            # First part should be the serial
                            potential_serial = parts[0].strip()
                            # Serial numbers are typically 8+ characters, alphanumeric
                            # Can contain hyphens, underscores
                            if len(potential_serial) >= 6 and (
                                potential_serial.replace("-", "").replace("_", "").isalnum() or
                                all(c.isalnum() or c in "-_" for c in potential_serial)
                            ):
                                serial = potential_serial
                    
                    # Validate and add device
                    if serial and len(serial) >= 6:
                        # Additional validation - serial shouldn't be common words
                        invalid_serials = ["list", "of", "devices", "attached", "unauthorized", "offline"]
                        if serial.lower() not in invalid_serials:
                            # Check if not already in devices list
                            if not any(d["serial"] == serial for d in devices):
                                logger.debug(f"Found fastboot device: {serial}")
                                devices.append({
                                    "id": serial,
                                    "serial": serial,
                                    "state": state,
                                })
                            else:
                                logger.debug(f"Fastboot device {serial} already in list, skipping")
                        else:
                            logger.debug(f"Skipping invalid serial: {serial}")
                    else:
                        logger.debug(f"Could not extract valid serial from line: {line}")
                        
    except Exception as e:
        logger.error(f"Error getting fastboot devices: {e}", exc_info=True)
    
    return devices


def identify_device(serial: str) -> Optional[Dict[str, str]]:
    """Identify device codename - works in both ADB and Fastboot mode"""
    # Try Fastboot first (if device is in fastboot mode)
    # Use shorter timeout for identification during reboots
    try:
        result = run_fastboot_command(["getvar", "product"], serial=serial, timeout=10)
        if result:
            # Fastboot outputs to stderr, not stdout!
            output = result.stderr if result.stderr else result.stdout
            if output and "timed out" not in output.lower():
                for line in output.split("\n"):
                    line_lower = line.lower().strip()
                    if "product:" in line_lower:
                        # Handle format: "product: panther" or "product:panther"
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            codename = parts[1].strip()
                            # Remove any extra text after the codename (like "Finished", "Total time", etc.)
                            codename = codename.split()[0] if codename else ""
                            # Also remove any trailing dots or special chars
                            codename = codename.rstrip('.,;')
                            if codename and codename in settings.supported_codenames_list:
                                device_name = get_device_name(codename)
                                return {
                                    "codename": codename,
                                    "deviceName": device_name,
                                }
    except Exception as e:
        logger.debug(f"Fastboot identification failed for {serial}: {e}")
    
    # Try ADB (if device is in ADB mode)
    try:
        result = run_adb_command(["shell", "getprop", "ro.product.device"], serial=serial, timeout=10)
        if result and result.returncode == 0 and result.stdout.strip():
            codename = result.stdout.strip()
            # Validate codename
            if codename in settings.supported_codenames_list:
                device_name = get_device_name(codename)
                return {
                    "codename": codename,
                    "deviceName": device_name,
                }
    except Exception as e:
        logger.debug(f"ADB identification failed for {serial}: {e}")
    
    # Try vendor property as fallback
    try:
        result = run_adb_command(["shell", "getprop", "ro.product.vendor.device"], serial=serial, timeout=10)
        if result and result.returncode == 0 and result.stdout.strip():
            codename = result.stdout.strip()
            if codename in settings.supported_codenames_list:
                device_name = get_device_name(codename)
                return {
                    "codename": codename,
                    "deviceName": device_name,
                }
    except Exception as e:
        logger.debug(f"ADB vendor identification failed for {serial}: {e}")
    
    return None


def get_device_name(codename: str) -> str:
    """Get human-readable device name from codename"""
    device_names = {
        "cheetah": "Pixel 7 Pro",
        "panther": "Pixel 7",
        "raven": "Pixel 6 Pro",
        "oriole": "Pixel 6",
        "husky": "Pixel 8 Pro",
        "shiba": "Pixel 8",
        "akita": "Pixel 6a",
        "felix": "Pixel Fold",
        "tangorpro": "Pixel Tablet",
        "lynx": "Pixel 7a",
        "bluejay": "Pixel 7a",
        "barbet": "Pixel 5a",
        "redfin": "Pixel 5",
    }
    return device_names.get(codename, codename)

