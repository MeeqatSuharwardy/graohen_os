from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..utils.tools import get_devices, identify_device, run_adb_command, run_fastboot_command
from ..config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
@router.get("/")
async def list_devices():
    """List all connected devices"""
    import logging
    import asyncio
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Listing devices - checking ADB and Fastboot...")
        
        # Run get_devices in executor to avoid blocking
        loop = asyncio.get_event_loop()
        devices = await loop.run_in_executor(None, get_devices)
        logger.info(f"Found {len(devices)} device(s): {[d['serial'] for d in devices]}")
        
        # Try to identify each device (with timeout handling)
        # Use asyncio.gather for parallel identification with timeout
        async def identify_device_async(device):
            if device["state"] in ["device", "fastboot"]:
                try:
                    logger.debug(f"Identifying device {device['serial']} in {device['state']} state...")
                    # Run identify_device in executor with timeout
                    identification = await asyncio.wait_for(
                        loop.run_in_executor(None, identify_device, device["serial"]),
                        timeout=5.0
                    )
                    if identification:
                        device.update(identification)
                        logger.info(f"Device {device['serial']} identified as {identification.get('codename', 'unknown')}")
                except asyncio.TimeoutError:
                    logger.warning(f"Device {device['serial']} identification timed out")
                except Exception as e:
                    # Log but don't fail - device list should still be returned
                    logger.warning(f"Could not identify device {device['serial']}: {e}", exc_info=True)
            return device
        
        # Identify devices in parallel with timeout
        if devices:
            try:
                devices = await asyncio.wait_for(
                    asyncio.gather(*[identify_device_async(d) for d in devices]),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Device identification timed out, returning devices without full identification")
        
        return devices
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        # Return empty list on error rather than crashing
        return []


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
    """Debug endpoint to check fastboot device detection"""
    try:
        # Run fastboot devices command directly
        result = run_fastboot_command(["devices"], timeout=15)
        
        if result is None:
            return {
                "error": "Fastboot command returned None - fastboot may not be installed or accessible",
                "fastboot_path": settings.FASTBOOT_PATH
            }
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout if result.stdout else "",
            "stderr": result.stderr if result.stderr else "",
            "stdout_raw": repr(result.stdout) if result.stdout else "None",
            "stderr_raw": repr(result.stderr) if result.stderr else "None",
            "detected_devices": get_devices(),
        }
    except Exception as e:
        logger.error(f"Error in debug_fastboot_devices: {e}", exc_info=True)
        return {"error": str(e), "traceback": str(e.__traceback__)}

