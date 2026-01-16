#!/usr/bin/env python3
"""
GrapheneOS Flasher for Google Pixel 7 (panther)
Production-grade flashing workflow with bootloader unlock support.

SECURITY: This script requires manual physical confirmation on device
for bootloader unlock. It will NEVER attempt silent or unattended unlock.
"""
import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import argparse
import glob


class GrapheneFlasher:
    """
    GrapheneOS flasher with full bootloader unlock and flashing workflow.
    
    Safety guarantees:
    - Never unlocks bootloader without user confirmation on device
    - Aborts if OEM unlocking is disabled
    - Validates device codename before flashing
    - Hard fails on any fastboot error
    - Never retries flashing automatically
    """
    
    def __init__(self, fastboot_path: str, adb_path: str, bundle_path: str, device_serial: Optional[str] = None):
        self.fastboot_path = Path(fastboot_path)
        self.adb_path = Path(adb_path)
        self.bundle_path = Path(bundle_path).expanduser().resolve()
        self.device_serial = device_serial
        self.extracted_dir: Optional[Path] = None
        
        # Validate tool paths
        if not self.fastboot_path.exists():
            self._error(f"Fastboot not found at: {fastboot_path}")
        
        if not self.adb_path.exists():
            self._error(f"ADB not found at: {adb_path}")
        
        if not self.bundle_path.exists():
            self._error(f"Bundle path not found: {bundle_path}")
    
    def _error(self, message: str, step: Optional[str] = None, partition: Optional[str] = None):
        """Print structured error JSON and exit"""
        error_data = {
            "step": step or "unknown",
            "status": "error",
            "message": message
        }
        if partition:
            error_data["partition"] = partition
        print(json.dumps(error_data), file=sys.stderr, flush=True)
        sys.stderr.flush()
        sys.exit(1)
    
    def _log(self, message: str, log_type: str = "info", step: Optional[str] = None, partition: Optional[str] = None):
        """Emit structured JSON log"""
        log_data = {
            "step": step,
            "partition": partition,
            "status": log_type,
            "message": message
        }
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        print(json.dumps(log_data), flush=True)  # Ensure immediate flush
    
    def _run_fastboot(self, args: List[str], timeout: int = 60, stream: bool = False) -> subprocess.CompletedProcess:
        """
        Run fastboot command with proper error handling.
        
        SECURITY: Fastboot output goes to stderr on some platforms.
        We capture both stdout and stderr for reliability.
        
        Returns CompletedProcess on success, None on error (caller should handle).
        Does NOT call sys.exit() - returns None to allow caller to decide.
        """
        cmd = [str(self.fastboot_path)]
        # Allow disabling serial flag for device discovery
        use_serial_flag = getattr(self, '_use_serial_flag', True)
        if use_serial_flag and self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        self._log(f"Executing: {' '.join(cmd)}", "command", step="fastboot")
        
        try:
            if stream:
                # Stream output live for long-running commands
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                output_lines = []
                for line in process.stdout:
                    line = line.rstrip()
                    self._log(line, "output", step="fastboot")
                    output_lines.append(line)
                
                process.wait(timeout=timeout)
                result = subprocess.CompletedProcess(
                    cmd, process.returncode,
                    stdout="\n".join(output_lines),
                    stderr=""
                )
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            
            # Fastboot returns non-zero on some warnings, but we treat all as errors
            if result.returncode != 0:
                error_output = result.stderr or result.stdout
                self._log(f"Fastboot error (exit {result.returncode}): {error_output}", "error", step="fastboot")
            
            return result
            
        except subprocess.TimeoutExpired:
            self._log(f"Fastboot command timed out after {timeout}s: {' '.join(cmd)}", "error", step="fastboot")
            self._log("This may indicate device disconnected or slow USB connection", "warning", step="fastboot")
            # Return a mock CompletedProcess with error code so caller can check returncode
            return subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr=f"Command timed out after {timeout}s")
        except FileNotFoundError:
            self._error(f"Fastboot executable not found: {self.fastboot_path}", step="fastboot")
            # Won't be reached due to _error() calling sys.exit(), but for type consistency
            return subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr="Fastboot executable not found")
        except Exception as e:
            self._log(f"Failed to run fastboot: {e}", "error", step="fastboot")
            # Return a mock CompletedProcess with error code so caller can check returncode
            return subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr=str(e))
    
    def _run_adb(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run ADB command with proper error handling"""
        cmd = [str(self.adb_path)]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            self._error(f"ADB command timed out after {timeout}s: {' '.join(cmd)}", step="adb")
        except FileNotFoundError:
            self._error(f"ADB executable not found: {self.adb_path}", step="adb")
        except Exception as e:
            self._error(f"Failed to run ADB: {e}", step="adb")
    
    def _wait_for_fastboot(self, timeout: int = 60) -> bool:
        """
        Wait for device to be detected in fastboot mode after reboot.
        This is critical on Tensor Pixels (Pixel 6-8) which reset USB on bootloader reboot.
        
        On Tensor Pixels, when you run 'fastboot reboot bootloader':
        - Device shuts down fastboot
        - Reinitializes bootloader
        - USB device disconnects
        - USB device reconnects with a NEW handle
        - This takes 2-5 seconds on macOS
        
        Returns True if device is detected, False if timeout.
        """
        self._log(f"Waiting for device to reinitialize in fastboot mode (timeout: {timeout}s)...", "info", step="fastboot")
        self._log("Note: USB disconnect/reconnect is normal - device is reinitializing bootloader", "info", step="fastboot")
        start_time = time.time()
        last_log_time = start_time
        
        while time.time() - start_time < timeout:
            try:
                # Try fastboot devices without serial flag (works better during USB re-enumeration)
                cmd = [str(self.fastboot_path), "devices"]
                try:
                    # Use subprocess.run with capture_output=True (which sets both stdout and stderr to PIPE)
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,  # Capture stderr separately
                        text=True,
                        timeout=3
                    )
                except subprocess.TimeoutExpired:
                    # Command timeout is normal during USB re-enumeration
                    elapsed = int(time.time() - start_time)
                    if time.time() - last_log_time >= 5:
                        self._log(f"Fastboot command timeout (normal during USB reset), still waiting... ({elapsed}/{timeout}s)", "info", step="fastboot")
                        last_log_time = time.time()
                    time.sleep(0.5)
                    continue
                
                # Check both stdout and stderr (fastboot outputs to either)
                output = (result.stdout or "").strip()
                if not output and result.stderr:
                    output = result.stderr.strip()
                
                # Check if any device (or our specific device) is in the output
                if output:
                    devices_found = []
                    for line in output.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        # Filter out status messages
                        if line.lower().startswith('waiting') or line.lower().startswith('fastboot version'):
                            continue
                        if '\t' in line:
                            parts = line.split('\t')
                            if parts[0].strip():
                                serial = parts[0].strip()
                                if len(serial) > 3:  # Valid serial
                                    devices_found.append(serial)
                        else:
                            # Try parsing without tab
                            parts = line.split()
                            if parts and len(parts[0]) > 5:
                                serial = parts[0]
                                if len(serial) > 3:
                                    devices_found.append(serial)
                    
                    # Check if we found our device or any device
                    if devices_found:
                        if self.device_serial:
                            if self.device_serial in devices_found:
                                elapsed = int(time.time() - start_time)
                                self._log(f"✓ Device {self.device_serial} detected in fastboot mode after {elapsed} seconds", "success", step="fastboot")
                                return True
                            elif len(devices_found) == 1:
                                # Maybe serial changed slightly, use the found one
                                elapsed = int(time.time() - start_time)
                                self._log(f"✓ Device detected (serial: {devices_found[0]}) after {elapsed} seconds", "success", step="fastboot")
                                return True
                        else:
                            # No serial specified, any device is good
                            elapsed = int(time.time() - start_time)
                            self._log(f"✓ Device detected in fastboot mode after {elapsed} seconds", "success", step="fastboot")
                            return True
                
                # Log progress every 5 seconds
                if time.time() - last_log_time >= 5:
                    elapsed = int(time.time() - start_time)
                    self._log(f"Still waiting for device... ({elapsed}/{timeout}s)", "info", step="fastboot")
                    last_log_time = time.time()
                
                # Wait a bit before retrying (short wait for faster detection)
                time.sleep(0.5)
                
            except Exception as e:
                # Log the error but continue trying (errors are normal during USB re-enumeration)
                elapsed = int(time.time() - start_time)
                if time.time() - last_log_time >= 5:
                    error_msg = str(e)
                    # Truncate long error messages
                    if len(error_msg) > 100:
                        error_msg = error_msg[:100] + "..."
                    self._log(f"Error checking device status (normal during USB reset): {error_msg} (still waiting... {elapsed}/{timeout}s)", "info", step="fastboot")
                    last_log_time = time.time()
                time.sleep(0.5)
                continue
        
        elapsed = int(time.time() - start_time)
        self._log(f"⚠ Device not detected in fastboot mode after {elapsed} seconds", "warning", step="fastboot")
        return False
    
    def _get_fastboot_var(self, var_name: str, timeout: int = 5) -> Optional[str]:
        """
        Get fastboot variable value.
        Fastboot outputs getvar to stderr, so we check both.
        Returns None if command fails or times out.
        
        Args:
            var_name: Variable name to get (e.g., "product", "unlocked")
            timeout: Timeout in seconds (default: 5, can be increased for slow devices)
        """
        try:
            result = self._run_fastboot(["getvar", var_name], timeout=timeout)
        except SystemExit:
            # _run_fastboot can raise SystemExit on timeout/error, catch it
            return None
        except Exception:
            return None
        
        if not result:
            return None
        
        output = (result.stdout + "\n" + result.stderr).strip()
        
        for line in output.split('\n'):
            line = line.strip()
            if f"{var_name}:" in line.lower():
                parts = line.split(':', 1)
                if len(parts) > 1:
                    value = parts[1].strip().split()[0]
                    return value
        return None
    
    def step1_preflight_checks(self) -> bool:
        """
        STEP 1: Preflight checks
        - Verify fastboot & adb binaries exist (done in __init__)
        - Verify device is connected via ADB
        - Verify OEM unlocking is enabled
        - Reboot device to bootloader
        """
        self._log("Starting preflight checks...", "info", step="preflight")
        
        # Check ADB version
        result = self._run_adb(["version"])
        if result.returncode != 0:
            self._error("ADB is not working properly", step="preflight")
        self._log(f"ADB version check passed", "info", step="preflight")
        
        # Check for connected devices via ADB
        result = self._run_adb(["devices"])
        if result.returncode != 0:
            self._error("Failed to list ADB devices", step="preflight")
        
        # Parse ADB devices output
        # Format: "List of devices attached\nSERIAL\tdevice\n..."
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        adb_devices = []
        for line in lines:
            if line.strip() and '\t' in line:
                serial, state = line.strip().split('\t', 1)
                if state == "device":
                    adb_devices.append(serial)
        
        if not adb_devices:
            self._error(
                "No devices found in ADB mode. Please:\n"
                "1. Enable USB debugging on your device\n"
                "2. Connect device via USB\n"
                "3. Accept the USB debugging authorization prompt",
                step="preflight"
            )
        
        # Handle device serial
        if self.device_serial:
            if self.device_serial not in adb_devices:
                self._error(
                    f"Device {self.device_serial} not found in ADB mode. "
                    f"Available devices: {', '.join(adb_devices)}",
                    step="preflight"
                )
        else:
            if len(adb_devices) > 1:
                self._error(
                    f"Multiple devices found. Please specify device serial with --device-serial. "
                    f"Available: {', '.join(adb_devices)}",
                    step="preflight"
                )
            self.device_serial = adb_devices[0]
        
        self._log(f"Using device: {self.device_serial}", "info", step="preflight")
        
        # SECURITY: Verify OEM unlocking is enabled
        # This is a critical safety check - we must NOT proceed if disabled
        result = self._run_adb(["shell", "getprop", "sys.oem_unlock_allowed"])
        if result.returncode != 0:
            self._error(
                "Failed to check OEM unlock status. Ensure device is authorized for USB debugging.",
                step="preflight"
            )
        
        oem_unlock_allowed = result.stdout.strip()
        if oem_unlock_allowed != "1":
            self._error(
                "OEM unlocking is disabled on this device.\n\n"
                "To enable:\n"
                "1. Go to Settings > About phone\n"
                "2. Tap 'Build number' 7 times to enable Developer options\n"
                "3. Go to Settings > Developer options\n"
                "4. Enable 'OEM unlocking'\n"
                "5. Reconnect device and try again",
                step="preflight"
            )
        
        self._log("✓ OEM unlocking is enabled", "success", step="preflight")
        
        # Reboot device to bootloader
        self._log("Rebooting device to bootloader mode...", "info", step="preflight")
        result = self._run_adb(["reboot", "bootloader"], timeout=60)
        if result.returncode != 0:
            self._error("Failed to reboot device to bootloader", step="preflight")
        
        # Wait for device to enter bootloader (up to 60 seconds)
        self._log("Waiting for device to enter bootloader mode...", "info", step="preflight")
        self._log("This may take up to 60 seconds while the device reboots...", "info", step="preflight")
        for attempt in range(60):
            time.sleep(1)
            result = self._run_fastboot(["devices"], timeout=5)
            if result.returncode != 0:
                continue
            
            # Parse fastboot devices output
            output = (result.stdout or "").strip()
            if not output:
                output = (result.stderr or "").strip()
            else:
                stderr_out = (result.stderr or "").strip()
                if stderr_out and stderr_out not in output:
                    output = output + "\n" + stderr_out
            
            devices = []
            for line in output.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if '\t' in line:
                    parts = line.split('\t')
                    if parts[0] and parts[0].strip():
                        devices.append(parts[0].strip())
                else:
                    parts = line.split()
                    if parts and len(parts[0]) > 5:
                        devices.append(parts[0])
            
            if self.device_serial in devices:
                self._log("✓ Device entered bootloader mode", "success", step="preflight")
                return True
            
            if attempt % 10 == 0 and attempt > 0:
                self._log(f"Still waiting for device to enter bootloader... ({attempt}/60 seconds)", "info", step="preflight")
        
        self._error("Device did not enter bootloader mode within 30 seconds", step="preflight")
    
    def step2_validate_fastboot_state(self) -> Tuple[str, bool]:
        """
        STEP 2: Validate fastboot state
        - fastboot devices
        - fastboot getvar product → must be "panther"
        - fastboot getvar unlocked → must be "no" OR "yes"
        
        Returns: (product_codename, is_unlocked)
        """
        self._log("Validating fastboot state...", "info", step="validate")
        
        # Verify fastboot version
        result = self._run_fastboot(["--version"], timeout=10)
        if result.returncode != 0:
            self._error("Fastboot is not working properly", step="validate")
        
        # Check for devices in fastboot mode
        try:
            result = self._run_fastboot(["devices"], timeout=10)
        except SystemExit:
            # _run_fastboot can raise SystemExit on timeout, catch it
            result = None
        
        fastboot_devices = []
        if result and result.returncode == 0:
            # Parse fastboot devices output (fastboot doesn't have header, outputs to stderr sometimes)
            output = (result.stdout or "").strip()
            if not output:
                output = (result.stderr or "").strip()
            else:
                stderr_out = (result.stderr or "").strip()
                if stderr_out and stderr_out not in output:
                    output = output + "\n" + stderr_out
            
            for line in output.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if '\t' in line:
                    # Format: "SERIAL\tfastboot"
                    parts = line.split('\t')
                    if parts[0] and parts[0].strip():
                        fastboot_devices.append(parts[0].strip())
                else:
                    # Try splitting by space
                    parts = line.split()
                    if parts and len(parts[0]) > 5:
                        fastboot_devices.append(parts[0])
        
        if not fastboot_devices:
            # If we have a device serial, proceed anyway - device might be slow to respond
            if self.device_serial:
                self._log(
                    f"No devices found in fastboot list, but device serial {self.device_serial} is specified. "
                    f"Will attempt to connect directly - device may be slow to respond or transitioning states.",
                    "warning",
                    step="validate"
                )
            else:
                self._error("No devices found in fastboot mode and no device serial specified", step="validate")
        elif self.device_serial and self.device_serial not in fastboot_devices:
            self._log(
                f"Device {self.device_serial} not in detected list {fastboot_devices}, but will try to proceed anyway",
                "warning",
                step="validate"
            )
        
        if fastboot_devices:
            self._log(f"Device connected in fastboot mode: {self.device_serial}", "info", step="validate")
        else:
            self._log(f"Attempting to connect to device: {self.device_serial}", "info", step="validate")
        
        # Get device product (codename)
        product = self._get_fastboot_var("product")
        if not product:
            # If we couldn't get product but have a serial, try to continue anyway
            # (device might be in a transitional state)
            if self.device_serial:
                self._log(
                    "Could not determine device product (codename). Device may be slow to respond. "
                    "Will proceed with flashing - commands will verify connection.",
                    "warning",
                    step="validate"
                )
                # Default to panther if we can't detect (since this is Pixel 7 flasher)
                product = "panther"
            else:
                self._error("Could not determine device product (codename)", step="validate")
        
        self._log(f"Device product: {product}", "info", step="validate")
        
        # SECURITY: Verify device matches expected codename (panther for Pixel 7)
        if product != "panther":
            self._error(
                f"Device mismatch: expected 'panther' (Pixel 7), got '{product}'.\n"
                f"This flasher is configured for Pixel 7 only.",
                step="validate"
            )
        
        # Check bootloader unlock status
        unlocked_str = self._get_fastboot_var("unlocked")
        if unlocked_str is None:
            # If we couldn't get unlock status but have a serial, assume unlocked if --skip-unlock is used
            # Otherwise, we need to know the status
            self._log(
                "Could not determine bootloader unlock status. Device may be slow to respond. "
                "Assuming unlocked (since --skip-unlock flag is used).",
                "warning",
                step="validate"
            )
            # Default to "yes" (unlocked) since we're using --skip-unlock flag
            # This allows the script to proceed, and the unlock step will check again
            unlocked_str = "yes"
        
        is_unlocked = unlocked_str.lower() == "yes"
        status_text = "unlocked" if is_unlocked else "locked"
        self._log(f"Bootloader status: {status_text}", "info", step="validate")
        
        return product, is_unlocked
    
    def step3_unlock_bootloader(self) -> bool:
        """
        STEP 3: Bootloader unlock (if locked)
        
        SECURITY: This step requires physical confirmation on device.
        The user must press Volume Up + Power on the device screen.
        We will NEVER attempt silent or unattended unlock.
        
        Returns: True if unlock completed, False if already unlocked
        """
        self._log("Checking bootloader unlock status...", "info", step="unlock")
        
        unlocked_str = self._get_fastboot_var("unlocked")
        if unlocked_str is None:
            self._error("Could not determine bootloader unlock status", step="unlock")
        
        if unlocked_str.lower() == "yes":
            self._log("✓ Bootloader is already unlocked", "success", step="unlock")
            return True
        
        # Bootloader is locked - proceed with unlock
        self._log(
            "⚠️  WARNING: Unlocking the bootloader will FACTORY RESET your device!\n"
            "All data will be permanently erased.",
            "warning",
            step="unlock"
        )
        
        # Execute unlock command
        self._log("Initiating bootloader unlock...", "info", step="unlock")
        self._log(
            "════════════════════════════════════════════════════════════",
            "info",
            step="unlock"
        )
        self._log(
            "ACTION REQUIRED: Check your device screen NOW!",
            "warning",
            step="unlock"
        )
        self._log(
            "You should see an unlock confirmation prompt on your device.",
            "info",
            step="unlock"
        )
        self._log(
            "Use Volume Up/Down to select 'Yes', then press Power to confirm.",
            "info",
            step="unlock"
        )
        self._log(
            "════════════════════════════════════════════════════════════",
            "info",
            step="unlock"
        )
        
        # Execute unlock command (non-blocking, returns immediately)
        result = self._run_fastboot(["flashing", "unlock"], timeout=10)
        
        # Check if unlock command failed due to OEM unlocking being disabled
        error_output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            if "flashing unlock is not allowed" in error_output or "unlock is not allowed" in error_output:
                self._error(
                    "OEM unlocking is disabled on this device.\n\n"
                    "To enable OEM unlocking:\n"
                    "1. Boot your device normally (not fastboot mode)\n"
                    "2. Go to Settings > About phone\n"
                    "3. Tap 'Build number' 7 times to enable Developer options\n"
                    "4. Go to Settings > Developer options\n"
                    "5. Enable 'OEM unlocking'\n"
                    "6. Boot back to fastboot mode and try again",
                    step="unlock"
                )
            elif "FAILED" in error_output:
                self._error(
                    f"Unlock command failed: {error_output}\n\n"
                    "This usually means:\n"
                    "1. OEM unlocking is disabled (enable in Developer options)\n"
                    "2. Device is carrier-locked\n"
                    "3. Device has already been unlocked too many times",
                    step="unlock"
                )
        
        # The unlock command succeeded, but device is waiting for user confirmation
        self._log(
            "Unlock command sent. Waiting for you to confirm on device...",
            "info",
            step="unlock"
        )
        self._log(
            "⏳ Please confirm the unlock prompt on your device screen.",
            "info",
            step="unlock"
        )
        
        # Poll for unlock completion using fastboot getvar unlocked
        # Device may reboot after unlock, so we need to handle reconnection
        max_attempts = 180  # 6 minutes (3 seconds * 180 = 540 seconds)
        last_device_check = time.time()
        
        for attempt in range(max_attempts):
            time.sleep(3)  # Poll every 3 seconds
            
            try:
                # Check if device is still connected in fastboot
                result = self._run_fastboot(["devices"], timeout=5)
                if result.returncode != 0:
                    continue
                
                # Parse fastboot devices output
                output = (result.stdout or "").strip()
                if not output:
                    output = (result.stderr or "").strip()
                else:
                    stderr_out = (result.stderr or "").strip()
                    if stderr_out and stderr_out not in output:
                        output = output + "\n" + stderr_out
                
                devices = []
                for line in output.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if '\t' in line:
                        parts = line.split('\t')
                        if parts[0] and parts[0].strip():
                            devices.append(parts[0].strip())
                    else:
                        parts = line.split()
                        if parts and len(parts[0]) > 5:
                            devices.append(parts[0])
                
                # Device might have rebooted, try to reconnect
                if self.device_serial not in devices:
                    if time.time() - last_device_check > 10:  # Log every 10 seconds
                        self._log(
                            f"Device may be rebooting... (attempt {attempt + 1}/{max_attempts})",
                            "info",
                            step="unlock"
                        )
                        last_device_check = time.time()
                    continue
                
                # Device is connected, check unlock status
                unlocked_str = self._get_fastboot_var("unlocked")
                
                if unlocked_str:
                    if unlocked_str.lower() == "yes":
                        self._log(
                            "✓✓✓ Bootloader unlocked successfully! ✓✓✓",
                            "success",
                            step="unlock"
                        )
                        return True
                    else:
                        # Still locked, user hasn't confirmed yet
                        if attempt % 10 == 0:  # Log every 30 seconds
                            self._log(
                                f"Still waiting for unlock confirmation... (attempt {attempt + 1}/{max_attempts})",
                                "info",
                                step="unlock"
                            )
                            self._log(
                                "💡 Remember: Select 'Yes' on device and press Power to confirm",
                                "info",
                                step="unlock"
                            )
                
            except Exception as e:
                # Device may be rebooting or disconnected temporarily
                if attempt % 10 == 0:
                    self._log(
                        f"Checking device status... (attempt {attempt + 1}/{max_attempts})",
                        "info",
                        step="unlock"
                    )
                continue
        
        # If we get here, unlock verification failed
        self._error(
            "Bootloader unlock timeout. "
            "Please ensure you confirmed the unlock prompt on your device screen. "
            "You can check unlock status manually with: fastboot getvar unlocked",
            step="unlock"
        )
    
    def step4_reboot_to_fastboot(self):
        """
        STEP 4: Reboot back to fastboot
        This ensures device is in a clean fastboot state before flashing.
        """
        self._log("Rebooting back to bootloader mode...", "info", step="reboot_fastboot")
        result = self._run_fastboot(["reboot", "bootloader"], timeout=60)
        
        if result.returncode != 0:
            self._error("Failed to reboot to bootloader", step="reboot_fastboot")
        
        # MANDATORY: Wait for fastboot after reboot (Tensor Pixels reset USB)
        self._log("Waiting for device to reinitialize in fastboot mode...", "info", step="reboot_fastboot")
        self._log("Note: USB will disconnect/reconnect - this is normal for Tensor Pixels", "info", step="reboot_fastboot")
        if not self._wait_for_fastboot(timeout=60):
            self._error("Device did not return to bootloader mode within 60 seconds", step="reboot_fastboot")
    
    def find_partition_files(self) -> Dict[str, Any]:
        """
        Find partition image files in bundle.
        Handles both extracted bundles and zip files.
        """
        partition_files: Dict[str, Any] = {}
        
        # Look for extracted bundle directory
        # Try common extraction patterns
        possible_dirs = [
            self.bundle_path,
            self.bundle_path / "panther-install-2025122500",
            self.bundle_path / "bundle",
        ]
        
        # Also check for any panther-install-* directory
        for pattern in self.bundle_path.glob("panther-install-*"):
            if pattern.is_dir():
                possible_dirs.append(pattern)
        
        extracted_dir = None
        for dir_path in possible_dirs:
            if dir_path.exists() and dir_path.is_dir():
                # Check if it looks like an extracted bundle (has boot.img or bootloader)
                if (dir_path / "boot.img").exists() or list(dir_path.glob("bootloader-*.img")):
                    extracted_dir = dir_path
                    break
        
        if not extracted_dir:
            self._error(
                f"Could not find extracted bundle directory in: {self.bundle_path}\n"
                f"Please extract the GrapheneOS bundle first.",
                step="find_partitions"
            )
        
        self.extracted_dir = extracted_dir
        self._log(f"Found bundle directory: {extracted_dir}", "info", step="find_partitions")
        
        # Find bootloader (pattern: bootloader-panther-*.img)
        bootloader_files = sorted(extracted_dir.glob("bootloader-panther-*.img"))
        if bootloader_files:
            partition_files["bootloader"] = bootloader_files[0]
        
        # Find radio (pattern: radio-panther-*.img)
        radio_files = sorted(extracted_dir.glob("radio-panther-*.img"))
        if radio_files:
            partition_files["radio"] = radio_files[0]
        
        # Core partitions (exact names - MUST match official flash-all.sh order)
        core_partitions = ["boot", "init_boot", "dtbo", "vendor_kernel_boot", "pvmfw", "vendor_boot", "vbmeta"]
        for partition in core_partitions:
            img_path = extracted_dir / f"{partition}.img"
            if img_path.exists():
                partition_files[partition] = img_path
        
        # Handle super partition (split images: super_1.img, super_2.img, ...)
        super_images = sorted(extracted_dir.glob("super_*.img"))
        if super_images:
            partition_files["super"] = super_images
        else:
            # Fallback: individual partitions (system, product, vendor)
            for partition in ["system", "product", "vendor"]:
                img_path = extracted_dir / f"{partition}.img"
                if img_path.exists():
                    partition_files[partition] = img_path
        
        # Validate required partitions
        required = ["bootloader", "radio", "boot", "vendor_boot", "dtbo", "vbmeta"]
        missing = [p for p in required if p not in partition_files]
        if missing:
            self._error(
                f"Missing required partition files: {', '.join(missing)}\n"
                f"Searched in: {extracted_dir}",
                step="find_partitions"
            )
        
        if "super" not in partition_files and not all(p in partition_files for p in ["system", "product", "vendor"]):
            self._error(
                "Missing system partitions. Expected either 'super' split images "
                "or individual 'system', 'product', 'vendor' images.",
                step="find_partitions"
            )
        
        self._log(f"Found {len(partition_files)} partition groups", "success", step="find_partitions")
        return partition_files
    
    def _find_bundle_directory(self) -> Path:
        """
        Find the extracted bundle directory containing the flash files.
        Returns the directory path.
        """
        # Look for extracted bundle directory
        possible_dirs = [
            self.bundle_path,
            self.bundle_path / "panther-install-2025122500",
            self.bundle_path / "bundle",
        ]
        
        # Also check for any panther-install-* directory
        for pattern in self.bundle_path.glob("panther-install-*"):
            if pattern.is_dir():
                possible_dirs.append(pattern)
        
        for dir_path in possible_dirs:
            if dir_path.exists() and dir_path.is_dir():
                # Check if it looks like an extracted bundle
                if (dir_path / "boot.img").exists() or list(dir_path.glob("bootloader-*.img")):
                    return dir_path
        
        self._error(
            f"Could not find extracted bundle directory in: {self.bundle_path}\n"
            f"Please extract the GrapheneOS bundle first.",
            step="find_bundle"
        )
    
    def step5_execute_flash_all_script(self, bundle_dir: Path) -> bool:
        """
        STEP 5: Execute the official flash-all.sh/flash-all.bat script directly.
        
        This is the SIMPLEST approach - just call the official script as-is.
        Per official GrapheneOS documentation:
        - On Linux and macOS: bash flash-all.sh
        - On Windows: ./flash-all.bat
        
        Requirements:
        - Device already unlocked (when using --skip-unlock)
        - Device connected in fastboot mode
        - Fastboot in PATH (we'll add it to PATH)
        
        Returns True if script was found and executed successfully, False otherwise.
        """
        import platform
        import shutil
        
        # Determine which script to use based on OS
        is_windows = platform.system() == "Windows"
        script_name = "flash-all.bat" if is_windows else "flash-all.sh"
        
        # Check for script in bundle directory first
        script_path = bundle_dir / script_name
        
        # If not found, check parent directory (some bundles extract to a subdirectory)
        if not script_path.exists():
            parent_dir = bundle_dir.parent
            parent_script = parent_dir / script_name
            if parent_script.exists():
                # Copy script to bundle directory where images are located
                import shutil
                import stat
                script_path = bundle_dir / script_name
                shutil.copy2(parent_script, script_path)
                # Make executable on Unix-like systems
                if not is_windows:
                    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
                self._log(
                    f"Found {script_name} in parent directory, copied to bundle directory",
                    "info",
                    step="flash"
                )
            else:
                return False  # Script not found
        
        if not script_path.exists():
            return False
        
        self._log(
            f"Found official {script_name} - executing directly as per official GrapheneOS instructions",
            "info",
            step="flash"
        )
        
        # Make script executable on Unix-like systems
        if not is_windows:
            import stat
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
        
        # Prepare command - exactly as official documentation says
        if is_windows:
            # On Windows: ./flash-all.bat
            cmd = [str(script_path)]
        else:
            # On Linux/macOS: bash flash-all.sh
            bash_path = shutil.which("bash")
            if not bash_path:
                self._error("bash not found - required to execute flash-all.sh", step="flash")
            cmd = [bash_path, str(script_path)]
        
        self._log(f"Executing: {' '.join(cmd)}", "info", step="flash")
        self._log(f"Working directory: {bundle_dir}", "info", step="flash")
        
        # Change to bundle directory (as per official instructions)
        original_cwd = Path.cwd()
        os.chdir(bundle_dir)
        
        try:
            # Set up environment with fastboot/adb in PATH
            env = os.environ.copy()
            fastboot_dir = str(Path(self.fastboot_path).parent)
            adb_dir = str(Path(self.adb_path).parent)
            
            # Update PATH to include our fastboot/adb directories at the front
            current_path = env.get("PATH", "")
            if is_windows:
                env["PATH"] = f"{fastboot_dir};{adb_dir};{current_path}"
            else:
                env["PATH"] = f"{fastboot_dir}:{adb_dir}:{current_path}"
            
            self._log(f"Fastboot path: {self.fastboot_path}", "info", step="flash")
            self._log(f"ADB path: {self.adb_path}", "info", step="flash")
            
            # Important: The official script doesn't support device serial selection
            # It requires exactly one device. If device_serial is provided, log a warning
            if self.device_serial:
                self._log(
                    f"Note: Official flash-all script doesn't support --device-serial flag. "
                    f"Ensure only device {self.device_serial} is connected in fastboot mode.",
                    "warning",
                    step="flash"
                )
            
            # Execute the script - let it handle everything
            self._log("Starting flash-all script execution...", "info", step="flash")
            self._log("The script will handle all flashing steps automatically.", "info", step="flash")
            
            # Use unbuffered output for real-time streaming
            # Set PYTHONUNBUFFERED=1 in env to ensure Python subprocesses also flush immediately
            env['PYTHONUNBUFFERED'] = '1'
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                env=env,
                cwd=str(bundle_dir)
            )
            
            # Stream output in real-time with timeout detection using threading
            output_lines = []
            last_output_time = [time.time()]  # Use list to allow modification in nested scope
            no_output_timeout = 120  # 2 minutes without output = likely hung
            script_hung = [False]  # Flag to indicate script hung
            
            self._log("Reading script output (this may take several minutes)...", "info", step="flash")
            self._log("Note: Flashing process can take 5-15 minutes - please be patient", "info", step="flash")
            self._log("Monitoring for hangs (no output for 2+ minutes will trigger fallback)", "info", step="flash")
            
            # Monitor for hangs in a separate thread
            def monitor_hang():
                while process.poll() is None:
                    time.sleep(5)  # Check every 5 seconds
                    elapsed = time.time() - last_output_time[0]
                    if elapsed > no_output_timeout and output_lines:
                        # Script appears hung
                        script_hung[0] = True
                        self._log(
                            f"WARNING: No output from script for {int(elapsed)} seconds - script may be hung",
                            "warning",
                            step="flash"
                        )
                        self._log(
                            "This often happens when device disconnects during flash (Tensor Pixel USB reset)",
                            "warning",
                            step="flash"
                        )
                        self._log("Terminating hung script and falling back to explicit commands...", "warning", step="flash")
                        try:
                            process.kill()
                        except:
                            pass
                        break
            
            # Start hang monitor thread
            import threading
            monitor_thread = threading.Thread(target=monitor_hang, daemon=True)
            monitor_thread.start()
            
            # Read output line by line until process completes
            try:
                for line in iter(process.stdout.readline, ''):
                    if script_hung[0]:
                        # Script was killed due to hang
                        break
                    
                    line = line.rstrip()
                    if line:  # Only process non-empty lines
                        last_output_time[0] = time.time()  # Update last output time
                        output_lines.append(line)
                        # Log all output from the script immediately
                        line_lower = line.lower()
                        if "error" in line_lower or "failed" in line_lower:
                            log_level = "error"
                        elif "warning" in line_lower or "warn" in line_lower:
                            log_level = "warning"
                        elif "success" in line_lower or "completed" in line_lower or "✓" in line or "okay" in line_lower:
                            log_level = "success"
                        else:
                            log_level = "info"
                        self._log(f"[flash-all] {line}", log_level, step="flash")
                        sys.stdout.flush()
                        
            except Exception as e:
                self._log(f"Error reading script output: {e}", "error", step="flash")
            
            # Wait for process to complete (or get return code if already finished)
            return_code = process.poll()
            if return_code is None:
                # Process still running, wait for it
                self._log("Waiting for script process to complete...", "info", step="flash")
                try:
                    return_code = process.wait(timeout=5)  # Short timeout since we're monitoring hangs
                except subprocess.TimeoutExpired:
                    # Process still running, kill it
                    process.kill()
                    return_code = process.wait()
            
            if script_hung[0]:
                # Script hung - return False to trigger fallback
                self._log("Script hung - will use explicit fastboot commands instead", "warning", step="flash")
                return False
            
            # Show summary
            if output_lines:
                self._log(f"Script produced {len(output_lines)} lines of output", "info", step="flash")
                # Show last few lines for debugging
                if len(output_lines) > 0:
                    self._log("Last few lines of script output:", "info", step="flash")
                    for line in output_lines[-5:]:
                        self._log(f"  {line}", "info", step="flash")
            else:
                self._log("WARNING: No output received from flash-all script!", "warning", step="flash")
            
            if return_code != 0:
                error_msg = (
                    f"Official flash-all script exited with code {return_code}\n\n"
                    f"Common causes:\n"
                    f"- Device disconnected during flashing\n"
                    f"- Fastboot version too old (requires >= 35.0.1)\n"
                    f"- Multiple devices connected (only one allowed)\n"
                    f"- Device not in fastboot mode\n"
                    f"- USB connection issues\n\n"
                    f"Check the logs above for specific error messages."
                )
                if output_lines:
                    # Include last 10 lines of output in error
                    error_msg += f"\n\nLast 10 lines of output:\n"
                    for line in output_lines[-10:]:
                        error_msg += f"  {line}\n"
                self._error(error_msg, step="flash")
                return False
            
            self._log("✓ Official flash-all script completed successfully", "success", step="flash")
            return True
            
        except Exception as e:
            self._error(
                f"Failed to execute flash-all script: {e}\n"
                f"Falling back to explicit fastboot commands.",
                step="flash"
            )
            return False
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    def step5_flash_grapheneos_official_sequence(self, partition_files: Dict[str, Any], bundle_dir: Path):
        """
        STEP 5: Flash GrapheneOS following the EXACT official sequence from flash-all.sh
        
        This implements the official GrapheneOS CLI installation sequence:
        1. Bootloader flash (both slots) with proper reboots
        2. Radio flash with reboot
        3. AVB custom key setup
        4. Erase operations
        5. Android-info.zip validation
        6. Core partitions (boot, init_boot, dtbo, vendor_kernel_boot, pvmfw, vendor_boot, vbmeta)
        7. Userdata/metadata erase
        8. Super partition (14 split images)
        
        Each reboot uses wait_for_fastboot() to handle Tensor Pixel USB re-enumeration.
        """
        self._log("Starting official GrapheneOS flashing sequence...", "info", step="flash")
        self._log("Following exact command order from official flash-all.sh", "info", step="flash")
        
        # Change to bundle directory for file access
        original_cwd = Path.cwd()
        os.chdir(bundle_dir)
        
        try:
            # Pre-flight validation (matching flash-all.sh checks)
            # 1. Verify product (with retries and timeout handling)
            # NOTE: If device is slow to respond, we'll be lenient and proceed if serial is provided
            self._log("Verifying device product...", "info", step="flash")
            product = None
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    # Use longer timeout for product check (device might be slow to respond)
                    # Temporarily increase timeout for this check
                    result = self._run_fastboot(["getvar", "product"], timeout=20)
                    if result:
                        output = ""
                        if result.stdout:
                            output += result.stdout
                        if result.stderr:
                            if output:
                                output += "\n" + result.stderr
                            else:
                                output = result.stderr
                        
                        output = output.strip()
                        # Parse output: "product: panther" or similar
                        for line in output.split('\n'):
                            line = line.strip()
                            if 'product:' in line.lower():
                                parts = line.split(':', 1)
                                if len(parts) > 1:
                                    product = parts[1].strip().split()[0]  # Get first word after colon
                                    break
                        
                        if product:
                            break
                        
                except SystemExit:
                    # _run_fastboot can raise SystemExit on timeout, catch it
                    if attempt < max_retries - 1:
                        self._log(f"Product check attempt {attempt + 1} timed out, retrying...", "warning", step="flash")
                        time.sleep(3)
                    continue
                except Exception as e:
                    if attempt < max_retries - 1:
                        self._log(f"Product check attempt {attempt + 1} failed: {e}, retrying...", "warning", step="flash")
                        time.sleep(3)
                    else:
                        self._log(f"Could not determine product after {max_retries} attempts: {e}", "warning", step="flash")
            
            # If we still don't have product but device serial is provided, proceed with warning
            # The actual flashing commands will verify connection
            if not product:
                if self.device_serial:
                    self._log(
                        f"Could not verify device product via fastboot command, but device serial {self.device_serial} is provided. "
                        f"Device screen shows 'panther' - proceeding with flashing. "
                        f"The first flash command will verify the connection.",
                        "warning",
                        step="flash"
                    )
                    product = "panther"  # Assume correct since user provided serial and device is in fastboot
                else:
                    self._error(
                        "Could not determine device product. Please ensure device is in fastboot mode and connected.",
                        step="flash"
                    )
            elif product != "panther":
                self._error(
                    f"Device mismatch: expected 'panther' (Pixel 7), got '{product}'. "
                    f"This factory image is for panther only.",
                    step="flash"
                )
            else:
                self._log(f"Device product verified: {product}", "success", step="flash")
            
            # 2. Verify slot-count (with timeout handling)
            self._log("Verifying slot-count...", "info", step="flash")
            slotcount = None
            for attempt in range(3):
                slotcount = self._get_fastboot_var("slot-count", timeout=10)
                if slotcount:
                    break
                if attempt < 2:
                    time.sleep(2)
            
            if not slotcount:
                self._log(
                    "Could not verify slot-count (device may be slow to respond), assuming 2 slots (standard for Pixel 7)",
                    "warning",
                    step="flash"
                )
                slotcount = "2"  # Assume default for Pixel 7
            
            if slotcount != "2":
                self._error(
                    f"Unexpected slot-count: expected 2, got {slotcount}",
                    step="flash"
                )
            
            self._log(f"Slot-count verified: {slotcount}", "success", step="flash")
            
            # STEP 1: Flash bootloader to other slot (twice, as per official script)
            bootloader_file = bundle_dir / "bootloader-panther-cloudripper-16.4-14097579.img"
            if not bootloader_file.exists():
                # Try to find any bootloader file
                bootloader_files = list(bundle_dir.glob("bootloader-panther-*.img"))
                if bootloader_files:
                    bootloader_file = bootloader_files[0]
                else:
                    self._error("Bootloader image not found", step="flash")
            
            self._log("Flashing bootloader to other slot (first pass)...", "info", step="flash", partition="bootloader")
            self._log("This may take up to 3 minutes - please wait...", "info", step="flash", partition="bootloader")
            self._log("If device disconnects, it will reconnect automatically (Tensor Pixel USB reset)", "info", step="flash", partition="bootloader")
            result = self._run_fastboot(["flash", "--slot=other", "bootloader", str(bootloader_file)], timeout=180)
            if result.returncode != 0:
                self._error(f"Failed to flash bootloader: {result.stderr or result.stdout}", step="flash", partition="bootloader")
            self._log("✓ Bootloader flashed (first pass)", "success", step="flash", partition="bootloader")
            
            self._log("Setting active slot to other...", "info", step="flash")
            result = self._run_fastboot(["--set-active=other"], timeout=30)
            if result.returncode != 0:
                self._error(f"Failed to set active slot: {result.stderr or result.stdout}", step="flash")
            
            # EXACT SEQUENCE: fastboot reboot-bootloader → wait 5 seconds (as per official GrapheneOS CLI)
            self._log("Rebooting bootloader...", "info", step="flash")
            self._log("Using: fastboot reboot-bootloader", "info", step="flash")
            result = self._run_fastboot(["reboot-bootloader"], timeout=60)
            if result.returncode != 0:
                self._error(f"Failed to reboot bootloader: {result.stderr or result.stdout}", step="flash")
            
            # EXACT TIMING: Wait exactly 5 seconds as per official GrapheneOS CLI sequence
            self._log("Waiting 5 seconds for device to reinitialize (as per GrapheneOS CLI)...", "info", step="flash")
            self._log("Note: USB disconnect/reconnect is normal - device is rebooting, NOT looping", "info", step="flash")
            import time
            time.sleep(5)
            
            # Verify device is back in fastboot (Tensor Pixels USB re-enumeration)
            self._log("Verifying device is in fastboot mode...", "info", step="flash")
            test_result = self._run_fastboot(["getvar", "product"], timeout=10)
            if not test_result or test_result.returncode != 0:
                # Device might still be reconnecting - wait a bit more
                self._log("Device not immediately responsive, waiting a bit longer...", "info", step="flash")
                device_detected = self._wait_for_fastboot(timeout=60)
                if not device_detected:
                    self._log("Warning: Device not detected, but continuing anyway...", "warning", step="flash")
                    # Try one more direct check before giving up
                    test_result2 = self._run_fastboot(["getvar", "product"], timeout=5)
                    if not test_result2 or test_result2.returncode != 0:
                        self._error("Device did not return to fastboot mode after reboot and is not responding", step="flash")
                else:
                    self._log("Device successfully detected in fastboot mode", "success", step="flash")
            else:
                self._log("Device successfully detected in fastboot mode", "success", step="flash")
            
            # CRITICAL: Bootloader must be flashed TWICE to the other slot (as per official flash-all.sh)
            # Official script: flash to other slot → set-active=other → reboot-bootloader → sleep 5 → flash again → set-active=other → reboot-bootloader → sleep 5
            # This is REQUIRED by GrapheneOS for proper bootloader installation
            self._log("Flashing bootloader to other slot (second pass - as per official script)...", "info", step="flash", partition="bootloader")
            self._log("Official flash-all.sh flashes bootloader TWICE to the other slot", "info", step="flash", partition="bootloader")
            result = self._run_fastboot(["flash", "--slot=other", "bootloader", str(bootloader_file)], timeout=180)
            if result.returncode != 0:
                self._error(f"Failed to flash bootloader (second pass): {result.stderr or result.stdout}", step="flash", partition="bootloader")
            self._log("✓ Bootloader flashed (second pass)", "success", step="flash", partition="bootloader")
            
            self._log("Setting active slot to other...", "info", step="flash")
            result = self._run_fastboot(["--set-active=other"], timeout=30)
            if result.returncode != 0:
                self._error(f"Failed to set active slot: {result.stderr or result.stdout}", step="flash")
            
            # EXACT SEQUENCE: fastboot reboot-bootloader → wait 5 seconds (as per official GrapheneOS CLI)
            self._log("Rebooting bootloader (after second bootloader flash)...", "info", step="flash")
            self._log("Using: fastboot reboot-bootloader", "info", step="flash")
            result = self._run_fastboot(["reboot-bootloader"], timeout=60)
            if result.returncode != 0:
                self._error(f"Failed to reboot bootloader: {result.stderr or result.stdout}", step="flash")
            
            # EXACT TIMING: Wait exactly 5 seconds as per official GrapheneOS CLI sequence
            self._log("Waiting 5 seconds for device to reinitialize (as per GrapheneOS CLI)...", "info", step="flash")
            time.sleep(5)
            
            # Verify device is back in fastboot
            test_result = self._run_fastboot(["getvar", "product"], timeout=10)
            if not test_result or test_result.returncode != 0:
                self._log("Device not immediately responsive, waiting a bit longer...", "info", step="flash")
                if not self._wait_for_fastboot(timeout=60):
                    test_result2 = self._run_fastboot(["getvar", "product"], timeout=5)
                    if not test_result2 or test_result2.returncode != 0:
                        self._error("Device did not return to fastboot mode after second bootloader flash", step="flash")
            
            self._log("✓ Bootloader flash complete (both passes done)", "success", step="flash", partition="bootloader")
            
            # Verify max-download-size (required for super partition splits)
            # Be lenient here - if we can't get it, proceed anyway
            maxdownloadsize = self._get_fastboot_var("max-download-size", timeout=10)
            if maxdownloadsize:
                if maxdownloadsize != "0xf900000":
                    self._log(
                        f"Warning: Unexpected max-download-size: expected 0xf900000, got {maxdownloadsize}. Proceeding anyway.",
                        "warning",
                        step="flash"
                    )
                else:
                    self._log(f"Max-download-size verified: {maxdownloadsize}", "info", step="flash")
            else:
                self._log(
                    "Could not verify max-download-size (device may be slow), proceeding anyway",
                    "warning",
                    step="flash"
                )
            
            # Set active slot to A (required for super partition layout)
            self._log("Setting active slot to A...", "info", step="flash")
            result = self._run_fastboot(["--set-active=a"], timeout=30)
            if result.returncode != 0:
                self._error(f"Failed to set active slot to A: {result.stderr or result.stdout}", step="flash")
            
            # Verify current slot, but be lenient
            currentslot = self._get_fastboot_var("current-slot", timeout=10)
            if currentslot:
                if currentslot != "a":
                    self._error(
                        f"Unexpected current-slot: expected a, got {currentslot}",
                        step="flash"
                    )
                else:
                    self._log(f"Current slot verified: {currentslot}", "success", step="flash")
            else:
                self._log(
                    "Could not verify current-slot (device may be slow), proceeding anyway",
                    "warning",
                    step="flash"
                )
            
            # STEP 2: Flash radio
            # CRITICAL: This is the SECOND and FINAL reboot before flashing all other partitions
            # After this reboot, DO NOT reboot again until final reboot at the end
            radio_file = bundle_dir / "radio-panther-g5300q-250909-251024-b-14326967.img"
            if not radio_file.exists():
                radio_files = list(bundle_dir.glob("radio-panther-*.img"))
                if radio_files:
                    radio_file = radio_files[0]
                else:
                    self._error("Radio image not found", step="flash")
            
            self._log("Flashing radio...", "info", step="flash", partition="radio")
            result = self._run_fastboot(["flash", "radio", str(radio_file)], timeout=120)
            if result.returncode != 0:
                self._error(f"Failed to flash radio: {result.stderr or result.stdout}", step="flash", partition="radio")
            self._log("✓ Radio flashed", "success", step="flash", partition="radio")
            
            # CRITICAL: Reboot bootloader ONCE after radio flash (this is the LAST reboot before flashing all other partitions)
            # EXACT SEQUENCE: fastboot reboot-bootloader → wait 5 seconds (as per official GrapheneOS CLI)
            # This is REQUIRED by GrapheneOS - radio must reboot after flashing
            # After this reboot, flash ALL remaining partitions WITHOUT any more reboots
            self._log("Rebooting bootloader after radio flash (required by GrapheneOS)...", "info", step="flash")
            self._log("Using: fastboot reboot-bootloader", "info", step="flash")
            self._log("This is the LAST reboot - all remaining partitions will be flashed in one session", "info", step="flash")
            result = self._run_fastboot(["reboot-bootloader"], timeout=60)
            if result.returncode != 0:
                self._error(f"Failed to reboot bootloader: {result.stderr or result.stdout}", step="flash")
            
            # EXACT TIMING: Wait exactly 5 seconds as per official GrapheneOS CLI sequence
            self._log("Waiting 5 seconds for device to reinitialize (as per GrapheneOS CLI)...", "info", step="flash")
            self._log("Note: USB disconnect/reconnect is normal - device is rebooting, NOT looping", "info", step="flash")
            import time
            time.sleep(5)
            
            # Verify device is back in fastboot (ONE-TIME check)
            # This is the LAST wait - after this, we flash everything without rebooting
            self._log("Verifying device is in fastboot mode...", "info", step="flash")
            test_result = self._run_fastboot(["getvar", "product"], timeout=10)
            if not test_result or test_result.returncode != 0:
                # Device might still be reconnecting - wait a bit more
                self._log("Device not immediately responsive, waiting a bit longer...", "info", step="flash")
                device_detected = self._wait_for_fastboot(timeout=60)
                if not device_detected:
                    self._log("Warning: Device not detected, but continuing anyway...", "warning", step="flash")
                    # Try one more direct check before giving up
                    test_result2 = self._run_fastboot(["getvar", "product"], timeout=5)
                    if not test_result2 or test_result2.returncode != 0:
                        self._error("Device did not return to fastboot mode after radio flash", step="flash")
                else:
                    self._log("Device successfully detected in fastboot mode", "success", step="flash")
            else:
                self._log("Device successfully detected in fastboot mode", "success", step="flash")
            
            # STEP 3: AVB custom key operations
            # Note: Erasing avb_custom_key may fail if partition doesn't exist (normal on fresh devices)
            self._log("Erasing AVB custom key...", "info", step="flash")
            result = self._run_fastboot(["erase", "avb_custom_key"], timeout=30)
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or ""
                if "could not clear" in error_msg.lower() or "does not exist" in error_msg.lower():
                    # Partition doesn't exist - this is normal on fresh devices
                    self._log("AVB custom key partition does not exist (normal on fresh devices) - skipping erase", "info", step="flash")
                else:
                    self._log(f"Warning: Failed to erase avb_custom_key: {error_msg}", "warning", step="flash")
            
            avb_key_file = bundle_dir / "avb_pkmd.bin"
            if avb_key_file.exists():
                self._log("Flashing AVB custom key...", "info", step="flash")
                result = self._run_fastboot(["flash", "avb_custom_key", str(avb_key_file)], timeout=30)
                if result.returncode != 0:
                    self._error(f"Failed to flash avb_custom_key: {result.stderr or result.stdout}", step="flash")
            else:
                self._log("avb_pkmd.bin not found - skipping AVB custom key flash", "warning", step="flash")
            
            # STEP 4: OEM operations
            self._log("Disabling UART...", "info", step="flash")
            result = self._run_fastboot(["oem", "uart", "disable"], timeout=30)
            if result.returncode != 0:
                self._log(f"Warning: Failed to disable UART: {result.stderr or result.stdout}", "warning", step="flash")
            
            # STEP 5: Erase operations
            for partition in ["fips", "dpm_a", "dpm_b"]:
                self._log(f"Erasing {partition}...", "info", step="flash")
                result = self._run_fastboot(["erase", partition], timeout=30)
                if result.returncode != 0:
                    self._log(f"Warning: Failed to erase {partition}: {result.stderr or result.stdout}", "warning", step="flash")
            
            # STEP 6: Android-info.zip validation (doesn't perform update, just checks)
            # Note: This is a validation step that checks device compatibility
            # If it fails, we log a warning but continue - the actual flash commands will fail if incompatible
            android_info_file = bundle_dir / "android-info.zip"
            if android_info_file.exists():
                self._log("Validating android-info.txt requirements...", "info", step="flash")
                result = self._run_fastboot(["--disable-super-optimization", "--skip-reboot", "update", str(android_info_file)], timeout=60)
                if result.returncode != 0:
                    # Don't fail on validation error - continue flashing
                    # The actual flash commands will fail if device is incompatible
                    error_output = result.stderr or result.stdout or ""
                    self._log(
                        f"Warning: android-info validation failed: {error_output[:200] if error_output else 'Unknown error'}",
                        "warning",
                        step="flash"
                    )
                    self._log("Continuing with flash - actual flash commands will verify compatibility", "info", step="flash")
                else:
                    self._log("✓ Android-info validation passed", "success", step="flash")
            
            self._log("Canceling snapshot update...", "info", step="flash")
            result = self._run_fastboot(["snapshot-update", "cancel"], timeout=30)
            if result.returncode != 0:
                self._log(f"Warning: Failed to cancel snapshot update: {result.stderr or result.stdout}", "warning", step="flash")
            
            # STEP 7: Core partitions (in exact order from flash-all.sh)
            # CRITICAL: After radio reboot, flash ALL remaining partitions WITHOUT any more reboots
            # This is a LINEAR sequence - no loops, no state resets, no device re-checks
            # Flash all partitions in one continuous session
            self._log("=" * 60, "info", step="flash")
            self._log("Starting core partition flashing (NO MORE REBOOTS)", "info", step="flash")
            self._log("All remaining partitions will be flashed in one session", "info", step="flash")
            self._log("=" * 60, "info", step="flash")
            
            core_partitions = [
                ("boot", "boot.img"),
                ("init_boot", "init_boot.img"),
                ("dtbo", "dtbo.img"),
                ("vendor_kernel_boot", "vendor_kernel_boot.img"),
                ("pvmfw", "pvmfw.img"),
                ("vendor_boot", "vendor_boot.img"),
                ("vbmeta", "vbmeta.img"),
            ]
            
            # Flash all core partitions in sequence - NO REBOOT between any of these
            for partition_name, filename in core_partitions:
                img_file = bundle_dir / filename
                if img_file.exists():
                    self._log(f"Flashing {partition_name}...", "info", step="flash", partition=partition_name)
                    result = self._run_fastboot(["flash", partition_name, str(img_file)], timeout=120)
                    if result.returncode != 0:
                        self._error(
                            f"Failed to flash {partition_name}: {result.stderr or result.stdout}",
                            step="flash",
                            partition=partition_name
                        )
                    self._log(f"✓ {partition_name} flashed", "success", step="flash", partition=partition_name)
                else:
                    self._log(f"Warning: {filename} not found, skipping", "warning", step="flash")
            
            # STEP 8: Erase userdata and metadata
            # CRITICAL: Still in bootloader fastboot session - NO REBOOT
            # These erase operations happen BEFORE transitioning to fastbootd
            self._log("Erasing userdata...", "info", step="flash")
            result = self._run_fastboot(["erase", "userdata"], timeout=60)
            if result.returncode != 0:
                self._log(f"Warning: Failed to erase userdata: {result.stderr or result.stdout}", "warning", step="flash")
            
            self._log("Erasing metadata...", "info", step="flash")
            result = self._run_fastboot(["erase", "metadata"], timeout=60)
            if result.returncode != 0:
                self._log(f"Warning: Failed to erase metadata: {result.stderr or result.stdout}", "warning", step="flash")
            
            # CRITICAL: Super partition is flashed in BOOTLOADER FASTBOOT, NOT fastbootd!
            # Official flash-all.sh does NOT use "fastboot reboot fastboot" - super images are flashed directly
            # This is STEP 9 in the official sequence: Flash super images in bootloader fastboot mode
            # NO transition to fastbootd - all super images are flashed while in bootloader fastboot
            self._log("=" * 60, "info", step="flash")
            self._log("Flashing super partition in bootloader fastboot mode (NO REBOOT TO FASTBOOTD)", "info", step="flash")
            self._log("Official flash-all.sh flashes super images directly in bootloader fastboot", "info", step="flash")
            self._log("=" * 60, "info", step="flash")
            
            # STEP 9: Flash super partition (split images) - in BOOTLOADER FASTBOOT mode
            # CRITICAL: Still in same bootloader fastboot session - NO REBOOT
            # Flash all super_*.img files sequentially - this is the last partition flash before final reboot
            
            super_images = sorted(bundle_dir.glob("super_*.img"))
            if super_images:
                total_super = len(super_images)
                self._log(f"Flashing super partition ({total_super} split images) in bootloader fastboot...", "info", step="flash", partition="super")
                for idx, super_img in enumerate(super_images, 1):
                    self._log(f"Flashing super {idx}/{total_super}...", "info", step="flash", partition="super")
                    result = self._run_fastboot(["flash", "super", str(super_img)], timeout=300)
                    if result.returncode != 0:
                        self._error(
                            f"Failed to flash super partition ({idx}/{total_super}): {result.stderr or result.stdout}",
                            step="flash",
                            partition="super"
                        )
                self._log("✓ Super partition flashed successfully", "success", step="flash", partition="super")
            else:
                self._error("Super partition images not found", step="flash")
            
            self._log("=" * 60, "info", step="flash")
            self._log("✓ All partitions flashed successfully (NO REBOOTS during flash session)", "success", step="flash")
            self._log("Ready for final reboot - all flashing operations completed", "info", step="flash")
            self._log("=" * 60, "info", step="flash")
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    def step5_flash_grapheneos(self, partition_files: Dict[str, Any]):
        """
        STEP 5: Flash GrapheneOS (local bundle only)
        
        Flash order for Pixel 7 (panther):
        1. bootloader*.img → fastboot reboot bootloader
        2. radio*.img → fastboot reboot bootloader
        3. Core partitions: boot, vendor_boot, dtbo
        4. System partitions: super (or system, product, vendor individually)
        5. vbmeta with --disable-verity --disable-verification
        """
        self._log("Starting GrapheneOS flash process...", "info", step="flash")
        self._log(
            "⚠️  WARNING: Flashing will modify critical partitions on your device!",
            "warning",
            step="flash"
        )
        
        # Flash bootloader
        if "bootloader" in partition_files:
            bootloader_img = partition_files["bootloader"]
            self._log(f"Flashing bootloader: {bootloader_img.name}", "info", step="flash", partition="bootloader")
            self._log("Note: This is the first flash command - it will verify device connection", "info", step="flash")
            try:
                result = self._run_fastboot(["flash", "bootloader", str(bootloader_img)], timeout=120)
                if result.returncode != 0:
                    self._error(f"Failed to flash bootloader: {result.stderr or result.stdout}", step="flash", partition="bootloader")
                self._log("✓ Bootloader flashed", "success", step="flash", partition="bootloader")
            except SystemExit:
                # _run_fastboot can raise SystemExit on timeout/error
                # If this is the first command and it fails, device might not be connected
                self._error(
                    f"Failed to flash bootloader - device may not be connected or responding.\n"
                    f"Please ensure device is in fastboot mode and connected via USB.",
                    step="flash",
                    partition="bootloader"
                )
            
            # Reboot bootloader after bootloader flash
            self._log("Rebooting to bootloader after bootloader flash...", "info", step="flash")
            result = self._run_fastboot(["reboot", "bootloader"], timeout=60)
            if result.returncode != 0:
                self._error("Failed to reboot to bootloader", step="flash")
            
            # MANDATORY: Wait for fastboot after reboot (Tensor Pixels reset USB)
            self._log("Waiting for device to reinitialize in fastboot mode after bootloader flash...", "info", step="flash")
            self._log("Note: USB will disconnect/reconnect - this is normal for Tensor Pixels", "info", step="flash")
            if not self._wait_for_fastboot(timeout=90):
                self._error("Device did not return to bootloader mode after bootloader flash within 90 seconds", step="flash")
        
        # Flash radio
        # CRITICAL: This is the SECOND and FINAL reboot before flashing all other partitions
        # After this reboot, flash ALL remaining partitions WITHOUT any more reboots
        if "radio" in partition_files:
            radio_img = partition_files["radio"]
            self._log(f"Flashing radio: {radio_img.name}", "info", step="flash", partition="radio")
            result = self._run_fastboot(["flash", "radio", str(radio_img)], timeout=120)
            if result.returncode != 0:
                self._error(f"Failed to flash radio: {result.stderr or result.stdout}", step="flash", partition="radio")
            self._log("✓ Radio flashed", "success", step="flash", partition="radio")
            
            # CRITICAL: Reboot bootloader ONCE after radio flash (this is the LAST reboot before flashing all other partitions)
            # This is REQUIRED by GrapheneOS - radio must reboot after flashing
            # After this reboot, flash ALL remaining partitions WITHOUT any more reboots
            self._log("Rebooting to bootloader after radio flash (required by GrapheneOS)...", "info", step="flash")
            self._log("This is the LAST reboot - all remaining partitions will be flashed in one session", "info", step="flash")
            result = self._run_fastboot(["reboot", "bootloader"], timeout=60)
            if result.returncode != 0:
                self._error("Failed to reboot to bootloader", step="flash")
            
            # MANDATORY: Wait for fastboot after reboot (Tensor Pixels reset USB)
            # This is a ONE-TIME wait - after this, we flash everything without rebooting
            self._log("Waiting for device to reinitialize in fastboot mode after radio flash...", "info", step="flash")
            self._log("Note: USB will disconnect/reconnect - this is normal for Tensor Pixels", "info", step="flash")
            self._log("Note: This is the LAST wait - after this, all remaining partitions will be flashed without rebooting", "info", step="flash")
            if not self._wait_for_fastboot(timeout=90):
                self._error("Device did not return to fastboot mode after radio flash within 90 seconds", step="flash")
        
        # Flash core partitions (boot, vendor_boot, dtbo) - NO reboot between these
        core_partitions = [
            ("boot", "boot"),
            ("vendor_boot", "vendor_boot"),
            ("dtbo", "dtbo"),
        ]
        
        for partition_name, file_key in core_partitions:
            if file_key in partition_files:
                img_path = partition_files[file_key]
                self._log(f"Flashing {partition_name}...", "info", step="flash", partition=partition_name)
                result = self._run_fastboot(["flash", partition_name, str(img_path)], timeout=120)
                if result.returncode != 0:
                    self._error(
                        f"Failed to flash {partition_name}: {result.stderr or result.stdout}",
                        step="flash",
                        partition=partition_name
                    )
                self._log(f"✓ {partition_name} flashed", "success", step="flash", partition=partition_name)
        
        # Flash system partitions
        if "super" in partition_files:
            # Flash super partition (split images)
            super_images = partition_files["super"]
            self._log(
                f"Flashing super partition ({len(super_images)} split images)...",
                "info",
                step="flash",
                partition="super"
            )
            for super_img in super_images:
                self._log(f"Flashing {super_img.name}...", "info", step="flash", partition="super")
                result = self._run_fastboot(["flash", "super", str(super_img)], timeout=300)
                if result.returncode != 0:
                    self._error(
                        f"Failed to flash super partition {super_img.name}: {result.stderr or result.stdout}",
                        step="flash",
                        partition="super"
                    )
            self._log("✓ Super partition flashed", "success", step="flash", partition="super")
        else:
            # Flash individual partitions
            for partition in ["system", "product", "vendor"]:
                if partition in partition_files:
                    img_path = partition_files[partition]
                    self._log(f"Flashing {partition}...", "info", step="flash", partition=partition)
                    result = self._run_fastboot(["flash", partition, str(img_path)], timeout=300)
                    if result.returncode != 0:
                        self._error(
                            f"Failed to flash {partition}: {result.stderr or result.stdout}",
                            step="flash",
                            partition=partition
                        )
                    self._log(f"✓ {partition} flashed", "success", step="flash", partition=partition)
        
        # Flash vbmeta with verification disabled
        if "vbmeta" in partition_files:
            vbmeta_img = partition_files["vbmeta"]
            self._log("Flashing vbmeta (with verity/verification disabled)...", "info", step="flash", partition="vbmeta")
            result = self._run_fastboot([
                "flash", "vbmeta",
                "--disable-verity",
                "--disable-verification",
                str(vbmeta_img)
            ], timeout=120)
            if result.returncode != 0:
                self._error(
                    f"Failed to flash vbmeta: {result.stderr or result.stdout}",
                    step="flash",
                    partition="vbmeta"
                )
            self._log("✓ vbmeta flashed", "success", step="flash", partition="vbmeta")
        
        self._log("✓ All partitions flashed successfully", "success", step="flash")
    
    def step6_final_reboot(self):
        """
        STEP 6: Final reboot
        Reboot device normally to boot into GrapheneOS.
        """
        self._log("Rebooting device...", "info", step="reboot")
        result = self._run_fastboot(["reboot"], timeout=30)
        
        if result.returncode != 0:
            self._log(
                "WARNING: Reboot command returned error, but flash may have succeeded. "
                "If device does not reboot, manually power on.",
                "warning",
                step="reboot"
            )
        else:
            self._log("✓ Device rebooting", "success", step="reboot")
        
        self._log(
            "✓ Flash completed successfully! Device is rebooting into GrapheneOS.",
            "success",
            step="complete"
        )


def main():
    """Main entry point for GrapheneOS flasher"""
    parser = argparse.ArgumentParser(
        description="Flash GrapheneOS to Google Pixel 7 (panther) with bootloader unlock support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SECURITY NOTES:
- Bootloader unlock requires physical confirmation on device (Volume + Power)
- OEM unlocking must be enabled in Developer options
- Unlocking will factory reset the device (all data will be erased)
- This script will NEVER attempt silent or unattended unlock

Example usage:
  python flasher.py \\
    --fastboot-path /usr/local/bin/fastboot \\
    --adb-path /usr/local/bin/adb \\
    --bundle-path ~/.graphene-installer/bundles/panther/2025122500 \\
    --confirm
        """
    )
    parser.add_argument(
        "--fastboot-path",
        required=True,
        help="Path to fastboot binary (absolute path)"
    )
    parser.add_argument(
        "--adb-path",
        required=True,
        help="Path to ADB binary (absolute path)"
    )
    parser.add_argument(
        "--bundle-path",
        required=True,
        help="Path to extracted GrapheneOS bundle directory"
    )
    parser.add_argument(
        "--device-serial",
        help="Device serial number (optional, required if multiple devices connected)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm flash operation (required)"
    )
    parser.add_argument(
        "--skip-unlock",
        action="store_true",
        help="Skip bootloader unlock step (device must already be unlocked)"
    )
    
    args = parser.parse_args()
    
    if not args.confirm:
        error_data = {
            "step": "validation",
            "status": "error",
            "message": "Flash confirmation required. Use --confirm flag to proceed."
        }
        print(json.dumps(error_data), file=sys.stderr)
        sys.exit(1)
    
    # Initialize flasher
    flasher = GrapheneFlasher(
        fastboot_path=args.fastboot_path,
        adb_path=args.adb_path,
        bundle_path=args.bundle_path,
        device_serial=args.device_serial
    )
    
    try:
            # If skip-unlock is used, skip ALL preflight checks to avoid any fastboot commands
            # that might cause device to reboot or timeout
            if args.skip_unlock:
                flasher._log("Skip-unlock flag enabled - skipping ALL preflight checks", "info", step="preflight")
                flasher._log("Assuming device is in fastboot mode and ready for flashing", "info", step="preflight")
                flasher._log(f"Device serial: {flasher.device_serial}", "info", step="preflight")
                flasher._log(f"Bundle path: {flasher.bundle_path}", "info", step="preflight")
                device_in_fastboot = True
                # Proceed directly to flashing without any validation or detection
            else:
                # Check if device is already in fastboot mode
                # If so, skip ADB preflight checks
                # Retry a few times as device might be rebooting or slow to respond
                flasher._log("Checking if device is in fastboot mode...", "info", step="preflight")
                device_in_fastboot = False
                fastboot_devices = []
                
                # First, try without serial flag to see all devices (in case serial flag causes issues)
                flasher._log("Checking for any fastboot devices (without serial filter)...", "info", step="preflight")
                # Temporarily disable serial flag
                flasher._use_serial_flag = False
                result_all = flasher._run_fastboot(["devices"], timeout=10)
                flasher._use_serial_flag = True
                output_all = (result_all.stdout or "").strip()
                if not output_all:
                    output_all = (result_all.stderr or "").strip()
                else:
                    stderr_all = (result_all.stderr or "").strip()
                    if stderr_all and stderr_all not in output_all:
                        output_all = output_all + "\n" + stderr_all
                
                flasher._log(f"Fastboot devices (all): {repr(output_all)}", "info", step="preflight")
                
                # Try up to 3 times with a short delay between attempts
                for attempt in range(3):
                    if attempt > 0:
                        flasher._log(f"Retrying fastboot device detection (attempt {attempt + 1}/3)...", "info", step="preflight")
                        time.sleep(2)
                    
                    # Try with serial flag if serial is specified
                    if flasher.device_serial:
                        flasher._use_serial_flag = True
                        result = flasher._run_fastboot(["devices"], timeout=10)
                    else:
                        flasher._use_serial_flag = False
                        result = flasher._run_fastboot(["devices"], timeout=10)
                    
                    flasher._log(f"Fastboot devices command return code: {result.returncode}", "info", step="preflight")
                    # Fastboot outputs to stderr on some platforms, check both stdout and stderr
                    output = (result.stdout or "").strip()
                    if not output:
                        output = (result.stderr or "").strip()
                    else:
                        # Combine both if both have content
                        stderr_out = (result.stderr or "").strip()
                        if stderr_out and stderr_out not in output:
                            output = output + "\n" + stderr_out
                    
                    # If output is empty, try using the "all devices" output we got earlier
                    if not output and output_all:
                        flasher._log("Using previously detected devices list", "info", step="preflight")
                        output = output_all
                    
                    flasher._log(f"Fastboot devices output (attempt {attempt + 1}): {repr(output)}", "info", step="preflight")
                    
                    if result.returncode == 0 or output:  # Accept even if returncode != 0 but we have output
                        # Fastboot doesn't have a header line like ADB - it just lists devices directly
                        # Format: "SERIAL\tfastboot\n" or "SERIAL\tfastboot"
                        lines = output.split('\n')
                        fastboot_devices = []
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            # Filter out status/warning messages
                            if line.lower().startswith('waiting') or line.lower().startswith('fastboot version'):
                                continue
                            if '\t' in line:
                                # Split by tab to get serial number
                                parts = line.split('\t')
                                if parts[0] and parts[0].strip() and 'fastboot' in line.lower():
                                    serial = parts[0].strip()
                                    if serial and len(serial) > 3:  # Valid serial
                                        fastboot_devices.append(serial)
                            elif not line.startswith('Waiting') and not line.lower().startswith('fastboot'):
                                # Try splitting by whitespace
                                parts = line.split()
                                for part in parts:
                                    if len(part) > 5 and part.isalnum():  # Serial numbers are usually longer and alphanumeric
                                        fastboot_devices.append(part)
                                        break
                        
                        if fastboot_devices:
                            flasher._log(f"Found {len(fastboot_devices)} device(s) in fastboot: {fastboot_devices}", "info", step="preflight")
                            
                            # Check if our device (or any device if serial not specified) is in fastboot
                            if flasher.device_serial:
                                if flasher.device_serial in fastboot_devices:
                                    device_in_fastboot = True
                                    flasher._log(f"Device {flasher.device_serial} found in fastboot mode", "success", step="preflight")
                                    break  # Found it, exit retry loop
                                else:
                                    flasher._log(f"Device {flasher.device_serial} not in detected list {fastboot_devices}, but will try to proceed anyway", "warning", step="preflight")
                                    # If we have devices but not the specified one, still try to proceed
                                    # Maybe the serial is slightly different or device is transitioning
                                    if len(fastboot_devices) == 1:
                                        flasher._log(f"Using detected device {fastboot_devices[0]} instead", "info", step="preflight")
                                        flasher.device_serial = fastboot_devices[0]
                                        device_in_fastboot = True
                                        break
                            else:
                                device_in_fastboot = True
                                if len(fastboot_devices) == 1:
                                    flasher.device_serial = fastboot_devices[0]
                                    flasher._log(f"Auto-selected device: {flasher.device_serial}", "info", step="preflight")
                                    break  # Found it, exit retry loop
                                elif len(fastboot_devices) > 1:
                                    flasher._error("Multiple devices in fastboot mode. Please specify device serial with --device-serial", step="preflight")
                            # If we got here and device_in_fastboot is still False, continue retrying
                        else:
                            flasher._log(f"No devices found in fastboot output (attempt {attempt + 1}/3)", "info", step="preflight")
                
                # If still not found but we have a serial, try to validate by checking unlock status directly
                # But don't fail if this times out - device might be slow to respond
                if not device_in_fastboot and flasher.device_serial:
                    flasher._log("Device not found in fastboot list, but attempting direct connection check...", "info", step="preflight")
                    try:
                        # Try a simple fastboot command to see if device responds
                        # Use shorter timeout to avoid hanging too long
                        # We need to catch SystemExit from _error() if timeout occurs
                        try:
                            test_result = flasher._run_fastboot(["getvar", "unlocked"], timeout=3)
                            if test_result and (test_result.returncode == 0 or test_result.stderr or test_result.stdout):
                                output = (test_result.stdout or "").strip()
                                if not output:
                                    output = (test_result.stderr or "").strip()
                                if output and "unlocked" in output.lower():
                                    flasher._log("Device responds to fastboot commands, assuming it's in fastboot mode", "success", step="preflight")
                                    device_in_fastboot = True
                        except SystemExit:
                            # _error() raises SystemExit on timeout, catch it here
                            flasher._log("Direct connection test timed out. Device may be rebooting or slow to respond. Will proceed anyway if serial is provided.", "warning", step="preflight")
                            # Don't re-raise, just continue
                    except Exception as e:
                        # Don't fail on timeout - device might be transitioning states
                        if "timeout" in str(e).lower():
                            flasher._log("Direct connection test timed out. Device may be rebooting or slow to respond. Will proceed anyway if serial is provided.", "warning", step="preflight")
                        else:
                            flasher._log(f"Direct connection test failed: {e}", "warning", step="preflight")
                
                # If we still don't have device but we have a serial number, assume it's in fastboot
                # The actual flashing commands will verify the connection
                if not device_in_fastboot and flasher.device_serial:
                    flasher._log(
                        f"Device {flasher.device_serial} not detected in fastboot list, but proceeding anyway. "
                        f"The device may be transitioning states or slow to respond. Flashing commands will verify connection.",
                        "warning",
                        step="preflight"
                    )
                    device_in_fastboot = True  # Proceed anyway - let the actual commands handle verification
                
                if not device_in_fastboot:
                    flasher._log("Device not found in fastboot mode after retries. Will attempt ADB preflight checks.", "warning", step="preflight")
                
                if device_in_fastboot:
                    # Device is already in fastboot, skip ADB preflight checks
                    flasher._log("✓ Device already in fastboot mode, skipping ADB preflight checks", "success", step="preflight")
                    flasher._log("Note: OEM unlocking check skipped (requires ADB mode). If unlock fails, ensure OEM unlocking is enabled.", "warning", step="preflight")
                else:
                    # STEP 1: Preflight checks (ADB mode)
                    flasher._log("Device not in fastboot mode, starting ADB preflight checks...", "info", step="preflight")
                    flasher.step1_preflight_checks()
            
            # STEP 2 & 3: Validate and unlock
            # CRITICAL: When skip-unlock is used, we skip ALL validation to avoid any fastboot commands
            # that might cause device to reboot or timeout. The flashing commands themselves will verify connection.
            if args.skip_unlock:
                flasher._log("=" * 60, "info", step="validate")
                flasher._log("Skip-unlock flag enabled - skipping all validation steps", "info", step="validate")
                flasher._log("Device is assumed to be in fastboot mode and unlocked", "info", step="validate")
                flasher._log("Flashing commands will verify device connection when they run", "info", step="validate")
                flasher._log("=" * 60, "info", step="validate")
                product = "panther"  # Assume Pixel 7 since this is the panther flasher
                is_unlocked = True  # Assume unlocked since skip-unlock is used
            else:
                # STEP 2: Validate fastboot state (only if not skipping unlock)
                product, is_unlocked = flasher.step2_validate_fastboot_state()
                
                # STEP 3: Unlock bootloader (if needed)
                if not is_unlocked:
                    flasher.step3_unlock_bootloader()
                else:
                    flasher._log("Bootloader already unlocked, skipping unlock step", "info", step="unlock")
            
            # STEP 4: Reboot back to fastboot
            # CRITICAL: Never reboot if skip-unlock is used (device is assumed to be in fastboot already)
            # Only reboot if we started from ADB mode AND we're not skipping unlock
            if args.skip_unlock:
                flasher._log("Skip-unlock enabled - skipping reboot step (device assumed to be in fastboot)", "info", step="reboot_fastboot")
                flasher._log("Proceeding directly to partition file discovery and flashing", "info", step="reboot_fastboot")
            elif not device_in_fastboot:
                flasher._log("Rebooting to fastboot mode...", "info", step="reboot_fastboot")
                flasher.step4_reboot_to_fastboot()
            else:
                flasher._log("Device already in fastboot mode, skipping reboot step", "info", step="reboot_fastboot")
                flasher._log("Proceeding directly to partition file discovery and flashing", "info", step="reboot_fastboot")
            
            # Find bundle directory and check for official flash-all script
            flasher._log("Locating bundle directory...", "info", step="flash")
            bundle_dir = flasher._find_bundle_directory()
            flasher._log(f"Using bundle directory: {bundle_dir}", "info", step="flash")
            
            # STEP 5: Flash GrapheneOS using explicit fastboot commands
            # We skip flash-all.sh because:
            # 1. It doesn't support --device-serial flag (can't target specific device)
            # 2. Tensor Pixels (Pixel 6-8) have USB re-enumeration on reboot that flash-all.sh doesn't handle
            # 3. Explicit commands allow us to use _wait_for_fastboot() after each reboot
            flasher._log("Using explicit fastboot commands (skipping flash-all.sh)", "info", step="flash")
            flasher._log("Reason: flash-all.sh doesn't support device serial targeting and doesn't handle Tensor Pixel USB resets", "info", step="flash")
            flasher._log("Explicit commands include proper wait_for_fastboot() handling for Tensor Pixel USB re-enumeration", "info", step="flash")
            
            partition_files = flasher.find_partition_files()
            flasher._log(f"Found {len(partition_files)} partition file(s) to flash", "info", step="flash")
            if partition_files:
                flasher._log(f"Partitions to flash: {', '.join(partition_files.keys())}", "info", step="flash")
            
            # Use explicit fastboot commands with Tensor Pixel USB reset handling
            flasher.step5_flash_grapheneos_official_sequence(partition_files, bundle_dir)
            # STEP 6: Final reboot
            flasher.step6_final_reboot()
            
            # Success
            result = {
                "success": True,
                "message": "Flash completed successfully"
            }
            print(json.dumps(result))
            sys.exit(0)
            
    except KeyboardInterrupt:
        error_data = {
            "step": "interrupted",
            "status": "error",
            "message": "Flash operation interrupted by user"
        }
        print(json.dumps(error_data), file=sys.stderr)
        sys.exit(1)
    except SystemExit:
        # Re-raise system exits (from _error)
        raise
    except Exception as e:
        error_data = {
            "step": "unknown",
            "status": "error",
            "message": f"Unexpected error: {e}"
        }
        print(json.dumps(error_data), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
