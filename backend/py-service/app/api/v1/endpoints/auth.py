"""Authentication endpoints"""

import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, field_validator
from jose import jwt, JWTError

from app.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.redis_client import get_redis
from app.core.security_hardening import (
    get_security_service,
    SecurityEvent,
    BruteForceError,
)
from app.services.user_service import get_user_service
from app.core.secure_derivation import get_current_time_slot
from app.services.device_key_service import (
    create_device_seed_for_user,
    get_device_seed,
    user_has_any_device_seed,
    encrypt_seed_for_device_download,
    store_challenge,
    get_and_consume_challenge,
    verify_device_login_proof,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Redis key prefixes
REDIS_TOKEN_REVOKED_PREFIX = "auth:revoked:"
REDIS_REFRESH_TOKEN_PREFIX = "auth:refresh:"
REDIS_DEVICE_PREFIX = "auth:device:"
REDIS_DEVICE_KEY_FINGERPRINT_PREFIX = "auth:device_key:"

# Token rotation settings
REFRESH_TOKEN_ROTATION_ENABLED = True


# Pydantic Models
class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    device_id: Optional[str] = Field(None, max_length=255, description="Device identifier for device binding")
    ssh_public_key: Optional[str] = Field(
        None,
        max_length=4096,
        description="SSH public key for browser login (OpenSSH format, e.g. ssh-ed25519 AAAA...)"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Add more validation as needed (uppercase, lowercase, numbers, symbols)
        return v


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str
    device_id: Optional[str] = Field(None, max_length=255, description="Device identifier for device binding")
    device_key_fingerprint: Optional[str] = Field(
        None,
        min_length=32,
        max_length=128,
        description="SHA-256 hash/fingerprint of the device encryption key (stored/replaced on every login)"
    )
    device_key_algorithm: Optional[str] = Field(
        default="AES-256-GCM",
        description="Encryption algorithm used for device key"
    )


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    device_id: Optional[str] = None
    device_key_download: Optional[Dict[str, str]] = None  # Encrypted key - save to device


class DeviceKeyDownloadRequest(BaseModel):
    """Request device key download (requires password)"""
    email: EmailStr
    password: str
    device_id: str = Field(..., min_length=8, max_length=255)


class LoginChallengeRequest(BaseModel):
    """Request login challenge"""
    email: EmailStr
    device_id: str = Field(..., min_length=8, max_length=255)


class LoginChallengeResponse(BaseModel):
    """Login challenge response"""
    challenge: str
    time_slot: int
    expires_in_seconds: int = 120


class LoginWithDeviceRequest(BaseModel):
    """Login with device proof"""
    email: EmailStr
    password: str
    device_id: str = Field(..., min_length=8, max_length=255)
    challenge: str = Field(..., min_length=1)
    proof: str = Field(..., min_length=1)
    time_slot: Optional[int] = None  # Client's time slot for clock skew


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str
    device_id: Optional[str] = Field(None, max_length=255)


class LogoutRequest(BaseModel):
    """Logout request"""
    refresh_token: Optional[str] = None
    all_devices: bool = False


class DeviceEncryptionKeyRegister(BaseModel):
    """Device encryption key registration (fingerprint only, never the actual key)"""
    device_id: str = Field(..., min_length=1, max_length=255, description="Device identifier")
    key_fingerprint: str = Field(
        ...,
        min_length=32,
        max_length=128,
        description="SHA-256 hash/fingerprint of the device encryption key (for verification only)"
    )
    key_algorithm: str = Field(default="AES-256-GCM", description="Encryption algorithm used")


class DeviceEncryptionKeyResponse(BaseModel):
    """Device encryption key response"""
    device_id: str
    registered: bool
    message: str


# SSH key models (browser-only login, device_id flow kept for mobile)
class SSHKeyAddRequest(BaseModel):
    """Add SSH public key to account (requires auth). Ed25519 lines are ~70–100 chars."""
    ssh_public_key: str = Field(..., min_length=20, max_length=4096)


class SSHChallengeRequest(BaseModel):
    """Request SSH login challenge"""
    email: EmailStr


class SSHChallengeResponse(BaseModel):
    """SSH challenge response"""
    challenge: str
    expires_in_seconds: int = 120


class SSHLoginRequest(BaseModel):
    """SSH key login - sign challenge with private key"""
    email: EmailStr
    signature: str = Field(..., min_length=1, description="Base64-encoded signature of challenge")


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email from PostgreSQL.
    """
    try:
        user_service = get_user_service()
        return await user_service.get_user_by_email(email)
    except Exception as e:
        logger.error(f"Failed to get user by email: {e}", exc_info=True)
        return None


async def create_user(email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new user in PostgreSQL.
    """
    try:
        user_service = get_user_service()
        return await user_service.create_user(email, password, full_name)
    except ValueError as e:
        # Email already exists
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )


async def verify_device_binding(device_id: Optional[str], token_payload: Dict[str, Any]) -> bool:
    """
    Verify that the device_id in the token matches the provided device_id.
    
    Args:
        device_id: Device identifier from request
        token_payload: Decoded JWT token payload
    
    Returns:
        True if device binding is valid, False otherwise
    """
    if not device_id:
        # No device binding required
        return True
    
    token_device_id = token_payload.get("device_id")
    if not token_device_id:
        # Token doesn't have device binding, allow it
        return True
    
    # Device IDs must match
    return token_device_id == device_id


async def is_token_revoked(token_jti: str, user_id: Optional[str] = None) -> bool:
    """Check if a token is revoked in Redis"""
    redis = await get_redis()
    
    # Check specific token JTI
    if token_jti:
        key = f"{REDIS_TOKEN_REVOKED_PREFIX}{token_jti}"
        if await redis.get(key):
            return True
    
    # Check if all user tokens are revoked
    if user_id:
        user_revoke_key = f"{REDIS_TOKEN_REVOKED_PREFIX}user:{user_id}"
        if await redis.get(user_revoke_key):
            return True
    
    return False


async def revoke_token(token_jti: str, expires_in: Optional[timedelta] = None) -> None:
    """Revoke a token by storing its JTI in Redis"""
    if not token_jti:
        return
    
    redis = await get_redis()
    key = f"{REDIS_TOKEN_REVOKED_PREFIX}{token_jti}"
    
    # Store revocation with expiration matching token expiration
    if expires_in:
        await redis.setex(key, int(expires_in.total_seconds()), "1")
    else:
        # Default: store for 30 days (longer than refresh token lifetime)
        await redis.setex(key, 30 * 24 * 60 * 60, "1")
    
    logger.info(f"Token revoked: {token_jti[:8]}...")


async def store_refresh_token(
    refresh_token: str,
    user_id: str,
    device_id: Optional[str],
    expires_in: timedelta
) -> None:
    """Store refresh token metadata in Redis for rotation"""
    redis = await get_redis()
    
    # Create token identifier
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    # Store token metadata as JSON
    key = f"{REDIS_REFRESH_TOKEN_PREFIX}{token_hash}"
    metadata = {
        "user_id": user_id,
        "device_id": device_id or "",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Store with expiration
    await redis.setex(
        key,
        int(expires_in.total_seconds()),
        json.dumps(metadata)
    )
    
    # If device_id provided, also store device-to-token mapping
    if device_id:
        device_key = f"{REDIS_DEVICE_PREFIX}{user_id}:{device_id}"
        await redis.setex(
            device_key,
            int(expires_in.total_seconds()),
            token_hash
        )


async def get_refresh_token_metadata(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Get refresh token metadata from Redis"""
    redis = await get_redis()
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    key = f"{REDIS_REFRESH_TOKEN_PREFIX}{token_hash}"
    
    metadata_str = await redis.get(key)
    if not metadata_str:
        return None
    
    # Parse metadata JSON
    try:
        metadata = json.loads(metadata_str)
        metadata["token_hash"] = token_hash
        return metadata
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse refresh token metadata: {e}")
        return None


async def revoke_refresh_token(refresh_token: str) -> None:
    """Revoke a refresh token"""
    redis = await get_redis()
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    key = f"{REDIS_REFRESH_TOKEN_PREFIX}{token_hash}"
    
    # Delete token metadata
    await redis.delete(key)
    
    logger.info(f"Refresh token revoked: {token_hash[:8]}...")


async def revoke_all_user_tokens(user_id: str) -> None:
    """Revoke all tokens for a user (logout from all devices)"""
    redis = await get_redis()
    
    # Find all device keys for this user using SCAN (production-safe)
    pattern = f"{REDIS_DEVICE_PREFIX}{user_id}:*"
    deleted_count = 0
    
    async for key in redis.scan_iter(match=pattern):
        # Get token hash from device key
        token_hash = await redis.get(key)
        if token_hash:
            # Delete refresh token metadata
            refresh_key = f"{REDIS_REFRESH_TOKEN_PREFIX}{token_hash}"
            await redis.delete(refresh_key)
            deleted_count += 1
        
        # Delete device key
        await redis.delete(key)
    
    # Also add a user-level revocation marker for immediate access token rejection
    user_revoke_key = f"{REDIS_TOKEN_REVOKED_PREFIX}user:{user_id}"
    await redis.setex(user_revoke_key, 7 * 24 * 60 * 60, "1")  # 7 days
    
    logger.info(f"All tokens revoked for user: {user_id} ({deleted_count} tokens)")


def generate_token_jti() -> str:
    """Generate a unique token identifier (JWT ID)"""
    return secrets.token_urlsafe(32)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
):
    """
    Register a new user.
    
    Creates account and returns tokens + device_key_download.
    Save device_key_download to device - required for future logins.
    Key rotates every 2 min (server-synced), does not affect email/drive.
    """
    security = get_security_service()
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        await security.check_rate_limit(
            identifier=client_ip,
            max_requests=settings.REGISTER_RATE_LIMIT_MAX,
            window_seconds=settings.REGISTER_RATE_LIMIT_WINDOW,
            action="register",
        )
        
        user = await create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )
        
        device_id = user_data.device_id or generate_token_jti()
        if len(device_id) < 8:
            device_id = generate_token_jti()
        
        # Generate token JTI for revocation tracking
        access_jti = generate_token_jti()
        refresh_jti = generate_token_jti()
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={
                "sub": user["id"],
                "email": user["email"],
                "jti": access_jti,
                "device_id": device_id,
            },
            expires_delta=access_token_expires,
        )
        
        refresh_token = create_refresh_token(
            data={
                "sub": user["id"],
                "email": user["email"],
                "jti": refresh_jti,
                "device_id": device_id,
            }
        )
        
        await store_refresh_token(
            refresh_token=refresh_token,
            user_id=user["id"],
            device_id=device_id,
            expires_in=refresh_token_expires,
        )
        
        # Create device-bound encryption key (2-min rotation, 256-bit, Argon2id)
        device_seed = await create_device_seed_for_user(user["id"], device_id)
        device_key_blob = encrypt_seed_for_device_download(device_seed, user_data.password)
        device_seed = b"\x00" * len(device_seed)

        # Optional: store SSH public key for browser-only login (no device_id needed)
        if user_data.ssh_public_key:
            try:
                from app.services.ssh_key_service import store_ssh_key
                await store_ssh_key(int(user["id"]), user_data.ssh_public_key)
            except ValueError as e:
                logger.warning(f"SSH key not stored at registration: {e}")
            except Exception as e:
                logger.warning(f"SSH key storage failed (non-fatal): {e}")
        
        await security.log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            identifier=user_data.email,
            user_id=user["id"],
            ip_address=client_ip,
            action="register",
            metadata={"device_id": device_id},
            success=True,
        )
        
        logger.info(f"User registered and logged in: {user_data.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_token_expires.total_seconds()),
            device_id=device_id,
            device_key_download=device_key_blob,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/device-key/download")
async def download_device_key(
    data: DeviceKeyDownloadRequest,
    request: Request,
):
    """
    Download encrypted device key. Save to device - required for login.
    For existing users who don't have device key yet.
    """
    user = await get_user_by_email(data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    seed = await get_device_seed(user["id"], data.device_id)
    if not seed:
        seed = await create_device_seed_for_user(user["id"], data.device_id)
    blob = encrypt_seed_for_device_download(seed, data.password)
    seed = b"\x00" * len(seed)
    return {"device_key_download": blob, "device_id": data.device_id}


# --- SSH key endpoints (browser-only login, no device_id) ---

@router.post("/login/ssh/challenge", response_model=SSHChallengeResponse)
async def ssh_login_challenge(data: SSHChallengeRequest):
    """
    Get challenge for SSH key login (browser only).
    User must have registered an SSH public key. Challenge expires in 2 min.
    """
    from app.services.ssh_key_service import get_ssh_key_by_email, store_ssh_challenge

    key_info = await get_ssh_key_by_email(data.email)
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SSH key registered for this email. Add one via settings or register with ssh_public_key.",
        )
    challenge = secrets.token_urlsafe(32)
    await store_ssh_challenge(data.email, challenge)
    return SSHChallengeResponse(challenge=challenge, expires_in_seconds=120)


@router.post("/login/ssh", response_model=TokenResponse)
async def ssh_login(
    data: SSHLoginRequest,
    request: Request,
):
    """
    Login with SSH key (browser only). No device_id required.
    Requires prior POST /auth/login/ssh/challenge. Sign challenge with private key, send signature.
    """
    from app.services.ssh_key_service import (
        get_ssh_key_by_email,
        get_and_consume_ssh_challenge,
        verify_ssh_signature,
    )

    key_info = await get_ssh_key_by_email(data.email)
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No SSH key registered for this email",
        )
    user_id, _, _ = key_info

    challenge = await get_and_consume_ssh_challenge(data.email)
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired challenge. Request new challenge.",
        )

    if not await verify_ssh_signature(user_id, challenge, data.signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature verification failed",
        )

    user = await get_user_by_email(data.email)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    device_id = f"ssh-browser-{generate_token_jti()}"
    access_jti = generate_token_jti()
    refresh_jti = generate_token_jti()
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        data={
            "sub": user["id"],
            "email": user["email"],
            "jti": access_jti,
            "device_id": device_id,
        },
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        data={
            "sub": user["id"],
            "email": user["email"],
            "jti": refresh_jti,
            "device_id": device_id,
        },
    )
    await store_refresh_token(
        refresh_token=refresh_token,
        user_id=user["id"],
        device_id=device_id,
        expires_in=refresh_token_expires,
    )

    security = get_security_service()
    client_ip = request.client.host if request.client else "unknown"
    await security.log_security_event(
        SecurityEvent.LOGIN_SUCCESS,
        identifier=data.email,
        user_id=user["id"],
        ip_address=client_ip,
        action="ssh_login",
        metadata={"device_id": device_id},
        success=True,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_token_expires.total_seconds()),
        device_id=device_id,
    )


@router.post("/login/challenge", response_model=LoginChallengeResponse)
async def login_challenge(data: LoginChallengeRequest):
    """
    Get challenge for device-bound login. Call before login.
    Challenge expires in 2 minutes.
    """
    challenge = secrets.token_urlsafe(32)
    await store_challenge(data.email, data.device_id, challenge)
    return LoginChallengeResponse(
        challenge=challenge,
        time_slot=get_current_time_slot(),
        expires_in_seconds=120,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
):
    """
    Login with email and password (legacy - no device proof).
    Use /login/secure for device-bound login.
    """
    return await _do_login(
        email=credentials.email,
        password=credentials.password,
        device_id=credentials.device_id,
        challenge=None,
        proof=None,
        time_slot=None,
        request=request,
        device_key_fingerprint=credentials.device_key_fingerprint,
        device_key_algorithm=credentials.device_key_algorithm,
    )


@router.post("/login/secure", response_model=TokenResponse)
async def login_secure(
    data: LoginWithDeviceRequest,
    request: Request,
):
    """
    Login with device-bound proof. Requires device key (from register or download).
    Key rotates every 2 min - device derives current key from stored seed.
    """
    return await _do_login(
        email=data.email,
        password=data.password,
        device_id=data.device_id,
        challenge=data.challenge,
        proof=data.proof,
        time_slot=data.time_slot,
        request=request,
    )


async def _do_login(
    email: str,
    password: str,
    device_id: Optional[str],
    challenge: Optional[str],
    proof: Optional[str],
    time_slot: Optional[int],
    request: Request,
    device_key_fingerprint: Optional[str] = None,
    device_key_algorithm: Optional[str] = None,
) -> TokenResponse:
    """Shared login logic."""
    security = get_security_service()
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{email}:{client_ip}"
    
    try:
        try:
            await security.check_brute_force(
                identifier=identifier,
                max_attempts=5,
                window_seconds=3600,
                lockout_seconds=3600,
                action="login",
            )
        except BruteForceError as e:
            await security.log_security_event(
                SecurityEvent.BRUTE_FORCE_DETECTED,
                identifier=email,
                ip_address=client_ip,
                action="login",
                metadata={"reason": "too_many_attempts"},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
            )
        
        user = await get_user_by_email(email)
        if not user:
            await security.record_failed_attempt(identifier=identifier, action="login")
            await security.log_security_event(
                SecurityEvent.LOGIN_FAILURE,
                identifier=email,
                ip_address=client_ip,
                action="login",
                metadata={"reason": "user_not_found"},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password(password, user["hashed_password"]):
            await security.record_failed_attempt(identifier=identifier, action="login")
            await security.log_security_event(
                SecurityEvent.LOGIN_FAILURE,
                identifier=email,
                user_id=user["id"],
                ip_address=client_ip,
                action="login",
                metadata={"reason": "invalid_password"},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Device proof required if user has device seed (from register or download)
        has_device_seed = await user_has_any_device_seed(user["id"])
        if has_device_seed:
            if not device_id or len(device_id) < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="device_id required. Use the device_id from your device key.",
                )
            if not challenge or not proof:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Device-bound login required. 1) POST /auth/login/challenge 2) Derive key from device seed + time_slot 3) POST /auth/login/secure with proof=HMAC(key,challenge)",
                )
            stored_challenge = await get_and_consume_challenge(email, device_id)
            if not stored_challenge or stored_challenge != challenge:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired challenge. Request new challenge.",
                )
            if not await verify_device_login_proof(user["id"], device_id, challenge, proof, time_slot):
                await security.record_failed_attempt(identifier=identifier, action="login")
                seed_for_device = await get_device_seed(user["id"], device_id)
                detail = (
                    "No device key for this device. Download at POST /auth/device-key/download"
                    if seed_for_device is None
                    else "Device verification failed. Key rotates every 2 min - sync time with server."
                )
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        
        await security.reset_brute_force_counter(identifier, action="login")
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )
        
        device_id = device_id or generate_token_jti()
        
        # Generate token JTIs
        access_jti = generate_token_jti()
        refresh_jti = generate_token_jti()
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={
                "sub": user["id"],
                "email": user["email"],
                "jti": access_jti,
                "device_id": device_id,
            },
            expires_delta=access_token_expires,
        )
        
        refresh_token = create_refresh_token(
            data={
                "sub": user["id"],
                "email": user["email"],
                "jti": refresh_jti,
                "device_id": device_id,
            }
        )
        
        # Store refresh token metadata
        await store_refresh_token(
            refresh_token=refresh_token,
            user_id=user["id"],
            device_id=device_id,
            expires_in=refresh_token_expires,
        )
        
        # Store or replace device encryption key fingerprint on every login
        if device_key_fingerprint and device_id:
            try:
                redis = await get_redis()
                device_key_fingerprint_key = f"{REDIS_DEVICE_KEY_FINGERPRINT_PREFIX}{user['id']}:{device_id}"
                
                fingerprint_data = {
                    "device_id": device_id,
                    "key_fingerprint": device_key_fingerprint,
                    "key_algorithm": device_key_algorithm or "AES-256-GCM",
                    "registered_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "user_email": user["email"],
                }
                
                import json
                # Store or replace (set will overwrite if exists)
                await redis.set(
                    device_key_fingerprint_key,
                    json.dumps(fingerprint_data)
                )
                
                # Also store in device list for user
                user_devices_key = f"{REDIS_DEVICE_PREFIX}{user['id']}:devices"
                await redis.sadd(user_devices_key, device_id)
                
                logger.info(
                    f"Device encryption key fingerprint stored/replaced on login: "
                    f"user={email}, device_id={device_id[:8]}..."
                )
            except Exception as e:
                # Log error but don't fail login if device key storage fails
                logger.warning(
                    f"Failed to store device key fingerprint on login (non-fatal): {e}",
                    exc_info=True
                )
        
        # Log successful login
        await security.log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            identifier=email,
            user_id=user["id"],
            ip_address=client_ip,
            action="login",
            metadata={
                "device_id": device_id,
                "device_key_stored": bool(device_key_fingerprint),
            },
            success=True,
        )
        
        logger.info(f"User logged in: {email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_token_expires.total_seconds()),
            device_id=device_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: RefreshTokenRequest,
):
    """
    Refresh access token using refresh token.
    
    Implements token rotation: old refresh token is revoked and a new one is issued.
    """
    try:
        # Decode refresh token
        try:
            payload = decode_token(token_data.refresh_token)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        
        # Check if token is revoked
        token_jti = payload.get("jti")
        user_id = payload.get("sub")
        if await is_token_revoked(token_jti, user_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )
        
        # Verify refresh token exists in Redis (for rotation)
        refresh_metadata = await get_refresh_token_metadata(token_data.refresh_token)
        if not refresh_metadata:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or expired",
            )
        
        # Verify device binding
        if not await verify_device_binding(token_data.device_id, payload):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device binding mismatch",
            )
        
        # Get user ID from token
        user_id = payload.get("sub")
        email = payload.get("email")
        device_id = token_data.device_id or payload.get("device_id") or generate_token_jti()
        
        # Revoke old refresh token (token rotation)
        if REFRESH_TOKEN_ROTATION_ENABLED:
            await revoke_refresh_token(token_data.refresh_token)
            if token_jti:
                await revoke_token(token_jti, expires_in=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
        
        # Generate new tokens
        access_jti = generate_token_jti()
        refresh_jti = generate_token_jti()
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": email,
                "jti": access_jti,
                "device_id": device_id,
            },
            expires_delta=access_token_expires,
        )
        
        # Generate new refresh token (token rotation)
        new_refresh_token = create_refresh_token(
            data={
                "sub": user_id,
                "email": email,
                "jti": refresh_jti,
                "device_id": device_id,
            }
        )
        
        # Store new refresh token
        await store_refresh_token(
            refresh_token=new_refresh_token,
            user_id=user_id,
            device_id=device_id,
            expires_in=refresh_token_expires,
        )
        
        logger.info(f"Tokens refreshed for user: {user_id}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=int(access_token_expires.total_seconds()),
            device_id=device_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    logout_data: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Logout and revoke tokens.
    
    If `refresh_token` is provided, revokes that refresh token.
    If `all_devices` is True, revokes all tokens for the user.
    """
    try:
        # Decode access token
        try:
            token = credentials.credentials
            payload = decode_token(token)
        except (ValueError, JWTError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
            )
        
        user_id = payload.get("sub")
        token_jti = payload.get("jti")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # Revoke access token
        if token_jti:
            await revoke_token(token_jti, expires_in=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        
        # Revoke refresh token if provided
        if logout_data.refresh_token:
            await revoke_refresh_token(logout_data.refresh_token)
            refresh_payload = decode_token(logout_data.refresh_token)
            refresh_jti = refresh_payload.get("jti")
            if refresh_jti:
                await revoke_token(refresh_jti, expires_in=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
        
        # Revoke all tokens if requested
        if logout_data.all_devices:
            await revoke_all_user_tokens(user_id)
        
        logger.info(f"User logged out: {user_id}")
        
        return {"message": "Successfully logged out"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# Dependency for protected routes
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.
    
    Usage:
        @router.get("/protected")
        async def protected_route(current_user = Depends(get_current_user)):
            return {"user_id": current_user["id"]}
    """
    try:
        token = credentials.credentials
        
        # Check if token is revoked
        try:
            payload = decode_token(token)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_jti = payload.get("jti")
        user_id = payload.get("sub")
        if await is_token_revoked(token_jti, user_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # Get user from database
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/ssh-key/add")
async def add_ssh_key(
    data: SSHKeyAddRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Add SSH public key for browser login. Requires Bearer token.
    Key is stored encrypted; only server can decrypt for verification.
    """
    try:
        from app.services.ssh_key_service import store_ssh_key
        fingerprint = await store_ssh_key(int(current_user["id"]), data.ssh_public_key)
        return {"fingerprint": fingerprint, "message": "SSH key added successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"SSH key add failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add SSH key")


@router.post("/device/register-key", response_model=DeviceEncryptionKeyResponse)
async def register_device_encryption_key(
    key_data: DeviceEncryptionKeyRegister,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Register device encryption key fingerprint.
    
    IMPORTANT: This endpoint only stores a fingerprint/hash of the encryption key,
    NEVER the actual encryption key. The actual key is generated and stored
    client-side only (on first app launch) and never transmitted to the server.
    
    The fingerprint is used for:
    - Verifying device identity
    - Ensuring key consistency across sessions
    - Security auditing
    
    The server cannot decrypt any content encrypted with this key.
    """
    try:
        user_id = current_user.get("id")
        user_email = current_user.get("email")
        
        # Store device key fingerprint (not the actual key)
        redis = await get_redis()
        device_key_fingerprint_key = f"{REDIS_DEVICE_KEY_FINGERPRINT_PREFIX}{user_id}:{key_data.device_id}"
        
        fingerprint_data = {
            "device_id": key_data.device_id,
            "key_fingerprint": key_data.key_fingerprint,
            "key_algorithm": key_data.key_algorithm,
            "registered_at": datetime.utcnow().isoformat(),
            "user_email": user_email,
        }
        
        import json
        await redis.set(
            device_key_fingerprint_key,
            json.dumps(fingerprint_data)
        )
        
        # Also store in device list for user
        user_devices_key = f"{REDIS_DEVICE_PREFIX}{user_id}:devices"
        await redis.sadd(user_devices_key, key_data.device_id)
        
        logger.info(
            f"Device encryption key fingerprint registered: "
            f"user={user_email}, device_id={key_data.device_id[:8]}..."
        )
        
        return DeviceEncryptionKeyResponse(
            device_id=key_data.device_id,
            registered=True,
            message="Device encryption key fingerprint registered successfully. The actual key remains on your device and is never transmitted to the server."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device key registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device encryption key"
        )


@router.get("/device/key-info/{device_id}", response_model=Dict[str, Any])
async def get_device_key_info(
    device_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get device encryption key fingerprint information.
    
    Returns only the fingerprint (hash) of the key, never the actual key.
    Used for verification and security auditing.
    """
    try:
        user_id = current_user.get("id")
        
        redis = await get_redis()
        device_key_fingerprint_key = f"{REDIS_DEVICE_KEY_FINGERPRINT_PREFIX}{user_id}:{device_id}"
        
        fingerprint_json = await redis.get(device_key_fingerprint_key)
        if not fingerprint_json:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device encryption key fingerprint not found"
            )
        
        import json
        fingerprint_data = json.loads(fingerprint_json)
        
        # Return only fingerprint info, never the actual key
        return {
            "device_id": fingerprint_data.get("device_id"),
            "key_fingerprint": fingerprint_data.get("key_fingerprint"),
            "key_algorithm": fingerprint_data.get("key_algorithm"),
            "registered_at": fingerprint_data.get("registered_at"),
            "note": "This is only a fingerprint/hash of your encryption key. The actual key is stored only on your device and never transmitted to the server."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get device key info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device key information"
        )

