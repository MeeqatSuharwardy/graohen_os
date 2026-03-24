"""
Aggregate registered clients for a user: device-bound (mobile/native), browser SSH sessions,
encryption key fingerprints, and stored SSH public keys for web login.
"""

import json
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select

from app.core import database
from app.models.user_ssh_key import UserSSHKey
from app.services.device_key_service import REDIS_DEVICE_SEED_PREFIX

# Must match auth.py
REDIS_DEVICE_PREFIX = "auth:device:"
REDIS_DEVICE_KEY_FINGERPRINT_PREFIX = "auth:device_key:"


def _classify_device_kind(device_id: str) -> str:
    if device_id.startswith("ssh-browser-"):
        return "browser_ssh"
    return "native_app"


def _platform_hint(device_kind: str) -> str:
    if device_kind == "browser_ssh":
        return "Web browser (SSH sign-in)"
    return "Mobile or desktop app (device-bound login)"


async def _device_ids_with_seed(redis, user_id: str) -> Set[str]:
    out: Set[str] = set()
    prefix = f"{REDIS_DEVICE_SEED_PREFIX}{user_id}:"
    try:
        async for key in redis.scan_iter(match=f"{REDIS_DEVICE_SEED_PREFIX}{user_id}:*"):
            ks = key.decode() if isinstance(key, bytes) else key
            if ks.startswith(prefix):
                out.add(ks[len(prefix) :])
    except Exception:
        pass
    return out


async def _device_ids_from_fingerprint_set(redis, user_id: str) -> Set[str]:
    out: Set[str] = set()
    key = f"{REDIS_DEVICE_PREFIX}{user_id}:devices"
    try:
        members = await redis.smembers(key)
        for m in members or []:
            out.add(m.decode() if isinstance(m, bytes) else m)
    except Exception:
        pass
    return out


async def _device_ids_from_refresh_mappings(redis, user_id: str) -> Set[str]:
    """device_id keys that still have an active refresh mapping (may overlap seeds)."""
    out: Set[str] = set()
    base = f"{REDIS_DEVICE_PREFIX}{user_id}:"
    try:
        async for key in redis.scan_iter(match=f"{base}*"):
            ks = key.decode() if isinstance(key, bytes) else key
            suffix = ks[len(base) :]
            if suffix == "devices":
                continue
            out.add(suffix)
    except Exception:
        pass
    return out


async def _fingerprint_meta(redis, user_id: str, device_id: str) -> Optional[Dict[str, Any]]:
    fk = f"{REDIS_DEVICE_KEY_FINGERPRINT_PREFIX}{user_id}:{device_id}"
    try:
        raw = await redis.get(fk)
        if not raw:
            return None
        s = raw.decode() if isinstance(raw, bytes) else raw
        return json.loads(s)
    except Exception:
        return None


async def _has_refresh_mapping(redis, user_id: str, device_id: str) -> bool:
    k = f"{REDIS_DEVICE_PREFIX}{user_id}:{device_id}"
    try:
        v = await redis.get(k)
        return bool(v)
    except Exception:
        return False


async def list_registered_devices_for_user(
    user_id: str,
    current_device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a summary of known clients for settings / security UI.

    user_id: string as in JWT (sub).
    current_device_id: optional device_id from current access token for is_current_session.
    """
    uid = user_id
    all_ids: Set[str] = set()

    redis = None
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
    except Exception:
        redis = None

    seed_ids: Set[str] = set()
    if redis:
        seed_ids = await _device_ids_with_seed(redis, uid)
        all_ids |= seed_ids
        all_ids |= await _device_ids_from_fingerprint_set(redis, uid)
        all_ids |= await _device_ids_from_refresh_mappings(redis, uid)

    devices_out: List[Dict[str, Any]] = []
    for device_id in sorted(all_ids):
        kind = _classify_device_kind(device_id)
        has_seed = device_id in seed_ids

        fp_meta = await _fingerprint_meta(redis, uid, device_id) if redis else None
        has_refresh = await _has_refresh_mapping(redis, uid, device_id) if redis else False

        fp_display = None
        if fp_meta and fp_meta.get("key_fingerprint"):
            h = fp_meta["key_fingerprint"]
            fp_display = f"{h[:12]}…{h[-8:]}" if len(h) > 20 else h

        devices_out.append(
            {
                "device_id": device_id,
                "device_kind": kind,
                "platform_hint": _platform_hint(kind),
                "has_device_seed": has_seed,
                "has_active_refresh_session": has_refresh,
                "encryption_key_fingerprint_preview": fp_display,
                "key_algorithm": fp_meta.get("key_algorithm") if fp_meta else None,
                "fingerprint_registered_at": fp_meta.get("registered_at") if fp_meta else None,
                "is_current_session": bool(
                    current_device_id and current_device_id == device_id
                ),
            }
        )

    ssh_keys: List[Dict[str, Any]] = []
    if database.AsyncSessionLocal is not None:
        try:
            async with database.AsyncSessionLocal() as session:
                q = await session.execute(
                    select(UserSSHKey).where(UserSSHKey.user_id == int(uid))
                )
                rows = q.scalars().all()
                for row in rows:
                    ssh_keys.append(
                        {
                            "key_fingerprint": row.key_fingerprint,
                            "key_type": row.key_type,
                            "registered_at": row.created_at.isoformat()
                            if row.created_at
                            else None,
                            "purpose": "browser_ssh_login",
                            "description": "SSH public key for web sign-in (no private key stored on server)",
                        }
                    )
        except Exception:
            pass

    return {
        "devices": devices_out,
        "ssh_keys_for_browser_login": ssh_keys,
        "note": (
            "device_kind native_app = mobile or desktop clients using device key + password flow; "
            "browser_ssh = sessions created via SSH key login. "
            "ssh_keys_for_browser_login lists registered public keys for challenge sign-in."
        ),
    }
