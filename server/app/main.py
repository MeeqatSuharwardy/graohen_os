"""
FastAPI Server for GrapheneOS Bundle Distribution
Serves bundles from local disk with API key authentication
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import hashlib
import zipfile
import tarfile
from pathlib import Path
import uvicorn
from .config import settings

app = FastAPI(
    title="GrapheneOS Bundle Server",
    description="Secure bundle distribution API",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication
security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Authorization header"""
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


class BundleInfo(BaseModel):
    device: str
    build_id: str
    size: int
    sha256: str
    path: str


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "GrapheneOS Bundle Server"}


@app.get("/bundles", dependencies=[Depends(verify_api_key)])
async def list_bundles() -> List[BundleInfo]:
    """
    List all available bundles
    Returns device, build_id, size, checksum for each bundle
    """
    bundles_root = Path(settings.BUNDLES_ROOT)
    if not bundles_root.exists():
        return []
    
    bundles = []
    
    for device_dir in bundles_root.iterdir():
        if not device_dir.is_dir():
            continue
        
        device = device_dir.name
        
        for build_dir in device_dir.iterdir():
            if not build_dir.is_dir():
                continue
            
            build_id = build_dir.name
            
            # Check for image.zip or factory zip
            image_zip = build_dir / "image.zip"
            factory_zip = build_dir / f"{device}-factory-{build_id}.zip"
            
            bundle_file = image_zip if image_zip.exists() else (factory_zip if factory_zip.exists() else None)
            
            if bundle_file and bundle_file.exists():
                # Calculate size and SHA256
                size = bundle_file.stat().st_size
                sha256 = calculate_sha256(bundle_file)
                
                bundles.append(BundleInfo(
                    device=device,
                    build_id=build_id,
                    size=size,
                    sha256=sha256,
                    path=str(build_dir)
                ))
    
    return bundles


@app.get("/bundles/{device}/{build_id}/info", dependencies=[Depends(verify_api_key)])
async def get_bundle_info(device: str, build_id: str) -> BundleInfo:
    """Get information about a specific bundle"""
    bundle_path = Path(settings.BUNDLES_ROOT) / device / build_id
    
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail=f"Bundle not found: {device}/{build_id}")
    
    # Find bundle file
    image_zip = bundle_path / "image.zip"
    factory_zip = bundle_path / f"{device}-factory-{build_id}.zip"
    
    bundle_file = image_zip if image_zip.exists() else (factory_zip if factory_zip.exists() else None)
    
    if not bundle_file or not bundle_file.exists():
        raise HTTPException(status_code=404, detail=f"Bundle archive not found: {device}/{build_id}")
    
    size = bundle_file.stat().st_size
    sha256 = calculate_sha256(bundle_file)
    
    return BundleInfo(
        device=device,
        build_id=build_id,
        size=size,
        sha256=sha256,
        path=str(bundle_path)
    )


@app.get("/bundles/{device}/{build_id}/download", dependencies=[Depends(verify_api_key)])
async def download_bundle(
    device: str,
    build_id: str,
    request: Request,
    format: str = "zip"
):
    """
    Download bundle archive with resume support (HTTP Range)
    Supports ZIP and TAR formats
    """
    bundle_path = Path(settings.BUNDLES_ROOT) / device / build_id
    
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail=f"Bundle not found: {device}/{build_id}")
    
    # Find bundle file
    image_zip = bundle_path / "image.zip"
    factory_zip = bundle_path / f"{device}-factory-{build_id}.zip"
    
    bundle_file = image_zip if image_zip.exists() else (factory_zip if factory_zip.exists() else None)
    
    if not bundle_file or not bundle_file.exists():
        raise HTTPException(status_code=404, detail=f"Bundle archive not found: {device}/{build_id}")
    
    # Create archive on-the-fly if format requested
    if format == "tar":
        # Create TAR archive dynamically
        archive_path = bundle_path / f"{device}-{build_id}.tar"
        if not archive_path.exists():
            create_tar_archive(bundle_path, archive_path)
        bundle_file = archive_path
    elif format == "zip" and not bundle_file.exists():
        # Create ZIP archive dynamically
        archive_path = bundle_path / f"{device}-{build_id}.zip"
        if not archive_path.exists():
            create_zip_archive(bundle_path, archive_path)
        bundle_file = archive_path
    
    # Support HTTP Range for resume
    file_size = bundle_file.stat().st_size
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range header
        byte_start = 0
        byte_end = file_size - 1
        
        if range_header.startswith("bytes="):
            ranges = range_header[6:].split("-")
            if ranges[0]:
                byte_start = int(ranges[0])
            if ranges[1]:
                byte_end = int(ranges[1])
        
        # Open file and seek to start position
        file_handle = open(bundle_file, "rb")
        file_handle.seek(byte_start)
        
        content_length = byte_end - byte_start + 1
        
        headers = {
            "Content-Range": f"bytes {byte_start}-{byte_end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "application/zip" if format == "zip" else "application/x-tar",
        }
        
        return StreamingResponse(
            iter(lambda: file_handle.read(8192), b""),
            status_code=206,
            headers=headers,
            media_type="application/zip" if format == "zip" else "application/x-tar"
        )
    else:
        # Full file download
        return FileResponse(
            bundle_file,
            media_type="application/zip" if format == "zip" else "application/x-tar",
            filename=bundle_file.name,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            }
        )


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_zip_archive(source_dir: Path, output_path: Path):
    """Create ZIP archive from directory"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Skip the archive file itself if it exists
            for file in files:
                file_path = Path(root) / file
                if file_path != output_path:
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)


def create_tar_archive(source_dir: Path, output_path: Path):
    """Create TAR archive from directory"""
    with tarfile.open(output_path, 'w:gz') as tar:
        tar.add(source_dir, arcname=source_dir.name, recursive=True)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

