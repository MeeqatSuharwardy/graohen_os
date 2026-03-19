"""
Device-bound encryption key for login security.

Uses secure_derivation multi-layer algorithm - resistant to reverse engineering.
256-bit, rotates every 2 min, server-synced. Does NOT affect email/drive.
"""

import secrets
import hashlib
import hmac
import time
from typing import Tuple

from app.core.encryption import KEY_SIZE
from app.core.secure_derivation import (
    derive_device_time_key,
    get_current_time_slot,
    get_valid_time_slots,
)
import logging

logger = logging.getLogger(__name__)

TIME_SLOT_SECONDS = 120


def generate_device_seed() -> bytes:
    """Generate 256-bit cryptographically secure device seed."""
    return secrets.token_bytes(KEY_SIZE)


def create_device_proof(time_slot_key: bytes, challenge: str) -> str:
    """Create HMAC proof that device possesses current time-slot key."""
    return hmac.new(
        time_slot_key,
        challenge.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_device_proof(time_slot_key: bytes, challenge: str, proof: str) -> bool:
    """Verify device proof using constant-time comparison."""
    expected = create_device_proof(time_slot_key, challenge)
    return hmac.compare_digest(expected, proof)
