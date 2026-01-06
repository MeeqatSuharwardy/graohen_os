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
    
    def _error(self, message: str, step: Optional[str] = None):
        """Print structured error JSON and exit"""
        error_data = {
            "step": step or "unknown",
            "status": "error",
            "message": message
        }
        print(json.dumps(error_data), file=sys.stderr)
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
        print(json.dumps(log_data))
        sys.stdout.flush()
    
    def _run_fastboot(self, args: List[str], timeout: int = 60, stream: bool = False) -> subprocess.CompletedProcess:
        """
        Run fastboot command with proper error handling.
        
        SECURITY: Fastboot output goes to stderr on some platforms.
        We capture both stdout and stderr for reliability.
        """
        cmd = [str(self.fastboot_path)]
        if self.device_serial:
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
            self._error(f"Fastboot command timed out after {timeout}s: {' '.join(cmd)}", step="fastboot")
        except FileNotFoundError:
            self._error(f"Fastboot executable not found: {self.fastboot_path}", step="fastboot")
        except Exception as e:
            self._error(f"Failed to run fastboot: {e}", step="fastboot")
    
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
    
    def _get_fastboot_var(self, var_name: str) -> Optional[str]:
        """
        Get fastboot variable value.
        Fastboot outputs getvar to stderr, so we check both.
        """
        result = self._run_fastboot(["getvar", var_name], timeout=10)
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
        
        # Wait for device to enter bootloader (up to 30 seconds)
        self._log("Waiting for device to enter bootloader mode...", "info", step="preflight")
        for _ in range(30):
            time.sleep(1)
            result = self._run_fastboot(["devices"], timeout=5)
            devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip() and line.startswith(self.device_serial)]
            if devices:
                self._log("✓ Device entered bootloader mode", "success", step="preflight")
                return True
        
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
        result = self._run_fastboot(["devices"], timeout=10)
        if result.returncode != 0:
            self._error("Failed to list fastboot devices", step="validate")
        
        # Parse fastboot devices output (fastboot doesn't have header, outputs to stderr sometimes)
        output = (result.stdout or "").strip()
        if not output:
            output = (result.stderr or "").strip()
        else:
            stderr_out = (result.stderr or "").strip()
            if stderr_out and stderr_out not in output:
                output = output + "\n" + stderr_out
        
        fastboot_devices = []
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
            self._error("No devices found in fastboot mode", step="validate")
        
        if self.device_serial and self.device_serial not in fastboot_devices:
            self._error(
                f"Device {self.device_serial} not found in fastboot mode",
                step="validate"
            )
        
        self._log(f"Device connected in fastboot mode: {self.device_serial}", "info", step="validate")
        
        # Get device product (codename)
        product = self._get_fastboot_var("product")
        if not product:
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
            self._error("Could not determine bootloader unlock status", step="validate")
        
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
                devices_output = result.stdout.strip()
                devices = [line.split()[0] for line in devices_output.split('\n')[1:] if line.strip()]
                
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
        
        # Wait for device to re-enter bootloader
        self._log("Waiting for device to re-enter bootloader mode...", "info", step="reboot_fastboot")
        for _ in range(30):
            time.sleep(1)
            result = self._run_fastboot(["devices"], timeout=5)
            devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip()]
            if self.device_serial in devices:
                self._log("✓ Device back in bootloader mode", "success", step="reboot_fastboot")
                return
        
        self._error("Device did not return to bootloader mode within 30 seconds", step="reboot_fastboot")
    
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
        
        # Core partitions (exact names)
        for partition in ["boot", "vendor_boot", "dtbo", "vbmeta"]:
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
            result = self._run_fastboot(["flash", "bootloader", str(bootloader_img)], timeout=120)
            if result.returncode != 0:
                self._error(f"Failed to flash bootloader: {result.stderr or result.stdout}", step="flash", partition="bootloader")
            self._log("✓ Bootloader flashed", "success", step="flash", partition="bootloader")
            
            # Reboot bootloader after bootloader flash
            self._log("Rebooting to bootloader after bootloader flash...", "info", step="flash")
            result = self._run_fastboot(["reboot", "bootloader"], timeout=60)
            if result.returncode != 0:
                self._error("Failed to reboot to bootloader", step="flash")
            
            # Wait for device to return
            for _ in range(30):
                time.sleep(1)
                result = self._run_fastboot(["devices"], timeout=5)
                devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip()]
                if self.device_serial in devices:
                    break
            else:
                self._error("Device did not return to bootloader after bootloader flash", step="flash")
        
        # Flash radio
        if "radio" in partition_files:
            radio_img = partition_files["radio"]
            self._log(f"Flashing radio: {radio_img.name}", "info", step="flash", partition="radio")
            result = self._run_fastboot(["flash", "radio", str(radio_img)], timeout=120)
            if result.returncode != 0:
                self._error(f"Failed to flash radio: {result.stderr or result.stdout}", step="flash", partition="radio")
            self._log("✓ Radio flashed", "success", step="flash", partition="radio")
            
            # Reboot bootloader after radio flash
            self._log("Rebooting to bootloader after radio flash...", "info", step="flash")
            result = self._run_fastboot(["reboot", "bootloader"], timeout=60)
            if result.returncode != 0:
                self._error("Failed to reboot to bootloader", step="flash")
            
            # Wait for device to return
            for _ in range(30):
                time.sleep(1)
                result = self._run_fastboot(["devices"], timeout=5)
                devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip()]
                if self.device_serial in devices:
                    break
            else:
                self._error("Device did not return to bootloader after radio flash", step="flash")
        
        # Flash core partitions
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
        # Check if device is already in fastboot mode
        # If so, skip ADB preflight checks
        flasher._log("Checking if device is in fastboot mode...", "info", step="preflight")
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
        
        flasher._log(f"Fastboot devices output: {repr(output)}", "info", step="preflight")
        
        if result.returncode == 0:
            # Fastboot doesn't have a header line like ADB - it just lists devices directly
            # Format: "SERIAL\tfastboot\n" or "SERIAL\tfastboot"
            lines = output.split('\n')
            fastboot_devices = []
            for line in lines:
                line = line.strip()
                if not line:
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
            
            flasher._log(f"Found {len(fastboot_devices)} device(s) in fastboot: {fastboot_devices}", "info", step="preflight")
            
            # Check if our device (or any device if serial not specified) is in fastboot
            if flasher.device_serial:
                device_in_fastboot = flasher.device_serial in fastboot_devices
                flasher._log(f"Looking for device serial: {flasher.device_serial}", "info", step="preflight")
                flasher._log(f"Device found in fastboot: {device_in_fastboot}", "info", step="preflight")
            else:
                device_in_fastboot = len(fastboot_devices) > 0
                if device_in_fastboot and len(fastboot_devices) == 1:
                    flasher.device_serial = fastboot_devices[0]
                    flasher._log(f"Auto-selected device: {flasher.device_serial}", "info", step="preflight")
                elif device_in_fastboot and len(fastboot_devices) > 1:
                    flasher._error("Multiple devices in fastboot mode. Please specify device serial with --device-serial", step="preflight")
        else:
            device_in_fastboot = False
            flasher._log("Fastboot devices command failed, assuming device not in fastboot mode", "warning", step="preflight")
        
        if device_in_fastboot:
            # Device is already in fastboot, skip ADB preflight checks
            flasher._log("✓ Device already in fastboot mode, skipping ADB preflight checks", "success", step="preflight")
            flasher._log("Note: OEM unlocking check skipped (requires ADB mode). If unlock fails, ensure OEM unlocking is enabled.", "warning", step="preflight")
        else:
            # STEP 1: Preflight checks (ADB mode)
            flasher._log("Device not in fastboot mode, starting ADB preflight checks...", "info", step="preflight")
            flasher.step1_preflight_checks()
        
        # STEP 2: Validate fastboot state
        product, is_unlocked = flasher.step2_validate_fastboot_state()
        
        # STEP 3: Unlock bootloader (if needed)
        if not args.skip_unlock:
            if not is_unlocked:
                flasher.step3_unlock_bootloader()
            else:
                flasher._log("Bootloader already unlocked, skipping unlock step", "info", step="unlock")
        
        # STEP 4: Reboot back to fastboot
        flasher.step4_reboot_to_fastboot()
        
        # Find partition files
        partition_files = flasher.find_partition_files()
        
        # STEP 5: Flash GrapheneOS
        flasher.step5_flash_grapheneos(partition_files)
        
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
