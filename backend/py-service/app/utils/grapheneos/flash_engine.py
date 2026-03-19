"""
GrapheneOS Flashing Engine - Shared FSM Implementation

This module provides a finite state machine (FSM) for flashing GrapheneOS.
It is designed to be reusable across:
- Python backend
- Electron app  
- Browser/WebUSB flasher

The FSM follows the official GrapheneOS CLI installation sequence:
1. ADB mode: Unlock bootloader (if needed)
2. Fastboot mode: Flash bootloader & radio
3. Reboot to fastbootd: Flash super partition images
4. Final reboot: Complete installation

States:
- INIT → ADB → FASTBOOT → FASTBOOT_FLASH → FASTBOOTD → FINAL → DONE

Critical rules:
- NO reboots between images (except required bootloader/radio reboots)
- NO polling loops - use timeouts
- NO state resets during flash
- USB disconnects are normal (ignore them)
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Protocol
from dataclasses import dataclass, field
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)


class FlashState(Enum):
    """FSM States for GrapheneOS flashing process"""
    INIT = "init"                           # Initial state
    ADB = "adb"                             # Device in ADB mode
    FASTBOOT = "fastboot"                   # Device in bootloader fastboot
    FASTBOOT_FLASH = "fastboot_flash"       # Flashing in bootloader fastboot
    FASTBOOTD = "fastbootd"                 # Device in fastbootd (userspace)
    FASTBOOTD_FLASH = "fastbootd_flash"     # Flashing super images in fastbootd
    FINAL = "final"                         # Flash complete, ready to reboot
    DONE = "done"                           # Successfully completed
    ERROR = "error"                         # Error state


@dataclass
class FlashProgress:
    """Progress information during flashing"""
    state: FlashState
    step_name: str
    progress_percent: int = 0
    message: str = ""
    partition: Optional[str] = None
    partition_index: Optional[int] = None
    total_partitions: Optional[int] = None
    log_lines: List[str] = field(default_factory=list)


class TransportProtocol(Protocol):
    """
    Transport abstraction for ADB/Fastboot/WebUSB commands.
    
    Implementations must provide:
    - ADB commands (for bootloader unlock)
    - Fastboot commands (for flashing in bootloader mode)
    - Fastbootd commands (for flashing in userspace fastboot mode)
    """
    
    def adb_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Execute ADB command. Returns dict with 'success', 'stdout', 'stderr', 'returncode'"""
        ...
    
    def fastboot_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Execute fastboot command in bootloader mode. Returns dict with 'success', 'stdout', 'stderr', 'returncode'"""
        ...
    
    def fastbootd_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Execute fastboot command in fastbootd (userspace) mode. Returns dict with 'success', 'stdout', 'stderr', 'returncode'"""
        ...
    
    def wait_for_fastboot(self, timeout: int = 90) -> bool:
        """Wait for device to be available in fastboot mode. Returns True if device found."""
        ...
    
    def wait_for_fastbootd(self, timeout: int = 60) -> bool:
        """Wait for device to be available in fastbootd mode. Returns True if device found."""
        ...


class BuildManager(Protocol):
    """Build management - handles bundle location and download"""
    
    def get_bundle_path(self, codename: str, version: Optional[str] = None) -> Optional[Path]:
        """Get path to bundle. Returns None if bundle not found."""
        ...
    
    def ensure_bundle_available(self, codename: str, version: Optional[str] = None, 
                               on_progress: Optional[Callable[[int], None]] = None) -> Path:
        """Ensure bundle is available. Downloads if missing. Returns bundle path."""
        ...
    
    def find_partition_files(self, bundle_path: Path) -> Dict[str, Any]:
        """Find all partition files in bundle. Returns dict mapping partition names to file paths."""
        ...


class GrapheneOSFlashEngine:
    """
    GrapheneOS Flashing Engine - FSM Implementation
    
    This class implements a finite state machine for flashing GrapheneOS.
    It is stateless with respect to frontend - all state is explicitly managed.
    
    Usage:
        engine = GrapheneOSFlashEngine(transport, build_manager, device_serial)
        engine.set_callbacks(on_progress=my_progress_callback, on_log=my_log_callback)
        
        # Execute flash
        result = engine.execute_flash(codename="panther", version="2025122500", skip_unlock=True)
        
        if result["success"]:
            print("Flash completed successfully")
        else:
            print(f"Flash failed: {result["error"]}")
    """
    
    def __init__(
        self,
        transport: TransportProtocol,
        build_manager: BuildManager,
        device_serial: str,
    ):
        """
        Initialize flashing engine.
        
        Args:
            transport: Transport layer for ADB/Fastboot commands
            build_manager: Build manager for bundle location/download
            device_serial: Device serial number
        """
        self.transport = transport
        self.build_manager = build_manager
        self.device_serial = device_serial
        
        # Current state
        self.current_state = FlashState.INIT
        
        # Progress tracking
        self.progress = FlashProgress(state=FlashState.INIT, step_name="Initializing")
        
        # Callbacks
        self.on_progress: Optional[Callable[[FlashProgress], None]] = None
        self.on_log: Optional[Callable[[str, str], None]] = None  # (message, level)
        
        # Bundle information
        self.bundle_path: Optional[Path] = None
        self.partition_files: Dict[str, Any] = {}
    
    def set_callbacks(
        self,
        on_progress: Optional[Callable[[FlashProgress], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
    ):
        """Set callbacks for progress updates and logging"""
        self.on_progress = on_progress
        self.on_log = on_log
    
    def _log(self, message: str, level: str = "info"):
        """Internal logging"""
        if self.on_log:
            self.on_log(message, level)
        else:
            logger.log(
                getattr(logging, level.upper(), logging.INFO),
                message
            )
    
    def _update_progress(self, state: FlashState, step_name: str, message: str = "", 
                        progress: int = 0, partition: Optional[str] = None,
                        partition_index: Optional[int] = None, total_partitions: Optional[int] = None):
        """Update progress and notify callbacks"""
        self.current_state = state
        self.progress = FlashProgress(
            state=state,
            step_name=step_name,
            progress_percent=progress,
            message=message,
            partition=partition,
            partition_index=partition_index,
            total_partitions=total_partitions,
            log_lines=self.progress.log_lines + [message] if message else self.progress.log_lines,
        )
        
        if self.on_progress:
            self.on_progress(self.progress)
    
    def _transition(self, new_state: FlashState, step_name: str, message: str = ""):
        """Transition to new state and log"""
        old_state = self.current_state
        self.current_state = new_state
        
        transition_msg = f"[STATE: {old_state.value} → {new_state.value}] {message}"
        self._log(transition_msg, "info")
        self._update_progress(new_state, step_name, message)
    
    def execute_flash(
        self,
        codename: str,
        version: Optional[str] = None,
        skip_unlock: bool = False,
        lock_bootloader: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute complete flash process.
        
        Args:
            codename: Device codename (e.g., "panther")
            version: Bundle version (e.g., "2025122500"). If None, uses latest.
            skip_unlock: Skip bootloader unlock (device already unlocked)
            lock_bootloader: Lock bootloader after flash (requires verified boot)
        
        Returns:
            Dict with 'success' (bool), 'error' (str if failed), 'final_state' (FlashState)
        """
        try:
            # INIT → ADB
            self._transition(FlashState.INIT, "Initializing", "Starting GrapheneOS flash process")
            
            # Ensure bundle is available
            self._log(f"Ensuring bundle is available: {codename} {version or 'latest'}", "info")
            bundle_path = self.build_manager.ensure_bundle_available(
                codename=codename,
                version=version,
                on_progress=lambda p: self._log(f"Download progress: {p}%", "info")
            )
            self.bundle_path = bundle_path
            
            # Find partition files
            self._log("Scanning bundle for partition files...", "info")
            self.partition_files = self.build_manager.find_partition_files(bundle_path)
            self._log(f"Found {len(self.partition_files)} partition file(s)", "info")
            
            # ADB state: Unlock bootloader if needed
            if not skip_unlock:
                self._transition(FlashState.ADB, "Unlocking Bootloader", "Device must be in ADB mode for unlock")
                if not self._unlock_bootloader():
                    return {
                        "success": False,
                        "error": "Failed to unlock bootloader",
                        "final_state": FlashState.ERROR,
                    }
            else:
                self._log("Skipping bootloader unlock (device already unlocked)", "info")
            
            # FASTBOOT state: Reboot to fastboot if needed
            self._transition(FlashState.FASTBOOT, "Entering Fastboot", "Rebooting to bootloader fastboot mode")
            if not self._enter_fastboot():
                return {
                    "success": False,
                    "error": "Failed to enter fastboot mode",
                    "final_state": FlashState.ERROR,
                }
            
            # FASTBOOT_FLASH state: Flash bootloader, radio, and core partitions
            self._transition(FlashState.FASTBOOT_FLASH, "Flashing Firmware", "Flashing in bootloader fastboot mode")
            if not self._flash_in_bootloader_fastboot():
                return {
                    "success": False,
                    "error": "Failed to flash partitions in bootloader fastboot",
                    "final_state": FlashState.ERROR,
                }
            
            # FASTBOOTD state: Transition to fastbootd
            self._transition(FlashState.FASTBOOTD, "Entering Fastbootd", "Rebooting to fastbootd (userspace fastboot)")
            if not self._enter_fastbootd():
                return {
                    "success": False,
                    "error": "Failed to enter fastbootd mode",
                    "final_state": FlashState.ERROR,
                }
            
            # FASTBOOTD_FLASH state: Flash super partition images
            self._transition(FlashState.FASTBOOTD_FLASH, "Flashing Super Partition", "Flashing super images in fastbootd")
            if not self._flash_super_in_fastbootd():
                return {
                    "success": False,
                    "error": "Failed to flash super partition in fastbootd",
                    "final_state": FlashState.ERROR,
                }
            
            # FINAL state: Lock bootloader (optional) and reboot
            self._transition(FlashState.FINAL, "Finalizing", "Flash complete, preparing to reboot")
            
            if lock_bootloader:
                self._log("Locking bootloader (requires verified boot support)...", "info")
                if not self._lock_bootloader():
                    self._log("Warning: Failed to lock bootloader, but flash succeeded", "warning")
            
            # Reboot device
            self._log("Rebooting device...", "info")
            reboot_result = self.transport.fastbootd_command(["reboot"], timeout=30)
            if not reboot_result.get("success"):
                self._log("Warning: Reboot command failed, but flash succeeded. Manually reboot device.", "warning")
            
            # DONE state
            self._transition(FlashState.DONE, "Complete", "GrapheneOS flash completed successfully")
            
            return {
                "success": True,
                "final_state": FlashState.DONE,
                "bundle_path": str(bundle_path),
            }
            
        except Exception as e:
            self._transition(FlashState.ERROR, "Error", f"Flash failed: {str(e)}")
            logger.exception("Flash execution failed")
            return {
                "success": False,
                "error": str(e),
                "final_state": FlashState.ERROR,
            }
    
    def _unlock_bootloader(self) -> bool:
        """
        Unlock bootloader (requires device in ADB mode).
        
        This is a CRITICAL step that requires user confirmation on device.
        The user must press Volume Up + Power on the device screen.
        
        Returns:
            True if unlock successful or already unlocked, False on error
        """
        # Check if already unlocked
        self._log("Checking bootloader unlock status...", "info")
        result = self.transport.adb_command(["shell", "getprop", "ro.boot.flash.locked"], timeout=10)
        
        if result.get("success") and "0" in result.get("stdout", ""):
            self._log("Bootloader is already unlocked", "info")
            return True
        
        # Request unlock
        self._log("Bootloader is locked. Requesting unlock...", "info")
        self._log("ACTION REQUIRED: Check device screen and confirm unlock (Volume Up + Power)", "warning")
        
        result = self.transport.fastboot_command(["flashing", "unlock"], timeout=60)
        
        if not result.get("success"):
            self._log(f"Unlock command failed: {result.get('stderr', 'Unknown error')}", "error")
            return False
        
        # Wait for unlock completion
        self._log("Waiting for unlock to complete (device will reboot)...", "info")
        time.sleep(5)
        
        # Verify unlock by checking fastboot state
        if not self.transport.wait_for_fastboot(timeout=60):
            self._log("Warning: Device did not return to fastboot after unlock", "warning")
            return False
        
        self._log("Bootloader unlocked successfully", "info")
        return True
    
    def _enter_fastboot(self) -> bool:
        """
        Enter fastboot mode (reboot to bootloader).
        
        This is the FIRST transition to fastboot mode.
        After this, device will remain in fastboot until we transition to fastbootd.
        
        Returns:
            True if device enters fastboot successfully
        """
        # If device is already in fastboot, skip reboot
        test_result = self.transport.fastboot_command(["getvar", "product"], timeout=5)
        if test_result.get("success"):
            self._log("Device is already in fastboot mode", "info")
            return True
        
        # Reboot to bootloader
        self._log("Rebooting device to bootloader fastboot mode...", "info")
        result = self.transport.adb_command(["reboot", "bootloader"], timeout=60)
        
        if not result.get("success"):
            self._log("Failed to reboot to bootloader via ADB, device may already be in fastboot", "warning")
        
        # Wait for fastboot
        self._log("Waiting for device to enter fastboot mode (this may take up to 60 seconds)...", "info")
        if not self.transport.wait_for_fastboot(timeout=90):
            return False
        
        self._log("Device successfully entered fastboot mode", "info")
        return True
    
    def _flash_in_bootloader_fastboot(self) -> bool:
        """
        Flash partitions in bootloader fastboot mode.
        
        Sequence:
        1. Flash bootloader → reboot bootloader ONCE
        2. Flash radio → reboot bootloader ONCE (LAST reboot before fastbootd)
        3. Flash core partitions (boot, vendor_boot, dtbo, vbmeta, etc.) - NO REBOOT
        
        This is a LINEAR sequence - no loops, no state resets.
        
        Returns:
            True if all partitions flashed successfully
        """
        self._log("=" * 60, "info")
        self._log("Starting partition flashing in bootloader fastboot mode", "info")
        self._log("Sequence: bootloader → radio → core partitions", "info")
        self._log("=" * 60, "info")
        
        # Step 1: Flash bootloader (if present)
        if "bootloader" in self.partition_files:
            bootloader_file = self.partition_files["bootloader"]
            if isinstance(bootloader_file, list):
                bootloader_file = bootloader_file[0]
            
            self._log(f"Flashing bootloader: {bootloader_file.name}", "info")
            self._update_progress(
                FlashState.FASTBOOT_FLASH,
                "Flashing Bootloader",
                f"Flashing bootloader: {bootloader_file.name}",
                progress=5,
                partition="bootloader"
            )
            
            result = self.transport.fastboot_command(["flash", "bootloader", str(bootloader_file)], timeout=120)
            if not result.get("success"):
                self._log(f"Failed to flash bootloader: {result.get('stderr', 'Unknown error')}", "error")
                return False
            
            self._log("✓ Bootloader flashed", "info")
            
            # CRITICAL: Reboot bootloader ONCE after bootloader flash (FIRST reboot)
            # EXACT SEQUENCE: fastboot reboot-bootloader → wait 5 seconds (as per official GrapheneOS CLI)
            # This is REQUIRED by GrapheneOS - use "reboot-bootloader" not "reboot bootloader"
            self._log("Rebooting bootloader (required after bootloader flash)...", "info")
            self._log("Using: fastboot reboot-bootloader", "info")
            self._log("This is the FIRST reboot - radio will be flashed next, then one more reboot", "info")
            
            result = self.transport.fastboot_command(["reboot-bootloader"], timeout=60)
            if not result.get("success"):
                self._log(f"Failed to reboot bootloader: {result.get('stderr', 'Unknown error')}", "error")
                return False
            
            # EXACT TIMING: Wait exactly 5 seconds as per official GrapheneOS CLI sequence
            self._log("Waiting 5 seconds for device to reinitialize (as per GrapheneOS CLI)...", "info")
            self._log("Note: USB disconnect/reconnect is normal - device is rebooting, NOT looping", "info")
            time.sleep(5)
            
            # Verify device is back in fastboot (USB disconnect/reconnect is normal)
            self._log("Verifying device is in fastboot mode...", "info")
            test_result = self.transport.fastboot_command(["getvar", "product"], timeout=10)
            if not test_result.get("success"):
                # Device might still be reconnecting - wait a bit more
                self._log("Device not immediately responsive, waiting a bit longer...", "info")
                if not self.transport.wait_for_fastboot(timeout=60):
                    self._log("Warning: Device not detected, but continuing anyway...", "warning")
                    # Try one more direct check before giving up
                    test_result2 = self.transport.fastboot_command(["getvar", "product"], timeout=5)
                    if not test_result2.get("success"):
                        self._log("Device is not responding in fastboot mode", "error")
                        return False
            else:
                self._log("Device successfully detected in fastboot mode", "info")
        
        # Step 2: Flash radio (if present)
        if "radio" in self.partition_files:
            radio_file = self.partition_files["radio"]
            if isinstance(radio_file, list):
                radio_file = radio_file[0]
            
            self._log(f"Flashing radio: {radio_file.name}", "info")
            self._update_progress(
                FlashState.FASTBOOT_FLASH,
                "Flashing Radio",
                f"Flashing radio: {radio_file.name}",
                progress=15,
                partition="radio"
            )
            
            result = self.transport.fastboot_command(["flash", "radio", str(radio_file)], timeout=120)
            if not result.get("success"):
                self._log(f"Failed to flash radio: {result.get('stderr', 'Unknown error')}", "error")
                return False
            
            self._log("✓ Radio flashed", "info")
            
            # CRITICAL: Reboot bootloader ONCE after radio flash (LAST reboot before fastbootd)
            # EXACT SEQUENCE: fastboot reboot-bootloader → wait 5 seconds (as per official GrapheneOS CLI)
            # This is REQUIRED by GrapheneOS - use "reboot-bootloader" not "reboot bootloader"
            # After this, flash core partitions WITHOUT any more reboots, then transition to fastbootd
            self._log("Rebooting bootloader after radio flash (required by GrapheneOS)...", "info")
            self._log("Using: fastboot reboot-bootloader", "info")
            self._log("This is the LAST reboot - core partitions will be flashed next, then transition to fastbootd", "info")
            
            result = self.transport.fastboot_command(["reboot-bootloader"], timeout=60)
            if not result.get("success"):
                self._log(f"Failed to reboot bootloader: {result.get('stderr', 'Unknown error')}", "error")
                return False
            
            # EXACT TIMING: Wait exactly 5 seconds as per official GrapheneOS CLI sequence
            self._log("Waiting 5 seconds for device to reinitialize (as per GrapheneOS CLI)...", "info")
            self._log("Note: USB disconnect/reconnect is normal - device is rebooting, NOT looping", "info")
            time.sleep(5)
            
            # Verify device is back in fastboot (USB disconnect/reconnect is normal)
            # This is the LAST wait - after this, we flash core partitions WITHOUT any more reboots
            self._log("Verifying device is in fastboot mode...", "info")
            test_result = self.transport.fastboot_command(["getvar", "product"], timeout=10)
            if not test_result.get("success"):
                # Device might still be reconnecting - wait a bit more
                self._log("Device not immediately responsive, waiting a bit longer...", "info")
                if not self.transport.wait_for_fastboot(timeout=60):
                    self._log("Warning: Device not detected, but continuing anyway...", "warning")
                    # Try one more direct check before giving up
                    test_result2 = self.transport.fastboot_command(["getvar", "product"], timeout=5)
                    if not test_result2.get("success"):
                        self._log("Device is not responding in fastboot mode", "error")
                        return False
            else:
                self._log("Device successfully detected in fastboot mode", "info")
        
        # Step 3: Flash core partitions (NO REBOOT between any of these)
        # Core partitions: boot, vendor_boot, dtbo, vbmeta, init_boot, etc.
        self._log("=" * 60, "info")
        self._log("Flashing core partitions (NO MORE REBOOTS until fastbootd transition)", "info")
        self._log("=" * 60, "info")
        
        core_partitions = [
            ("boot", "boot.img"),
            ("init_boot", "init_boot.img"),
            ("dtbo", "dtbo.img"),
            ("vendor_kernel_boot", "vendor_kernel_boot.img"),
            ("pvmfw", "pvmfw.img"),
            ("vendor_boot", "vendor_boot.img"),
            ("vbmeta", "vbmeta.img"),
        ]
        
        core_flash_count = 0
        core_total = len([p for p in core_partitions if p[0] in self.partition_files or 
                         (self.bundle_path / p[1]).exists()])
        
        for partition_name, filename in core_partitions:
            # Check if partition file exists
            partition_file = None
            if partition_name in self.partition_files:
                partition_file = self.partition_files[partition_name]
                if isinstance(partition_file, list):
                    partition_file = partition_file[0]
            elif self.bundle_path:
                candidate_file = self.bundle_path / filename
                if candidate_file.exists():
                    partition_file = candidate_file
            
            if not partition_file:
                self._log(f"Skipping {partition_name} (file not found)", "info")
                continue
            
            core_flash_count += 1
            self._log(f"Flashing {partition_name} ({core_flash_count}/{core_total})...", "info")
            self._update_progress(
                FlashState.FASTBOOT_FLASH,
                f"Flashing {partition_name}",
                f"Flashing {partition_name}: {partition_file.name}",
                progress=20 + int((core_flash_count / core_total) * 30),
                partition=partition_name,
                partition_index=core_flash_count,
                total_partitions=core_total,
            )
            
            result = self.transport.fastboot_command(["flash", partition_name, str(partition_file)], timeout=120)
            if not result.get("success"):
                self._log(f"Failed to flash {partition_name}: {result.get('stderr', 'Unknown error')}", "error")
                return False
            
            self._log(f"✓ {partition_name} flashed", "info")
        
        self._log("✓ All core partitions flashed successfully", "info")
        return True
    
    def _enter_fastbootd(self) -> bool:
        """
        Transition from bootloader fastboot to fastbootd (userspace fastboot).
        
        This is a ONE-TIME transition required for flashing super partition.
        After this, device will be in fastbootd mode.
        
        Returns:
            True if device enters fastbootd successfully
        """
        # EXACT SEQUENCE: fastboot reboot fastboot → wait until is-userspace=yes
        self._log("Rebooting to fastbootd (userspace fastboot)...", "info")
        self._log("Using: fastboot reboot fastboot", "info")
        self._log("This transition is required for flashing super partition images", "info")
        
        result = self.transport.fastboot_command(["reboot", "fastboot"], timeout=60)
        if not result.get("success"):
            self._log(f"Failed to reboot to fastbootd: {result.get('stderr', 'Unknown error')}", "error")
            return False
        
        # EXACT SEQUENCE: Wait until `fastboot getvar is-userspace` returns yes
        self._log("Waiting for device to enter fastbootd mode...", "info")
        self._log("Waiting until 'fastboot getvar is-userspace' returns 'yes'", "info")
        self._log("USB disconnect/reconnect is normal during this transition", "info")
        
        # Poll for is-userspace=yes with timeout
        start_time = time.time()
        timeout_seconds = 90
        check_interval = 2  # Check every 2 seconds
        
        while time.time() - start_time < timeout_seconds:
            try:
                test_result = self.transport.fastbootd_command(["getvar", "is-userspace"], timeout=5)
                if test_result.get("success"):
                    output = (test_result.get("stdout", "") + " " + test_result.get("stderr", "")).lower()
                    if "is-userspace: yes" in output or "is-userspace:yes" in output:
                        self._log("Device successfully entered fastbootd mode (is-userspace=yes)", "info")
                        return True
            except:
                pass
            
            time.sleep(check_interval)
        
        # Final check
        test_result = self.transport.fastbootd_command(["getvar", "is-userspace"], timeout=5)
        if test_result.get("success"):
            output = (test_result.get("stdout", "") + " " + test_result.get("stderr", "")).lower()
            if "is-userspace: yes" in output or "is-userspace:yes" in output:
                self._log("Device successfully entered fastbootd mode (is-userspace=yes)", "info")
                return True
        
        self._log("Device did not enter fastbootd mode within timeout", "error")
        return False
    
    def _flash_super_in_fastbootd(self) -> bool:
        """
        Flash super partition images in fastbootd mode.
        
        Super partition is split into multiple images (super_1.img, super_2.img, etc.).
        These MUST be flashed in fastbootd mode, NOT in bootloader fastboot.
        
        Sequence:
        - Flash all super_*.img files sequentially - NO REBOOT between images
        
        Returns:
            True if all super images flashed successfully
        """
        self._log("=" * 60, "info")
        self._log("Flashing super partition in fastbootd mode", "info")
        self._log("Super images MUST be flashed in fastbootd (not bootloader fastboot)", "info")
        self._log("=" * 60, "info")
        
        # Find super images
        super_images = []
        if "super" in self.partition_files:
            super_images = self.partition_files["super"]
            if not isinstance(super_images, list):
                super_images = [super_images]
        elif self.bundle_path:
            # Find super_*.img files
            super_images = sorted(self.bundle_path.glob("super_*.img"))
        
        if not super_images:
            self._log("Error: No super partition images found", "error")
            return False
        
        total_super = len(super_images)
        self._log(f"Found {total_super} super partition image(s)", "info")
        
        # Flash each super image sequentially
        for idx, super_img in enumerate(super_images, 1):
            self._log(f"Flashing super {idx}/{total_super}: {super_img.name}", "info")
            self._update_progress(
                FlashState.FASTBOOTD_FLASH,
                f"Flashing Super {idx}/{total_super}",
                f"Flashing {super_img.name}",
                progress=60 + int((idx / total_super) * 35),
                partition="super",
                partition_index=idx,
                total_partitions=total_super,
            )
            
            result = self.transport.fastbootd_command(["flash", "super", str(super_img)], timeout=300)
            if not result.get("success"):
                self._log(f"Failed to flash super {idx}/{total_super}: {result.get('stderr', 'Unknown error')}", "error")
                return False
            
            self._log(f"✓ Super {idx}/{total_super} flashed", "info")
        
        self._log("✓ All super partition images flashed successfully", "info")
        return True
    
    def _lock_bootloader(self) -> bool:
        """
        Lock bootloader (requires verified boot support).
        
        This is OPTIONAL but recommended for security.
        Device must support verified boot for this to work.
        
        Returns:
            True if lock successful, False on error (but not fatal - flash succeeded)
        """
        # Note: Locking must be done in fastbootd or bootloader fastboot
        # We're in fastbootd, so use fastbootd command
        result = self.transport.fastbootd_command(["flashing", "lock"], timeout=30)
        
        if not result.get("success"):
            return False
        
        self._log("Bootloader locked successfully", "info")
        return True


# Export for use in other modules
__all__ = [
    "FlashState",
    "FlashProgress",
    "TransportProtocol",
    "BuildManager",
    "GrapheneOSFlashEngine",
]
