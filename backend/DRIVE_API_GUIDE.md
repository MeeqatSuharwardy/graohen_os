# Drive API Guide for Frontend Developers

Complete guide for implementing encrypted file storage (like Google Drive) in your mobile/web applications.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [How File Upload Works (API Side)](#how-file-upload-works-api-side)
- [How File Download Works (API Side)](#how-file-download-works-api-side)
- [How File Listing Works (API Side)](#how-file-listing-works-api-side)
- [Frontend Implementation](#frontend-implementation)
- [Storage Quota Management](#storage-quota-management)
- [Error Handling](#error-handling)
- [Security Best Practices](#security-best-practices)
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

### Base URL

**Production:**
```
https://freedomos.vulcantech.co/api/v1
```

**Development:**
```
http://localhost:8000/api/v1
```

### Key Features

- ✅ **Google Drive-like functionality** - Upload, view, list, delete files
- ✅ **End-to-end encryption** - Files encrypted before storage
- ✅ **Multi-layer encryption** - 3 layers for maximum security
- ✅ **Storage quota** - 5GB per user, tracked automatically
- ✅ **Passcode protection** - Optional passcode for sensitive files
- ✅ **Signed URLs** - Time-limited secure download links
- ✅ **File expiration** - Optional automatic file deletion

---

## Authentication

**All Drive API endpoints require authentication** using the same JWT tokens as other APIs.

See [AUTHENTICATION_GUIDE.md](./AUTHENTICATION_GUIDE.md) for complete authentication setup.

**Quick Example:**
```javascript
const { accessToken } = await getTokens();

const response = await fetch(`${API_BASE_URL}/drive/storage/quota`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
  },
});
```

---

## How File Upload Works (API Side)

### Upload Flow

```
1. Frontend sends file with FormData
   ↓
2. API validates file size (max 100MB)
   ↓
3. API checks storage quota (5GB per user)
   ↓
4. API reads file content into memory
   ↓
5. API generates unique file_id
   ↓
6. API generates random content key
   ↓
7. API encrypts file with 3-layer encryption:
   - Layer 1: AES-256-GCM with content key
   - Layer 2: ChaCha20-Poly1305 with secondary key
   - Layer 3: AES-256-GCM with Scrypt-derived key
   ↓
8. API encrypts content key:
   - If passcode: encrypted with passcode-derived key
   - If no passcode: encrypted with user email-derived key
   ↓
9. API stores encrypted file in MongoDB
   ↓
10. API updates user storage usage
   ↓
11. API adds file_id to user's file list
   ↓
12. API returns file_id and metadata
```

### Upload Endpoint

**Endpoint:** `POST /drive/upload`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Form Data:**
- `file` (required): File to upload (max 100MB)
- `passcode` (optional): Passcode for file protection (min 4 chars)
- `expires_in_hours` (optional): Expiration time in hours (1-8760)

**Response (201 Created):**
```json
{
  "file_id": "Aa6wVDnKTqIY9Rwhv8aOhlRfEsE6ySLz5psMKcYCFaA",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": null,
  "created_at": "2026-01-29T20:45:51.168035"
}
```

### What Happens on the Server

1. **File Validation**
   - Maximum file size: 100MB
   - Empty files rejected
   - File type detection (content_type)

2. **Storage Quota Check**
   - Checks current storage usage
   - Verifies quota availability (5GB default)
   - Rejects upload if quota exceeded

3. **Encryption Process**
   - **Content Key**: Random 256-bit key generated
   - **File Encryption**: File encrypted with 3 layers using content key
   - **Key Encryption**: Content key encrypted with:
     - User email-derived key (if no passcode)
     - Passcode-derived key (if passcode provided)

4. **MongoDB Storage**
   - Encrypted file content stored in `files` collection
   - File metadata stored (filename, size, content_type, etc.)
   - Passcode salt stored (if passcode-protected)
   - Expiration timestamp stored (if provided)

5. **Storage Tracking**
   - User storage usage incremented
   - File ID added to user's file list
   - Storage tracked in Redis for fast queries

### Error Responses

**413 Payload Too Large** - File too large:
```json
{
  "detail": "File size exceeds maximum of 100MB"
}
```

**413 Payload Too Large** - Quota exceeded:
```json
{
  "detail": "Storage quota exceeded. Used: 4.95GB / 5.00GB. Available: 0.05GB"
}
```

**400 Bad Request** - Empty file:
```json
{
  "detail": "File is empty"
}
```

---

## How File Download Works (API Side)

### Download Flow

```
1. Frontend requests file download
   ↓
2. API verifies access:
   - Signed URL token (if provided), OR
   - Authentication + file ownership
   ↓
3. API retrieves file from MongoDB
   ↓
4. API checks file expiration
   ↓
5. If passcode-protected:
   - Check if unlocked (signed URL)
   - If not unlocked → return error
   ↓
6. API decrypts content key:
   - If passcode: use passcode-derived key
   - If authenticated: use user email-derived key
   ↓
7. API decrypts file content (3 layers)
   ↓
8. API streams decrypted file to client
   ↓
9. Client receives file
```

### Download Endpoint

**Endpoint:** `GET /drive/file/{file_id}/download`

**Headers:**
```
Authorization: Bearer {access_token}  (if not using signed URL)
```

**Query Parameters:**
- `token` (optional): Signed URL token for passcode-protected files

**Response (200 OK):**
- File stream with appropriate content-type
- `Content-Disposition` header with filename
- `Content-Length` header with file size

### Signed URLs

For passcode-protected files, you get a signed URL after unlocking:

**Signed URL Format:**
```
/drive/file/{file_id}/download?token={signed_token}
```

**Signed URL Features:**
- Time-limited (default: 1 hour)
- Cryptographically signed
- Cannot be forged
- Automatically expires

### What Happens on the Server

1. **Access Verification**
   - If signed URL token: verify signature and expiration
   - If authenticated: verify file ownership
   - Reject if neither valid

2. **File Retrieval**
   - Load encrypted file from MongoDB
   - Check file expiration
   - Verify file exists

3. **Decryption Process**
   - **Content Key Decryption**: Decrypt content key using:
     - User email-derived key (authenticated files)
     - Passcode-derived key (passcode-protected files)
   - **File Decryption**: Decrypt file content (3 layers)
   - **Streaming**: Stream decrypted content to client

4. **Security**
   - Server never stores decrypted files
   - Decryption happens on-the-fly
   - Passcode-protected files require unlock first

---

## How File Listing Works (API Side)

### List Flow

```
1. Frontend requests file list
   ↓
2. API verifies authentication
   ↓
3. API queries MongoDB for user's files
   ↓
4. API filters expired files
   ↓
5. API returns file metadata (no encrypted content)
   ↓
6. Frontend displays file list
```

### List Files Endpoint

**Endpoint:** `GET /drive/files`

**Note:** This endpoint was added to provide Google Drive-like file listing functionality.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional): Number of files to return (default: 50, max: 100)
- `offset` (optional): Offset for pagination (default: 0)

**Response (200 OK):**
```json
{
  "files": [
    {
      "file_id": "Aa6wVDnKTqIY9Rwhv8aOhlRfEsE6ySLz5psMKcYCFaA",
      "filename": "document.pdf",
      "size": 1048576,
      "content_type": "application/pdf",
      "passcode_protected": false,
      "created_at": "2026-01-29T20:45:51.168035",
      "expires_at": null
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

### What Happens on the Server

1. **Authentication Check**
   - Verifies JWT token
   - Extracts user email from token

2. **File Query**
   - Queries MongoDB `files` collection
   - Filters by `owner_email` (case-insensitive)
   - Excludes expired files
   - Sorts by `created_at` (newest first)

3. **Metadata Return**
   - Returns file metadata only (no encrypted content)
   - Includes: file_id, filename, size, content_type, created_at, expires_at
   - Includes total count for pagination

---

## Frontend Implementation

### Step 1: Check Storage Quota

Always check quota before uploading:

```javascript
async function checkStorageQuota(accessToken) {
  const response = await fetch(`${API_BASE_URL}/drive/storage/quota`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to get storage quota');
  }
  
  const quota = await response.json();
  return quota;
}

// Usage
const quota = await checkStorageQuota(accessToken);
console.log(`Used: ${quota.used_gb}GB / ${quota.quota_gb}GB`);
console.log(`Available: ${quota.available_gb}GB`);
```

### Step 2: Upload File

**React Native (Expo):**
```javascript
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';

async function uploadFile(accessToken, passcode = null, expiresInHours = null) {
  try {
    // Pick file
    const result = await DocumentPicker.getDocumentAsync({
      type: '*/*',
      copyToCacheDirectory: true,
    });
    
    if (result.canceled) {
      return { success: false, error: 'File selection cancelled' };
    }
    
    const fileUri = result.assets[0].uri;
    const filename = result.assets[0].name;
    const fileSize = result.assets[0].size;
    
    // Check quota first
    const quota = await checkStorageQuota(accessToken);
    if (fileSize > quota.available_bytes) {
      return {
        success: false,
        error: `File too large. Available: ${quota.available_gb}GB`,
      };
    }
    
    // Read file content
    const fileContent = await FileSystem.readAsStringAsync(fileUri, {
      encoding: FileSystem.EncodingType.Base64,
    });
    
    // Convert to blob
    const byteCharacters = atob(fileContent);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray]);
    
    // Create FormData
    const formData = new FormData();
    formData.append('file', {
      uri: fileUri,
      name: filename,
      type: 'application/octet-stream',
    });
    
    if (passcode) {
      formData.append('passcode', passcode);
    }
    
    if (expiresInHours) {
      formData.append('expires_in_hours', expiresInHours.toString());
    }
    
    // Upload file
    const response = await fetch(`${API_BASE_URL}/drive/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'multipart/form-data',
      },
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.detail || 'Upload failed',
        statusCode: response.status,
      };
    }
    
    const data = await response.json();
    return {
      success: true,
      file: data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Upload failed',
    };
  }
}
```

**Web (Browser):**
```javascript
async function uploadFile(accessToken, fileInput, passcode = null, expiresInHours = null) {
  try {
    const file = fileInput.files[0];
    
    if (!file) {
      return { success: false, error: 'No file selected' };
    }
    
    // Check quota first
    const quota = await checkStorageQuota(accessToken);
    if (file.size > quota.available_bytes) {
      return {
        success: false,
        error: `File too large. Available: ${quota.available_gb}GB`,
      };
    }
    
    // Create FormData
    const formData = new FormData();
    formData.append('file', file);
    
    if (passcode) {
      formData.append('passcode', passcode);
    }
    
    if (expiresInHours) {
      formData.append('expires_in_hours', expiresInHours.toString());
    }
    
    // Upload file
    const response = await fetch(`${API_BASE_URL}/drive/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        // Don't set Content-Type - browser will set it with boundary
      },
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.detail || 'Upload failed',
        statusCode: response.status,
      };
    }
    
    const data = await response.json();
    return {
      success: true,
      file: data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Upload failed',
    };
  }
}
```

### Step 3: List Files

```javascript
async function listFiles(accessToken, limit = 50, offset = 0) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/drive/files?limit=${limit}&offset=${offset}`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to list files');
    }
    
    return await response.json();
  } catch (error) {
    throw error;
  }
}

// Usage
const fileList = await listFiles(accessToken);
console.log(`Total files: ${fileList.total}`);
fileList.files.forEach(file => {
  console.log(`${file.filename} - ${(file.size / 1024 / 1024).toFixed(2)}MB`);
});
```

### Step 4: Get File Info

```javascript
async function getFileInfo(accessToken, fileId, signedUrlExpiresMinutes = 60) {
  try {
    const url = `${API_BASE_URL}/drive/file/${fileId}?signed_url_expires_minutes=${signedUrlExpiresMinutes}`;
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get file info');
    }
    
    return await response.json();
  } catch (error) {
    throw error;
  }
}
```

### Step 5: Download File

**Authenticated Download:**
```javascript
async function downloadFile(accessToken, fileId) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/drive/file/${fileId}/download`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Download failed');
    }
    
    // Get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
    const filename = filenameMatch ? filenameMatch[1] : 'download';
    
    // Get file blob
    const blob = await response.blob();
    
    // For React Native, save to file system
    // For Web, create download link
    
    return {
      blob,
      filename,
      contentType: response.headers.get('Content-Type'),
    };
  } catch (error) {
    throw error;
  }
}
```

**Signed URL Download (Passcode-Protected):**
```javascript
async function downloadFileWithSignedUrl(fileId, signedToken) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/drive/file/${fileId}/download?token=${signedToken}`,
      {
        // No Authorization header needed for signed URLs
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Download failed');
    }
    
    const blob = await response.blob();
    return blob;
  } catch (error) {
    throw error;
  }
}
```

### Step 6: Unlock Passcode-Protected File

```javascript
async function unlockFile(fileId, passcode) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/drive/file/${fileId}/unlock`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ passcode }),
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      
      if (response.status === 429) {
        throw new Error('Too many unlock attempts. Please try again later.');
      }
      
      if (response.status === 401) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail?.message || 
          `Incorrect passcode. ${errorData.detail?.attempts_remaining || 0} attempts remaining.`
        );
      }
      
      throw new Error(error.detail || 'Unlock failed');
    }
    
    const data = await response.json();
    
    // Extract signed token from signed_url
    const signedUrl = data.signed_url;
    const tokenMatch = signedUrl.match(/token=([^&]+)/);
    const signedToken = tokenMatch ? tokenMatch[1] : null;
    
    return {
      fileId: data.file_id,
      signedUrl: data.signed_url,
      signedToken: signedToken,
      expiresAt: data.signed_url_expires_at,
    };
  } catch (error) {
    throw error;
  }
}
```

### Step 7: Delete File

```javascript
async function deleteFile(accessToken, fileId) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/drive/file/${fileId}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Delete failed');
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    throw error;
  }
}
```

---

## Storage Quota Management

### Get Storage Quota

```javascript
async function getStorageQuota(accessToken) {
  const response = await fetch(`${API_BASE_URL}/drive/storage/quota`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to get storage quota');
  }
  
  return await response.json();
}
```

**Response:**
```json
{
  "used_bytes": 2147483648,
  "quota_bytes": 5368709120,
  "used_gb": 2.0,
  "quota_gb": 5.0,
  "available_bytes": 3221225472,
  "available_gb": 3.0,
  "percentage_used": 40.0
}
```

### Check Quota Before Upload

```javascript
async function canUploadFile(accessToken, fileSize) {
  const quota = await getStorageQuota(accessToken);
  return fileSize <= quota.available_bytes;
}

// Usage
const file = fileInput.files[0];
if (await canUploadFile(accessToken, file.size)) {
  await uploadFile(accessToken, fileInput);
} else {
  alert('Not enough storage space');
}
```

---

## Error Handling

### Common Error Scenarios

```javascript
async function handleDriveError(error, statusCode) {
  switch (statusCode) {
    case 400:
      return 'Invalid request. Please check your input.';
    
    case 401:
      return 'Authentication required. Please login.';
    
    case 403:
      return 'Access denied. You don\'t have permission to access this file.';
    
    case 404:
      return 'File not found or expired.';
    
    case 413:
      return 'File too large or storage quota exceeded.';
    
    case 429:
      return 'Too many unlock attempts. Please try again later.';
    
    case 500:
      return 'Server error. Please try again later.';
    
    default:
      return error || 'An unexpected error occurred.';
  }
}
```

### User-Friendly Error Messages

```javascript
function getUserFriendlyDriveError(error, statusCode) {
  const errorMessages = {
    400: {
      'File is empty': 'The selected file is empty. Please choose a different file.',
      'Invalid file': 'The selected file is invalid.',
    },
    401: {
      'Authentication required': 'Please login to upload files.',
      'Incorrect passcode': 'The passcode you entered is incorrect.',
    },
    403: {
      'Access denied': 'You don\'t have permission to access this file.',
    },
    404: {
      'File not found': 'The file you\'re looking for doesn\'t exist or has been deleted.',
      'File has expired': 'This file has expired and is no longer available.',
    },
    413: {
      'File size exceeds maximum': 'File is too large. Maximum size is 100MB.',
      'Storage quota exceeded': 'You\'ve reached your storage limit. Please delete some files.',
    },
    429: {
      'Too many unlock attempts': 'Too many failed attempts. Please wait before trying again.',
    },
  };
  
  const statusMessages = errorMessages[statusCode];
  if (statusMessages && statusMessages[error]) {
    return statusMessages[error];
  }
  
  return error || 'An error occurred. Please try again.';
}
```

---

## Security Best Practices

### 1. Always Check Quota Before Upload

```javascript
// ✅ GOOD
const quota = await getStorageQuota(accessToken);
if (file.size > quota.available_bytes) {
  alert('Not enough storage space');
  return;
}
await uploadFile(accessToken, file);

// ❌ BAD - Uploads without checking
await uploadFile(accessToken, file);
```

### 2. Handle Large Files Appropriately

```javascript
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

if (file.size > MAX_FILE_SIZE) {
  alert('File is too large. Maximum size is 100MB.');
  return;
}
```

### 3. Show Upload Progress

```javascript
async function uploadFileWithProgress(accessToken, file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);
  
  // Use XMLHttpRequest for progress tracking
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percentComplete = (e.loaded / e.total) * 100;
        onProgress(percentComplete);
      }
    });
    
    xhr.addEventListener('load', () => {
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error('Upload failed'));
      }
    });
    
    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'));
    });
    
    xhr.open('POST', `${API_BASE_URL}/drive/upload`);
    xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`);
    xhr.send(formData);
  });
}
```

### 4. Secure Passcode Handling

```javascript
// ✅ GOOD - Passcode only sent during upload/unlock
async function uploadWithPasscode(accessToken, file, passcode) {
  // Passcode sent securely over HTTPS
  // Never stored on client
  const formData = new FormData();
  formData.append('file', file);
  formData.append('passcode', passcode);
  
  return await uploadFile(accessToken, formData);
}

// ❌ BAD - Never store passcode
localStorage.setItem('file_passcode', passcode);
```

### 5. Handle Token Expiration

```javascript
async function downloadFileWithRetry(accessToken, fileId) {
  try {
    return await downloadFile(accessToken, fileId);
  } catch (error) {
    if (error.message.includes('401') || error.message.includes('expired')) {
      // Try to refresh token
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        const { accessToken: newToken } = await getTokens();
        return await downloadFile(newToken, fileId);
      } else {
        // Redirect to login
        navigateToLogin();
        throw new Error('Session expired. Please login again.');
      }
    }
    throw error;
  }
}
```

---

## Code Examples

### Complete File Manager Component (React Native)

```javascript
import React, { useState, useEffect } from 'react';
import { View, FlatList, Text, Button, Alert } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as SecureStore from 'expo-secure-store';

const FileManagerScreen = () => {
  const [files, setFiles] = useState([]);
  const [quota, setQuota] = useState(null);
  const [loading, setLoading] = useState(false);
  const [accessToken, setAccessToken] = useState(null);

  useEffect(() => {
    loadTokens();
    loadFiles();
    loadQuota();
  }, []);

  const loadTokens = async () => {
    const token = await SecureStore.getItemAsync('access_token');
    setAccessToken(token);
  };

  const loadFiles = async () => {
    if (!accessToken) return;
    
    setLoading(true);
    try {
      const fileList = await listFiles(accessToken);
      setFiles(fileList.files);
    } catch (error) {
      Alert.alert('Error', 'Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const loadQuota = async () => {
    if (!accessToken) return;
    
    try {
      const quotaData = await getStorageQuota(accessToken);
      setQuota(quotaData);
    } catch (error) {
      console.error('Failed to load quota:', error);
    }
  };

  const handleUpload = async () => {
    if (!accessToken) {
      Alert.alert('Error', 'Please login first');
      return;
    }

    try {
      // Check quota first
      const quotaData = await getStorageQuota(accessToken);
      
      // Pick file
      const result = await DocumentPicker.getDocumentAsync();
      if (result.canceled) return;
      
      const fileSize = result.assets[0].size;
      if (fileSize > quotaData.available_bytes) {
        Alert.alert(
          'Storage Full',
          `Not enough space. Available: ${quotaData.available_gb}GB`
        );
        return;
      }
      
      // Upload file
      const uploadResult = await uploadFile(accessToken);
      
      if (uploadResult.success) {
        Alert.alert('Success', 'File uploaded successfully');
        loadFiles();
        loadQuota();
      } else {
        Alert.alert('Error', uploadResult.error);
      }
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const handleDownload = async (fileId) => {
    try {
      const fileData = await downloadFile(accessToken, fileId);
      // Save file to device
      Alert.alert('Success', 'File downloaded');
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const handleDelete = async (fileId) => {
    Alert.alert(
      'Delete File',
      'Are you sure you want to delete this file?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteFile(accessToken, fileId);
              Alert.alert('Success', 'File deleted');
              loadFiles();
              loadQuota();
            } catch (error) {
              Alert.alert('Error', error.message);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={{ flex: 1, padding: 20 }}>
      {/* Storage Quota Display */}
      {quota && (
        <View style={{ marginBottom: 20 }}>
          <Text>Storage: {quota.used_gb}GB / {quota.quota_gb}GB</Text>
          <Text>{quota.percentage_used}% used</Text>
        </View>
      )}

      {/* Upload Button */}
      <Button title="Upload File" onPress={handleUpload} />

      {/* File List */}
      <FlatList
        data={files}
        keyExtractor={(item) => item.file_id}
        renderItem={({ item }) => (
          <View style={{ padding: 10, borderBottomWidth: 1 }}>
            <Text>{item.filename}</Text>
            <Text>{(item.size / 1024 / 1024).toFixed(2)} MB</Text>
            <View style={{ flexDirection: 'row', marginTop: 10 }}>
              <Button
                title="Download"
                onPress={() => handleDownload(item.file_id)}
              />
              <Button
                title="Delete"
                onPress={() => handleDelete(item.file_id)}
                color="red"
              />
            </View>
          </View>
        )}
        refreshing={loading}
        onRefresh={loadFiles}
      />
    </View>
  );
};
```

### Complete File Manager Component (Web)

```javascript
import React, { useState, useEffect } from 'react';

const FileManager = () => {
  const [files, setFiles] = useState([]);
  const [quota, setQuota] = useState(null);
  const [loading, setLoading] = useState(false);
  const [accessToken, setAccessToken] = useState(null);

  useEffect(() => {
    loadTokens();
    loadFiles();
    loadQuota();
  }, []);

  const loadTokens = () => {
    const token = localStorage.getItem('access_token');
    setAccessToken(token);
  };

  const loadFiles = async () => {
    if (!accessToken) return;
    
    setLoading(true);
    try {
      const fileList = await listFiles(accessToken);
      setFiles(fileList.files);
    } catch (error) {
      alert('Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const loadQuota = async () => {
    if (!accessToken) return;
    
    try {
      const quotaData = await getStorageQuota(accessToken);
      setQuota(quotaData);
    } catch (error) {
      console.error('Failed to load quota:', error);
    }
  };

  const handleFileSelect = async (event) => {
    const fileInput = event.target;
    if (!fileInput.files[0]) return;

    try {
      // Check quota
      const quotaData = await getStorageQuota(accessToken);
      const file = fileInput.files[0];
      
      if (file.size > quotaData.available_bytes) {
        alert(`Not enough space. Available: ${quotaData.available_gb}GB`);
        return;
      }

      // Upload file
      const result = await uploadFile(accessToken, fileInput);
      
      if (result.success) {
        alert('File uploaded successfully');
        loadFiles();
        loadQuota();
      } else {
        alert(result.error);
      }
    } catch (error) {
      alert(error.message);
    }
  };

  const handleDownload = async (fileId) => {
    try {
      const fileData = await downloadFile(accessToken, fileId);
      
      // Create download link
      const url = window.URL.createObjectURL(fileData.blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileData.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      alert(error.message);
    }
  };

  const handleDelete = async (fileId) => {
    if (!confirm('Are you sure you want to delete this file?')) {
      return;
    }

    try {
      await deleteFile(accessToken, fileId);
      alert('File deleted');
      loadFiles();
      loadQuota();
    } catch (error) {
      alert(error.message);
    }
  };

  return (
    <div>
      {/* Storage Quota */}
      {quota && (
        <div>
          <p>Storage: {quota.used_gb}GB / {quota.quota_gb}GB</p>
          <p>{quota.percentage_used}% used</p>
        </div>
      )}

      {/* Upload */}
      <input
        type="file"
        onChange={handleFileSelect}
        disabled={!accessToken}
      />

      {/* File List */}
      <ul>
        {files.map((file) => (
          <li key={file.file_id}>
            <div>
              <strong>{file.filename}</strong>
              <span> - {(file.size / 1024 / 1024).toFixed(2)} MB</span>
            </div>
            <button onClick={() => handleDownload(file.file_id)}>
              Download
            </button>
            <button onClick={() => handleDelete(file.file_id)}>
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};
```

---

## Summary

### Key Points

1. **Authentication Required**
   - All endpoints require `Authorization: Bearer {access_token}` header
   - Use same authentication as email/messaging APIs

2. **File Upload Process:**
   - Check storage quota first
   - Upload file with FormData
   - File encrypted with 3 layers automatically
   - Storage usage tracked automatically

3. **File Download Process:**
   - Authenticated users can download their files
   - Passcode-protected files require unlock first
   - Signed URLs for secure sharing

4. **File Listing:**
   - Get all user's files with `/drive/files`
   - Pagination supported (limit/offset)
   - Returns metadata only (no encrypted content)

5. **Storage Management:**
   - 5GB quota per user (default)
   - Check quota before upload
   - Quota automatically updated on upload/delete

### Quick Reference

**Upload File:**
```javascript
POST /drive/upload
Headers: { Authorization: "Bearer {access_token}" }
Body: FormData { file, passcode?, expires_in_hours? }
```

**List Files:**
```javascript
GET /drive/files?limit=50&offset=0
Headers: { Authorization: "Bearer {access_token}" }
```

**Get File Info:**
```javascript
GET /drive/file/{file_id}?signed_url_expires_minutes=60
Headers: { Authorization: "Bearer {access_token}" }
```

**Download File:**
```javascript
GET /drive/file/{file_id}/download?token={signed_token}
Headers: { Authorization: "Bearer {access_token}" } (if no token)
```

**Unlock File:**
```javascript
POST /drive/file/{file_id}/unlock
Body: { passcode: "..." }
```

**Delete File:**
```javascript
DELETE /drive/file/{file_id}
Headers: { Authorization: "Bearer {access_token}" }
```

**Get Storage Quota:**
```javascript
GET /drive/storage/quota
Headers: { Authorization: "Bearer {access_token}" }
```

---

For more information, see the main [API Documentation](./API_README.md) and [Authentication Guide](./AUTHENTICATION_GUIDE.md).
