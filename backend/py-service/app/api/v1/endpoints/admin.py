"""Admin/CMS API endpoints - storage and drive management"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.api.v1.endpoints.auth import get_current_user
from app.core.redis_client import get_redis
from app.services.storage_service import (
    get_all_users_storage,
    get_user_storage_quota,
    set_user_storage_quota,
    get_total_storage_used,
)
from app.api.v1.endpoints.drive import (
    REDIS_FILE_PREFIX,
    REDIS_FILE_METADATA_PREFIX,
    get_file_metadata,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

REDIS_DRIVE_PASSCODE_PREFIX = "drive:passcode_salt:"
REDIS_DRIVE_RATE_LIMIT_PREFIX = "drive:rate_limit:unlock:"
REDIS_DRIVE_UNLOCKED_PREFIX = "drive:unlocked:"


def _get_admin_emails() -> set:
    """Get admin emails from config"""
    emails = getattr(settings, "ADMIN_EMAILS", "") or ""
    return {e.strip().lower() for e in emails.split(",") if e.strip()}


async def get_current_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin role"""
    admin_emails = _get_admin_emails()
    if not admin_emails:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin access not configured (ADMIN_EMAILS)",
        )
    email = (current_user.get("email") or "").lower()
    if email not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# Pydantic models
class StorageQuotaUpdate(BaseModel):
    """Update user storage quota"""
    quota_bytes: Optional[int] = Field(None, gt=0, description="Storage quota in bytes")
    quota_gb: Optional[float] = Field(None, gt=0, description="Or quota in GB")


class AdminStatsResponse(BaseModel):
    """Admin dashboard stats"""
    total_storage_used_bytes: int
    total_storage_used_gb: float
    user_count: int


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
):
    """Get system capacity and usage stats."""
    users = await get_all_users_storage()
    total = sum(u["used_bytes"] for u in users)
    return AdminStatsResponse(
        total_storage_used_bytes=total,
        total_storage_used_gb=round(total / (1024 * 1024 * 1024), 2),
        user_count=len(users),
    )


@router.get("/storage")
async def list_users_storage(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
):
    """List all users' storage usage and quotas."""
    users = await get_all_users_storage()
    return {"users": users}


@router.put("/storage/{user_email}")
async def update_user_storage_quota(
    user_email: str,
    payload: StorageQuotaUpdate,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
):
    """Set storage quota for a user (admin only)."""
    if payload.quota_gb is not None:
        quota_bytes = int(payload.quota_gb * 1024 * 1024 * 1024)
    elif payload.quota_bytes is not None:
        quota_bytes = payload.quota_bytes
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide quota_bytes or quota_gb",
        )
    await set_user_storage_quota(user_email, quota_bytes)
    return {
        "email": user_email.lower(),
        "quota_bytes": quota_bytes,
        "quota_gb": round(quota_bytes / (1024 * 1024 * 1024), 2),
        "message": "Storage quota updated",
    }


@router.get("/drive")
async def list_all_files(
    user_email: Optional[str] = None,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
):
    """List all drive files (admin). Can filter by user_email."""
    redis = await get_redis()
    files = []
    async for key in redis.scan_iter(match=f"{REDIS_FILE_METADATA_PREFIX}*"):
        key_str = key.decode() if isinstance(key, bytes) else key
        file_id = key_str.replace(REDIS_FILE_METADATA_PREFIX, "")
        metadata_json = await redis.get(key_str)
        if not metadata_json:
            continue
        import json
        try:
            meta = json.loads(metadata_json)
            owner = meta.get("owner_email", "")
            if user_email and owner.lower() != user_email.lower():
                continue
            files.append({
                "file_id": file_id,
                "filename": meta.get("filename"),
                "size": meta.get("size"),
                "owner_email": owner,
                "passcode_protected": meta.get("passcode_protected", False),
                "created_at": meta.get("created_at"),
            })
        except json.JSONDecodeError:
            continue
    return {"files": files, "count": len(files)}


@router.delete("/drive/{file_id}")
async def admin_delete_file(
    file_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
):
    """Delete any file (admin). Updates storage quota for owner."""
    metadata = await get_file_metadata(file_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    owner_email = metadata.get("owner_email", "")
    file_size = metadata.get("size", 0)

    redis = await get_redis()
    deleted = 0

    keys_to_delete = [
        f"{REDIS_FILE_PREFIX}{file_id}",
        f"{REDIS_FILE_METADATA_PREFIX}{file_id}",
        f"{REDIS_DRIVE_PASSCODE_PREFIX}{file_id}",
        f"{REDIS_DRIVE_RATE_LIMIT_PREFIX}{file_id}",
    ]
    for k in keys_to_delete:
        if await redis.delete(k):
            deleted += 1

    # Delete unlocked keys (pattern)
    async for key in redis.scan_iter(match=f"{REDIS_DRIVE_UNLOCKED_PREFIX}{file_id}:*"):
        await redis.delete(key)

    if owner_email and file_size > 0:
        from app.services.storage_service import subtract_storage_used
        await subtract_storage_used(owner_email, file_size)

    logger.info(f"Admin deleted file: {file_id[:8]}...")
    return {"file_id": file_id, "deleted": True, "message": "File deleted by admin"}
