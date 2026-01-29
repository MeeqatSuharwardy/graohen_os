# Drive API - Complete Guide for Frontend Developers

**Last Updated**: January 29, 2026  
**Base URL**: `https://freedomos.vulcantech.co/api/v1`

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Authentication](#authentication)
4. [Device Key Setup](#device-key-setup)
5. [Drive API Endpoints](#drive-api-endpoints)
   - [Upload File](#1-upload-file)
   - [Upload Encrypted File (Client-Side)](#2-upload-encrypted-file-client-side)
   - [List Files](#3-list-files)
   - [Get File Info](#4-get-file-info)
   - [Download File (Server-Side Decryption)](#5-download-file-server-side-decryption)
   - [Download Encrypted File (Client-Side Decryption)](#6-download-encrypted-file-client-side-decryption)
   - [Unlock Passcode-Protected File](#7-unlock-passcode-protected-file)
   - [Delete File](#8-delete-file)
   - [Get Storage Quota](#9-get-storage-quota)
6. [Recent Updates](#recent-updates)
7. [Error Handling](#error-handling)
8. [Code Examples](#code-examples)
9. [Best Practices](#best-practices)

---

## Overview

The Drive API provides **encrypted file storage** similar to Google Drive with **maximum security**:

- ✅ **3-layer encryption** for all files
- ✅ **End-to-end encryption** support (client-side encryption)
- ✅ **5GB storage quota** per user
- ✅ **All file types supported** (PDF, Word, images, text, etc.)
- ✅ **Flexible expiration** (never expire or set hours/days)
- ✅ **Passcode protection** for sensitive files
- ✅ **Device key management** (automatic on login)

### Key Features

- **Google Drive-like functionality**: Upload, view, list, delete files
- **Maximum security**: Multi-layer encryption, E2E encryption support
- **Storage management**: 5GB quota per user, automatic tracking
- **File expiration**: Never expire or set expiration in hours/days
- **Client-side decryption**: Download encrypted files and decrypt on device

---

## Quick Start

### 1. Authenticate

```javascript
// Login
const loginResponse = await fetch('https://freedomos.vulcantech.co/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@fxmail.ai',
    password: 'password123',
    device_id: 'your-device-id',
    device_key_fingerprint: 'sha256_hash_of_device_key' // Optional but recommended
  })
});

const { access_token, refresh_token } = await loginResponse.json();
```

### 2. Upload a File

```javascript
const formData = new FormData();
formData.append('file', fileBlob);
formData.append('never_expire', 'true'); // File never expires

const uploadResponse = await fetch('https://freedomos.vulcantech.co/api/v1/drive/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`
  },
  body: formData
});

const fileData = await uploadResponse.json();
console.log('File uploaded:', fileData.file_id);
```

### 3. List Files

```javascript
const listResponse = await fetch('https://freedomos.vulcantech.co/api/v1/drive/files', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const { files } = await listResponse.json();
console.log('Files:', files);
```

---

## Authentication

**All Drive API endpoints require authentication** using JWT Bearer tokens.

### Login Endpoint

**`POST /auth/login`**

```json
{
  "email": "user@fxmail.ai",
  "password": "password123",
  "device_id": "device-123",
  "device_key_fingerprint": "sha256_hash_of_device_key",
  "device_key_algorithm": "AES-256-GCM"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_id": "device-123"
}
```

### Using Access Token

Include the access token in the `Authorization` header for all API requests:

```javascript
headers: {
  'Authorization': `Bearer ${access_token}`
}
```

---

## Device Key Setup

### What is Device Key?

The device key is an encryption key generated **on first app launch** and stored **locally on the device**. It's used for:
- Encrypting files client-side before upload
- Decrypting files downloaded from the server
- Ensuring true end-to-end encryption

### Device Key Storage on Login

**NEW**: Device key fingerprint is automatically stored/replaced on every login.

When logging in, include `device_key_fingerprint`:

```javascript
// Generate device key fingerprint (SHA-256 hash)
const deviceKey = await getDeviceKeyFromLocalStorage(); // Your function
const deviceKeyFingerprint = await crypto.subtle.digest(
  'SHA-256',
  deviceKey
);

// Login with fingerprint
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@fxmail.ai',
    password: 'password123',
    device_id: 'device-123',
    device_key_fingerprint: Array.from(new Uint8Array(deviceKeyFingerprint))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')
  })
});
```

**Important**: 
- Only the **fingerprint/hash** is sent to the server
- The **actual device key** never leaves the device
- Server cannot decrypt files encrypted with device key

---

## Drive API Endpoints

### 1. Upload File

**`POST /drive/upload`**

Upload and encrypt a file. Supports **all file types** (PDF, Word, images, text, etc.).

#### Request

**Form Data:**
- `file` (File, required): File to upload
- `passcode` (String, optional): Optional passcode for additional protection
- `never_expire` (Boolean, optional): If `true`, file never expires. Default: `false`
- `expires_in_hours` (Integer, optional): Expiration in hours (1-8760). Only used if `never_expire=false`
- `expires_in_days` (Integer, optional): Expiration in days (1-365). Takes precedence over hours. Only used if `never_expire=false`

#### Expiration Logic

1. **If `never_expire=true`**: File never expires
2. **If `never_expire=false`**:
   - If `expires_in_days` provided: Use days
   - Else if `expires_in_hours` provided: Use hours
   - Else: No expiration (same as `never_expire=true`)

#### Example

```javascript
const formData = new FormData();
formData.append('file', fileBlob);
formData.append('never_expire', 'true'); // Never expires

// OR with expiration
formData.append('never_expire', 'false');
formData.append('expires_in_days', '30'); // Expires in 30 days

const response = await fetch('https://freedomos.vulcantech.co/api/v1/drive/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`
  },
  body: formData
});

const result = await response.json();
// {
//   "file_id": "abc123...",
//   "filename": "document.pdf",
//   "size": 1024000,
//   "content_type": "application/pdf",
//   "passcode_protected": false,
//   "expires_at": null,
//   "created_at": "2026-01-29T12:00:00Z"
// }
```

#### Supported File Types

✅ **All file types are supported:**
- Documents: PDF, Word (.doc, .docx), Text (.txt, .md)
- Images: PNG, JPG, JPEG, GIF, WebP, SVG
- Spreadsheets: Excel (.xls, .xlsx), CSV
- Archives: ZIP, RAR, TAR, GZ
- **Any other file format**

#### File Size Limits

- **Max file size**: 100MB per file
- **Storage quota**: 5GB per user (total)

---

### 2. Upload Encrypted File (Client-Side)

**`POST /drive/upload-encrypted`**

Upload a file that is **already encrypted on the client-side**. This ensures true end-to-end encryption where the server never sees plaintext.

#### Request Body

```json
{
  "filename": "document.pdf",
  "encrypted_content": {
    "ciphertext": "base64_encoded_ciphertext...",
    "layers": 3,
    "metadata": [...]
  },
  "encrypted_content_key": {
    "ciphertext": "base64_encoded_ciphertext...",
    "layers": 3,
    "metadata": [...]
  },
  "content_type": "application/pdf",
  "size": 1024000,
  "passcode": "optional-passcode",
  "never_expire": false,
  "expires_in_days": 30,
  "expires_in_hours": null
}
```

#### Example

```javascript
const response = await fetch('https://freedomos.vulcantech.co/api/v1/drive/upload-encrypted', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    filename: 'document.pdf',
    encrypted_content: encryptedFileContent,
    encrypted_content_key: encryptedContentKey,
    content_type: 'application/pdf',
    size: fileSize,
    never_expire: false,
    expires_in_days: 30
  })
});
```

---

### 3. List Files

**`GET /drive/files?limit=50&offset=0`**

Get a list of all files for the authenticated user.

#### Query Parameters

- `limit` (Integer, optional): Number of files to return. Default: 50
- `offset` (Integer, optional): Number of files to skip. Default: 0

#### Example

```javascript
const response = await fetch('https://freedomos.vulcantech.co/api/v1/drive/files?limit=50&offset=0', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const result = await response.json();
// {
//   "files": [
//     {
//       "file_id": "abc123...",
//       "filename": "document.pdf",
//       "size": 1024000,
//       "content_type": "application/pdf",
//       "passcode_protected": false,
//       "created_at": "2026-01-29T12:00:00Z",
//       "expires_at": null
//     }
//   ],
//   "total": 10,
//   "limit": 50,
//   "offset": 0
// }
```

---

### 4. Get File Info

**`GET /drive/file/{file_id}`**

Get file information and generate a signed download URL.

#### Example

```javascript
const response = await fetch(`https://freedomos.vulcantech.co/api/v1/drive/file/${fileId}`, {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const result = await response.json();
// {
//   "file_id": "abc123...",
//   "filename": "document.pdf",
//   "size": 1024000,
//   "content_type": "application/pdf",
//   "passcode_protected": false,
//   "owner_email": "user@fxmail.ai",
//   "expires_at": null,
//   "created_at": "2026-01-29T12:00:00Z",
//   "signed_url": "/api/v1/drive/file/abc123.../download?token=...",
//   "signed_url_expires_at": "2026-01-29T13:00:00Z"
// }
```

---

### 5. Download File (Server-Side Decryption)

**`GET /drive/file/{file_id}/download?token={signed_token}`**

Download a file with server-side decryption. Returns the decrypted file content.

#### Example

```javascript
// First get file info to get signed URL
const fileInfo = await fetch(`https://freedomos.vulcantech.co/api/v1/drive/file/${fileId}`, {
  headers: { 'Authorization': `Bearer ${access_token}` }
}).then(r => r.json());

// Download using signed URL
const downloadUrl = `https://freedomos.vulcantech.co${fileInfo.signed_url}`;
const fileBlob = await fetch(downloadUrl).then(r => r.blob());

// Save file
const url = URL.createObjectURL(fileBlob);
const a = document.createElement('a');
a.href = url;
a.download = fileInfo.filename;
a.click();
```

---

### 6. Download Encrypted File (Client-Side Decryption) ⭐ NEW

**`GET /drive/file/{file_id}/download-encrypted`**

Download encrypted file with encrypted content key for **client-side decryption**. This ensures true end-to-end encryption.

#### How It Works

1. **Download**: Get encrypted file content and encrypted content key
2. **Decrypt Content Key**: Use device key to decrypt `encrypted_content_key` → get content key
3. **Decrypt File**: Use content key to decrypt `encrypted_content` → get plaintext file

#### Example

```javascript
// Download encrypted file
const response = await fetch(
  `https://freedomos.vulcantech.co/api/v1/drive/file/${fileId}/download-encrypted`,
  {
    headers: {
      'Authorization': `Bearer ${access_token}`
    }
  }
);

const data = await response.json();
// {
//   "file_id": "abc123...",
//   "filename": "document.pdf",
//   "size": 1024000,
//   "content_type": "application/pdf",
//   "encrypted_content": {
//     "ciphertext": "...",
//     "layers": 3,
//     "metadata": [...]
//   },
//   "encrypted_content_key": {
//     "ciphertext": "...",
//     "layers": 3,
//     "metadata": [...]
//   },
//   "passcode_protected": false,
//   "created_at": "2026-01-29T12:00:00Z",
//   "expires_at": null,
//   "message": "File downloaded. Decrypt encrypted_content_key using your device key..."
// }

// Step 1: Decrypt content key using device key
const deviceKey = await getDeviceKeyFromLocalStorage();
const contentKey = await decryptMultiLayer(
  data.encrypted_content_key,
  deviceKey
);

// Step 2: Decrypt file content using content key
const fileContent = await decryptMultiLayer(
  data.encrypted_content,
  contentKey
);

// Save file
const blob = new Blob([fileContent], { type: data.content_type });
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = data.filename;
a.click();
```

**Important**: 
- If device key is not present locally, file **cannot be decrypted**
- Server never sees plaintext content
- All decryption happens on the device

---

### 7. Unlock Passcode-Protected File

**`POST /drive/file/{file_id}/unlock`**

Unlock a passcode-protected file and get a signed download URL.

#### Request Body

```json
{
  "passcode": "file-passcode"
}
```

#### Example

```javascript
const response = await fetch(
  `https://freedomos.vulcantech.co/api/v1/drive/file/${fileId}/unlock`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${access_token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      passcode: 'file-passcode'
    })
  }
);

const result = await response.json();
// {
//   "file_id": "abc123...",
//   "signed_url": "/api/v1/drive/file/abc123.../download?token=...",
//   "signed_url_expires_at": "2026-01-29T13:00:00Z",
//   "unlocked_at": "2026-01-29T12:00:00Z"
// }

// Use signed_url to download file
const fileBlob = await fetch(
  `https://freedomos.vulcantech.co${result.signed_url}`
).then(r => r.blob());
```

**Rate Limiting**: Max 5 unlock attempts per hour per file.

---

### 8. Delete File

**`DELETE /drive/file/{file_id}`**

Delete a file and all associated data.

#### Example

```javascript
const response = await fetch(
  `https://freedomos.vulcantech.co/api/v1/drive/file/${fileId}`,
  {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${access_token}`
    }
  }
);

const result = await response.json();
// {
//   "file_id": "abc123...",
//   "deleted": true,
//   "message": "File deleted successfully"
// }
```

---

### 9. Get Storage Quota

**`GET /drive/storage/quota`**

Get storage quota information for the current user.

#### Example

```javascript
const response = await fetch(
  'https://freedomos.vulcantech.co/api/v1/drive/storage/quota',
  {
    headers: {
      'Authorization': `Bearer ${access_token}`
    }
  }
);

const result = await response.json();
// {
//   "used_bytes": 1073741824,
//   "quota_bytes": 5368709120,
//   "used_gb": 1.0,
//   "quota_gb": 5.0,
//   "available_bytes": 4294967296,
//   "available_gb": 4.0,
//   "percentage_used": 20.0
// }
```

---

## Recent Updates

### 1. Flexible File Expiration ⭐ NEW

Files can now be configured with flexible expiration options:

- **Never Expire**: `never_expire=true` - File never expires
- **Expire in Days**: `expires_in_days=30` - File expires in 30 days
- **Expire in Hours**: `expires_in_hours=24` - File expires in 24 hours

**Priority**: Days take precedence over hours.

### 2. All File Types Supported ⭐ NEW

**All file types are now supported** - no restrictions:
- PDF, Word, Text files
- Images (PNG, JPG, GIF, WebP, etc.)
- Spreadsheets (Excel, CSV)
- Archives (ZIP, RAR, TAR, GZ)
- **Any other file format**

### 3. Encrypted Download Endpoint ⭐ NEW

New endpoint for downloading encrypted files with client-side decryption:
- **`GET /drive/file/{file_id}/download-encrypted`**
- Returns encrypted file content and encrypted content key
- Client decrypts using device key
- Ensures true end-to-end encryption

### 4. Device Key Storage on Login ⭐ NEW

Device key fingerprint is automatically stored/replaced on every login:
- Include `device_key_fingerprint` in login request
- Automatically stored/replaced in Redis
- Used for verifying device identity
- Enables encrypted file downloads

---

## Error Handling

### Common HTTP Status Codes

| Status Code | Meaning | Solution |
|-------------|---------|----------|
| `200` | Success | - |
| `201` | Created | File uploaded successfully |
| `400` | Bad Request | Check request parameters |
| `401` | Unauthorized | Check access token |
| `403` | Forbidden | User doesn't own the file |
| `404` | Not Found | File doesn't exist |
| `410` | Gone | File has expired |
| `413` | Payload Too Large | File exceeds size limit or quota |
| `429` | Too Many Requests | Rate limit exceeded (unlock attempts) |
| `500` | Internal Server Error | Server error, try again later |

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

### Example Error Handling

```javascript
try {
  const response = await fetch(url, options);
  
  if (!response.ok) {
    const error = await response.json();
    
    switch (response.status) {
      case 401:
        // Token expired, refresh or re-login
        await refreshToken();
        break;
      case 403:
        // Access denied
        console.error('Access denied:', error.detail);
        break;
      case 413:
        // File too large or quota exceeded
        console.error('Storage issue:', error.detail);
        break;
      default:
        console.error('Error:', error.detail);
    }
    
    throw new Error(error.detail);
  }
  
  return await response.json();
} catch (error) {
  console.error('Request failed:', error);
  throw error;
}
```

---

## Code Examples

### Complete Upload Flow

```javascript
async function uploadFile(file, accessToken, options = {}) {
  const formData = new FormData();
  formData.append('file', file);
  
  // Expiration options
  if (options.neverExpire) {
    formData.append('never_expire', 'true');
  } else {
    formData.append('never_expire', 'false');
    if (options.expiresInDays) {
      formData.append('expires_in_days', options.expiresInDays.toString());
    } else if (options.expiresInHours) {
      formData.append('expires_in_hours', options.expiresInHours.toString());
    }
  }
  
  // Optional passcode
  if (options.passcode) {
    formData.append('passcode', options.passcode);
  }
  
  const response = await fetch(
    'https://freedomos.vulcantech.co/api/v1/drive/upload',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      },
      body: formData
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

// Usage
const fileData = await uploadFile(fileBlob, accessToken, {
  neverExpire: true
  // OR
  // expiresInDays: 30
  // OR
  // expiresInHours: 24
});
```

### Complete Download Flow (Encrypted)

```javascript
async function downloadEncryptedFile(fileId, accessToken) {
  // Download encrypted file
  const response = await fetch(
    `https://freedomos.vulcantech.co/api/v1/drive/file/${fileId}/download-encrypted`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  const data = await response.json();
  
  // Get device key from local storage
  const deviceKey = await getDeviceKeyFromLocalStorage();
  
  // Decrypt content key
  const contentKey = await decryptMultiLayer(
    data.encrypted_content_key,
    deviceKey
  );
  
  // Decrypt file content
  const fileContent = await decryptMultiLayer(
    data.encrypted_content,
    contentKey
  );
  
  return {
    filename: data.filename,
    content: fileContent,
    contentType: data.content_type
  };
}

// Usage
const file = await downloadEncryptedFile(fileId, accessToken);
const blob = new Blob([file.content], { type: file.contentType });
// Save or display file
```

### Complete File Management

```javascript
class DriveAPI {
  constructor(baseURL, accessToken) {
    this.baseURL = baseURL;
    this.accessToken = accessToken;
  }
  
  async uploadFile(file, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    
    if (options.neverExpire) {
      formData.append('never_expire', 'true');
    } else {
      formData.append('never_expire', 'false');
      if (options.expiresInDays) {
        formData.append('expires_in_days', options.expiresInDays);
      } else if (options.expiresInHours) {
        formData.append('expires_in_hours', options.expiresInHours);
      }
    }
    
    if (options.passcode) {
      formData.append('passcode', options.passcode);
    }
    
    return this.request('/drive/upload', {
      method: 'POST',
      body: formData
    });
  }
  
  async listFiles(limit = 50, offset = 0) {
    return this.request(`/drive/files?limit=${limit}&offset=${offset}`);
  }
  
  async getFileInfo(fileId) {
    return this.request(`/drive/file/${fileId}`);
  }
  
  async downloadEncryptedFile(fileId) {
    return this.request(`/drive/file/${fileId}/download-encrypted`);
  }
  
  async deleteFile(fileId) {
    return this.request(`/drive/file/${fileId}`, {
      method: 'DELETE'
    });
  }
  
  async getStorageQuota() {
    return this.request('/drive/storage/quota');
  }
  
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Authorization': `Bearer ${this.accessToken}`,
      ...options.headers
    };
    
    const response = await fetch(url, {
      ...options,
      headers
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }
    
    return await response.json();
  }
}

// Usage
const drive = new DriveAPI(
  'https://freedomos.vulcantech.co/api/v1',
  accessToken
);

// Upload
const fileData = await drive.uploadFile(fileBlob, {
  neverExpire: true
});

// List files
const { files } = await drive.listFiles();

// Get quota
const quota = await drive.getStorageQuota();
console.log(`Used: ${quota.used_gb}GB / ${quota.quota_gb}GB`);
```

---

## Best Practices

### 1. Device Key Management

- ✅ Generate device key on **first app launch**
- ✅ Store device key **securely** on device (encrypted at rest)
- ✅ **Never** send actual device key to server
- ✅ Send only **fingerprint/hash** on login
- ✅ Use device key for client-side encryption/decryption

### 2. File Upload

- ✅ Check storage quota before uploading large files
- ✅ Use `never_expire=true` for important files
- ✅ Set appropriate expiration for temporary files
- ✅ Use passcode protection for sensitive files

### 3. File Download

- ✅ Use **encrypted download** endpoint for maximum security
- ✅ Decrypt files on device using device key
- ✅ Handle decryption errors gracefully
- ✅ Cache decrypted files securely if needed

### 4. Error Handling

- ✅ Always check response status
- ✅ Handle token expiration (401) by refreshing token
- ✅ Show user-friendly error messages
- ✅ Log errors for debugging

### 5. Performance

- ✅ Use pagination for file lists (`limit` and `offset`)
- ✅ Implement file upload progress indicators
- ✅ Cache file metadata locally
- ✅ Batch operations when possible

---

## Summary

### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/drive/upload` | POST | Upload file |
| `/drive/upload-encrypted` | POST | Upload pre-encrypted file |
| `/drive/files` | GET | List files |
| `/drive/file/{file_id}` | GET | Get file info |
| `/drive/file/{file_id}/download` | GET | Download (server decrypts) |
| `/drive/file/{file_id}/download-encrypted` | GET | Download (client decrypts) ⭐ |
| `/drive/file/{file_id}/unlock` | POST | Unlock passcode file |
| `/drive/file/{file_id}` | DELETE | Delete file |
| `/drive/storage/quota` | GET | Get storage quota |

### Key Features

- ✅ **All file types supported**
- ✅ **Flexible expiration** (never expire or hours/days)
- ✅ **Client-side decryption** for E2E encryption
- ✅ **Device key management** on login
- ✅ **5GB storage quota** per user
- ✅ **Multi-layer encryption** (3 layers)

---

**Need Help?** Check the error messages or contact the backend team.

**Last Updated**: January 29, 2026
