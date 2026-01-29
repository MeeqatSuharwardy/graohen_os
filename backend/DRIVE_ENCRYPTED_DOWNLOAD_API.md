# Drive Encrypted Download API

## Overview

New API endpoint for downloading encrypted files with encrypted content keys for **client-side decryption**. This ensures true end-to-end encryption where the server never sees plaintext file content.

## Endpoint

**`GET /api/v1/drive/file/{file_id}/download-encrypted`**

## Authentication

**Required**: Bearer token in `Authorization` header

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## Authorization

- User must be authenticated
- User must own the file (ownership is verified)

## Request

```http
GET /api/v1/drive/file/{file_id}/download-encrypted
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_id` | String | ✅ Yes | Unique file identifier |

## Response

### Success Response (200 OK)

```json
{
  "file_id": "abc123xyz...",
  "filename": "document.pdf",
  "size": 1024000,
  "content_type": "application/pdf",
  "encrypted_content": {
    "ciphertext": "base64_encoded_ciphertext...",
    "layers": 3,
    "metadata": [
      {
        "algorithm": "AES-256-GCM",
        "nonce": "base64_nonce1...",
        "tag": "base64_tag1..."
      },
      {
        "algorithm": "ChaCha20-Poly1305",
        "nonce": "base64_nonce2...",
        "tag": "base64_tag2..."
      },
      {
        "algorithm": "AES-256-GCM-Scrypt",
        "nonce": "base64_nonce3...",
        "tag": "base64_tag3...",
        "salt": "base64_salt3..."
      }
    ]
  },
  "encrypted_content_key": {
    "ciphertext": "base64_encoded_ciphertext...",
    "layers": 3,
    "metadata": [
      {
        "algorithm": "AES-256-GCM",
        "nonce": "base64_nonce1...",
        "tag": "base64_tag1..."
      },
      {
        "algorithm": "ChaCha20-Poly1305",
        "nonce": "base64_nonce2...",
        "tag": "base64_tag2..."
      },
      {
        "algorithm": "AES-256-GCM-Scrypt",
        "nonce": "base64_nonce3...",
        "tag": "base64_tag3...",
        "salt": "base64_salt3..."
      }
    ]
  },
  "passcode_protected": false,
  "created_at": "2026-01-29T12:00:00Z",
  "expires_at": null,
  "message": "File downloaded. Decrypt encrypted_content_key using your device key, then decrypt encrypted_content using the decrypted content key."
}
```

### Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Authentication required"
}
```

#### 403 Forbidden
```json
{
  "detail": "Access denied: You don't own this file"
}
```

#### 404 Not Found
```json
{
  "detail": "File not found or expired"
}
```

#### 410 Gone
```json
{
  "detail": "File has expired"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to download encrypted file: [error message]"
}
```

## Client-Side Decryption Process

The client must decrypt the file in two steps:

### Step 1: Decrypt the Content Key

1. Retrieve the device key stored locally on the device (from first app launch)
2. Use the device key to decrypt `encrypted_content_key`:
   - Decrypt using multi-layer decryption (3 layers)
   - Layer 1: AES-256-GCM decryption
   - Layer 2: ChaCha20-Poly1305 decryption
   - Layer 3: AES-256-GCM-Scrypt decryption
3. The result is the **content key** (32 bytes)

### Step 2: Decrypt the File Content

1. Use the decrypted **content key** from Step 1
2. Decrypt `encrypted_content` using multi-layer decryption:
   - Same 3-layer process as above
3. The result is the **plaintext file content**

### Important Notes

- **If the device key is not present locally**, the file **cannot be decrypted**
- The server never sees plaintext content or keys
- All decryption happens on the client device
- The device key must be stored securely on the device (encrypted at rest)

## Example Usage

### cURL Example

```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/file/abc123xyz/download-encrypted" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Python Example

```python
import requests

url = "https://freedomos.vulcantech.co/api/v1/drive/file/{file_id}/download-encrypted"
headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    
    encrypted_content = data["encrypted_content"]
    encrypted_content_key = data["encrypted_content_key"]
    
    # Step 1: Decrypt content key using device key
    device_key = get_device_key_from_local_storage()  # Your function
    content_key = decrypt_multi_layer(encrypted_content_key, device_key)
    
    # Step 2: Decrypt file content using content key
    file_content = decrypt_multi_layer(encrypted_content, content_key)
    
    # Save file
    with open(data["filename"], "wb") as f:
        f.write(file_content)
else:
    print(f"Error: {response.status_code} - {response.json()}")
```

### JavaScript/TypeScript Example

```typescript
async function downloadEncryptedFile(fileId: string, accessToken: string) {
  const url = `https://freedomos.vulcantech.co/api/v1/drive/file/${fileId}/download-encrypted`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  
  const data = await response.json();
  
  // Get device key from local storage
  const deviceKey = await getDeviceKeyFromLocalStorage();
  
  // Step 1: Decrypt content key
  const contentKey = await decryptMultiLayer(
    data.encrypted_content_key,
    deviceKey
  );
  
  // Step 2: Decrypt file content
  const fileContent = await decryptMultiLayer(
    data.encrypted_content,
    contentKey
  );
  
  // Save file
  const blob = new Blob([fileContent], { type: data.content_type });
  const downloadUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = data.filename;
  a.click();
  
  return {
    filename: data.filename,
    size: data.size,
    content: fileContent
  };
}
```

## Multi-Layer Decryption Details

The encryption uses 3 layers:

1. **Layer 1: AES-256-GCM**
   - Algorithm: AES-256 in GCM mode
   - Key: Primary key (device key or passcode-derived key)
   - Nonce: 12 bytes (96 bits)
   - Tag: 16 bytes (128-bit authentication tag)

2. **Layer 2: ChaCha20-Poly1305**
   - Algorithm: ChaCha20 stream cipher with Poly1305 MAC
   - Key: Secondary key (derived from primary key)
   - Nonce: 12 bytes
   - Tag: 16 bytes

3. **Layer 3: AES-256-GCM-Scrypt**
   - Algorithm: AES-256-GCM with Scrypt key derivation
   - Key: Derived using Scrypt from combined primary + secondary keys
   - Salt: 16 bytes (stored in metadata)
   - Nonce: 12 bytes
   - Tag: 16 bytes

**Decryption must be performed in reverse order** (Layer 3 → Layer 2 → Layer 1).

## Security Features

✅ **End-to-End Encryption**: Server never sees plaintext  
✅ **Multi-Layer Encryption**: 3 layers make decryption extremely difficult  
✅ **Client-Side Decryption**: All decryption happens on device  
✅ **Device Key Required**: File cannot be opened without device key  
✅ **Authentication Required**: Only authenticated users can download  
✅ **Ownership Verification**: Users can only download their own files  
✅ **Expiration Check**: Expired files cannot be downloaded  

## Comparison with Other Download Endpoints

| Endpoint | Decryption | Use Case |
|----------|------------|----------|
| `/file/{file_id}/download` | Server-side | Quick download, server decrypts |
| `/file/{file_id}/download-encrypted` | Client-side | Maximum security, E2E encryption |

## Files Modified

1. **`backend/py-service/app/api/v1/endpoints/drive.py`**
   - Added `EncryptedFileDownloadResponse` Pydantic model
   - Added `download_encrypted_file` endpoint

## Testing

```bash
# Test download encrypted file
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/file/FILE_ID/download-encrypted" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  | jq .
```

---

**Status**: ✅ Implemented and ready for deployment  
**Last Updated**: January 29, 2026
