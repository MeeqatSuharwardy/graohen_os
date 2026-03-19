"""
Build Manager for Flashing Engine

This module provides build management functionality:
- Finding bundles at correct paths (local vs server)
- Downloading bundles if missing
- Finding partition files in bundles

Build paths:
- Local: /Users/vt_dev/upwork_graphene/graohen_os/bundles/panther/2025122500
- Server: graohen_os/bundles/panther/2025122500 (relative to project root)

Bundle structure:
- bundles/panther/2025122500/panther-install-2025122500/
  - boot.img
  - vendor_boot.img
  - dtbo.img
  - vbmeta.img
  - super_*.img (super_1.img ... super_14.img)
  - bootloader-panther-*.img
  - radio-panther-*.img
"""

import os
import zipfile
import httpx
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import logging

from ...utils.bundles import get_bundle_for_codename, get_bundle_info, index_bundles
from ...config import settings

logger = logging.getLogger(__name__)


class PythonBuildManager:
    """
    Python build manager implementation.
    
    Handles:
    - Finding bundles at correct paths (supports both local and server paths)
    - Downloading bundles if missing (via backend download API)
    - Finding partition files in bundles
    """
    
    def __init__(self, download_callback: Optional[Callable[[str, Optional[str]], Path]] = None):
        """
        Initialize build manager.
        
        Args:
            download_callback: Optional callback for downloading bundles.
                              Should take (codename, version) and return Path to downloaded bundle.
                              If None, uses default download logic.
        """
        self.download_callback = download_callback
        self._project_root: Optional[Path] = None
    
    def _find_project_root(self) -> Path:
        """Find project root directory"""
        if self._project_root:
            return self._project_root
        
        # Try multiple methods
        # Method 1: From bundles.py location
        try:
            from ...utils.bundles import _find_project_root as find_root
            root = find_root()
            if (root / "bundles").exists():
                self._project_root = root
                return root
        except:
            pass
        
        # Method 2: Current working directory
        cwd = Path.cwd().resolve()
        if (cwd / "bundles").exists():
            self._project_root = cwd
            return cwd
        
        # Method 3: Go up from current file
        current_file = Path(__file__).resolve()
        for levels in [4, 5, 6, 7]:
            candidate = current_file
            for _ in range(levels):
                candidate = candidate.parent
            if (candidate / "bundles").exists():
                self._project_root = candidate
                return candidate
        
        # Fallback
        self._project_root = cwd
        return cwd
    
    def get_bundle_path(self, codename: str, version: Optional[str] = None) -> Optional[Path]:
        """
        Get path to bundle directory.
        
        Args:
            codename: Device codename (e.g., "panther")
            version: Bundle version (e.g., "2025122500"). If None, uses latest.
        
        Returns:
            Path to bundle directory, or None if not found.
        """
        # Try to find bundle via existing utilities
        if version:
            # Get specific version
            bundle_info = get_bundle_info(codename, version, None)
            if bundle_info and bundle_info.get("path"):
                bundle_path = Path(bundle_info["path"])
                if bundle_path.exists():
                    return self._find_install_directory(bundle_path)
        else:
            # Get latest version
            bundle_info = get_bundle_for_codename(codename)
            if bundle_info and bundle_info.get("path"):
                bundle_path = Path(bundle_info["path"])
                if bundle_path.exists():
                    return self._find_install_directory(bundle_path)
        
        # Try direct path resolution
        project_root = self._find_project_root()
        bundles_root = project_root / "bundles"
        
        if not bundles_root.exists():
            # Try config path
            bundles_root_str = os.path.expanduser(str(settings.GRAPHENE_BUNDLES_ROOT))
            bundles_root = Path(bundles_root_str).resolve()
            if not bundles_root.exists():
                return None
        
        codename_dir = bundles_root / codename
        if not codename_dir.exists():
            return None
        
        if version:
            version_dir = codename_dir / version
            if version_dir.exists():
                return self._find_install_directory(version_dir)
        else:
            # Find latest version
            versions = []
            for v_dir in codename_dir.iterdir():
                if v_dir.is_dir() and not v_dir.name.startswith('.'):
                    versions.append((v_dir.name, v_dir))
            
            if versions:
                # Sort by version (newest first) - assuming YYYYMMDDXX format
                versions.sort(key=lambda x: x[0], reverse=True)
                latest_version_dir = versions[0][1]
                return self._find_install_directory(latest_version_dir)
        
        return None
    
    def _find_install_directory(self, bundle_path: Path) -> Path:
        """
        Find the actual install directory within a bundle path.
        
        Bundle structure:
        - bundles/panther/2025122500/panther-install-2025122500/ (actual install files)
        - OR bundles/panther/2025122500/ (if already extracted to root)
        
        EXACT STRUCTURE:
        /Users/vt_dev/upwork_graphene/graohen_os/bundles/panther/2025122500/panther-install-2025122500/
        
        Returns:
            Path to directory containing partition files
        """
        # Check if bundle_path itself contains partition files
        if (bundle_path / "boot.img").exists() or list(bundle_path.glob("bootloader-*.img")):
            logger.info(f"Found partition files directly in: {bundle_path}")
            return bundle_path
        
        # Look for panther-install-* subdirectory (EXACT pattern from user's file listing)
        install_dirs = list(bundle_path.glob("*-install-*"))
        for install_dir in install_dirs:
            if install_dir.is_dir():
                # Verify it contains partition files
                if (install_dir / "boot.img").exists() or list(install_dir.glob("bootloader-*.img")):
                    logger.info(f"Found install directory: {install_dir}")
                    return install_dir
        
        # Try common pattern: panther-install-*
        panther_install = bundle_path / "panther-install-2025122500"
        if panther_install.exists() and panther_install.is_dir():
            if (panther_install / "boot.img").exists() or list(panther_install.glob("bootloader-*.img")):
                logger.info(f"Found install directory: {panther_install}")
                return panther_install
        
        # Fallback: return bundle_path (may need extraction)
        logger.warning(f"Could not find install directory, using bundle path: {bundle_path}")
        return bundle_path
    
    def ensure_bundle_available(
        self,
        codename: str,
        version: Optional[str] = None,
        on_progress: Optional[Callable[[int], None]] = None,
    ) -> Path:
        """
        Ensure bundle is available. Downloads if missing.
        
        Args:
            codename: Device codename
            version: Bundle version (None for latest)
            on_progress: Progress callback (percentage 0-100)
        
        Returns:
            Path to bundle directory
        
        Raises:
            FileNotFoundError: If bundle not found and download failed
        """
        # Check if bundle already exists
        bundle_path = self.get_bundle_path(codename, version)
        if bundle_path and bundle_path.exists():
            logger.info(f"Bundle found at: {bundle_path}")
            return bundle_path
        
        # Bundle not found - need to download
        logger.info(f"Bundle not found, downloading: {codename} {version or 'latest'}")
        
        if self.download_callback:
            # Use custom download callback
            downloaded_path = self.download_callback(codename, version)
            if downloaded_path and downloaded_path.exists():
                install_dir = self._find_install_directory(downloaded_path)
                return install_dir
        else:
            # Use default download logic
            downloaded_path = self._download_bundle(codename, version, on_progress)
            if downloaded_path and downloaded_path.exists():
                install_dir = self._find_install_directory(downloaded_path)
                return install_dir
        
        raise FileNotFoundError(
            f"Bundle not found and download failed: {codename} {version or 'latest'}"
        )
    
    def _download_bundle(
        self,
        codename: str,
        version: Optional[str] = None,
        on_progress: Optional[Callable[[int], None]] = None,
    ) -> Optional[Path]:
        """
        Download bundle from GrapheneOS releases.
        
        This is a basic implementation - in production, use the backend download API.
        """
        # For now, just raise error - downloading should be handled by backend
        raise NotImplementedError(
            "Bundle download must be handled by backend download API. "
            "Provide download_callback to BuildManager constructor."
        )
    
    def find_partition_files(self, bundle_path: Path) -> Dict[str, Any]:
        """
        Find all partition files in bundle.
        
        Returns:
            Dict mapping partition names to file paths or lists of file paths.
            Format:
            {
                "bootloader": Path("bootloader-panther-*.img"),
                "radio": Path("radio-panther-*.img"),
                "boot": Path("boot.img"),
                "vendor_boot": Path("vendor_boot.img"),
                "dtbo": Path("dtbo.img"),
                "vbmeta": Path("vbmeta.img"),
                "init_boot": Path("init_boot.img"),
                "vendor_kernel_boot": Path("vendor_kernel_boot.img"),
                "pvmfw": Path("pvmfw.img"),
                "super": [Path("super_1.img"), Path("super_2.img"), ...],
            }
        """
        partition_files: Dict[str, Any] = {}
        
        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle path does not exist: {bundle_path}")
        
        # Bootloader (may have multiple, use first found)
        bootloader_files = sorted(bundle_path.glob("bootloader-*.img"))
        if bootloader_files:
            partition_files["bootloader"] = bootloader_files[0]
        
        # Radio (may have multiple, use first found)
        radio_files = sorted(bundle_path.glob("radio-*.img"))
        if radio_files:
            partition_files["radio"] = radio_files[0]
        
        # Core partitions (single files)
        core_partitions = [
            "boot",
            "vendor_boot",
            "dtbo",
            "vbmeta",
            "init_boot",
            "vendor_kernel_boot",
            "pvmfw",
        ]
        
        for partition in core_partitions:
            partition_file = bundle_path / f"{partition}.img"
            if partition_file.exists():
                partition_files[partition] = partition_file
        
        # Super partition (split images: super_1.img, super_2.img, ...)
        super_images = sorted(bundle_path.glob("super_*.img"))
        if super_images:
            partition_files["super"] = super_images
        
        # Log found partitions
        logger.info(f"Found partition files:")
        for name, files in partition_files.items():
            if isinstance(files, list):
                logger.info(f"  {name}: {len(files)} file(s)")
            else:
                logger.info(f"  {name}: {files.name}")
        
        return partition_files


__all__ = ["PythonBuildManager"]
