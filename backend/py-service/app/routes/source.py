from fastapi import APIRouter, HTTPException
from pathlib import Path
from ..config import settings

router = APIRouter()


@router.get("/status")
async def get_source_status():
    """Check GrapheneOS source status"""
    source_root = Path(settings.GRAPHENE_SOURCE_ROOT)
    
    if not source_root.exists():
        return {
            "exists": False,
            "message": "Source root does not exist",
        }
    
    repo_dir = source_root / ".repo"
    if not repo_dir.exists():
        return {
            "exists": True,
            "repo_initialized": False,
            "message": "Source root exists but .repo directory not found",
        }
    
    # Try to read manifest revision
    manifest_file = repo_dir / "manifests" / ".git" / "HEAD"
    manifest_revision = None
    if manifest_file.exists():
        try:
            with open(manifest_file, "r") as f:
                manifest_revision = f.read().strip()
        except Exception:
            pass
    
    return {
        "exists": True,
        "repo_initialized": True,
        "path": str(source_root),
        "manifest_revision": manifest_revision,
    }


@router.post("/validate")
async def validate_source():
    """Validate GrapheneOS source"""
    source_root = Path(settings.GRAPHENE_SOURCE_ROOT)
    
    if not source_root.exists():
        raise HTTPException(status_code=404, detail="Source root does not exist")
    
    repo_dir = source_root / ".repo"
    if not repo_dir.exists():
        raise HTTPException(status_code=400, detail="Source not initialized (no .repo directory)")
    
    return {
        "valid": True,
        "message": "Source appears to be valid",
    }

