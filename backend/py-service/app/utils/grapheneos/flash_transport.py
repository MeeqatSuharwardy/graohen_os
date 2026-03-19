"""
Transport Implementation for Python Backend

This module provides a Python-based transport layer for the flashing engine.
It uses subprocess to execute ADB and Fastboot commands.

This is the reference implementation - other transports (WebUSB, Electron) 
should follow the same TransportProtocol interface.
"""

import subprocess
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PythonTransport:
    """
    Python transport implementation using subprocess for ADB/Fastboot commands.
    
    This implementation:
    - Executes ADB commands via subprocess
    - Executes Fastboot commands via subprocess
    - Handles fastbootd vs bootloader fastboot automatically
    - Waits for device reconnection after reboots
    """
    
    def __init__(
        self,
        adb_path: str = "/usr/local/bin/adb",
        fastboot_path: str = "/usr/local/bin/fastboot",
        device_serial: Optional[str] = None,
    ):
        """
        Initialize Python transport.
        
        Args:
            adb_path: Path to adb binary
            fastboot_path: Path to fastboot binary
            device_serial: Device serial number (optional, for multi-device support)
        """
        self.adb_path = adb_path
        self.fastboot_path = fastboot_path
        self.device_serial = device_serial
        self._current_mode: Optional[str] = None  # "bootloader" or "fastbootd"
    
    def _run_command(
        self,
        cmd: List[str],
        timeout: int = 30,
        capture_output: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute command and return result dict.
        
        Returns:
            Dict with 'success' (bool), 'stdout' (str), 'stderr' (str), 'returncode' (int)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": -1,
            }
        except Exception as e:
            logger.error(f"Command failed: {' '.join(cmd)} - {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }
    
    def adb_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Execute ADB command"""
        cmd = [self.adb_path]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        logger.debug(f"Executing ADB: {' '.join(cmd)}")
        return self._run_command(cmd, timeout=timeout)
    
    def fastboot_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Execute fastboot command in bootloader fastboot mode"""
        cmd = [self.fastboot_path]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        logger.debug(f"Executing Fastboot (bootloader): {' '.join(cmd)}")
        self._current_mode = "bootloader"
        return self._run_command(cmd, timeout=timeout)
    
    def fastbootd_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Execute fastboot command in fastbootd (userspace) mode"""
        # fastbootd uses the same fastboot binary, but device is in different mode
        # The binary automatically detects which mode the device is in
        cmd = [self.fastboot_path]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        logger.debug(f"Executing Fastboot (fastbootd): {' '.join(cmd)}")
        self._current_mode = "fastbootd"
        return self._run_command(cmd, timeout=timeout)
    
    def wait_for_fastboot(self, timeout: int = 90) -> bool:
        """
        Wait for device to be available in bootloader fastboot mode.
        
        This handles USB re-enumeration after reboots (Tensor Pixels disconnect/reconnect).
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            True if device found in fastboot mode
        """
        logger.info(f"Waiting for device in fastboot mode (timeout: {timeout}s)...")
        
        start_time = time.time()
        check_interval = 2  # Check every 2 seconds
        
        while time.time() - start_time < timeout:
            # Check if device is in fastboot
            result = self.fastboot_command(["devices"], timeout=5)
            
            if result.get("success"):
                output = result.get("stdout", "")
                # Look for device serial in fastboot devices list
                if self.device_serial:
                    if f"{self.device_serial}\tfastboot" in output:
                        logger.info("Device found in fastboot mode")
                        return True
                else:
                    # If no serial specified, check for any fastboot device
                    if "fastboot" in output and "List of devices" not in output:
                        lines = [l for l in output.splitlines() if l.strip() and "List of devices" not in l]
                        if any("fastboot" in l for l in lines):
                            logger.info("Device found in fastboot mode")
                            return True
            
            # Wait before next check
            time.sleep(check_interval)
        
        logger.warning(f"Device not found in fastboot mode within {timeout}s timeout")
        return False
    
    def wait_for_fastbootd(self, timeout: int = 60) -> bool:
        """
        Wait for device to be available in fastbootd mode.
        
        This handles USB re-enumeration after fastbootd transition.
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            True if device found in fastbootd mode
        """
        logger.info(f"Waiting for device in fastbootd mode (timeout: {timeout}s)...")
        
        start_time = time.time()
        check_interval = 2  # Check every 2 seconds
        
        while time.time() - start_time < timeout:
            # Check if device is in fastbootd by querying is-userspace variable
            result = self.fastbootd_command(["getvar", "is-userspace"], timeout=5)
            
            if result.get("success"):
                output = (result.get("stdout", "") + " " + result.get("stderr", "")).lower()
                if "is-userspace: yes" in output or "is-userspace:yes" in output:
                    logger.info("Device found in fastbootd mode")
                    return True
            
            # Also check devices list (fastbootd devices may show differently)
            devices_result = self.fastbootd_command(["devices"], timeout=5)
            if devices_result.get("success"):
                output = devices_result.get("stdout", "")
                if self.device_serial:
                    if self.device_serial in output:
                        logger.info("Device found (checking fastbootd mode)...")
                        # Verify it's actually fastbootd
                        verify_result = self.fastbootd_command(["getvar", "is-userspace"], timeout=5)
                        if verify_result.get("success"):
                            verify_output = (verify_result.get("stdout", "") + " " + 
                                           verify_result.get("stderr", "")).lower()
                            if "is-userspace: yes" in verify_output:
                                return True
            
            # Wait before next check
            time.sleep(check_interval)
        
        logger.warning(f"Device not found in fastbootd mode within {timeout}s timeout")
        return False


__all__ = ["PythonTransport"]
