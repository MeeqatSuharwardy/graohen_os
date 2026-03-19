"""
CLI Wrapper for GrapheneOS Flash Engine

This module provides a CLI interface for the flashing engine.
It can be used from command line or imported for programmatic use.

Usage:
    python -m app.utils.grapheneos.flash_cli --codename panther --device-serial ABC123

Or import:
    from app.utils.grapheneos.flash_cli import flash_device
    result = flash_device(codename="panther", device_serial="ABC123", version="2025122500")
"""

import argparse
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .flash_engine import GrapheneOSFlashEngine, FlashState, FlashProgress
from .flash_transport import PythonTransport
from .flash_build_manager import PythonBuildManager
from ...config import settings

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def progress_callback(progress: FlashProgress):
    """Callback for progress updates"""
    state_name = progress.state.value
    step_name = progress.step_name
    percent = progress.progress_percent
    message = progress.message
    
    # Format progress display
    if progress.partition:
        if progress.partition_index and progress.total_partitions:
            partition_info = f" ({progress.partition_index}/{progress.total_partitions})"
        else:
            partition_info = f" ({progress.partition})"
    else:
        partition_info = ""
    
    print(f"[{state_name:15}] [{percent:3}%] {step_name}{partition_info}: {message}")


def log_callback(message: str, level: str = "info"):
    """Callback for log messages"""
    level_upper = level.upper()
    if level_upper == "ERROR":
        print(f"❌ {message}", file=sys.stderr)
    elif level_upper == "WARNING":
        print(f"⚠️  {message}")
    elif level_upper == "INFO":
        print(f"ℹ️  {message}")
    else:
        print(f"   {message}")


def flash_device(
    codename: str,
    device_serial: str,
    version: Optional[str] = None,
    skip_unlock: bool = False,
    lock_bootloader: bool = False,
    adb_path: Optional[str] = None,
    fastboot_path: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Flash GrapheneOS to device.
    
    Args:
        codename: Device codename (e.g., "panther")
        device_serial: Device serial number
        version: Bundle version (e.g., "2025122500"). If None, uses latest.
        skip_unlock: Skip bootloader unlock (device already unlocked)
        lock_bootloader: Lock bootloader after flash (requires verified boot)
        adb_path: Path to adb binary (uses config default if None)
        fastboot_path: Path to fastboot binary (uses config default if None)
        verbose: Enable verbose logging
    
    Returns:
        Dict with 'success' (bool), 'error' (str if failed), 'final_state' (FlashState)
    """
    setup_logging(verbose=verbose)
    
    # Initialize transport
    transport = PythonTransport(
        adb_path=adb_path or settings.ADB_PATH,
        fastboot_path=fastboot_path or settings.FASTBOOT_PATH,
        device_serial=device_serial,
    )
    
    # Initialize build manager
    build_manager = PythonBuildManager()
    
    # Initialize flash engine
    engine = GrapheneOSFlashEngine(
        transport=transport,
        build_manager=build_manager,
        device_serial=device_serial,
    )
    
    # Set callbacks
    engine.set_callbacks(
        on_progress=progress_callback,
        on_log=log_callback,
    )
    
    # Execute flash
    print(f"Starting GrapheneOS flash for {codename} (device: {device_serial})")
    if version:
        print(f"Using bundle version: {version}")
    else:
        print("Using latest available bundle")
    
    print("-" * 60)
    
    result = engine.execute_flash(
        codename=codename,
        version=version,
        skip_unlock=skip_unlock,
        lock_bootloader=lock_bootloader,
    )
    
    print("-" * 60)
    
    if result["success"]:
        print("✅ Flash completed successfully!")
        print(f"Final state: {result['final_state'].value}")
    else:
        print(f"❌ Flash failed: {result.get('error', 'Unknown error')}")
        print(f"Final state: {result['final_state'].value}")
    
    return result


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Flash GrapheneOS to device using FSM engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Flash latest version (requires bootloader unlock)
  python -m app.utils.grapheneos.flash_cli --codename panther --device-serial ABC123
  
  # Flash specific version (skip unlock)
  python -m app.utils.grapheneos.flash_cli --codename panther --device-serial ABC123 \\
    --version 2025122500 --skip-unlock
  
  # Flash and lock bootloader
  python -m app.utils.grapheneos.flash_cli --codename panther --device-serial ABC123 \\
    --skip-unlock --lock-bootloader
        """,
    )
    
    parser.add_argument(
        "--codename",
        required=True,
        help="Device codename (e.g., panther, cheetah, raven)",
    )
    
    parser.add_argument(
        "--device-serial",
        required=True,
        help="Device serial number",
    )
    
    parser.add_argument(
        "--version",
        help="Bundle version (e.g., 2025122500). If not specified, uses latest.",
    )
    
    parser.add_argument(
        "--skip-unlock",
        action="store_true",
        help="Skip bootloader unlock (device already unlocked)",
    )
    
    parser.add_argument(
        "--lock-bootloader",
        action="store_true",
        help="Lock bootloader after flash (requires verified boot support)",
    )
    
    parser.add_argument(
        "--adb-path",
        help=f"Path to adb binary (default: {settings.ADB_PATH})",
    )
    
    parser.add_argument(
        "--fastboot-path",
        help=f"Path to fastboot binary (default: {settings.FASTBOOT_PATH})",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Execute flash
    result = flash_device(
        codename=args.codename,
        device_serial=args.device_serial,
        version=args.version,
        skip_unlock=args.skip_unlock,
        lock_bootloader=args.lock_bootloader,
        adb_path=args.adb_path,
        fastboot_path=args.fastboot_path,
        verbose=args.verbose,
    )
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
