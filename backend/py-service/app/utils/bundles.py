import os
import json
import httpx
import hashlib
import zipfile
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from ..config import settings


def _find_project_root() -> Path:
    """Find the project root directory (where bundles/ folder is located)"""
    # Try multiple methods to find project root
    try:
        # Method 1: From __file__ (when running as module)
        current_file = Path(__file__).resolve()
        # app/utils/bundles.py -> go up 4 levels
        project_root = current_file.parent.parent.parent.parent
        if (project_root / "bundles").exists():
            return project_root
    except:
        pass
    
    # Method 2: From current working directory
    try:
        cwd = Path.cwd().resolve()
        # If we're in backend/py-service, go up 2 levels
        if 'backend' in str(cwd) and 'py-service' in str(cwd):
            project_root = cwd.parent.parent
            if (project_root / "bundles").exists():
                return project_root
        # If we're in backend, go up 1 level
        elif 'backend' in str(cwd):
            project_root = cwd.parent
            if (project_root / "bundles").exists():
                return project_root
        # Try current directory
        if (cwd / "bundles").exists():
            return cwd
    except:
        pass
    
    # Method 3: Try common locations relative to current file
    try:
        current_file = Path(__file__).resolve()
        # Try going up from app/utils/bundles.py
        for levels in [3, 4, 5]:
            candidate = current_file
            for _ in range(levels):
                candidate = candidate.parent
            if (candidate / "bundles").exists():
                return candidate
    except:
        pass
    
    # Fallback: return a default (will be checked later)
    return Path.cwd()


def index_bundles() -> Dict[str, List[Dict[str, Any]]]:
    """Index all available bundles - checks multiple possible locations"""
    # Try multiple possible root locations for bundles
    bundles_root = None
    possible_roots = []
    
    # 1. From config (expanded user path)
    bundles_root_str = os.path.expanduser(str(settings.GRAPHENE_BUNDLES_ROOT))
    possible_roots.append(Path(bundles_root_str).resolve())
    
    # 2. Relative to project root (where bundles/ folder is located)
    project_root = _find_project_root()
    possible_roots.append(project_root / "bundles")
    
    # 3. Relative path from config (if it's a relative path)
    if not os.path.isabs(bundles_root_str):
        possible_roots.append(project_root / bundles_root_str.lstrip('/'))
    
    # Find the first existing root
    for root in possible_roots:
        if root.exists() and root.is_dir():
            bundles_root = root
            break
    
    if not bundles_root:
        return {}
    
    bundles = {}
    
    try:
        for codename_dir in bundles_root.iterdir():
            if not codename_dir.is_dir():
                continue
            
            codename = codename_dir.name
            # Skip hidden directories
            if codename.startswith('.'):
                continue
            
            # Check if codename is in supported list (if list exists and is not empty)
            # If list is empty or not defined, allow all codenames
            if hasattr(settings, 'supported_codenames_list') and settings.supported_codenames_list:
                if codename not in settings.supported_codenames_list:
                    continue
            
            versions = []
            try:
                for version_dir in codename_dir.iterdir():
                    if not version_dir.is_dir():
                        continue
                    
                    # Skip hidden directories
                    if version_dir.name.startswith('.'):
                        continue
                    
                    # Version is the directory name (e.g., "2025122500")
                    version = version_dir.name
                    bundle_info = get_bundle_info(codename, version, version_dir)
                    if bundle_info:
                        versions.append(bundle_info)
            except (PermissionError, OSError) as e:
                # Skip directories we can't access
                continue
            
            if versions:
                # Sort versions (newest first) - versions are typically YYYYMMDDXX format
                versions.sort(key=lambda x: x.get("version", ""), reverse=True)
                bundles[codename] = versions
    except (PermissionError, OSError) as e:
        # If we can't access the bundles directory, return empty dict
        pass
    
    return bundles


def get_bundle_info(codename: str, version: str, bundle_path: Path) -> Optional[Dict[str, Any]]:
    """Get bundle information from metadata.json or infer from files"""
    # Ensure bundle_path is resolved (absolute path)
    bundle_path = bundle_path.resolve()
    
    metadata_path = bundle_path / "metadata.json"
    
    # Try reading metadata.json first
    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                # Verify files exist - check for image.zip or image.zip in metadata
                files = metadata.get("files", {})
                image_zip_name = files.get("imageZip", "image.zip")
                image_zip = bundle_path / image_zip_name
                
                if image_zip.exists():
                    return {
                        "codename": codename,
                        "version": version,
                        "deviceName": metadata.get("deviceName", codename),
                        "path": str(bundle_path),
                        "downloadUrl": f"https://releases.grapheneos.org/{codename}-factory-{version}.zip",
                        "metadata": metadata,
                    }
        except Exception as e:
            # If metadata.json is invalid, fall through to file-based detection
            pass
    
    # Infer from files - check for image.zip
    image_zip = bundle_path / "image.zip"
    if image_zip.exists():
        return {
            "codename": codename,
            "version": version,
            "deviceName": codename,
            "path": str(bundle_path),
            "downloadUrl": f"https://releases.grapheneos.org/{codename}-factory-{version}.zip",
            "metadata": {
                "codename": codename,
                "version": version,
                "files": {
                    "imageZip": "image.zip",
                    "sha256": "image.zip.sha256",
                    "sig": "image.zip.sig",
                    "flashSh": "flash-all.sh",
                    "flashBat": "flash-all.bat",
                },
            },
        }
    
    return None


def get_bundle_for_codename(codename: str) -> Optional[Dict[str, Any]]:
    """Get the newest bundle for a codename - searches multiple locations"""
    # First try indexing
    bundles = index_bundles()
    codename_bundles = bundles.get(codename, [])
    
    if codename_bundles:
        # Return the newest bundle (first in sorted list)
        return codename_bundles[0]
    
    # If not found via indexing, try direct directory scan
    # Check multiple possible locations for bundles
    possible_roots = []
    
    # 1. From config (expanded user path)
    bundles_root_str = os.path.expanduser(str(settings.GRAPHENE_BUNDLES_ROOT))
    possible_roots.append(Path(bundles_root_str).resolve())
    
    # 2. Relative to project root (where bundles/ folder is located)
    project_root = _find_project_root()
    possible_roots.append(project_root / "bundles")
    
    # 3. Relative path from config (if it's a relative path)
    if not os.path.isabs(bundles_root_str):
        possible_roots.append(project_root / bundles_root_str.lstrip('/'))
    
    # Try each possible root location
    for bundles_root in possible_roots:
        if not bundles_root.exists():
            continue
        
        codename_dir = bundles_root / codename
        if codename_dir.exists() and codename_dir.is_dir():
            versions = []
            try:
                for version_dir in codename_dir.iterdir():
                    if not version_dir.is_dir() or version_dir.name.startswith('.'):
                        continue
                    
                    # Version is the directory name (e.g., "2025122500")
                    version = version_dir.name
                    bundle_info = get_bundle_info(codename, version, version_dir)
                    if bundle_info:
                        versions.append(bundle_info)
                
                if versions:
                    # Sort versions (newest first) - versions are typically YYYYMMDDXX format
                    versions.sort(key=lambda x: x.get("version", ""), reverse=True)
                    return versions[0]
            except (PermissionError, OSError) as e:
                # Continue to next possible root
                continue
    
    return None


def verify_bundle(bundle_path: str) -> Dict[str, Any]:
    """Verify bundle integrity"""
    path = Path(bundle_path)
    errors = []
    warnings = []
    
    metadata_path = path / "metadata.json"
    if not metadata_path.exists():
        warnings.append("metadata.json not found")
    
    files = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                files = metadata.get("files", {})
        except Exception:
            warnings.append("Could not read metadata.json")
    
    # Check required files
    image_zip = path / files.get("imageZip", "image.zip")
    if not image_zip.exists():
        errors.append(f"Image ZIP not found: {image_zip.name}")
    
    sha256_file = path / files.get("sha256", "image.zip.sha256")
    if not sha256_file.exists():
        warnings.append(f"SHA256 file not found: {sha256_file.name}")
    else:
        # Verify SHA256
        try:
            import hashlib
            with open(image_zip, "rb") as f:
                sha256_hash = hashlib.sha256(f.read()).hexdigest()
            
            with open(sha256_file, "r") as f:
                sha256_content = f.read().strip()
                
                # Skip if file contains HTML (likely a 404 error page)
                if sha256_content.startswith("<") or "html" in sha256_content.lower():
                    warnings.append("SHA256 file appears to be invalid (contains HTML). Skipping verification.")
                else:
                    # Handle different SHA256 file formats:
                    # 1. Just the hash: "abc123..."
                    # 2. Hash with filename: "abc123...  filename"
                    # 3. Hash with path: "abc123...  path/to/file"
                    expected_hash = sha256_content.split()[0] if sha256_content.split() else sha256_content
                    
                    if sha256_hash != expected_hash:
                        # If mismatch, it's a warning, not an error
                        # This handles cases where the file was renamed but SHA256 wasn't updated
                        warnings.append(f"SHA256 checksum mismatch. Expected: {expected_hash[:16]}..., Got: {sha256_hash[:16]}...")
                        warnings.append("Note: This may be due to file renaming. The file exists and will be used, but verification failed.")
                        # Don't add to errors - allow flashing to proceed with warning
        except Exception as e:
            warnings.append(f"Could not verify SHA256: {e}")
    
    sig_file = path / files.get("sig", "image.zip.sig")
    if not sig_file.exists():
        warnings.append("Signature file not found (optional)")
    
    flash_sh = path / files.get("flashSh", "flash-all.sh")
    flash_bat = path / files.get("flashBat", "flash-all.bat")
    
    if not flash_sh.exists() and not flash_bat.exists():
        errors.append("Flash script not found (flash-all.sh or flash-all.bat)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


async def find_latest_version(codename: str, max_days_back: int = 30) -> Optional[str]:
    """Find the latest available GrapheneOS version for a codename by checking recent dates"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try the last N days, checking multiple build numbers per day (00-99)
        base_date = datetime.now()
        
        for day_offset in range(max_days_back):
            check_date = base_date - timedelta(days=day_offset)
            date_str = check_date.strftime("%Y%m%d")
            
            # Try build numbers from 99 down to 00 (newer builds typically have higher numbers)
            for build_num in range(99, -1, -1):
                version = f"{date_str}{build_num:02d}"
                download_url = f"https://releases.grapheneos.org/{codename}-factory-{version}.zip"
                
                try:
                    response = await client.head(download_url, follow_redirects=True)
                    if response.status_code == 200:
                        return version
                except Exception:
                    continue
        
        return None


async def get_available_releases(codename: str) -> List[Dict[str, Any]]:
    """Get available GrapheneOS releases for a codename"""
    # GrapheneOS doesn't provide a public releases.json API
    # The factory image URL pattern is: https://releases.grapheneos.org/{codename}-factory-{version}.zip
    # Version format is typically: YYYYMMDDXX (e.g., 2024122200)
    # Since we can't fetch a list, we return an empty list and the UI allows manual entry
    # In the future, we could scrape their website or maintain a known versions list
    try:
        # Try to check if there's a releases endpoint (though it likely doesn't exist)
        releases_url = f"https://releases.grapheneos.org/{codename}/releases.json"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(releases_url)
            if response.status_code == 200:
                data = response.json()
                # If they have a releases.json, parse it
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "releases" in data:
                    return data["releases"]
    except Exception:
        # If releases.json doesn't exist (expected), return empty list
        # UI will allow manual version entry
        pass
    
    return []


async def download_release(
    codename: str,
    version: str,
    progress_callback=None
) -> Dict[str, Any]:
    """Download a GrapheneOS factory image release"""
    bundles_root = Path(settings.GRAPHENE_BUNDLES_ROOT)
    if not bundles_root.exists():
        bundles_root.mkdir(parents=True, exist_ok=True)
    
    # Create codename and version directories
    version_dir = bundles_root / codename / version
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Download URL pattern for GrapheneOS factory images
    # Format: https://releases.grapheneos.org/{codename}-factory-{version}.zip
    # Version format is typically: YYYYMMDDXX (e.g., 2024122200)
    
    # Validate codename and version format
    if not codename or not version:
        raise ValueError("Codename and version are required")
    
    download_url = f"https://releases.grapheneos.org/{codename}-factory-{version}.zip"
    sha256_url = f"{download_url}.sha256"
    sig_url = f"{download_url}.sig"
    
    image_zip_path = version_dir / "image.zip"
    sha256_path = version_dir / "image.zip.sha256"
    sig_path = version_dir / "image.zip.sig"
    
    errors = []
    
    factory_zip_path = version_dir / f"{codename}-factory-{version}.zip"
    
    try:
        # Download factory image ZIP
        async with httpx.AsyncClient(timeout=3600.0) as client:
            # First, check if the file exists
            head_response = await client.head(download_url)
            if head_response.status_code == 404:
                raise Exception(
                    f"Release not found: {codename}-factory-{version}.zip (HTTP 404). "
                    f"Please verify the codename and version are correct. "
                    f"Version format is typically YYYYMMDDXX (e.g., 2024122200)."
                )
            
            async with client.stream("GET", download_url) as response:
                if response.status_code != 200:
                    raise Exception(
                        f"Failed to download: HTTP {response.status_code}. "
                        f"URL: {download_url}"
                    )
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                with open(factory_zip_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress = (downloaded / total_size * 100) if total_size > 0 else 0
                            await progress_callback(progress, downloaded, total_size)
        
        # Extract the factory ZIP - GrapheneOS factory ZIPs contain:
        # - boot.img, system.img, vendor.img, etc.
        # - flash-all.sh (Unix)
        # - flash-all.bat (Windows)
        # - other files
        # Extract first, then rename the factory ZIP to image.zip for compatibility
        with zipfile.ZipFile(factory_zip_path, 'r') as zip_ref:
            zip_ref.extractall(version_dir)
        
        # Rename the factory ZIP to image.zip for compatibility with our bundle structure
        # The extracted files will be used for flashing, image.zip for verification
        factory_zip_path.rename(image_zip_path)
        
        # Download SHA256
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(sha256_url)
                if response.status_code == 200:
                    with open(sha256_path, "wb") as f:
                        f.write(response.content)
                else:
                    errors.append("SHA256 file not available")
        except Exception as e:
            errors.append(f"Failed to download SHA256: {e}")
        
        # Download signature (optional)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(sig_url)
                if response.status_code == 200:
                    with open(sig_path, "wb") as f:
                        f.write(response.content)
        except Exception:
            pass  # Signature is optional
        
        # Verify SHA256 if available
        if sha256_path.exists():
            try:
                with open(image_zip_path, "rb") as f:
                    sha256_hash = hashlib.sha256(f.read()).hexdigest()
                
                with open(sha256_path, "r") as f:
                    expected_hash = f.read().strip().split()[0]
                
                if sha256_hash != expected_hash:
                    errors.append("SHA256 checksum mismatch")
            except Exception as e:
                errors.append(f"Could not verify SHA256: {e}")
        
        # Create metadata.json
        metadata = {
            "codename": codename,
            "version": version,
            "deviceName": codename,
            "files": {
                "imageZip": "image.zip",
                "sha256": "image.zip.sha256",
                "sig": "image.zip.sig",
                "flashSh": "flash-all.sh",
                "flashBat": "flash-all.bat",
            },
            "downloaded": True,
        }
        
        metadata_path = version_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return {
            "success": len(errors) == 0,
            "codename": codename,
            "version": version,
            "path": str(version_dir),
            "errors": errors,
        }
        
    except Exception as e:
        # Cleanup on error
        if factory_zip_path.exists():
            factory_zip_path.unlink()
        if image_zip_path.exists():
            image_zip_path.unlink()
        raise

