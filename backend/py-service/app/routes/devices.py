from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..utils.tools import get_devices, identify_device, run_adb_command, run_fastboot_command
from ..config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class DeviceInfo(BaseModel):
    """Device information from frontend"""
    serial: str
    state: str  # 'device', 'fastboot', 'unauthorized', 'offline'
    codename: Optional[str] = None
    device_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    bootloader_unlocked: Optional[bool] = None


class DeviceListRequest(BaseModel):
    """Request to register devices from frontend"""
    devices: List[DeviceInfo]


@router.get("")
@router.get("/")
async def list_devices():
    """List all connected devices (DISABLED: backend does not look for ADB/fastboot devices - returns empty list)"""
    # Backend device detection disabled - do not call ADB/fastboot
    # Frontend/electron should use WebADB or local adb for device detection.
    logger.info("Listing devices - backend device detection disabled, returning empty list")
    return []
    # try:
    #     logger.info("Listing devices - checking ADB and Fastboot...")
    #     loop = asyncio.get_event_loop()
    #     devices = await loop.run_in_executor(None, get_devices)
    #     ...
    # except Exception as e:
    #     logger.error(f"Error listing devices: {e}", exc_info=True)
    #     return []


@router.post("")
@router.post("/")
async def register_devices(request: DeviceListRequest):
    """
    Register devices from frontend (WebADB detection).
    Frontend detects devices locally and sends device info to backend.
    Backend stores device info and can use it for flashing operations.
    """
    try:
        logger.info(f"Received {len(request.devices)} device(s) from frontend")
        
        registered_devices = []
        for device_info in request.devices:
            logger.info(f"Registering device: {device_info.serial} (state: {device_info.state}, codename: {device_info.codename})")
            
            # Try to identify device if codename not provided
            codename = device_info.codename
            if not codename:
                try:
                    identification = identify_device(device_info.serial)
                    if identification:
                        codename = identification.get("codename")
                        logger.info(f"Identified device {device_info.serial} as {codename}")
                except Exception as e:
                    logger.warning(f"Could not identify device {device_info.serial}: {e}")
            
            registered_device = {
                "serial": device_info.serial,
                "state": device_info.state,
                "codename": codename,
                "device_name": device_info.device_name,
                "manufacturer": device_info.manufacturer,
                "model": device_info.model,
                "bootloader_unlocked": device_info.bootloader_unlocked,
            }
            
            registered_devices.append(registered_device)
        
        logger.info(f"Successfully registered {len(registered_devices)} device(s)")
        
        return {
            "success": True,
            "message": f"Registered {len(registered_devices)} device(s)",
            "devices": registered_devices,
        }
        
    except Exception as e:
        logger.error(f"Error registering devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        # Use shorter timeout since device will disconnect quickly
        result = run_adb_command(["reboot", "bootloader"], serial=device_id, timeout=10)
        
        if not result:
            # Command failed to execute (tool not found, permission error, etc.)
            raise HTTPException(
                status_code=500,
                detail="Failed to execute reboot command (ADB may not be available or device unresponsive)"
            )
        
        # ADB reboot command often succeeds even if connection is lost
        # Check if command was sent successfully (returncode 0 or timeout/connection loss is OK)
        # Timeout/connection loss is expected when device reboots
        if result.returncode == -1:
            # Timeout is expected - device is rebooting and connection is lost
            logger.info(f"Device {device_id} rebooting to bootloader (connection lost as expected)")
            return {"success": True, "message": "Device rebooting to bootloader", "note": "Connection lost as device reboots - this is normal"}
        
        if result.returncode != 0:
            # Check if error is about connection loss (which is OK for reboot)
            error_msg = result.stderr if result.stderr else result.stdout or "Unknown error"
            if "device offline" in error_msg.lower() or "device not found" in error_msg.lower():
                # Device disconnected during reboot - this is expected
                logger.info(f"Device {device_id} rebooting to bootloader (disconnected as expected)")
                return {"success": True, "message": "Device rebooting to bootloader", "note": "Device disconnected during reboot - this is normal"}
            
            # Real error
            logger.error(f"Failed to reboot device {device_id}: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to reboot: {error_msg}"
            )
        
        # Success
        logger.info(f"Device {device_id} reboot command sent successfully")
        return {"success": True, "message": "Device rebooting to bootloader"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error rebooting device {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/debug/fastboot")
async def debug_fastboot_devices():
    """Debug endpoint to check fastboot device detection (DISABLED: backend does not run fastboot)"""
    # Backend fastboot device detection disabled - do not call fastboot
    # result = run_fastboot_command(["devices"], timeout=15)
    # ...
    return {
        "disabled": True,
        "message": "Fastboot device detection is disabled on backend. Use frontend/electron or local tools for device detection.",
        "fastboot_path": settings.FASTBOOT_PATH,
    }

