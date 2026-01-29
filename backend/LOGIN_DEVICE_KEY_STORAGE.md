# Login Device Key Storage

## Overview

Updated the login endpoint to automatically store or replace the device encryption key fingerprint on every successful login. This ensures the device key fingerprint is always up-to-date and synchronized with the server.

## Changes Made

### 1. Updated UserLogin Model

Added optional fields to the login request:

```python
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    device_id: Optional[str] = None
    device_key_fingerprint: Optional[str] = None  # NEW
    device_key_algorithm: Optional[str] = "AES-256-GCM"  # NEW
```

### 2. Updated Login Endpoint

The login endpoint now:
- Accepts optional `device_key_fingerprint` and `device_key_algorithm` in the request
- Automatically stores or replaces the device key fingerprint on every successful login
- Updates the `updated_at` timestamp if the key already exists
- Adds device to user's device list
- Logs the operation (non-fatal if storage fails)

## API Usage

### Request

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@fxmail.ai",
  "password": "user_password",
  "device_id": "device_unique_id",
  "device_key_fingerprint": "sha256_hash_of_device_key",
  "device_key_algorithm": "AES-256-GCM"
}
```

### Response

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "device_id": "device_unique_id"
}
```

## Behavior

### On Every Login

1. **If `device_key_fingerprint` is provided**:
   - Stores the fingerprint in Redis (key: `auth:device_key:{user_id}:{device_id}`)
   - If fingerprint already exists, it is **replaced** with the new one
   - Updates `updated_at` timestamp
   - Adds device to user's device list

2. **If `device_key_fingerprint` is NOT provided**:
   - Login proceeds normally
   - No device key fingerprint is stored/updated

### Key Points

- ✅ **Automatic**: No separate API call needed - happens during login
- ✅ **Replace on Login**: Key fingerprint is replaced/updated on every login
- ✅ **Non-Fatal**: If storage fails, login still succeeds (error is logged)
- ✅ **Secure**: Only fingerprint/hash is stored, never the actual key
- ✅ **Timestamped**: Both `registered_at` and `updated_at` are tracked

## Example Usage

### cURL Example

```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test20@fxmail.ai",
    "password": "test20@#",
    "device_id": "my-device-123",
    "device_key_fingerprint": "a1b2c3d4e5f6...",
    "device_key_algorithm": "AES-256-GCM"
  }'
```

### Python Example

```python
import requests
import hashlib

# Generate device key fingerprint (client-side)
device_key = b"your_device_encryption_key"  # Generated on first app launch
device_key_fingerprint = hashlib.sha256(device_key).hexdigest()

# Login with device key fingerprint
response = requests.post(
    "https://freedomos.vulcantech.co/api/v1/auth/login",
    json={
        "email": "test20@fxmail.ai",
        "password": "test20@#",
        "device_id": "my-device-123",
        "device_key_fingerprint": device_key_fingerprint,
        "device_key_algorithm": "AES-256-GCM"
    }
)

tokens = response.json()
print(f"Access Token: {tokens['access_token']}")
print(f"Device ID: {tokens['device_id']}")
```

### JavaScript/TypeScript Example

```typescript
import crypto from 'crypto';

// Get device key from local storage (generated on first app launch)
const deviceKey = await getDeviceKeyFromLocalStorage();
const deviceKeyFingerprint = crypto
  .createHash('sha256')
  .update(deviceKey)
  .digest('hex');

// Login with device key fingerprint
const response = await fetch('https://freedomos.vulcantech.co/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'test20@fxmail.ai',
    password: 'test20@#',
    device_id: 'my-device-123',
    device_key_fingerprint: deviceKeyFingerprint,
    device_key_algorithm: 'AES-256-GCM',
  }),
});

const tokens = await response.json();
console.log('Access Token:', tokens.access_token);
console.log('Device ID:', tokens.device_id);
```

## Storage Details

### Redis Key Structure

```
auth:device_key:{user_id}:{device_id}
```

### Stored Data Format

```json
{
  "device_id": "device_unique_id",
  "key_fingerprint": "sha256_hash_of_device_key",
  "key_algorithm": "AES-256-GCM",
  "registered_at": "2026-01-29T12:00:00Z",
  "updated_at": "2026-01-29T12:00:00Z",
  "user_email": "user@fxmail.ai"
}
```

### Device List

Devices are also tracked in a set:
```
auth:device:{user_id}:devices
```

## Security Considerations

1. **Fingerprint Only**: Only the SHA-256 hash/fingerprint is stored, never the actual key
2. **Client-Side Key**: The actual device encryption key remains on the device
3. **Server Cannot Decrypt**: Server cannot decrypt files encrypted with the device key
4. **Non-Fatal Storage**: Login succeeds even if fingerprint storage fails
5. **Automatic Updates**: Key fingerprint is updated on every login

## Integration with Drive Download

This change works seamlessly with the encrypted file download endpoint:

1. **On Login**: Device key fingerprint is stored/replaced
2. **On Download**: Client uses device key to decrypt files
3. **Key Verification**: Server can verify device identity using fingerprint

## Migration Notes

- **Existing Logins**: Continue to work without `device_key_fingerprint`
- **New Logins**: Can optionally include `device_key_fingerprint` for automatic storage
- **Backward Compatible**: All fields are optional

## Files Modified

1. **`backend/py-service/app/api/v1/endpoints/auth.py`**
   - Updated `UserLogin` model (lines 63-68)
   - Updated `login` endpoint (lines 536-575)
   - Added device key storage logic

## Testing

```bash
# Test login without device key fingerprint (backward compatible)
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test20@fxmail.ai",
    "password": "test20@#"
  }'

# Test login with device key fingerprint (new feature)
curl -X POST "https://freedomos.vulcantech.co/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test20@fxmail.ai",
    "password": "test20@#",
    "device_id": "test-device-1",
    "device_key_fingerprint": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
    "device_key_algorithm": "AES-256-GCM"
  }'
```

---

**Status**: ✅ Implementation complete  
**Last Updated**: January 29, 2026
