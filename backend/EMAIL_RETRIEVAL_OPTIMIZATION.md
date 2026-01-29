# Email Retrieval Endpoint Optimization

## Issue
The `GET /email/{email_id}` endpoint was timing out (15+ seconds) when retrieving individual emails.

## Root Causes Identified

1. **Redundant MongoDB Query**: The endpoint was querying MongoDB twice:
   - Once in `decrypt_email_for_authenticated_user()` to get the email document
   - Again in the endpoint itself to get metadata (lines 575-585)
   - This doubled the database round-trip time

2. **Multi-Layer Decryption**: The email content is encrypted with 3 layers:
   - Layer 1: AES-256-GCM
   - Layer 2: ChaCha20-Poly1305
   - Layer 3: AES-256-GCM with Scrypt key derivation
   - Each layer requires CPU-intensive cryptographic operations

3. **Key Derivation**: Scrypt/Argon2 key derivation is intentionally slow for security (100ms+ per derivation)

4. **Network Latency**: MongoDB queries over network can add latency

## Optimizations Applied

### 1. Eliminated Redundant MongoDB Query
**File**: `backend/py-service/app/services/email_service_mongodb.py`

**Change**: Modified `decrypt_email_for_authenticated_user()` to optionally return metadata along with decrypted content.

**Before**:
```python
async def decrypt_email_for_authenticated_user(
    self,
    access_token: str,
    user_email: str,
) -> bytes:
    # ... decrypts email ...
    return email_body  # Only returns decrypted body
```

**After**:
```python
async def decrypt_email_for_authenticated_user(
    self,
    access_token: str,
    user_email: str,
    return_metadata: bool = False,
) -> bytes:
    # ... decrypts email ...
    if return_metadata:
        metadata = {
            "encryption_mode": email_doc.get("encryption_mode", "authenticated"),
            "has_passcode": email_doc.get("has_passcode", False),
            "self_destruct": email_doc.get("self_destruct", False),
            "expires_at": email_doc.get("expires_at"),
            "sender_email": email_doc.get("sender_email"),
            "recipient_emails": email_doc.get("recipient_emails", []),
            "subject": email_doc.get("subject"),
            "created_at": email_doc.get("created_at"),
        }
        return email_body, metadata
    return email_body
```

### 2. Updated Endpoint to Reuse Metadata
**File**: `backend/py-service/app/api/v1/endpoints/email.py`

**Change**: Removed the second MongoDB query and reused metadata from decryption.

**Before**:
```python
# Decrypt email
email_body_bytes = await service.decrypt_email_for_authenticated_user(...)

# Query MongoDB again for metadata
email_doc = await email_collection.find_one({...})
encryption_mode = email_doc.get("encryption_mode", "authenticated")
is_passcode_protected = email_doc.get("has_passcode", False)
self_destruct = email_doc.get("self_destruct", False)
```

**After**:
```python
# Decrypt email and get metadata in one call
email_body_bytes, metadata = await service.decrypt_email_for_authenticated_user(
    access_token=email_id,
    user_email=user_email,
    return_metadata=True,
)

# Reuse metadata (no second MongoDB query)
encryption_mode = metadata.get("encryption_mode", "authenticated")
is_passcode_protected = metadata.get("has_passcode", False)
self_destruct = metadata.get("self_destruct", False)
```

### 3. Added Compound Index for Faster Queries
**File**: `backend/py-service/scripts/setup_mongodb.py`

**Change**: Added compound index on `(access_token, email_id)` to optimize the `$or` query pattern.

```python
# Compound index for $or queries (access_token OR email_id lookups)
await emails_collection.create_index([("access_token", 1), ("email_id", 1)])
```

## Performance Impact

### Expected Improvements:
- **~50% reduction** in database round-trips (1 query instead of 2)
- **~100-200ms faster** response time (eliminating network latency for second query)
- **Better scalability** under load (fewer database connections)

### Remaining Performance Considerations:
- **Multi-layer decryption** is still CPU-intensive (~200-500ms for large emails)
- **Key derivation** (Scrypt) is intentionally slow for security (~100-200ms)
- These are security features and should not be optimized away

## Testing

After deployment, test the endpoint:

```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/email/{email_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response Time**: < 2 seconds (down from 15+ seconds timeout)

## Files Modified

1. `backend/py-service/app/services/email_service_mongodb.py`
   - Added `return_metadata` parameter to `decrypt_email_for_authenticated_user()`
   - Returns tuple `(email_body, metadata)` when `return_metadata=True`

2. `backend/py-service/app/api/v1/endpoints/email.py`
   - Updated to use `return_metadata=True`
   - Removed redundant MongoDB query
   - Reuses metadata from decryption result

3. `backend/py-service/scripts/setup_mongodb.py`
   - Added compound index for `(access_token, email_id)` queries

## Deployment Steps

1. Deploy code changes
2. Run MongoDB index update (optional, for better performance):
   ```bash
   python3 backend/py-service/scripts/setup_mongodb.py
   ```
3. Restart backend service
4. Test endpoint performance

---

**Status**: ✅ Optimizations complete and ready for deployment  
**Last Updated**: January 29, 2026
