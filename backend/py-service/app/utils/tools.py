import subprocess
import os
from typing import List, Dict, Optional
from ..config import settings


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


def run_adb_command(args: List[str], serial: Optional[str] = None, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run an ADB command"""
    cmd = [settings.ADB_PATH]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(args)
    
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_fastboot_command(args: List[str], serial: Optional[str] = None, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a Fastboot command"""
    cmd = [settings.FASTBOOT_PATH]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(args)
    
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def get_devices() -> List[Dict[str, str]]:
    """Get list of connected devices"""
    devices = []
    
    # Get ADB devices
    result = run_adb_command(["devices"], timeout=10)
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    devices.append({
                        "id": parts[0],
                        "serial": parts[0],
                        "state": parts[1],
                    })
    
    # Get Fastboot devices
    result = run_fastboot_command(["devices"], timeout=10)
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line.strip() and "\t" in line:
                serial = line.split("\t")[0].strip()
                # Check if not already in devices list
                if not any(d["serial"] == serial for d in devices):
                    devices.append({
                        "id": serial,
                        "serial": serial,
                        "state": "fastboot",
                    })
    
    return devices


def identify_device(serial: str) -> Optional[Dict[str, str]]:
    """Identify device codename - works in both ADB and Fastboot mode"""
    # Try Fastboot first (if device is in fastboot mode)
    result = run_fastboot_command(["getvar", "product"], serial=serial)
    if result.returncode == 0:
        for line in result.stdout.split("\n"):
            if line.startswith("product:"):
                codename = line.split(":")[1].strip()
                # Remove any extra text after the codename
                codename = codename.split()[0] if codename else ""
                if codename in settings.supported_codenames_list:
                    device_name = get_device_name(codename)
                    return {
                        "codename": codename,
                        "deviceName": device_name,
                    }
    
    # Try ADB (if device is in ADB mode)
    result = run_adb_command(["shell", "getprop", "ro.product.device"], serial=serial)
    if result.returncode == 0 and result.stdout.strip():
        codename = result.stdout.strip()
        # Validate codename
        if codename in settings.supported_codenames_list:
            device_name = get_device_name(codename)
            return {
                "codename": codename,
                "deviceName": device_name,
            }
    
    # Try vendor property as fallback
    result = run_adb_command(["shell", "getprop", "ro.product.vendor.device"], serial=serial)
    if result.returncode == 0 and result.stdout.strip():
        codename = result.stdout.strip()
        if codename in settings.supported_codenames_list:
            device_name = get_device_name(codename)
            return {
                "codename": codename,
                "deviceName": device_name,
            }
    
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

