from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..utils.tools import get_devices, identify_device, run_adb_command

router = APIRouter()


@router.get("/")
async def list_devices():
    """List all connected devices"""
    devices = get_devices()
    
    # Try to identify each device (with timeout handling)
    for device in devices:
        if device["state"] in ["device", "fastboot"]:
            try:
                identification = identify_device(device["serial"])
                if identification:
                    device.update(identification)
            except Exception as e:
                # Log but don't fail - device list should still be returned
                # even if identification fails (e.g., device is rebooting)
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Could not identify device {device['serial']}: {e}")
                # Continue with other devices
    
    return devices


@router.get("/{device_id}/identify")
async def identify_device_endpoint(device_id: str):
    """Identify a device's codename"""
    identification = identify_device(device_id)
    
    if not identification:
        # Return a more informative response instead of 404
        # This allows the frontend to proceed with flashing even if identification fails
        raise HTTPException(
            status_code=404,
            detail=f"Could not identify device codename for serial: {device_id}. "
                   f"Device may be in fastboot mode or codename not in supported list. "
                   f"Flashing can still proceed if a bundle is available."
        )
    
    return identification


@router.post("/{device_id}/reboot/bootloader")
async def reboot_to_bootloader(device_id: str):
    """Reboot device to bootloader"""
    result = run_adb_command(["reboot", "bootloader"], serial=device_id)
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to execute reboot command (device may be unresponsive)"
        )
    
    if result.returncode != 0:
        error_msg = result.stderr if result.stderr else result.stdout or "Unknown error"
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reboot: {error_msg}"
        )
    
    return {"success": True, "message": "Device rebooting to bootloader"}

