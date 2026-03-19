"""
Hardened multi-layer key derivation - computationally infeasible to crack.

Uses cascading Argon2id, deep Blake2b/SHA3/SHA512 chains, cross-feedback,
sponge-like absorption, and multi-phase XOR mixing. No single formula;
each layer depends on multiple previous outputs. Designed to resist
reverse engineering, brute force, and supercomputer attacks.
"""

import hashlib
import struct
import time
from typing import Tuple

from argon2.low_level import hash_secret_raw, Type

from app.core.encryption import KEY_SIZE

# Opaque domain constants (algorithm-specific, not security secrets)
# Multiple constants prevent pattern recognition
_D1 = 0x8F3A2B1C9E4D7F06
_D2 = "k9m2n7p4q1r5s8t0"
_D3 = b"\x7e\x3d\x9a\x2f\xb1\xc8\x4e\x6a\xd5\xf2\x18\x3c\x91\xa7\xb4\xe0"
_D4 = 0xC2E5A8F1
_D5 = b"\x2a\x5b\x8c\x1d\x4e\x9f\x30\x61\x72\xa3\xb4\xc5\xd6\xe7\xf8\x09"
_D6 = "v7x2w9z4"

TIME_SLOT_SECONDS = 120
ARGON_MEMORY = 65536  # 64 MB - memory-hard
ARGON_TIME = 5  # 5 iterations


def _blake2b_chain(data: bytes, rounds: int = 16, seed: bytes = b"") -> bytes:
    """Deep Blake2b chain - each round feeds into next with domain separation."""
    h = data
    for i in range(rounds):
        mix = struct.pack(">I", i) + _D3 + seed[:8] + _D2.encode()
        h = hashlib.blake2b(
            h + mix + h[-16:] if len(h) >= 16 else h,
            digest_size=32,
        ).digest()
    return h


def _sha3_chain(data: bytes, rounds: int = 14, ctx_seed: bytes = b"") -> bytes:
    """SHA3-256 chain with context mixing and feedback."""
    h = data
    ctx = ctx_seed[:16] if ctx_seed else data[:16]
    for i in range(rounds):
        ctx = hashlib.sha3_256(
            h + _D5 + ctx + struct.pack(">Q", i) + _D2.encode()
        ).digest()
        h = hashlib.sha3_256(h + ctx + h[-8:] if len(h) >= 8 else h).digest()
    return h


def _sha3_512_chain(data: bytes, rounds: int = 12) -> bytes:
    """SHA3-512 chain - produces 64-byte outputs for nonce expansion."""
    h = hashlib.sha3_512(data + _D3).digest()
    for i in range(rounds - 1):
        h = hashlib.sha3_512(
            h + data[:32] + struct.pack(">I", i) + _D6.encode()
        ).digest()
    return h


def _sha512_chain(data: bytes, rounds: int = 8) -> bytes:
    """SHA-512 chain - different primitive for diversity."""
    h = data
    for i in range(rounds):
        h = hashlib.sha512(
            h + _D3 + struct.pack(">Q", i) + _D5
        ).digest()
    return h[:32]


def _xor_mix(a: bytes, b: bytes, c: bytes, d: bytes = None) -> bytes:
    """Multi-input XOR mix - output depends on all inputs."""
    if d is None:
        return bytes(x ^ y ^ z for x, y, z in zip(a, b, c))
    return bytes(w ^ x ^ y ^ z for w, x, y, z in zip(a, b, c, d))


def _rotate_mix(a: bytes, b: bytes, rot: int = 7) -> bytes:
    """XOR with byte-rotated copy for diffusion."""
    n = len(a)
    rotated = bytes((a[(i + rot) % n] for i in range(n)))
    return bytes(x ^ y for x, y in zip(rotated, b))


def _argon_layer(secret: bytes, salt: bytes) -> bytes:
    """Argon2id layer - memory-hard, time-cost."""
    return hash_secret_raw(
        secret=secret,
        salt=salt,
        time_cost=ARGON_TIME,
        memory_cost=ARGON_MEMORY,
        parallelism=1,
        hash_len=KEY_SIZE,
        type=Type.ID,
    )


def _sponge_absorb_squeeze(blocks: list, output_len: int = 32) -> bytes:
    """Sponge-like absorption: absorb all blocks, squeeze output."""
    state = hashlib.sha3_512(b"".join(blocks) + _D3).digest()
    for _ in range(3):
        state = hashlib.sha3_512(state + _D5).digest()
    return state[:output_len]


def derive_device_time_key(
    device_seed: bytes,
    device_id: str,
    time_slot: int,
) -> bytes:
    """
    Hardened multi-layer derivation for device auth key.
    
    Phase 1: Cascading Argon2id (2 passes, each output feeds next salt)
    Phase 2: Deep Blake2b chain (16 rounds)
    Phase 3: SHA3-256 chain with feedback (14 rounds)
    Phase 4: SHA3-512 expansion for nonces (12 rounds)
    Phase 5: Multi-phase XOR mixing with 4 derived nonces
    Phase 6: Cross-feedback: SHA-512 chain on mixed result
    Phase 7: Final Blake2b with sponge absorption
    """
    dev_bytes = device_id.encode()
    
    # Phase 1: Cascading Argon2id
    salt1 = hashlib.sha3_256(
        f"{_D2}:{time_slot}:{device_id}:{_D1}:{_D4}".encode()
    ).digest()
    k1 = _argon_layer(device_seed, salt1)
    salt2 = hashlib.sha3_256(k1 + salt1 + dev_bytes).digest()
    k2 = _argon_layer(k1, salt2)
    
    # Phase 2: Deep Blake2b chain
    k3 = _blake2b_chain(k2 + dev_bytes + salt2, rounds=16, seed=salt1)
    
    # Phase 3: SHA3 chain with feedback
    k4 = _sha3_chain(k3, rounds=14, ctx_seed=salt2 + k2[:16])
    
    # Phase 4: SHA3-512 expansion for nonces
    expand = _sha3_512_chain(k4 + k3 + k2, rounds=12)
    nonce_a = expand[:32]
    nonce_b = expand[32:64]
    nonce_c = hashlib.sha3_512(
        expand + f"{time_slot}:{_D1}:{_D6}".encode()
    ).digest()[:32]
    nonce_d = hashlib.sha3_512(
        k4 + nonce_a + nonce_b + struct.pack(">Q", time_slot)
    ).digest()[:32]
    
    # Phase 5: Multi-phase XOR mixing
    m1 = _xor_mix(k4, nonce_a, nonce_b)
    m2 = _xor_mix(m1, nonce_c, nonce_d, k3)
    m3 = _rotate_mix(m2, nonce_a, 5)
    m4 = _xor_mix(m3, nonce_b, k2[:32])
    
    # Phase 6: SHA-512 chain for diversity
    k5 = _sha512_chain(m4 + k1[:16])
    
    # Phase 7: Final sponge + Blake2b
    sponge_in = [k5, m4, k4, salt2]
    final_salt = _sponge_absorb_squeeze(sponge_in, 32)
    return _blake2b_chain(
        k5 + final_salt + m4[:16] + k1[:16],
        rounds=8,
        seed=final_salt,
    )[:KEY_SIZE]


def derive_user_key_complex(
    primary_key: bytes,
    context: bytes,
) -> bytes:
    """
    Same hardened chain for drive/email keys.
    primary_key: output of Argon2id(passcode/email, salt)
    context: salt + identifier for uniqueness
    """
    # Phase 1: Deep Blake2b chain
    k1 = _blake2b_chain(primary_key + context, rounds=16, seed=context[:8])
    
    # Phase 2: SHA3 chain with feedback
    k2 = _sha3_chain(k1, rounds=14, ctx_seed=context + primary_key[:16])
    
    # Phase 3: SHA3-512 expansion for nonces
    expand = _sha3_512_chain(k2 + k1 + primary_key, rounds=12)
    nonce_a = expand[:32]
    nonce_b = expand[32:64]
    nonce_c = hashlib.sha3_512(expand + context + _D3).digest()[:32]
    nonce_d = hashlib.sha3_512(k2 + nonce_a + _D5).digest()[:32]
    
    # Phase 4: Multi-phase XOR mixing
    m1 = _xor_mix(k2, nonce_a, nonce_b)
    m2 = _xor_mix(m1, nonce_c, nonce_d, k1)
    m3 = _rotate_mix(m2, nonce_a, 11)
    m4 = _xor_mix(m3, nonce_b, primary_key[:32])
    
    # Phase 5: SHA-512 chain
    k3 = _sha512_chain(m4 + context[:16])
    
    # Phase 6: Final sponge + Blake2b
    sponge_in = [k3, m4, k2, context]
    final_salt = _sponge_absorb_squeeze(sponge_in, 32)
    return _blake2b_chain(
        k3 + final_salt + context[:16],
        rounds=8,
        seed=final_salt,
    )[:KEY_SIZE]


def get_current_time_slot() -> int:
    """Current 2-minute time slot."""
    return int(time.time()) // TIME_SLOT_SECONDS


def get_valid_time_slots() -> Tuple[int, int, int]:
    """Current, prev, next for clock skew."""
    c = get_current_time_slot()
    return (c, c - 1, c + 1)
