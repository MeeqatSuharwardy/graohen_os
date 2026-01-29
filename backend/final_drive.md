# Final Drive API Documentation

Complete guide for implementing encrypted file storage (like Google Drive) in your mobile/web applications.

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Drive API Endpoints](#drive-api-endpoints)
  - [Upload File](#1-upload-file)
  - [List Files](#2-list-files)
  - [Get File Info](#3-get-file-info)
  - [Download File](#4-download-file)
  - [Delete File](#5-delete-file)
  - [Get Storage Quota](#6-get-storage-quota)
  - [Unlock Passcode-Protected File](#7-unlock-passcode-protected-file)
  - [Upload Encrypted File (Client-Side)](#8-upload-encrypted-file-client-side)
- [Step-by-Step Implementation](#step-by-step-implementation)
- [Error Handling](#error-handling)
- [Code Examples](#code-examples)

---

## Overview

The Drive API provides **encrypted file storage** similar to Google Drive, but with **maximum security**:
- **3-layer encryption** for all files
- **MongoDB storage** for encrypted files
- **5GB storage quota** per user (enforced)
- **Passcode protection** for sensitive files
- **Signed URLs** for secure file sharing
- **Automatic expiration** support

### Key Features

- ✅ **Google Drive-like functionality** - Upload, view, list, delete files
- ✅ **End-to-end encryption** - Files encrypted before storage
- ✅ **Multi-layer encryption** - 3 layers for maximum security
- ✅ **Storage quota** - 5GB per user, tracked automatically
- ✅ **Passcode protection** - Optional passcode for sensitive files
- ✅ **Signed URLs** - Time-limited secure download links
- ✅ **File expiration** - Optional automatic file deletion

---

## Base URL

**Production:**
```
https://freedomos.vulcantech.co/api/v1
```

**Development:**
```
http://localhost:8000/api/v1
```

---

## Authentication

**All Drive API endpoints require authentication** using JWT Bearer tokens.

### Step 1: Register/Login

First, register or login to get access tokens:

**Register:**
```bash
POST /auth/register
Content-Type: application/json

{
  "email": "user@fxmail.ai",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Login:**
```bash
POST /auth/login
Content-Type: application/json

{
  "email": "user@fxmail.ai",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Step 2: Use Access Token

Include the access token in all API requests:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Drive API Endpoints

### 1. Upload File

Upload a file to encrypted storage.

**Endpoint:** `POST /drive/upload`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Request Body (FormData):**
- `file` (required): File to upload (max 100MB)
- `filename` (optional): Custom filename (defaults to original filename)
- `passcode` (optional): Passcode for file protection
- `expires_in_hours` (optional): Hours until file expires (1-8760)

**Response (201 Created):**
```json
{
  "file_id": "abc123xyz...",
  "filename": "document.pdf",
  "size": 1024000,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": null,
  "created_at": "2026-01-29T12:00:00Z"
}
```

**Example (cURL):**
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/file.pdf" \
  -F "filename=document.pdf"
```

**Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', fileBlob);
formData.append('filename', 'document.pdf');

const response = await fetch(`${API_BASE_URL}/drive/upload`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  },
  body: formData
});

const result = await response.json();
```

---

### 2. List Files

Get list of uploaded files.

**Endpoint:** `GET /drive/files`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional): Number of files to return (default: 50, max: 100)
- `offset` (optional): Number of files to skip (default: 0)

**Response (200 OK):**
```json
{
  "files": [
    {
      "file_id": "abc123xyz...",
      "filename": "document.pdf",
      "size": 1024000,
      "content_type": "application/pdf",
      "passcode_protected": false,
      "created_at": "2026-01-29T12:00:00Z",
      "expires_at": null
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Example:**
```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/files?limit=20&offset=0" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 3. Get File Info

Get information about a specific file.

**Endpoint:** `GET /drive/file/{file_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "file_id": "abc123xyz...",
  "filename": "document.pdf",
  "size": 1024000,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "owner_email": "user@fxmail.ai",
  "expires_at": null,
  "created_at": "2026-01-29T12:00:00Z",
  "signed_url": "https://freedomos.vulcantech.co/api/v1/drive/file/abc123xyz.../download?token=...",
  "signed_url_expires_at": "2026-01-29T13:00:00Z"
}
```

**Example:**
```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/file/abc123xyz..." \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Download File

Download a file using signed URL.

**Endpoint:** `GET /drive/file/{file_id}/download`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `token` (optional): Signed URL token (if provided, authentication not required)

**Response (200 OK):**
- File content as binary stream
- `Content-Type`: File's content type
- `Content-Disposition`: `attachment; filename="document.pdf"`

**Example:**
```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/file/abc123xyz.../download" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -o downloaded_file.pdf
```

**Example (JavaScript):**
```javascript
const response = await fetch(
  `${API_BASE_URL}/drive/file/${fileId}/download`,
  {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  }
);

const blob = await response.blob();
// Save or display the file
```

---

### 5. Delete File

Delete a file.

**Endpoint:** `DELETE /drive/file/{file_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "file_id": "abc123xyz...",
  "deleted": true,
  "message": "File deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE "https://freedomos.vulcantech.co/api/v1/drive/file/abc123xyz..." \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 6. Get Storage Quota

Get storage quota information.

**Endpoint:** `GET /drive/storage/quota`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "used_bytes": 1073741824,
  "quota_bytes": 5368709120,
  "used_gb": 1.0,
  "quota_gb": 5.0,
  "available_bytes": 4294967296,
  "available_gb": 4.0,
  "percentage_used": 20.0
}
```

**Example:**
```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/storage/quota" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 7. Unlock Passcode-Protected File

Unlock a passcode-protected file to get download access.

**Endpoint:** `POST /drive/file/{file_id}/unlock`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "passcode": "your-passcode"
}
```

**Response (200 OK):**
```json
{
  "file_id": "abc123xyz...",
  "signed_url": "https://freedomos.vulcantech.co/api/v1/drive/file/abc123xyz.../download?token=...",
  "signed_url_expires_at": "2026-01-29T13:00:00Z",
  "unlocked_at": "2026-01-29T12:00:00Z"
}
```

**Example:**
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/file/abc123xyz.../unlock" \
  -H "Content-Type: application/json" \
  -d '{
    "passcode": "your-passcode"
  }'
```

---

### 8. Upload Encrypted File (Client-Side)

Upload a file that was encrypted on the client-side (advanced).

**Endpoint:** `POST /drive/upload-encrypted`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "filename": "document.pdf",
  "encrypted_content": {
    "ciphertext": "base64_encoded_ciphertext",
    "nonce": "base64_encoded_nonce",
    "tag": "base64_encoded_tag"
  },
  "encrypted_content_key": {
    "ciphertext": "base64_encoded_ciphertext",
    "nonce": "base64_encoded_nonce",
    "tag": "base64_encoded_tag"
  },
  "content_type": "application/pdf",
  "size": 1024000,
  "passcode": "optional-passcode",
  "expires_in_hours": 24
}
```

**Response (201 Created):**
```json
{
  "file_id": "abc123xyz...",
  "filename": "document.pdf",
  "size": 1024000,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": null,
  "created_at": "2026-01-29T12:00:00Z"
}
```

**Note:** This endpoint is for advanced use cases where encryption is performed on the client-side. For most use cases, use `/drive/upload` instead.

---

## Step-by-Step Implementation

### Step 1: Authentication Setup

1. **Register a user:**
   ```javascript
   const registerResponse = await fetch(`${API_BASE_URL}/auth/register`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       email: 'user@fxmail.ai',
       password: 'securepassword123',
       full_name: 'John Doe'
     })
   });
   
   const { access_token, refresh_token } = await registerResponse.json();
   ```

2. **Store tokens securely:**
   ```javascript
   // Store in secure storage (Keychain/SecureStore)
   await SecureStore.setItemAsync('access_token', access_token);
   await SecureStore.setItemAsync('refresh_token', refresh_token);
   ```

3. **Login (if already registered):**
   ```javascript
   const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       email: 'user@fxmail.ai',
       password: 'securepassword123'
     })
   });
   
   const { access_token, refresh_token } = await loginResponse.json();
   ```

### Step 2: Upload File

```javascript
const uploadFile = async (file, filename, options = {}) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const formData = new FormData();
  formData.append('file', file);
  formData.append('filename', filename || file.name);
  
  if (options.passcode) {
    formData.append('passcode', options.passcode);
  }
  
  if (options.expiresInHours) {
    formData.append('expires_in_hours', options.expiresInHours.toString());
  }
  
  const response = await fetch(`${API_BASE_URL}/drive/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    },
    body: formData
  });
  
  return await response.json();
};
```

### Step 3: List Files

```javascript
const listFiles = async (limit = 50, offset = 0) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(
    `${API_BASE_URL}/drive/files?limit=${limit}&offset=${offset}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

### Step 4: Get File Info

```javascript
const getFileInfo = async (fileId) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(`${API_BASE_URL}/drive/file/${fileId}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  return await response.json();
};
```

### Step 5: Download File

```javascript
const downloadFile = async (fileId) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(
    `${API_BASE_URL}/drive/file/${fileId}/download`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  const blob = await response.blob();
  return blob;
};
```

### Step 6: Delete File

```javascript
const deleteFile = async (fileId) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(`${API_BASE_URL}/drive/file/${fileId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  return await response.json();
};
```

### Step 7: Get Storage Quota

```javascript
const getStorageQuota = async () => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(`${API_BASE_URL}/drive/storage/quota`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  return await response.json();
};
```

### Step 8: Unlock Passcode-Protected File

```javascript
const unlockFile = async (fileId, passcode) => {
  const response = await fetch(
    `${API_BASE_URL}/drive/file/${fileId}/unlock`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ passcode })
    }
  );
  
  return await response.json();
};
```

---

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid access token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: File not found
- **413 Payload Too Large**: File too large (max 100MB)
- **422 Unprocessable Entity**: Validation error
- **429 Too Many Requests**: Rate limit exceeded
- **507 Insufficient Storage**: Storage quota exceeded
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

### Example Error Handling

```javascript
const handleApiCall = async (apiCall) => {
  try {
    const response = await apiCall();
    
    if (!response.ok) {
      const error = await response.json();
      
      if (response.status === 401) {
        // Token expired, refresh it
        await refreshAccessToken();
        // Retry the request
        return await apiCall();
      }
      
      throw new Error(error.detail || 'API request failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};
```

---

## Code Examples

### Complete Drive App Example

```javascript
const API_BASE_URL = 'https://freedomos.vulcantech.co/api/v1';

class DriveService {
  constructor() {
    this.accessToken = null;
  }
  
  async authenticate(email, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    this.accessToken = data.access_token;
    return data;
  }
  
  async uploadFile(file, filename, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('filename', filename || file.name);
    
    if (options.passcode) {
      formData.append('passcode', options.passcode);
    }
    
    if (options.expiresInHours) {
      formData.append('expires_in_hours', options.expiresInHours.toString());
    }
    
    const response = await fetch(`${API_BASE_URL}/drive/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`
      },
      body: formData
    });
    
    return await response.json();
  }
  
  async listFiles(limit = 50, offset = 0) {
    const response = await fetch(
      `${API_BASE_URL}/drive/files?limit=${limit}&offset=${offset}`,
      {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      }
    );
    
    return await response.json();
  }
  
  async getFileInfo(fileId) {
    const response = await fetch(`${API_BASE_URL}/drive/file/${fileId}`, {
      headers: {
        'Authorization': `Bearer ${this.accessToken}`
      }
    });
    
    return await response.json();
  }
  
  async downloadFile(fileId) {
    const response = await fetch(
      `${API_BASE_URL}/drive/file/${fileId}/download`,
      {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      }
    );
    
    return await response.blob();
  }
  
  async deleteFile(fileId) {
    const response = await fetch(`${API_BASE_URL}/drive/file/${fileId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`
      }
    });
    
    return await response.json();
  }
  
  async getStorageQuota() {
    const response = await fetch(`${API_BASE_URL}/drive/storage/quota`, {
      headers: {
        'Authorization': `Bearer ${this.accessToken}`
      }
    });
    
    return await response.json();
  }
  
  async unlockFile(fileId, passcode) {
    const response = await fetch(
      `${API_BASE_URL}/drive/file/${fileId}/unlock`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passcode })
      }
    );
    
    return await response.json();
  }
}

// Usage
const driveService = new DriveService();

// Authenticate
await driveService.authenticate('user@fxmail.ai', 'password');

// Upload file
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];
await driveService.uploadFile(file, 'document.pdf');

// List files
const files = await driveService.listFiles();

// Get file info
const fileInfo = await driveService.getFileInfo('file_id');

// Download file
const blob = await driveService.downloadFile('file_id');
const url = URL.createObjectURL(blob);
// Use URL to download or display file

// Delete file
await driveService.deleteFile('file_id');

// Get storage quota
const quota = await driveService.getStorageQuota();
console.log(`Used: ${quota.used_gb} GB / ${quota.quota_gb} GB`);

// Unlock passcode-protected file
const unlockResult = await driveService.unlockFile('file_id', 'passcode');
const downloadUrl = unlockResult.signed_url;
```

### React Native Example

```javascript
import * as FileSystem from 'expo-file-system';
import * as DocumentPicker from 'expo-document-picker';

// Upload file from device
const uploadFileFromDevice = async () => {
  // Pick file
  const result = await DocumentPicker.getDocumentAsync();
  
  if (result.type === 'success') {
    const fileUri = result.uri;
    const fileName = result.name;
    
    // Read file
    const fileContent = await FileSystem.readAsStringAsync(fileUri, {
      encoding: FileSystem.EncodingType.Base64,
    });
    
    // Convert to blob
    const blob = await fetch(`data:application/octet-stream;base64,${fileContent}`)
      .then(res => res.blob());
    
    // Upload
    const formData = new FormData();
    formData.append('file', blob, fileName);
    
    const response = await fetch(`${API_BASE_URL}/drive/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'multipart/form-data',
      },
      body: formData,
    });
    
    return await response.json();
  }
};
```

---

## Summary

This Drive API provides complete encrypted file storage functionality with:
- ✅ Upload, download, list, and delete files
- ✅ Storage quota management (5GB per user)
- ✅ Passcode protection for sensitive files
- ✅ Signed URLs for secure file sharing
- ✅ File expiration support
- ✅ Full authentication integration

All files are encrypted with **3-layer encryption** and stored securely in MongoDB. The server never sees plaintext content.

---

**Base URL:** `https://freedomos.vulcantech.co/api/v1`  
**Authentication:** JWT Bearer Token  
**Storage:** MongoDB (encrypted)  
**Quota:** 5GB per user  
**Max File Size:** 100MB
