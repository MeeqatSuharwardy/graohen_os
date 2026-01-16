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
from app.core.database import get_db
from app.core.security_hardening import (
    get_security_service,
    SecurityEvent,
    BruteForceError,
)
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Redis key prefixes
REDIS_TOKEN_REVOKED_PREFIX = "auth:revoked:"
REDIS_REFRESH_TOKEN_PREFIX = "auth:refresh:"
REDIS_DEVICE_PREFIX = "auth:device:"

# Token rotation settings
REFRESH_TOKEN_ROTATION_ENABLED = True


# Pydantic Models
class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    device_id: Optional[str] = Field(None, max_length=255, description="Device identifier for device binding")
    
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


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    device_id: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str
    device_id: Optional[str] = Field(None, max_length=255)


class LogoutRequest(BaseModel):
    """Logout request"""
    refresh_token: Optional[str] = None
    all_devices: bool = False


# Temporary User model (until database models are defined)
# This is a simple in-memory store for demonstration
# In production, replace with proper database model
_users_db: Dict[str, Dict[str, Any]] = {}


async def get_user_by_email(email: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """
    Get user by email.
    
    TODO: Replace with proper database query when User model is available.
    """
    # Temporary implementation using in-memory store
    return _users_db.get(email.lower())
    
    # Future implementation:
    # from app.models.user import User
    # result = await db.execute(select(User).where(User.email == email.lower()))
    # user = result.scalar_one_or_none()
    # return user


async def create_user(email: str, password: str, full_name: Optional[str] = None, db: AsyncSession = None) -> Dict[str, Any]:
    """
    Create a new user.
    
    TODO: Replace with proper database insert when User model is available.
    """
    # Check if user exists
    existing = await get_user_by_email(email, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = hash_password(password)
    
    # Create user record
    user = {
        "id": secrets.token_urlsafe(16),
        "email": email.lower(),
        "hashed_password": hashed_password,
        "full_name": full_name,
        "created_at": datetime.utcnow(),
        "is_active": True,
    }
    
    # Store user (temporary - replace with database)
    _users_db[email.lower()] = user
    
    logger.info(f"User registered: {email}")
    return user


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
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    
    Creates a new user account and returns access and refresh tokens.
    """
    security = get_security_service()
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Rate limit registration attempts
        await security.check_rate_limit(
            identifier=client_ip,
            max_requests=5,  # 5 registrations per hour per IP
            window_seconds=3600,
            action="register",
        )
        
        # Create user
        user = await create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            db=db,
        )
        
        # Generate device ID if not provided
        device_id = user_data.device_id or generate_token_jti()
        
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
        
        # Store refresh token metadata in Redis
        await store_refresh_token(
            refresh_token=refresh_token,
            user_id=user["id"],
            device_id=device_id,
            expires_in=refresh_token_expires,
        )
        
        # Log registration event
        await security.log_security_event(
            SecurityEvent.LOGIN_SUCCESS,  # Using available event
            identifier=user_data.email,
            user_id=user["id"],
            ip_address=client_ip,
            action="register",
            metadata={"device_id": user_data.device_id},
            success=True,
        )
        
        logger.info(f"User registered and logged in: {user_data.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_token_expires.total_seconds()),
            device_id=device_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.
    
    Returns access and refresh tokens.
    """
    security = get_security_service()
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{credentials.email}:{client_ip}"
    
    try:
        # Check brute force protection
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
                identifier=credentials.email,
                ip_address=client_ip,
                action="login",
                metadata={"reason": "too_many_attempts"},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
            )
        
        # Get user
        user = await get_user_by_email(credentials.email, db)
        if not user:
            # Record failed attempt
            remaining = await security.record_failed_attempt(
                identifier=identifier,
                action="login",
            )
            await security.log_security_event(
                SecurityEvent.LOGIN_FAILURE,
                identifier=credentials.email,
                ip_address=client_ip,
                action="login",
                metadata={"reason": "user_not_found", "attempts_remaining": remaining},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(credentials.password, user["hashed_password"]):
            # Record failed attempt
            remaining = await security.record_failed_attempt(
                identifier=identifier,
                action="login",
            )
            await security.log_security_event(
                SecurityEvent.LOGIN_FAILURE,
                identifier=credentials.email,
                user_id=user["id"],
                ip_address=client_ip,
                action="login",
                metadata={"reason": "invalid_password", "attempts_remaining": remaining},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Reset brute force counter on success
        await security.reset_brute_force_counter(identifier, action="login")
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )
        
        # Generate or use device ID
        device_id = credentials.device_id or generate_token_jti()
        
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
        
        # Log successful login
        await security.log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            identifier=credentials.email,
            user_id=user["id"],
            ip_address=client_ip,
            action="login",
            metadata={"device_id": credentials.device_id},
            success=True,
        )
        
        logger.info(f"User logged in: {credentials.email}")
        
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
    db: AsyncSession = Depends(get_db),
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
        user = await get_user_by_email(email, db)
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

