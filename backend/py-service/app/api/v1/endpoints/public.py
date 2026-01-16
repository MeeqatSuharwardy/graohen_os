"""Public viewer endpoints for encrypted content"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import logging

from app.config import settings
from app.core.redis_client import get_redis
from app.services.email_service import get_email_service
from app.core.encryption import decrypt_bytes, EncryptionError
from app.core.key_manager import derive_key_from_passcode

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting for public unlock
REDIS_PUBLIC_RATE_LIMIT_PREFIX = "public:rate_limit:"
MAX_UNLOCK_ATTEMPTS = 5
UNLOCK_RATE_LIMIT_WINDOW = 3600  # 1 hour
LOCKOUT_DURATION = 3600  # 1 hour lockout

# Session key storage (for device-local storage)
REDIS_SESSION_KEY_PREFIX = "session:key:"
SESSION_KEY_EXPIRE_HOURS = 24 * 7  # 7 days


class UnlockRequest(BaseModel):
    """Unlock request"""
    passcode: str = Field(..., min_length=1)


async def check_rate_limit(identifier: str, max_attempts: int, window_seconds: int) -> bool:
    """Check if identifier has exceeded rate limit"""
    redis = await get_redis()
    key = f"{REDIS_PUBLIC_RATE_LIMIT_PREFIX}{identifier}"
    
    current_count = await redis.get(key)
    
    if current_count is None:
        await redis.setex(key, window_seconds, "1")
        return True
    
    count = int(current_count)
    
    if count >= max_attempts:
        ttl = await redis.ttl(key)
        if ttl > 0:
            return False
        else:
            await redis.setex(key, window_seconds, "1")
            return True
    
    await redis.incr(key)
    await redis.expire(key, window_seconds)
    return True


async def increment_unlock_attempt(token: str) -> int:
    """Increment unlock attempt counter"""
    redis = await get_redis()
    key = f"{REDIS_PUBLIC_RATE_LIMIT_PREFIX}{token}"
    
    current_count = await redis.incr(key)
    
    if current_count == 1:
        await redis.expire(key, UNLOCK_RATE_LIMIT_WINDOW)
    
    if current_count >= MAX_UNLOCK_ATTEMPTS:
        await redis.expire(key, LOCKOUT_DURATION)
    
    return current_count


async def get_unlock_attempts_remaining(token: str) -> int:
    """Get remaining unlock attempts"""
    redis = await get_redis()
    key = f"{REDIS_PUBLIC_RATE_LIMIT_PREFIX}{token}"
    
    current_count = await redis.get(key)
    if current_count is None:
        return MAX_UNLOCK_ATTEMPTS
    
    count = int(current_count)
    
    if count >= MAX_UNLOCK_ATTEMPTS:
        ttl = await redis.ttl(key)
        if ttl > 0:
            return 0
    
    return max(0, MAX_UNLOCK_ATTEMPTS - count)


async def reset_unlock_attempts(token: str) -> None:
    """Reset unlock attempt counter"""
    redis = await get_redis()
    key = f"{REDIS_PUBLIC_RATE_LIMIT_PREFIX}{token}"
    await redis.delete(key)


async def store_session_key(token: str, session_key: bytes, expires_in_hours: int = SESSION_KEY_EXPIRE_HOURS) -> None:
    """Store session key for device-local access"""
    redis = await get_redis()
    key = f"{REDIS_SESSION_KEY_PREFIX}{token}"
    
    # Encrypt session key with a device-specific key (in production, use device key)
    # For now, store base64-encoded
    session_key_b64 = base64.b64encode(session_key).decode("utf-8")
    
    expires_in_seconds = expires_in_hours * 3600
    await redis.setex(key, expires_in_seconds, session_key_b64)


async def get_session_key(token: str) -> Optional[bytes]:
    """Get session key for device"""
    redis = await get_redis()
    key = f"{REDIS_SESSION_KEY_PREFIX}{token}"
    
    session_key_b64 = await redis.get(key)
    if not session_key_b64:
        return None
    
    try:
        return base64.b64decode(session_key_b64)
    except Exception:
        return None


@router.get("/view/{token}", response_class=HTMLResponse)
async def view_encrypted_content(
    token: str,
    request: Request,
):
    """
    Serve HTML viewer page for encrypted content.
    
    This page handles client-side decryption using WebCrypto API.
    No plaintext is ever rendered on the server.
    """
    try:
        # Get content metadata to determine if passcode is required
        email_service = get_email_service()
        
        # Try to get metadata (for emails) or file metadata (for files)
        from app.api.v1.endpoints.drive import get_file_metadata
        from app.services.email_service import REDIS_ACCESS_TOKEN_PREFIX
        
        redis = await get_redis()
        
        # Check if it's an email token
        email_metadata_key = f"{REDIS_ACCESS_TOKEN_PREFIX}{token}"
        email_metadata_json = await redis.get(email_metadata_key)
        
        # Check if it's a file token
        file_metadata = await get_file_metadata(token)
        
        content_type = None
        requires_passcode = False
        
        if email_metadata_json:
            import json
            try:
                email_metadata = json.loads(email_metadata_json)
                requires_passcode = email_metadata.get("has_passcode", False)
                content_type = "email"
            except json.JSONDecodeError:
                pass
        elif file_metadata:
            requires_passcode = file_metadata.get("passcode_protected", False)
            content_type = "file"
        else:
            # Token not found
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Content Not Found</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .error { color: #d32f2f; }
                    </style>
                </head>
                <body>
                    <h1 class="error">Content Not Found</h1>
                    <p>The requested content was not found or has expired.</p>
                </body>
                </html>
                """,
                status_code=404
            )
        
        # Get rate limit status
        attempts_remaining = await get_unlock_attempts_remaining(token)
        is_locked = attempts_remaining == 0
        
        # Serve HTML viewer
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Viewer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        .passcode-form {{
            display: none;
        }}
        .passcode-form.active {{
            display: block;
        }}
        .input-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }}
        input[type="password"] {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }}
        input[type="password"]:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .error-message {{
            color: #d32f2f;
            font-size: 14px;
            margin-top: 8px;
            display: none;
        }}
        .error-message.show {{
            display: block;
        }}
        .rate-limit-info {{
            color: #f57c00;
            font-size: 12px;
            margin-top: 8px;
        }}
        .locked-message {{
            color: #d32f2f;
            background: #ffebee;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        button {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        button:hover:not(:disabled) {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}
        .content-viewer {{
            display: none;
        }}
        .content-viewer.active {{
            display: block;
        }}
        .content-display {{
            background: #f5f5f5;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 500px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.6;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        .spinner {{
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .biometric-prompt {{
            margin-top: 20px;
            padding: 16px;
            background: #e3f2fd;
            border-radius: 8px;
            text-align: center;
        }}
        .biometric-button {{
            background: #2196f3;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Secure Viewer</h1>
        <p class="subtitle">View encrypted content securely</p>
        
        <div id="lockedMessage" class="locked-message" style="display: {'block' if is_locked else 'none'};">
            <strong>⚠️ Too Many Failed Attempts</strong><br>
            This content is temporarily locked. Please try again later.
        </div>
        
        <div id="passcodeForm" class="passcode-form {'active' if requires_passcode and not is_locked else ''}">
            <form id="unlockForm" onsubmit="handleUnlock(event)">
                <div class="input-group">
                    <label for="passcode">Enter Passcode</label>
                    <input type="password" id="passcode" name="passcode" required autocomplete="off" autofocus>
                    <div id="errorMessage" class="error-message"></div>
                    <div id="rateLimitInfo" class="rate-limit-info"></div>
                </div>
                <button type="submit" id="unlockButton">Unlock Content</button>
            </form>
            
            <div class="biometric-prompt" id="biometricPrompt" style="display: none;">
                <p>Use device biometrics to unlock</p>
                <button type="button" class="biometric-button" onclick="requestBiometric()">
                    🔐 Use Biometric
                </button>
            </div>
        </div>
        
        <div id="contentViewer" class="content-viewer">
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Decrypting content...</p>
            </div>
            <div id="contentDisplay" class="content-display" style="display: none;"></div>
        </div>
    </div>
    
    <script>
        const token = '{token}';
        const requiresPasscode = {str(requires_passcode).lower()};
        const contentType = '{content_type}';
        let decryptedContent = null;
        let sessionKey = null;
        
        // Check for stored session key in localStorage
        const storedSessionKey = localStorage.getItem(`session_key_${{token}}`);
        if (storedSessionKey) {{
            try {{
                sessionKey = storedSessionKey; // Already base64 string, no need to parse
                // If we have a session key and no passcode required, decrypt immediately
                if (!requiresPasscode) {{
                    loadAndDecryptContent();
                }}
            }} catch (e) {{
                console.error('Failed to parse stored session key:', e);
            }}
        }}
        
        // Check for biometric support
        if ('credentials' in navigator && 'get' in navigator.credentials) {{
            document.getElementById('biometricPrompt').style.display = 'block';
        }}
        
        async function requestBiometric() {{
            try {{
                // Request credential (biometric authentication)
                const credential = await navigator.credentials.get({{
                    publicKey: {{
                        challenge: new Uint8Array(32),
                        allowCredentials: [],
                        userVerification: 'required'
                    }}
                }});
                
                // If biometric succeeds, try to get session key
                const sessionKeyResponse = await fetch(`/api/v1/public/session/${{token}}`, {{
                    method: 'GET',
                    headers: {{
                        'Authorization': 'Bearer ' + credential.id
                    }}
                }});
                
                if (sessionKeyResponse.ok) {{
                    const data = await sessionKeyResponse.json();
                    sessionKey = data.session_key; // Base64 string
                    localStorage.setItem(`session_key_${{token}}`, sessionKey);
                    loadAndDecryptContent();
                }}
            }} catch (error) {{
                console.error('Biometric authentication failed:', error);
                alert('Biometric authentication failed. Please use passcode.');
            }}
        }}
        
        async function handleUnlock(event) {{
            event.preventDefault();
            
            const passcode = document.getElementById('passcode').value;
            const errorDiv = document.getElementById('errorMessage');
            const rateLimitDiv = document.getElementById('rateLimitInfo');
            const unlockButton = document.getElementById('unlockButton');
            
            errorDiv.textContent = '';
            errorDiv.classList.remove('show');
            unlockButton.disabled = true;
            unlockButton.textContent = 'Unlocking...';
            
            try {{
                const response = await fetch(`/api/v1/public/unlock/${{token}}`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{ passcode }})
                }});
                
                const data = await response.json();
                
                if (response.ok) {{
                    // Store session key locally (device storage)
                    // This key can be accessed later with device biometrics
                    if (data.session_key) {{
                        sessionKey = data.session_key; // Base64 string
                        localStorage.setItem(`session_key_${{token}}`, sessionKey);
                        
                        // For Google Pixel / Android: Store in Android Keystore via Web API
                        // This would require a native app or PWA with WebAuthn
                        if ('credentials' in navigator && 'store' in navigator.credentials) {{
                            // Store credential for biometric access
                            try {{
                                await navigator.credentials.create({{
                                    publicKey: {{
                                        challenge: new Uint8Array(32),
                                        rp: {{ name: 'Secure Drive' }},
                                        user: {{
                                            id: new TextEncoder().encode(token),
                                            name: token,
                                            displayName: 'Session Key'
                                        }},
                                        pubKeyCredParams: [{{alg: -7, type: 'public-key'}}],
                                        authenticatorSelection: {{
                                            authenticatorAttachment: 'platform',
                                            userVerification: 'required'
                                        }},
                                        timeout: 60000,
                                        attestation: 'none'
                                    }}
                                }});
                            }} catch (e) {{
                                console.log('Biometric storage not available:', e);
                            }}
                        }}
                    }}
                    
                    // Decrypt and display content
                    await loadAndDecryptContent(data.encrypted_data);
                    
                    // Hide passcode form
                    document.getElementById('passcodeForm').classList.remove('active');
                }} else {{
                    errorDiv.textContent = data.detail || data.message || 'Unlock failed';
                    errorDiv.classList.add('show');
                    
                    if (data.attempts_remaining !== undefined) {{
                        rateLimitDiv.textContent = `${{data.attempts_remaining}} attempts remaining`;
                    }}
                    
                    if (data.attempts_remaining === 0) {{
                        document.getElementById('lockedMessage').style.display = 'block';
                        document.getElementById('passcodeForm').style.display = 'none';
                    }}
                }}
            }} catch (error) {{
                errorDiv.textContent = 'Network error. Please try again.';
                errorDiv.classList.add('show');
            }} finally {{
                unlockButton.disabled = false;
                unlockButton.textContent = 'Unlock Content';
            }}
        }}
        
        async function loadAndDecryptContent(encryptedData = null) {{
            document.getElementById('contentViewer').classList.add('active');
            document.getElementById('loading').style.display = 'block';
            document.getElementById('contentDisplay').style.display = 'none';
            
            try {{
                // If encrypted data not provided, fetch it
                if (!encryptedData) {{
                    const response = await fetch(`/api/v1/public/data/${{token}}`);
                    if (!response.ok) {{
                        throw new Error('Failed to fetch encrypted data');
                    }}
                    encryptedData = await response.json();
                }}
                
                // Decrypt using WebCrypto API
                const decrypted = await decryptWithWebCrypto(
                    encryptedData.encrypted_content,
                    encryptedData.encrypted_content_key,
                    sessionKey
                );
                
                decryptedContent = decrypted;
                
                // Display content
                document.getElementById('loading').style.display = 'none';
                document.getElementById('contentDisplay').textContent = decrypted;
                document.getElementById('contentDisplay').style.display = 'block';
                
            }} catch (error) {{
                console.error('Decryption failed:', error);
                document.getElementById('loading').innerHTML = 
                    '<p style="color: #d32f2f;">Failed to decrypt content. Please try again.</p>';
            }}
        }}
        
        async function decryptWithWebCrypto(encryptedContent, encryptedContentKey, sessionKey) {{
            // If session key provided, use it directly (it's the content key)
            if (sessionKey) {{
                const keyData = base64ToArrayBuffer(sessionKey);
                const contentKey = await crypto.subtle.importKey(
                    'raw',
                    keyData,
                    {{ name: 'AES-GCM' }},
                    false,
                    ['decrypt']
                );
                
                // Decrypt content directly with session key
                const decrypted = await decryptAESGCM(
                    base64ToArrayBuffer(encryptedContent.ciphertext),
                    base64ToArrayBuffer(encryptedContent.nonce),
                    base64ToArrayBuffer(encryptedContent.tag),
                    contentKey
                );
                
                return new TextDecoder().decode(decrypted);
            }}
            
            // Otherwise, decrypt content key first (for passcode-protected)
            // This requires server-side decryption of content key
            // For now, return error - should use unlock endpoint first
            throw new Error('Session key required. Please unlock first.');
        }}
        
        async function decryptAESGCM(ciphertext, nonce, tag, key) {{
            // Combine ciphertext and tag for GCM
            const combined = new Uint8Array(ciphertext.length + tag.length);
            combined.set(new Uint8Array(ciphertext), 0);
            combined.set(new Uint8Array(tag), ciphertext.length);
            
            try {{
                const decrypted = await crypto.subtle.decrypt(
                    {{
                        name: 'AES-GCM',
                        iv: nonce,
                        tagLength: 128
                    }},
                    key,
                    combined
                );
                return new Uint8Array(decrypted);
            }} catch (error) {{
                throw new Error('Decryption failed: ' + error.message);
            }}
        }}
        
        function base64ToArrayBuffer(base64) {{
            const binary = atob(base64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {{
                bytes[i] = binary.charCodeAt(i);
            }}
            return bytes.buffer;
        }}
        
        // Auto-load if no passcode required
        if (!requiresPasscode && !is_locked) {{
            loadAndDecryptContent();
        }}
    </script>
</body>
</html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Viewer page generation failed: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Failed to load viewer: {str(e)}</p></body></html>",
            status_code=500
        )


@router.post("/unlock/{token}")
async def unlock_public_content(
    token: str,
    unlock_data: UnlockRequest,
):
    """
    Unlock encrypted content with passcode.
    
    Returns encrypted data and session key for client-side decryption.
    No plaintext is ever sent from server.
    """
    try:
        # Check rate limit
        attempts_remaining = await get_unlock_attempts_remaining(token)
        
        if attempts_remaining == 0:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too many unlock attempts",
                    "message": "Content is temporarily locked. Please try again later.",
                    "lockout_duration_seconds": LOCKOUT_DURATION,
                }
            )
        
        # Get encrypted data
        redis = await get_redis()
        
        # Try email first
        from app.services.email_service import REDIS_EMAIL_PREFIX, REDIS_ACCESS_TOKEN_PREFIX, REDIS_PASSCODE_SALT_PREFIX
        
        email_data_key = f"{REDIS_EMAIL_PREFIX}{token}"
        email_data_json = await redis.get(email_data_key)
        
        # Try file
        from app.api.v1.endpoints.drive import get_encrypted_file, get_file_metadata
        
        file_data = await get_encrypted_file(token)
        file_metadata = await get_file_metadata(token)
        
        encrypted_content = None
        encrypted_content_key = None
        salt_base64 = None
        
        if email_data_json:
            import json
            email_data = json.loads(email_data_json)
            encrypted_content = email_data.get("encrypted_content")
            encrypted_content_key = email_data.get("encrypted_content_key")
            
            # Get salt
            salt_key = f"{REDIS_PASSCODE_SALT_PREFIX}{token}"
            salt_base64 = await redis.get(salt_key)
        elif file_data:
            encrypted_content = file_data.get("encrypted_content")
            encrypted_content_key = file_data.get("encrypted_content_key")
            
            # Get salt
            salt_key = f"drive:passcode_salt:{token}"
            salt_base64 = await redis.get(salt_key)
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Content not found or expired"}
            )
        
        if not encrypted_content or not encrypted_content_key:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Encrypted data not found"}
            )
        
        # Get salt
        if not salt_base64:
            # Try to derive from metadata
            if file_metadata:
                owner_email = file_metadata.get("owner_email")
                if owner_email:
                    from app.core.key_manager import generate_salt_for_identifier
                    salt = generate_salt_for_identifier(owner_email)
                    salt_base64 = base64.b64encode(salt).decode("utf-8")
        
        if not salt_base64:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Passcode salt not found"}
            )
        
        # Derive key from passcode
        salt = base64.b64decode(salt_base64)
        passcode_key = derive_key_from_passcode(unlock_data.passcode, salt)
        
        # Verify passcode by attempting to decrypt content key
        try:
            content_key = decrypt_bytes(encrypted_content_key, passcode_key)
        except Exception:
            # Increment failed attempt
            current_count = await increment_unlock_attempt(token)
            attempts_remaining = max(0, MAX_UNLOCK_ATTEMPTS - current_count)
            
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Incorrect passcode",
                    "attempts_remaining": attempts_remaining,
                    "message": f"Incorrect passcode. {attempts_remaining} attempts remaining." if attempts_remaining > 0 else "Content is now locked due to too many failed attempts."
                }
            )
        
        # Success - reset rate limit
        await reset_unlock_attempts(token)
        
        # Generate session key for device storage
        from app.core.encryption import generate_key
        session_key = generate_key()
        
        # Store session key (encrypted with content key for device access)
        await store_session_key(token, session_key)
        
        # Return encrypted data and session key (base64 encoded for client)
        session_key_b64 = base64.b64encode(session_key).decode("utf-8")
        
        return JSONResponse(content={
            "success": True,
            "encrypted_data": {
                "encrypted_content": encrypted_content,
                "encrypted_content_key": encrypted_content_key,
            },
            "session_key": session_key_b64,  # For device storage
        })
        
    except Exception as e:
        logger.error(f"Public unlock failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Unlock failed", "message": str(e)}
        )


@router.get("/data/{token}")
async def get_encrypted_data(token: str):
    """Get encrypted data for client-side decryption"""
    try:
        redis = await get_redis()
        
        # Try email
        from app.services.email_service import REDIS_EMAIL_PREFIX
        email_data_key = f"{REDIS_EMAIL_PREFIX}{token}"
        email_data_json = await redis.get(email_data_key)
        
        # Try file
        from app.api.v1.endpoints.drive import get_encrypted_file
        
        file_data = await get_encrypted_file(token)
        
        encrypted_content = None
        encrypted_content_key = None
        
        if email_data_json:
            import json
            email_data = json.loads(email_data_json)
            encrypted_content = email_data.get("encrypted_content")
            encrypted_content_key = email_data.get("encrypted_content_key")
        elif file_data:
            encrypted_content = file_data.get("encrypted_content")
            encrypted_content_key = file_data.get("encrypted_content_key")
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Content not found or expired"}
            )
        
        if not encrypted_content or not encrypted_content_key:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Encrypted data not found"}
            )
        
        return JSONResponse(content={
            "encrypted_content": encrypted_content,
            "encrypted_content_key": encrypted_content_key,
        })
        
    except Exception as e:
        logger.error(f"Failed to get encrypted data: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to retrieve encrypted data"}
        )


@router.get("/session/{token}")
async def get_session_key_for_device(token: str):
    """Get session key for device (requires biometric authentication)"""
    try:
        session_key = await get_session_key(token)
        
        if not session_key:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Session key not found or expired"}
            )
        
        # In production, verify biometric authentication here
        # For now, return session key (base64 encoded)
        session_key_b64 = base64.b64encode(session_key).decode("utf-8")
        
        return JSONResponse(content={
            "session_key": session_key_b64,
        })
        
    except Exception as e:
        logger.error(f"Failed to get session key: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to retrieve session key"}
        )

