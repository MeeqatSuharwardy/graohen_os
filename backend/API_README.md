# API Documentation for Mobile App Development

Complete API reference for building mobile applications with end-to-end encryption support.

## Table of Contents

- [Understanding End-to-End Encryption](#understanding-end-to-end-encryption)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Email API](#email-api)
- [Drive API](#drive-api)
- [Messaging API](#messaging-api)
- [Error Handling](#error-handling)
- [End-to-End Encryption Guide](#end-to-end-encryption-guide)

---

## Understanding End-to-End Encryption

### What is End-to-End Encryption?

End-to-end encryption (E2E) means that your data is encrypted **on your device** before it's sent to the server, and **only you (or the intended recipient) can decrypt it**. The server acts as a secure mailbox - it stores your encrypted data but **never has the keys to read it**.

### Multi-Layer Encryption (Maximum Security)

This API uses **3 layers of encryption** to make decryption extremely difficult:

1. **Layer 1: AES-256-GCM** - Industry-standard encryption
2. **Layer 2: ChaCha20-Poly1305** - Alternative encryption algorithm
3. **Layer 3: AES-256-GCM with Scrypt** - Memory-hard key derivation

Even if one layer is compromised, the data remains protected by the other layers. This makes it **extremely difficult** for attackers to decrypt your data, even with significant computational resources.

### Database Storage (MongoDB)

All encrypted emails and files are stored in **MongoDB** (not Redis):
- **Emails**: Stored in `emails` collection with full encryption
- **Files**: Stored in `files` collection with full encryption
- **Server never sees plaintext** - only encrypted ciphertext is stored
- **Automatic expiration** - Expired emails/files are automatically cleaned up

### Email Server (SMTP)

The backend includes an **email sending server** that:
- Sends notification emails via **fxmail.ai** domain
- Uses SMTP to deliver encrypted email notifications
- Recipients receive a secure link to access encrypted emails
- Email domain: `fxmail.ai` (all emails sent from `token@fxmail.ai` format)

Think of it like this:
- **Without E2E**: You write a letter, put it in an envelope, and give it to a mail carrier. The carrier can open and read your letter.
- **With E2E**: You write a letter, put it in a locked box (encrypt it), and give the locked box to a mail carrier. The carrier can deliver it, but **cannot open the box** because they don't have the key.

### How It Works in This API

#### 1. **Device Encryption Key (Your Master Key)**

When a user first launches your app:
- Your app generates a **256-bit encryption key** (32 random bytes)
- This key is stored **only on the user's device** (never sent to server)
- It's like a master key that locks/unlocks all the user's data

```
First App Launch:
┌─────────────────┐
│  Your Mobile    │
│     Device      │
│                 │
│  Generate Key   │ → Store locally (Keychain/SecureStore)
│  (32 bytes)     │   Never send to server!
└─────────────────┘
```

#### 2. **Encrypting Data Before Sending**

When you want to send a message or upload a file:

**Step 1: Generate a Content Key**
- Create a random key just for this piece of content
- This is like a unique lock for each message/file

**Step 2: Encrypt the Content**
- Encrypt your message/file using the content key
- Result: Encrypted ciphertext (unreadable without the key)

**Step 3: Encrypt the Content Key**
- Encrypt the content key using your device key
- Result: Encrypted content key (only you can decrypt this)

**Step 4: Send to Server**
- Send both encrypted pieces to the server
- Server stores them but **cannot read anything**

```
Encryption Flow:
┌─────────────────────────────────────────┐
│  Your Device                            │
│                                         │
│  1. Original File/Message               │
│     ↓                                   │
│  2. Generate Content Key (random)      │
│     ↓                                   │
│  3. Encrypt Content → Encrypted Content │
│     ↓                                   │
│  4. Encrypt Content Key → Encrypted Key │
│     (using Device Key)                  │
│     ↓                                   │
│  5. Send Both to Server                 │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  Server                                  │
│                                         │
│  Stores:                                │
│  - Encrypted Content (can't read)       │
│  - Encrypted Key (can't read)           │
│                                         │
│  Server has NO keys = Can't decrypt!   │
└─────────────────────────────────────────┘
```

#### 3. **Decrypting Data After Receiving**

When you download a file or receive a message:

**Step 1: Get Encrypted Data**
- Retrieve encrypted content and encrypted key from server

**Step 2: Decrypt the Content Key**
- Use your device key to decrypt the content key
- Now you have the content key in plaintext

**Step 3: Decrypt the Content**
- Use the content key to decrypt the actual content
- Now you have your original file/message

```
Decryption Flow:
┌─────────────────────────────────────────┐
│  Server                                  │
│                                         │
│  Sends:                                 │
│  - Encrypted Content                    │
│  - Encrypted Key                        │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  Your Device                            │
│                                         │
│  1. Receive Encrypted Data              │
│     ↓                                   │
│  2. Decrypt Key → Content Key           │
│     (using Device Key)                  │
│     ↓                                   │
│  3. Decrypt Content → Original File     │
│     (using Content Key)                 │
└─────────────────────────────────────────┘
```

### Two Types of Encryption in This API

#### Type 1: Server-Side Encryption (Easier, Less Secure)

**Used by:** `/email/send` and `/drive/upload`

- You send **plaintext** (unencrypted) data to the server
- Server encrypts it for you
- **Server can see your data** before encrypting
- Easier to implement, but server has access

**When to use:** For convenience when maximum security isn't critical

#### Type 2: Client-Side Encryption (True E2E, More Secure)

**Used by:** `/drive/upload-encrypted` and `/messaging/send`

- You encrypt data **on your device** before sending
- Server only receives encrypted ciphertext
- **Server never sees your data**
- More secure, requires encryption code in your app

**When to use:** For maximum security and privacy

### Key Concepts Explained

#### **Device Encryption Key**
- **What:** A master key unique to each device
- **Where:** Stored only on the device (never on server)
- **Purpose:** Used to encrypt/decrypt content keys
- **Security:** If device key is lost, data cannot be recovered (by design)

#### **Content Key**
- **What:** A random key generated for each piece of content
- **Where:** Encrypted and stored on server
- **Purpose:** Used to encrypt/decrypt the actual content
- **Security:** Each file/message has its own unique key

#### **Encryption Algorithms Used**

**Layer 1: AES-256-GCM**
- **AES-256:** Advanced Encryption Standard with 256-bit keys (very secure)
- **GCM:** Galois/Counter Mode (provides authentication - detects tampering)
- **Why:** Industry standard, used by banks and governments

**Layer 2: ChaCha20-Poly1305**
- **ChaCha20:** Stream cipher (alternative to AES)
- **Poly1305:** Authentication tag (detects tampering)
- **Why:** Different algorithm makes attacks harder, fast on mobile devices

**Layer 3: AES-256-GCM with Scrypt**
- **Scrypt:** Memory-hard key derivation function
- **Why:** Makes brute-force attacks extremely expensive (requires lots of memory)
- **Combined with AES-256-GCM** for final encryption layer

**Multi-Layer Benefits:**
- Even if one algorithm is broken, others remain secure
- Different algorithms require different attack methods
- Memory-hard key derivation prevents GPU-based attacks
- Multiple authentication tags prevent tampering

### Why This Matters

#### **Privacy**
- Your messages/files are private - even the server admins can't read them
- Only you and intended recipients can decrypt

#### **Security**
- If server is hacked, attackers only get encrypted data (useless without keys)
- Your device key never leaves your device

#### **Trust**
- You don't need to trust the server with your data
- Mathematical security, not just policy-based security

### What the Server Knows vs. Doesn't Know

**Server CAN see:**
- ✅ Who sent a message/file (email addresses)
- ✅ When it was sent (timestamps)
- ✅ File size and metadata
- ✅ Who has access (recipients)

**Server CANNOT see:**
- ❌ Message/file content (encrypted)
- ❌ Encryption keys (never sent)
- ❌ Decrypted data (never decrypted on server)

### Real-World Example: Sending a Photo

**Without E2E:**
```
You → [Photo] → Server (sees photo) → Recipient
```

**With E2E:**
```
You → [Encrypt Photo] → Server (sees gibberish) → Recipient → [Decrypt Photo]
```

The server receives something like: `aGVsbG8gd29ybGQK` (encrypted data) instead of your actual photo.

### Important Security Notes

1. **Never send device keys to the server** - They stay on the device
2. **Use secure storage** - Store keys in Keychain (iOS) or Keystore (Android)
3. **Generate keys securely** - Use cryptographically secure random number generators
4. **Protect the device** - If device is compromised, keys could be stolen
5. **Backup considerations** - If device key is lost, data cannot be recovered

### Quick Reference: Encryption Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ENCRYPTION (Upload)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Original File                                              │
│       ↓                                                     │
│  Generate Content Key (random 32 bytes)                    │
│       ↓                                                     │
│  Encrypt File with Content Key → Encrypted File            │
│       ↓                                                     │
│  Encrypt Content Key with Device Key → Encrypted Key       │
│       ↓                                                     │
│  Send Both to Server                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   DECRYPTION (Download)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Receive Encrypted File + Encrypted Key from Server        │
│       ↓                                                     │
│  Decrypt Key with Device Key → Content Key                 │
│       ↓                                                     │
│  Decrypt File with Content Key → Original File             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Now that you understand how encryption works, let's dive into the API endpoints!

---

## Base URL

```
Production: https://your-domain.com/api/v1
Development: http://localhost:8000/api/v1
```

All endpoints require authentication unless specified otherwise.

---

## Authentication

### Register User

Create a new user account.

**Endpoint:** `POST /auth/register`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "device_id": "optional-device-id"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_id": "device-id-generated"
}
```

**Example (JavaScript/React Native):**
```javascript
const registerUser = async (email, password, fullName) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
    }),
  });
  
  const data = await response.json();
  
  if (response.ok) {
    // Store tokens securely (e.g., SecureStore in React Native)
    await SecureStore.setItemAsync('access_token', data.access_token);
    await SecureStore.setItemAsync('refresh_token', data.refresh_token);
    return data;
  } else {
    throw new Error(data.detail || 'Registration failed');
  }
};
```

### Login

Authenticate and get access tokens.

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "device_id": "optional-device-id"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_id": "device-id"
}
```

**Example:**
```javascript
const login = async (email, password) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  
  const data = await response.json();
  
  if (response.ok) {
    await SecureStore.setItemAsync('access_token', data.access_token);
    await SecureStore.setItemAsync('refresh_token', data.refresh_token);
    return data;
  } else {
    throw new Error(data.detail || 'Login failed');
  }
};
```

### Using Access Token

Include the access token in the `Authorization` header for all protected endpoints:

```javascript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json',
};
```

### Refresh Token

**Endpoint:** `POST /auth/refresh`

**Request:**
```json
{
  "refresh_token": "your-refresh-token"
}
```

**Response:**
```json
{
  "access_token": "new-access-token",
  "refresh_token": "new-refresh-token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## Email API

### Email Server & Storage

**Email Server:**
- All emails are sent via **fxmail.ai** domain
- SMTP server handles email delivery
- Recipients receive notification emails with secure links
- Email addresses format: `{token}@fxmail.ai`

**Storage:**
- Emails stored in **MongoDB** database (not Redis)
- All data encrypted with **3-layer encryption** before storage
- Server never sees plaintext content
- Automatic expiration and cleanup

**Encryption:**
- Uses multi-layer encryption (AES-256-GCM + ChaCha20-Poly1305 + Scrypt)
- Makes decryption extremely difficult even if one layer is compromised
- Content keys encrypted separately from content
- Maximum security for sensitive communications

### Send Encrypted Email

Send an encrypted email. The email content is encrypted with **multi-layer encryption** and stored in MongoDB. Recipients receive notification emails via fxmail.ai domain.

**Endpoint:** `POST /email/send`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "to": ["recipient@example.com"],
  "subject": "Optional Subject",
  "body": "Email body content",
  "passcode": "optional-passcode",
  "expires_in_hours": 24,
  "self_destruct": false
}
```

**Request Fields:**
- `to` (required): Array of recipient email addresses
- `subject` (optional): Email subject (max 500 chars)
- `body` (required): Email body content
- `passcode` (optional): Additional passcode protection (min 4 chars)
- `expires_in_hours` (optional): Expiration time in hours (1-8760)
- `self_destruct` (optional): Delete after first read (default: false)

**Response:**
```json
{
  "email_id": "z5LVkIi8tELLPfYABwaJLmaSpeOwBpFjmsAoyco60rQ",
  "email_address": "z5LVkIi8tELLPfYABwaJLmaSpeOwBpFjmsAoyco60rQ@fxmail.ai",
  "secure_link": "https://fxmail.ai/email/z5LVkIi8tELLPfYABwaJLmaSpeOwBpFjmsAoyco60rQ",
  "expires_at": "2026-01-30T20:45:51.168035",
  "encryption_mode": "authenticated"
}
```

**What Happens:**
1. Your email content is encrypted with **3 layers of encryption**
2. Encrypted data is stored in **MongoDB** database
3. **SMTP server** sends notification email to recipients via `fxmail.ai`
4. Recipients receive email with secure link to access encrypted content
5. Server **never sees plaintext** - only encrypted ciphertext

**Email Delivery:**
- Notification emails are sent automatically to all recipients
- Email sent from: `{token}@fxmail.ai`
- Recipients can click secure link to decrypt and view email
- Email content remains encrypted until recipient decrypts it

**Example:**
```javascript
const sendEmail = async (recipients, subject, body, accessToken) => {
  const response = await fetch('http://localhost:8000/api/v1/email/send', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      to: recipients,
      subject: subject || null,
      body: body,
      expires_in_hours: 24,
    }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send email');
  }
  
  return await response.json();
};
```

### Get Email (Authenticated Users)

Retrieve an encrypted email. Only works for emails sent in authenticated mode (no passcode).

**Endpoint:** `GET /email/{email_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "email_id": "z5LVkIi8tELLPfYABwaJLmaSpeOwBpFjmsAoyco60rQ",
  "subject": "Email Subject",
  "body": "Decrypted email body content",
  "encryption_mode": "authenticated",
  "expires_at": "2026-01-30T20:45:51.168035",
  "is_passcode_protected": false
}
```

**Example:**
```javascript
const getEmail = async (emailId, accessToken) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/email/${emailId}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to retrieve email');
  }
  
  return await response.json();
};
```

### Unlock Passcode-Protected Email

Unlock an email protected with a passcode.

**Endpoint:** `POST /email/{email_id}/unlock`

**Request:**
```json
{
  "passcode": "user-passcode"
}
```

**Response:**
```json
{
  "email_id": "z5LVkIi8tELLPfYABwaJLmaSpeOwBpFjmsAoyco60rQ",
  "subject": "Email Subject",
  "body": "Decrypted email body",
  "unlocked_at": "2026-01-29T20:45:51.168035"
}
```

**Rate Limiting:**
- Maximum 5 unlock attempts per hour per email
- After 5 failed attempts, email is locked for 1 hour

**Example:**
```javascript
const unlockEmail = async (emailId, passcode) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/email/${emailId}/unlock`,
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
    throw new Error(error.detail || 'Failed to unlock email');
  }
  
  return await response.json();
};
```

### Delete Email

Delete an email (only if you are the sender).

**Endpoint:** `DELETE /email/{email_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "email_id": "z5LVkIi8tELLPfYABwaJLmaSpeOwBpFjmsAoyco60rQ",
  "deleted": true,
  "message": "Email deleted successfully"
}
```

---

## Drive API

### Drive Storage & Database

**Storage:**
- Files stored in **MongoDB** database (not Redis)
- All files encrypted with **multi-layer encryption** before storage
- 5GB storage quota per user (enforced)
- Storage usage tracked automatically

**Encryption:**
- Files encrypted with 3 layers (same as emails)
- Content keys encrypted separately
- Server never sees plaintext file content
- Maximum security for file storage

**File Management:**
- Upload, download, delete operations
- Storage quota tracking and enforcement
- Automatic cleanup of expired files
- Support for both server-side and client-side encryption

### Get Storage Quota

Get storage quota information for the current user.

**Endpoint:** `GET /drive/storage/quota`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "used_bytes": 1048576,
  "quota_bytes": 5368709120,
  "used_gb": 0.0,
  "quota_gb": 5.0,
  "available_bytes": 5367659520,
  "available_gb": 5.0,
  "percentage_used": 0.02
}
```

**Example:**
```javascript
const getStorageQuota = async (accessToken) => {
  const response = await fetch(
    'http://localhost:8000/api/v1/drive/storage/quota',
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to get storage quota');
  }
  
  return await response.json();
};
```

### Upload File

Upload and encrypt a file. File is encrypted server-side.

**Endpoint:** `POST /drive/upload`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Request (Form Data):**
- `file` (required): File to upload
- `passcode` (optional): Additional passcode protection
- `expires_in_hours` (optional): Expiration time in hours (1-8760)

**Response:**
```json
{
  "file_id": "Aa6wVDnKTqIY9Rwhv8aOhlRfEsE6ySLz5psMKcYCFaA",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": "2026-01-30T20:45:51.168035",
  "created_at": "2026-01-29T20:45:51.168035"
}
```

**Example (React Native):**
```javascript
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';

const uploadFile = async (fileUri, filename, accessToken, passcode = null) => {
  // Read file as base64
  const fileBase64 = await FileSystem.readAsStringAsync(fileUri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  
  // Create form data
  const formData = new FormData();
  formData.append('file', {
    uri: fileUri,
    type: 'application/octet-stream',
    name: filename,
  });
  
  if (passcode) {
    formData.append('passcode', passcode);
  }
  
  formData.append('expires_in_hours', '168'); // 7 days
  
  const response = await fetch(
    'http://localhost:8000/api/v1/drive/upload',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'multipart/form-data',
      },
      body: formData,
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    if (response.status === 413) {
      throw new Error('Storage quota exceeded or file too large');
    }
    throw new Error(error.detail || 'Failed to upload file');
  }
  
  return await response.json();
};
```

### Upload Encrypted File (E2E)

Upload a file that is already encrypted on the client-side. This provides true end-to-end encryption where the server never sees plaintext.

**Endpoint:** `POST /drive/upload-encrypted`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "encrypted_content": {
    "ciphertext": "base64-encoded-ciphertext",
    "nonce": "base64-encoded-nonce",
    "tag": "base64-encoded-tag"
  },
  "encrypted_content_key": {
    "ciphertext": "base64-encoded-key-ciphertext",
    "nonce": "base64-encoded-key-nonce",
    "tag": "base64-encoded-key-tag"
  },
  "passcode": "optional-passcode",
  "expires_in_hours": 168
}
```

**Response:**
```json
{
  "file_id": "0i8_pBTcCsHLz1tdQTS3BovRVzA4AW2Q5OLNBeH9RpQ",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": "2026-02-05T20:45:51.168035",
  "created_at": "2026-01-29T20:45:51.168035"
}
```

**Example:**
```javascript
import * as Crypto from 'expo-crypto';

const uploadEncryptedFile = async (
  fileData,
  filename,
  fileSize,
  contentType,
  deviceKey,
  accessToken
) => {
  // Generate random content key
  const contentKey = await Crypto.getRandomBytesAsync(32);
  
  // Encrypt file content with content key (using AES-256-GCM)
  const encryptedContent = await encryptAES256GCM(fileData, contentKey);
  
  // Encrypt content key with device key
  const encryptedContentKey = await encryptAES256GCM(contentKey, deviceKey);
  
  const response = await fetch(
    'http://localhost:8000/api/v1/drive/upload-encrypted',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        filename,
        size: fileSize,
        content_type: contentType,
        encrypted_content: {
          ciphertext: encryptedContent.ciphertext,
          nonce: encryptedContent.nonce,
          tag: encryptedContent.tag,
        },
        encrypted_content_key: {
          ciphertext: encryptedContentKey.ciphertext,
          nonce: encryptedContentKey.nonce,
          tag: encryptedContentKey.tag,
        },
      }),
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to upload encrypted file');
  }
  
  return await response.json();
};
```

### Get File Info

Get file information and generate a signed download URL.

**Endpoint:** `GET /drive/file/{file_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `signed_url_expires_minutes` (optional): Expiration time for signed URL (default: 60)

**Response:**
```json
{
  "file_id": "Aa6wVDnKTqIY9Rwhv8aOhlRfEsE6ySLz5psMKcYCFaA",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "owner_email": "user@example.com",
  "expires_at": "2026-01-30T20:45:51.168035",
  "created_at": "2026-01-29T20:45:51.168035",
  "signed_url": "/api/v1/drive/file/{file_id}/download?token=...",
  "signed_url_expires_at": "2026-01-29T21:45:55.546211"
}
```

**Example:**
```javascript
const getFileInfo = async (fileId, accessToken) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/drive/file/${fileId}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get file info');
  }
  
  return await response.json();
};
```

### Download File

Download a file using a signed URL or authentication token.

**Endpoint:** `GET /drive/file/{file_id}/download`

**Headers:**
```
Authorization: Bearer {access_token}  (or use token query parameter)
```

**Query Parameters:**
- `token` (optional): Signed URL token (if using signed URL)

**Response:**
- File content (binary)

**Example:**
```javascript
const downloadFile = async (fileId, signedUrl, accessToken) => {
  const url = signedUrl 
    ? `http://localhost:8000${signedUrl}`
    : `http://localhost:8000/api/v1/drive/file/${fileId}/download`;
  
  const headers = signedUrl 
    ? {} 
    : { 'Authorization': `Bearer ${accessToken}` };
  
  const response = await fetch(url, {
    method: 'GET',
    headers,
  });
  
  if (!response.ok) {
    throw new Error('Failed to download file');
  }
  
  // For React Native, save to file system
  const blob = await response.blob();
  const fileUri = FileSystem.documentDirectory + filename;
  await FileSystem.writeAsStringAsync(fileUri, blob, {
    encoding: FileSystem.EncodingType.Base64,
  });
  
  return fileUri;
};
```

### Unlock Passcode-Protected File

Unlock a file protected with a passcode.

**Endpoint:** `POST /drive/file/{file_id}/unlock`

**Request:**
```json
{
  "passcode": "user-passcode"
}
```

**Response:**
```json
{
  "file_id": "Aa6wVDnKTqIY9Rwhv8aOhlRfEsE6ySLz5psMKcYCFaA",
  "signed_url": "/api/v1/drive/file/{file_id}/download?token=...",
  "signed_url_expires_at": "2026-01-29T21:45:55.546211",
  "unlocked_at": "2026-01-29T20:45:51.168035"
}
```

**Rate Limiting:**
- Maximum 5 unlock attempts per hour per file
- After 5 failed attempts, file is locked for 1 hour

### Delete File

Delete a file.

**Endpoint:** `DELETE /drive/file/{file_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "file_id": "Aa6wVDnKTqIY9Rwhv8aOhlRfEsE6ySLz5psMKcYCFaA",
  "deleted": true,
  "message": "File deleted successfully"
}
```

**Example:**
```javascript
const deleteFile = async (fileId, accessToken) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/drive/file/${fileId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete file');
  }
  
  return await response.json();
};
```

---

## Messaging API

### Send Encrypted Message

Send an end-to-end encrypted message. Message must be encrypted client-side before sending.

**Endpoint:** `POST /messaging/send`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "recipient_email": "recipient@example.com",
  "encrypted_content": {
    "ciphertext": "base64-encoded-ciphertext",
    "nonce": "base64-encoded-nonce",
    "tag": "base64-encoded-tag"
  },
  "encrypted_content_key": {
    "ciphertext": "base64-encoded-key-ciphertext",
    "nonce": "base64-encoded-key-nonce",
    "tag": "base64-encoded-key-tag"
  },
  "message_type": "text",
  "metadata": {
    "filename": "optional-for-file-messages"
  }
}
```

**Response:**
```json
{
  "message_id": "mDmiGWMiEm2Rhh5J43Bbvdh4TyVBjhQSv4ow_rMUZuM",
  "recipient_email": "recipient@example.com",
  "sent_at": "2026-01-29T20:46:22.975629",
  "expires_at": "2026-02-27T20:46:22.969010"
}
```

**Example:**
```javascript
const sendMessage = async (
  recipientEmail,
  messageText,
  recipientPublicKey,
  deviceKey,
  accessToken
) => {
  // Encrypt message content with random key
  const contentKey = await Crypto.getRandomBytesAsync(32);
  const encryptedContent = await encryptAES256GCM(
    new TextEncoder().encode(messageText),
    contentKey
  );
  
  // Encrypt content key with recipient's public key (or shared secret)
  const encryptedContentKey = await encryptWithPublicKey(
    contentKey,
    recipientPublicKey
  );
  
  const response = await fetch(
    'http://localhost:8000/api/v1/messaging/send',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        recipient_email: recipientEmail,
        encrypted_content: {
          ciphertext: base64Encode(encryptedContent.ciphertext),
          nonce: base64Encode(encryptedContent.nonce),
          tag: base64Encode(encryptedContent.tag),
        },
        encrypted_content_key: {
          ciphertext: base64Encode(encryptedContentKey.ciphertext),
          nonce: base64Encode(encryptedContentKey.nonce),
          tag: base64Encode(encryptedContentKey.tag),
        },
        message_type: 'text',
      }),
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send message');
  }
  
  return await response.json();
};
```

### Get Messages

Get encrypted messages for the current user.

**Endpoint:** `GET /messaging/messages`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional): Number of messages to return (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response:**
```json
[
  {
    "message_id": "mDmiGWMiEm2Rhh5J43Bbvdh4TyVBjhQSv4ow_rMUZuM",
    "sender_email": "sender@example.com",
    "recipient_email": "recipient@example.com",
    "encrypted_content": {
      "ciphertext": "...",
      "nonce": "...",
      "tag": "..."
    },
    "encrypted_content_key": {
      "ciphertext": "...",
      "nonce": "...",
      "tag": "..."
    },
    "message_type": "text",
    "metadata": {},
    "sent_at": "2026-01-29T20:46:22.975629",
    "expires_at": "2026-02-27T20:46:22.969010"
  }
]
```

**Example:**
```javascript
const getMessages = async (accessToken, limit = 50, offset = 0) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/messaging/messages?limit=${limit}&offset=${offset}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to get messages');
  }
  
  const messages = await response.json();
  
  // Decrypt messages client-side
  return messages.map(msg => ({
    ...msg,
    decrypted_content: decryptMessage(msg, deviceKey), // Implement decryption
  }));
};
```

### Get Conversation

Get messages in a conversation with a specific participant.

**Endpoint:** `GET /messaging/conversation/{participant_email}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional): Number of messages (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response:**
```json
{
  "conversation_id": "conv_abc123",
  "messages": [...],
  "total": 10
}
```

### Get Conversations

Get list of all conversations.

**Endpoint:** `GET /messaging/conversations`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
[
  {
    "conversation_id": "conv_abc123",
    "participant_email": "user@example.com",
    "last_message_at": "2026-01-29T20:46:22.975629",
    "unread_count": 0
  }
]
```

### Delete Message

Delete a message (only if you are sender or recipient).

**Endpoint:** `DELETE /messaging/message/{message_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "message_id": "mDmiGWMiEm2Rhh5J43Bbvdh4TyVBjhQSv4ow_rMUZuM",
  "deleted": true
}
```

---

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or invalid token
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `413 Payload Too Large`: File too large or storage quota exceeded
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

### Handling Errors

```javascript
const handleApiError = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
    }));
    
    switch (response.status) {
      case 401:
        // Token expired, refresh or re-login
        await refreshToken();
        throw new Error('Session expired. Please try again.');
      case 403:
        throw new Error('Access denied: ' + error.detail);
      case 404:
        throw new Error('Resource not found');
      case 413:
        throw new Error('File too large or storage quota exceeded');
      case 429:
        throw new Error('Too many requests. Please try again later.');
      default:
        throw new Error(error.detail || 'An error occurred');
    }
  }
};
```

---

## End-to-End Encryption Guide

### Overview

The API supports true end-to-end encryption where:
- **Encryption happens on the client device** before data leaves
- **Server only stores encrypted ciphertext** (never sees plaintext)
- **Only the intended recipient can decrypt** using their private key
- **Server never has access to encryption keys**

### Multi-Layer Encryption Explained

**Why Multiple Layers?**

Using multiple encryption layers makes it **extremely difficult** to decrypt data, even if one layer is compromised. Think of it like multiple locks on a safe - even if someone breaks one lock, the others remain secure.

**The 3 Layers:**

1. **Layer 1: AES-256-GCM**
   - Industry-standard encryption algorithm
   - Used by banks and governments
   - 256-bit keys (extremely secure)
   - Provides authentication (detects tampering)

2. **Layer 2: ChaCha20-Poly1305**
   - Alternative encryption algorithm
   - Different from AES (harder to attack both)
   - Also provides authentication
   - Fast and secure

3. **Layer 3: AES-256-GCM with Scrypt**
   - Uses Scrypt for key derivation (memory-hard)
   - Makes brute-force attacks extremely expensive
   - Requires significant memory to attack
   - Combined with AES-256-GCM for final layer

**Security Benefits:**
- Even if attacker breaks Layer 1, Layers 2 and 3 remain secure
- Different algorithms make attacks more difficult
- Memory-hard key derivation prevents GPU-based attacks
- Multiple authentication tags prevent tampering

### Database Storage (MongoDB)

**Why MongoDB?**

MongoDB provides:
- **Persistent storage** (data survives server restarts)
- **Scalability** (handles large amounts of data)
- **Flexible schema** (easy to store encrypted data structures)
- **Automatic indexing** (fast lookups)

**What's Stored:**

**Emails Collection:**
```json
{
  "email_id": "unique-id",
  "access_token": "public-token",
  "sender_email": "sender@example.com",
  "recipient_emails": ["recipient@example.com"],
  "encrypted_content": {
    "ciphertext": "encrypted-data",
    "layers": 3,
    "metadata": [...]
  },
  "encrypted_content_key": {
    "ciphertext": "encrypted-key",
    "layers": 3,
    "metadata": [...]
  },
  "encryption_mode": "authenticated",
  "created_at": "2026-01-29T00:00:00",
  "expires_at": "2026-01-30T00:00:00"
}
```

**Files Collection:**
```json
{
  "file_id": "unique-id",
  "owner_email": "user@example.com",
  "filename": "document.pdf",
  "size": 1048576,
  "encrypted_content": {
    "ciphertext": "encrypted-data",
    "layers": 3,
    "metadata": [...]
  },
  "encrypted_content_key": {
    "ciphertext": "encrypted-key",
    "layers": 3,
    "metadata": [...]
  },
  "created_at": "2026-01-29T00:00:00"
}
```

**Important:** The server **never stores plaintext**. Everything is encrypted before being written to MongoDB.

### Email Server (SMTP)

**How Email Delivery Works:**

1. **User sends encrypted email** via API
2. **Backend encrypts and stores** in MongoDB
3. **SMTP server sends notification** to recipients
4. **Recipients receive email** with secure link
5. **Recipients click link** to decrypt and view email

**Email Domain:**
- All emails sent from `fxmail.ai` domain
- Format: `{token}@fxmail.ai`
- Example: `z5LVkIi8tELLPfYABwaJLmaSpeOwBpFjmsAoyco60rQ@fxmail.ai`

**Notification Email:**
Recipients receive an email like this:

```
Subject: You have received an encrypted email

You have received an encrypted email.

To view this email, click on the secure link below:
https://fxmail.ai/email/z5LVkIi8tELLPfYABwaJLmaSpeOwBpFjmsAoyco60rQ

This link will allow you to access the encrypted email securely.
```

**SMTP Configuration:**
- Host: `smtp.fxmail.ai`
- Port: `587` (TLS)
- Authentication: Required (if configured)
- Domain: `fxmail.ai`

### Device Encryption Key

On first app launch, generate and store a device encryption key locally:

```javascript
import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';

// Generate device key on first launch
const generateDeviceKey = async () => {
  const existingKey = await SecureStore.getItemAsync('device_encryption_key');
  
  if (existingKey) {
    return existingKey;
  }
  
  // Generate 256-bit key (32 bytes)
  const keyBytes = await Crypto.getRandomBytesAsync(32);
  const keyBase64 = base64Encode(keyBytes);
  
  // Store securely (never send to server)
  await SecureStore.setItemAsync('device_encryption_key', keyBase64);
  
  // Generate fingerprint for server registration
  const fingerprint = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    keyBase64
  );
  
  // Register fingerprint with server (not the actual key)
  await registerDeviceKeyFingerprint(fingerprint, accessToken);
  
  return keyBase64;
};
```

### Encrypting Files for Upload

```javascript
import { AES } from 'crypto-js';

const encryptFileForUpload = async (fileData, deviceKey) => {
  // Generate random content key
  const contentKey = await Crypto.getRandomBytesAsync(32);
  
  // Encrypt file with content key (AES-256-GCM)
  const encryptedContent = await encryptAES256GCM(fileData, contentKey);
  
  // Encrypt content key with device key
  const encryptedContentKey = await encryptAES256GCM(contentKey, deviceKey);
  
  return {
    encrypted_content: {
      ciphertext: base64Encode(encryptedContent.ciphertext),
      nonce: base64Encode(encryptedContent.nonce),
      tag: base64Encode(encryptedContent.tag),
    },
    encrypted_content_key: {
      ciphertext: base64Encode(encryptedContentKey.ciphertext),
      nonce: base64Encode(encryptedContentKey.nonce),
      tag: base64Encode(encryptedContentKey.tag),
    },
  };
};
```

### Decrypting Files After Download

```javascript
const decryptFileAfterDownload = async (
  encryptedContent,
  encryptedContentKey,
  deviceKey
) => {
  // Decrypt content key with device key
  const contentKey = await decryptAES256GCM(
    {
      ciphertext: base64Decode(encryptedContentKey.ciphertext),
      nonce: base64Decode(encryptedContentKey.nonce),
      tag: base64Decode(encryptedContentKey.tag),
    },
    deviceKey
  );
  
  // Decrypt file content with content key
  const fileData = await decryptAES256GCM(
    {
      ciphertext: base64Decode(encryptedContent.ciphertext),
      nonce: base64Decode(encryptedContent.nonce),
      tag: base64Decode(encryptedContent.tag),
    },
    contentKey
  );
  
  return fileData;
};
```

### Multi-Layer Encryption Implementation

**Important:** The backend uses **3-layer encryption** for maximum security. When you use the `/email/send` or `/drive/upload` endpoints, the server automatically applies all 3 layers.

**Layer Structure:**
```
Original Data
    ↓
Layer 1: AES-256-GCM (Primary Key)
    ↓
Layer 2: ChaCha20-Poly1305 (Secondary Key)
    ↓
Layer 3: AES-256-GCM + Scrypt (Derived Key)
    ↓
Final Encrypted Data (stored in MongoDB)
```

**For Client-Side Encryption (E2E):**

If you're using `/drive/upload-encrypted` or `/messaging/send`, you only need single-layer encryption on the client:

```javascript
// Single-layer encryption is sufficient for client-side
// The server will add additional layers if needed

const encryptAES256GCM = async (plaintext, key) => {
  // Generate random nonce (12 bytes for GCM)
  const nonce = await Crypto.getRandomBytesAsync(12);
  
  // Encrypt using AES-256-GCM
  // Implementation depends on your crypto library
  // Example with crypto-js:
  const cipher = AES.encrypt(
    base64Encode(plaintext),
    base64Encode(key),
    {
      iv: base64Encode(nonce),
      mode: CryptoJS.mode.GCM,
      padding: CryptoJS.pad.NoPadding,
    }
  );
  
  return {
    ciphertext: cipher.ciphertext,
    nonce: nonce,
    tag: cipher.tag, // 16 bytes authentication tag
  };
};

const decryptAES256GCM = async (encrypted, key) => {
  // Decrypt using AES-256-GCM
  const decrypted = AES.decrypt(
    {
      ciphertext: base64Decode(encrypted.ciphertext),
      iv: base64Decode(encrypted.nonce),
      tag: base64Decode(encrypted.tag),
    },
    base64Encode(key),
    {
      mode: CryptoJS.mode.GCM,
      padding: CryptoJS.pad.NoPadding,
    }
  );
  
  return base64Decode(decrypted.toString());
};
```

**Note:** The backend automatically applies multi-layer encryption when storing data in MongoDB. Your client-side encryption provides the first layer of security.

---

## Storage Quota

- **Default Quota**: 5GB per user
- **Tracked Automatically**: Storage usage is tracked on upload and decremented on deletion
- **Enforced**: Uploads will fail if quota is exceeded
- **Check Quota**: Use `/drive/storage/quota` endpoint before large uploads

---

## Best Practices

1. **Token Management**
   - Store tokens securely (e.g., SecureStore in React Native)
   - Refresh tokens before they expire
   - Handle token expiration gracefully

2. **Error Handling**
   - Always check response status
   - Provide user-friendly error messages
   - Implement retry logic for network errors

3. **Encryption**
   - Never send encryption keys to the server
   - Generate keys securely using cryptographically secure random number generators
   - Store keys securely on device (Keychain/Keystore)
   - Use multi-layer encryption for maximum security

4. **File Uploads**
   - Check storage quota before uploading
   - Show upload progress to users
   - Handle large files appropriately (chunking if needed)
   - Use encrypted upload endpoint for sensitive files

5. **Email Handling**
   - Recipients will receive notification emails automatically
   - Secure links expire based on email expiration settings
   - Self-destruct emails are deleted after first read
   - Passcode-protected emails require unlock before viewing

6. **Database & Storage**
   - All data is encrypted before storage in MongoDB
   - Server never sees plaintext content
   - Expired emails/files are automatically cleaned up
   - Storage quota is enforced (5GB per user)

7. **Rate Limiting**
   - Implement exponential backoff for rate limit errors
   - Cache responses when appropriate
   - Batch requests when possible

8. **Security**
   - Always use HTTPS in production
   - Validate user input on client-side
   - Never log sensitive data
   - Use strong passcodes for passcode-protected content

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Mobile App (Client)                      │
│                                                             │
│  • Generates device encryption keys                        │
│  • Encrypts data before sending                            │
│  • Decrypts data after receiving                           │
└─────────────────────────────────────────────────────────────┘
                        ↓ HTTPS
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (localhost:8000)               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Endpoints                                      │   │
│  │  • /api/v1/auth/*                                   │   │
│  │  • /api/v1/email/*                                  │   │
│  │  • /api/v1/drive/*                                  │   │
│  │  • /api/v1/messaging/*                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Encryption Layer                                   │   │
│  │  • Multi-layer encryption (3 layers)                │   │
│  │  • AES-256-GCM + ChaCha20-Poly1305 + Scrypt         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Email Service                                      │   │
│  │  • Encrypts and stores emails                       │   │
│  │  • Sends notifications via SMTP                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    MongoDB Database                         │
│                                                             │
│  • emails collection (encrypted)                            │
│  • files collection (encrypted)                              │
│  • All data encrypted before storage                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    SMTP Server                              │
│                                                             │
│  • Sends notification emails                                │
│  • Domain: fxmail.ai                                       │
│  • Recipients receive secure links                          │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow: Sending an Email

```
1. User composes email in mobile app
   ↓
2. App encrypts email content (3 layers)
   ↓
3. App sends encrypted data to backend API
   ↓
4. Backend stores encrypted data in MongoDB
   ↓
5. Backend sends notification email via SMTP
   ↓
6. Recipient receives email with secure link
   ↓
7. Recipient clicks link and decrypts email
```

### Data Flow: Uploading a File

```
1. User selects file in mobile app
   ↓
2. App encrypts file (3 layers) OR sends plaintext
   ↓
3. Backend encrypts (if plaintext) and stores in MongoDB
   ↓
4. Backend tracks storage usage (5GB quota)
   ↓
5. Backend returns file_id to app
   ↓
6. App can download/decrypt file later
```

### Security Layers

**Layer 1: Network Security**
- HTTPS/TLS encryption for all API calls
- Prevents man-in-the-middle attacks

**Layer 2: Authentication**
- JWT tokens for API access
- Token expiration and refresh

**Layer 3: Data Encryption**
- Multi-layer encryption (3 layers)
- Different algorithms for each layer
- Content keys encrypted separately

**Layer 4: Database Security**
- MongoDB connection encryption (TLS)
- Encrypted data at rest
- No plaintext storage

**Layer 5: Application Security**
- Rate limiting
- Brute-force protection
- Audit logging

## Configuration

### Backend Configuration

The backend runs on `localhost:8000` and requires:

**MongoDB:**
- Connection string configured in environment variables
- Database: `admin`
- Collections: `emails`, `files`

**SMTP:**
- Host: `smtp.fxmail.ai`
- Port: `587` (TLS)
- Domain: `fxmail.ai`

**Environment Variables:**
```bash
# MongoDB
MONGODB_CONNECTION_STRING=mongodb+srv://...
MONGODB_DATABASE=admin

# SMTP
SMTP_HOST=smtp.fxmail.ai
SMTP_PORT=587
SMTP_USE_TLS=true

# Email Domain
EMAIL_DOMAIN=fxmail.ai
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai
```

### Mobile App Configuration

**Base URL:**
```javascript
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

**No CORS Required:**
- Backend configured for mobile apps
- No CORS headers needed
- Direct API access from mobile devices

## Summary for Frontend Developers

### Quick Start Checklist

1. **Authentication**
   - Register users with `/auth/register`
   - Login with `/auth/login` to get access tokens
   - Store tokens securely (SecureStore/Keychain)
   - Include token in `Authorization: Bearer {token}` header

2. **Email Features**
   - Send emails with `/email/send` (server encrypts automatically)
   - Recipients receive notification emails via `fxmail.ai`
   - Emails stored in MongoDB with 3-layer encryption
   - Server never sees plaintext email content

3. **Drive Features**
   - Upload files with `/drive/upload` (server encrypts)
   - Or use `/drive/upload-encrypted` for client-side encryption
   - Check quota with `/drive/storage/quota` (5GB per user)
   - Files stored in MongoDB with 3-layer encryption

4. **Messaging Features**
   - Send messages with `/messaging/send` (client-side encryption required)
   - Messages stored encrypted in MongoDB
   - Only recipients can decrypt

### Key Architecture Points

**Backend:**
- Runs on `localhost:8000` (development)
- No CORS needed (for mobile apps)
- MongoDB for persistent storage
- SMTP server for email delivery
- Multi-layer encryption (3 layers)

**Email Server:**
- Domain: `fxmail.ai`
- Sends notification emails automatically
- Recipients get secure links to decrypt emails
- SMTP configured for `smtp.fxmail.ai`

**Database:**
- MongoDB stores all encrypted data
- Collections: `emails`, `files`
- All data encrypted before storage
- Server never sees plaintext

**Encryption:**
- 3 layers: AES-256-GCM + ChaCha20-Poly1305 + Scrypt
- Makes decryption extremely difficult
- Content keys encrypted separately
- Maximum security for sensitive data

### What Happens When You Send an Email

```
1. Your App:
   - User composes email
   - App sends to /email/send endpoint
   
2. Backend:
   - Receives email content
   - Encrypts with 3 layers
   - Stores in MongoDB (encrypted)
   - Sends notification via SMTP
   
3. Recipient:
   - Receives email from fxmail.ai
   - Clicks secure link
   - Decrypts email content
   - Views original message
```

### What Happens When You Upload a File

```
1. Your App:
   - User selects file
   - App sends to /drive/upload
   
2. Backend:
   - Receives file
   - Encrypts with 3 layers
   - Stores in MongoDB (encrypted)
   - Tracks storage usage
   - Returns file_id
   
3. Later:
   - User requests file
   - Backend retrieves encrypted data
   - Decrypts and returns to app
   - App displays file
```

### Security Guarantees

✅ **Server cannot decrypt** - No access to encryption keys  
✅ **Multi-layer encryption** - 3 layers make attacks extremely difficult  
✅ **MongoDB storage** - Persistent, encrypted storage  
✅ **Email delivery** - Secure notifications via fxmail.ai  
✅ **Storage limits** - 5GB quota enforced per user  
✅ **No plaintext storage** - Everything encrypted before database  

### Important Notes

1. **Backend runs on localhost:8000** - No CORS needed for mobile apps
2. **All emails via fxmail.ai** - Notification emails sent automatically
3. **MongoDB stores encrypted data** - Server never sees plaintext
4. **3-layer encryption** - Maximum security for all data
5. **Storage quota** - 5GB per user, tracked automatically

## Support

For API support or questions, contact the development team or refer to the main project documentation.

**Key Points:**
- All emails sent via `fxmail.ai` domain
- All data encrypted with 3-layer encryption
- MongoDB stores encrypted data only
- Server never sees plaintext content
- Maximum security for sensitive communications
- Backend: `localhost:8000` (no CORS for mobile apps)
