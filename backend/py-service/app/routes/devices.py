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
        raise HTTPException(
            status_code=404,
            detail="Device not found or unsupported codename"
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

