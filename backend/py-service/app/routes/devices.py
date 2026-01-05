from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..utils.tools import get_devices, identify_device, run_adb_command

router = APIRouter()


@router.get("/")
async def list_devices():
    """List all connected devices"""
    devices = get_devices()
    
    # Try to identify each device
    for device in devices:
        if device["state"] in ["device", "fastboot"]:
            identification = identify_device(device["serial"])
            if identification:
                device.update(identification)
    
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
    
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reboot: {result.stderr}"
        )
    
    return {"success": True, "message": "Device rebooting to bootloader"}

