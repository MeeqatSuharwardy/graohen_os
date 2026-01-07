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
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        # Fastboot sometimes returns non-zero exit codes even on success
        # Check if we got valid output instead of relying solely on returncode
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
    except Exception as e:
        logger.error(f"Error running fastboot command {' '.join(cmd)}: {e}")
        return None


def get_devices() -> List[Dict[str, str]]:
    """Get list of connected devices"""
    devices = []
    
    # Get ADB devices
    try:
        result = run_adb_command(["devices"], timeout=10)
        if result and result.returncode == 0:
            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        devices.append({
                            "id": parts[0],
                            "serial": parts[0],
                            "state": parts[1],
                        })
    except Exception as e:
        logger.warning(f"Error getting ADB devices: {e}")
    
    # Get Fastboot devices
    try:
        result = run_fastboot_command(["devices"], timeout=10)
        if result and result.returncode == 0:
            output = result.stdout.strip() if result.stdout else ""
            if not output and result.stderr:
                output = result.stderr.strip()
            
            for line in output.split("\n"):
                line = line.strip()
                if line and "\t" in line:
                    serial = line.split("\t")[0].strip()
                    # Check if not already in devices list
                    if serial and not any(d["serial"] == serial for d in devices):
                        devices.append({
                            "id": serial,
                            "serial": serial,
                            "state": "fastboot",
                        })
    except Exception as e:
        logger.warning(f"Error getting fastboot devices: {e}")
    
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

