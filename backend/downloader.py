#!/usr/bin/env python3
"""
GrapheneOS Bundle Downloader
Downloads bundles from API with resume support and SHA256 verification
"""
import os
import sys
import json
import hashlib
import zipfile
import tarfile
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from requests.auth import HTTPBasicAuth
import argparse


class BundleDownloader:
    def __init__(self, api_base: str, api_key: str, cache_dir: str):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "GrapheneOS-Installer/1.0"
        })
    
    def list_bundles(self) -> list:
        """List all available bundles"""
        try:
            response = self.session.get(f"{self.api_base}/bundles", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"ERROR: Failed to list bundles: {e}", file=sys.stderr)
            sys.exit(1)
    
    def get_bundle_info(self, device: str, build_id: str) -> Dict[str, Any]:
        """Get information about a specific bundle"""
        try:
            response = self.session.get(
                f"{self.api_base}/bundles/{device}/{build_id}/info",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"ERROR: Failed to get bundle info: {e}", file=sys.stderr)
            sys.exit(1)
    
    def download_bundle(
        self,
        device: str,
        build_id: str,
        format: str = "zip",
        progress_callback=None
    ) -> Path:
        """
        Download bundle with resume support
        Returns path to downloaded and extracted bundle
        """
        # Get bundle info
        info = self.get_bundle_info(device, build_id)
        expected_sha256 = info["sha256"]
        expected_size = info["size"]
        
        # Determine download path
        download_dir = self.cache_dir / device / build_id
        download_dir.mkdir(parents=True, exist_ok=True)
        
        archive_path = download_dir / f"{device}-{build_id}.{format}"
        
        # Download with resume support
        self._download_with_resume(
            device,
            build_id,
            archive_path,
            expected_size,
            format,
            progress_callback
        )
        
        # Verify SHA256
        actual_sha256 = self._calculate_sha256(archive_path)
        if actual_sha256 != expected_sha256:
            print(f"ERROR: SHA256 mismatch!", file=sys.stderr)
            print(f"Expected: {expected_sha256}", file=sys.stderr)
            print(f"Actual:   {actual_sha256}", file=sys.stderr)
            archive_path.unlink()
            sys.exit(1)
        
        print(f"✓ SHA256 verified: {actual_sha256[:16]}...", file=sys.stderr)
        
        # Extract archive
        extract_path = download_dir / "extracted"
        if extract_path.exists():
            import shutil
            shutil.rmtree(extract_path)
        extract_path.mkdir()
        
        print(f"Extracting to {extract_path}...", file=sys.stderr)
        self._extract_archive(archive_path, extract_path)
        
        # Move extracted contents to bundle directory
        bundle_path = download_dir / "bundle"
        if bundle_path.exists():
            import shutil
            shutil.rmtree(bundle_path)
        
        # Find the actual bundle content (could be in subdirectory)
        extracted_items = list(extract_path.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            # Single subdirectory - move its contents
            bundle_path.mkdir()
            for item in extracted_items[0].iterdir():
                import shutil
                shutil.move(str(item), str(bundle_path / item.name))
        else:
            # Multiple items or files - move all
            bundle_path.mkdir()
            for item in extracted_items:
                import shutil
                shutil.move(str(item), str(bundle_path / item.name))
        
        # Cleanup
        import shutil
        shutil.rmtree(extract_path)
        archive_path.unlink()  # Remove archive after extraction
        
        print(f"✓ Bundle ready at: {bundle_path}", file=sys.stderr)
        return bundle_path
    
    def _download_with_resume(
        self,
        device: str,
        build_id: str,
        output_path: Path,
        expected_size: int,
        format: str,
        progress_callback=None
    ):
        """Download with HTTP Range support for resume"""
        url = f"{self.api_base}/bundles/{device}/{build_id}/download?format={format}"
        
        # Check if partial download exists
        resume_pos = 0
        if output_path.exists():
            resume_pos = output_path.stat().st_size
            if resume_pos >= expected_size:
                print(f"✓ Download already complete", file=sys.stderr)
                return
        
        mode = "ab" if resume_pos > 0 else "wb"
        
        headers = {}
        if resume_pos > 0:
            headers["Range"] = f"bytes={resume_pos}-"
            print(f"Resuming download from byte {resume_pos}...", file=sys.stderr)
        else:
            print(f"Starting download...", file=sys.stderr)
        
        try:
            with open(output_path, mode) as f:
                response = self.session.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=3600
                )
                response.raise_for_status()
                
                downloaded = resume_pos
                chunk_size = 8192
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, expected_size)
                        else:
                            percent = (downloaded / expected_size * 100) if expected_size > 0 else 0
                            print(f"\rProgress: {percent:.1f}% ({downloaded}/{expected_size} bytes)", end="", file=sys.stderr)
                
                print("", file=sys.stderr)  # New line
                print(f"✓ Download complete", file=sys.stderr)
        
        except requests.RequestException as e:
            print(f"ERROR: Download failed: {e}", file=sys.stderr)
            sys.exit(1)
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 checksum"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _extract_archive(self, archive_path: Path, extract_to: Path):
        """Extract ZIP or TAR archive"""
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif archive_path.suffix in [".tar", ".gz"]:
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_to)
        else:
            print(f"ERROR: Unsupported archive format: {archive_path.suffix}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download GrapheneOS bundle")
    parser.add_argument("--api-base", required=True, help="API base URL")
    parser.add_argument("--api-key", required=True, help="API key")
    parser.add_argument("--cache-dir", required=True, help="Cache directory")
    parser.add_argument("--device", required=True, help="Device codename (e.g., panther)")
    parser.add_argument("--build-id", required=True, help="Build ID (e.g., 2025122500)")
    parser.add_argument("--format", default="zip", choices=["zip", "tar"], help="Archive format")
    
    args = parser.parse_args()
    
    downloader = BundleDownloader(args.api_base, args.api_key, args.cache_dir)
    bundle_path = downloader.download_bundle(args.device, args.build_id, args.format)
    
    # Output JSON result
    result = {
        "success": True,
        "device": args.device,
        "build_id": args.build_id,
        "bundle_path": str(bundle_path)
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()

