# Final Email API Documentation

Complete guide for implementing encrypted email functionality in your mobile/web applications.

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Email API Endpoints](#email-api-endpoints)
  - [Send Email](#1-send-email)
  - [Get Inbox Emails](#2-get-inbox-emails)
  - [Get Sent Emails](#3-get-sent-emails)
  - [Get Draft Emails](#4-get-draft-emails)
  - [Save Draft Email](#5-save-draft-email)
  - [Update Draft Email](#6-update-draft-email)
  - [Delete Draft Email](#7-delete-draft-email)
  - [Get Email by ID](#8-get-email-by-id)
  - [Unlock Passcode-Protected Email](#9-unlock-passcode-protected-email)
  - [Delete Email](#10-delete-email)
- [Step-by-Step Implementation](#step-by-step-implementation)
- [Error Handling](#error-handling)
- [Troubleshooting & Common Issues](#troubleshooting--common-issues)
- [Recent Fixes & Updates](#recent-fixes--updates)
- [Code Examples](#code-examples)

---

## Overview

The Email API provides **end-to-end encrypted email** functionality with:
- **3-layer encryption** for maximum security
- **MongoDB storage** for encrypted emails
- **SMTP integration** for sending/receiving emails
- **Passcode protection** for sensitive emails
- **Self-destruct** emails (delete after first read)
- **Email expiration** support
- **Rate limiting** (50 emails/hour, 200/day)

### Key Features

- ✅ **Send encrypted emails** - Multi-layer encryption before storage
- ✅ **Inbox/Sent/Drafts** - Organize emails by status
- ✅ **Draft management** - Save, update, delete drafts
- ✅ **Passcode protection** - Optional passcode for sensitive emails
- ✅ **Self-destruct** - Delete email after first read
- ✅ **Email expiration** - Automatic deletion after set time
- ✅ **SMTP integration** - Send via fxmail.ai domain

### ⚠️ Important Notes for Frontend Developers

**Recent Updates (January 2026):**
- All email list endpoints (inbox, sent, drafts) now return **complete data** with all required fields
- Response fields are **guaranteed to be present** (except `subject` which is optional)
- Error messages now include **detailed information** for better debugging
- All endpoints have been tested and verified to work correctly

**Field Guarantees:**
- `email_id`, `access_token`, `sender_email`, `recipient_emails` - Always present
- `created_at`, `expires_at`, `has_passcode`, `is_draft`, `status` - Always present
- `subject` - Optional (may be null)
- `expires_at` - Always present (null if no expiration)

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

**All Email API endpoints require authentication** using JWT Bearer tokens.

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

## Email API Endpoints

### 1. Send Email

Send an encrypted email to one or more recipients.

**Endpoint:** `POST /email/send`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "to": ["recipient@example.com"],
  "subject": "Email Subject",
  "body": "Email body content",
  "passcode": "optional-passcode",
  "expires_in_hours": 24,
  "self_destruct": false
}
```

**Request Fields:**
- `to` (required): Array of recipient email addresses (max 50)
- `subject` (optional): Email subject line
- `body` (required): Email body content
- `passcode` (optional): Passcode for email protection (min 4 chars)
- `expires_in_hours` (optional): Hours until email expires (1-8760)
- `self_destruct` (optional): Delete after first read (default: false)

**Response (201 Created):**
```json
{
  "email_id": "abc123xyz...",
  "email_address": "abc123xyz@fxmail.ai",
  "secure_link": "https://fxmail.ai/email/abc123xyz...",
  "expires_at": "2026-01-30T12:00:00Z",
  "encryption_mode": "authenticated"
}
```

**Example:**
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/email/send" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Hello",
    "body": "This is a test email"
  }'
```

---

### 2. Get Inbox Emails

Get list of received emails (inbox).

**Endpoint:** `GET /email/inbox`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional): Number of emails to return (default: 50, max: 100)
- `offset` (optional): Number of emails to skip (default: 0)

**Response (200 OK):**
```json
{
  "emails": [
    {
      "email_id": "abc123xyz...",
      "access_token": "abc123xyz...",
      "sender_email": "sender@example.com",
      "recipient_emails": ["you@example.com"],
      "subject": "Email Subject",
      "created_at": "2026-01-29T12:00:00Z",
      "expires_at": null,
      "has_passcode": false,
      "is_draft": false,
      "status": "inbox"
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Note:** All fields in the `emails` array are guaranteed to be present (except `subject` which is optional). The `expires_at` field will be `null` if the email has no expiration date.

**Example:**
```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/email/inbox?limit=20&offset=0" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 3. Get Sent Emails

Get list of sent emails.

**Endpoint:** `GET /email/sent`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional): Number of emails to return (default: 50, max: 100)
- `offset` (optional): Number of emails to skip (default: 0)

**Response (200 OK):**
```json
{
  "emails": [
    {
      "email_id": "abc123xyz...",
      "access_token": "abc123xyz...",
      "sender_email": "you@example.com",
      "recipient_emails": ["recipient@example.com"],
      "subject": "Email Subject",
      "created_at": "2026-01-29T12:00:00Z",
      "expires_at": null,
      "has_passcode": false,
      "is_draft": false,
      "status": "sent"
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

**Example:**
```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/email/sent" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Get Draft Emails

Get list of draft emails.

**Endpoint:** `GET /email/drafts`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional): Number of drafts to return (default: 50, max: 100)
- `offset` (optional): Number of drafts to skip (default: 0)

**Response (200 OK):**
```json
{
  "emails": [
    {
      "email_id": "abc123xyz...",
      "access_token": "abc123xyz...",
      "sender_email": "you@example.com",
      "recipient_emails": ["recipient@example.com"],
      "subject": "Draft Subject",
      "created_at": "2026-01-29T12:00:00Z",
      "expires_at": null,
      "has_passcode": false,
      "is_draft": true,
      "status": "draft"
    }
  ],
  "total": 3,
  "limit": 50,
  "offset": 0
}
```

**Note:** All fields are guaranteed to be present. Drafts always have `is_draft: true` and `status: "draft"`. The `expires_at` field is included for consistency but will typically be `null` for drafts.

**Example:**
```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/email/drafts" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 5. Save Draft Email

Save a new draft email.

**Endpoint:** `POST /email/drafts`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "to": ["recipient@example.com"],
  "subject": "Draft Subject",
  "body": "Draft body content"
}
```

**Request Fields:**
- `to` (required): Array of recipient email addresses
- `subject` (optional): Email subject
- `body` (required): Email body content

**Response (201 Created):**
```json
{
  "email_id": "abc123xyz...",
  "access_token": "abc123xyz...",
  "email_address": "abc123xyz@fxmail.ai",
  "status": "draft",
  "created_at": "2026-01-29T12:00:00Z",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

**Example:**
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/email/drafts" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Draft",
    "body": "This is a draft"
  }'
```

---

### 6. Update Draft Email

Update an existing draft email.

**Endpoint:** `PUT /email/drafts/{draft_id}`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "to": ["recipient@example.com"],
  "subject": "Updated Draft Subject",
  "body": "Updated draft body content"
}
```

**Response (200 OK):**
```json
{
  "email_id": "abc123xyz...",
  "access_token": "abc123xyz...",
  "email_address": "abc123xyz@fxmail.ai",
  "status": "draft",
  "created_at": "2026-01-29T12:00:00Z",
  "updated_at": "2026-01-29T13:00:00Z"
}
```

**Example:**
```bash
curl -X PUT "https://freedomos.vulcantech.co/api/v1/email/drafts/abc123xyz..." \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Updated Draft",
    "body": "Updated content"
  }'
```

---

### 7. Delete Draft Email

Delete a draft email.

**Endpoint:** `DELETE /email/drafts/{draft_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "email_id": "abc123xyz...",
  "deleted": true,
  "message": "Draft deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE "https://freedomos.vulcantech.co/api/v1/email/drafts/abc123xyz..." \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 8. Get Email by ID

Get a specific email by its ID (for authenticated users).

**Endpoint:** `GET /email/{email_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "email_id": "abc123xyz...",
  "subject": "Email Subject",
  "body": "Email body content",
  "encryption_mode": "authenticated",
  "expires_at": null,
  "is_passcode_protected": false
}
```

**Example:**
```bash
curl -X GET "https://freedomos.vulcantech.co/api/v1/email/abc123xyz..." \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 9. Unlock Passcode-Protected Email

Unlock a passcode-protected email.

**Endpoint:** `POST /email/{email_id}/unlock`

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
  "email_id": "abc123xyz...",
  "subject": "Email Subject",
  "body": "Email body content",
  "unlocked_at": "2026-01-29T12:00:00Z"
}
```

**Example:**
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/email/abc123xyz.../unlock" \
  -H "Content-Type: application/json" \
  -d '{
    "passcode": "your-passcode"
  }'
```

---

### 10. Delete Email

Delete an email (works for self-destruct emails too).

**Endpoint:** `DELETE /email/{email_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "email_id": "abc123xyz...",
  "deleted": true,
  "message": "Email deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE "https://freedomos.vulcantech.co/api/v1/email/abc123xyz..." \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

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

### Step 2: Send Email

```javascript
const sendEmail = async (to, subject, body) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(`${API_BASE_URL}/email/send`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      to: [to],
      subject: subject,
      body: body
    })
  });
  
  return await response.json();
};
```

### Step 3: Get Inbox

```javascript
const getInbox = async (limit = 50, offset = 0) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(
    `${API_BASE_URL}/email/inbox?limit=${limit}&offset=${offset}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

### Step 4: Get Sent Emails

```javascript
const getSent = async (limit = 50, offset = 0) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(
    `${API_BASE_URL}/email/sent?limit=${limit}&offset=${offset}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

### Step 5: Save Draft

```javascript
const saveDraft = async (to, subject, body) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(`${API_BASE_URL}/email/drafts`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      to: [to],
      subject: subject,
      body: body
    })
  });
  
  return await response.json();
};
```

### Step 6: Update Draft

```javascript
const updateDraft = async (draftId, to, subject, body) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(`${API_BASE_URL}/email/drafts/${draftId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      to: [to],
      subject: subject,
      body: body
    })
  });
  
  return await response.json();
};
```

### Step 7: Delete Draft

```javascript
const deleteDraft = async (draftId) => {
  const accessToken = await SecureStore.getItemAsync('access_token');
  
  const response = await fetch(`${API_BASE_URL}/email/drafts/${draftId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
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
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

**Note:** Error messages now include detailed information to help with debugging. For example:
- `"Failed to retrieve inbox emails: {specific error}"`
- `"Failed to retrieve sent emails: {specific error}"`
- `"Failed to retrieve draft emails: {specific error}"`

### Example Error Handling

```javascript
const handleApiCall = async (apiCall) => {
  try {
    const response = await apiCall();
    
    if (!response.ok) {
      const error = await response.json();
      const errorMessage = error.detail || 'API request failed';
      
      // Log detailed error for debugging
      console.error('API Error:', {
        status: response.status,
        message: errorMessage,
        endpoint: response.url
      });
      
      // Handle specific error cases
      if (response.status === 401) {
        // Token expired, refresh it
        await refreshAccessToken();
        // Retry the request
        return await apiCall();
      }
      
      throw new Error(errorMessage);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};
```

### Handling Email List Responses

**Important:** All email list endpoints now guarantee that required fields are always present:

```javascript
const getInbox = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/email/inbox`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get inbox: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // All fields are guaranteed to be present (except optional subject)
    data.emails.forEach(email => {
      console.log('Email ID:', email.email_id);           // ✅ Always present
      console.log('Access Token:', email.access_token);   // ✅ Always present
      console.log('Sender:', email.sender_email);         // ✅ Always present
      console.log('Recipients:', email.recipient_emails); // ✅ Always array
      console.log('Subject:', email.subject || 'No subject'); // Optional
      console.log('Created:', email.created_at);          // ✅ Always present
      console.log('Expires:', email.expires_at || 'Never'); // ✅ Always present (null if no expiration)
      console.log('Status:', email.status);               // ✅ Always present
      console.log('Is Draft:', email.is_draft);          // ✅ Always present
    });
    
    return data;
  } catch (error) {
    console.error('Error fetching inbox:', error);
    throw error;
  }
};
```

---

## Code Examples

### Complete Email App Example

```javascript
const API_BASE_URL = 'https://freedomos.vulcantech.co/api/v1';

class EmailService {
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
  
  async sendEmail(to, subject, body, options = {}) {
    const response = await fetch(`${API_BASE_URL}/email/send`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        to: Array.isArray(to) ? to : [to],
        subject,
        body,
        passcode: options.passcode,
        expires_in_hours: options.expiresInHours,
        self_destruct: options.selfDestruct || false
      })
    });
    
    return await response.json();
  }
  
  async getInbox(limit = 50, offset = 0) {
    const response = await fetch(
      `${API_BASE_URL}/email/inbox?limit=${limit}&offset=${offset}`,
      {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      }
    );
    
    return await response.json();
  }
  
  async getSent(limit = 50, offset = 0) {
    const response = await fetch(
      `${API_BASE_URL}/email/sent?limit=${limit}&offset=${offset}`,
      {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      }
    );
    
    return await response.json();
  }
  
  async getDrafts(limit = 50, offset = 0) {
    const response = await fetch(
      `${API_BASE_URL}/email/drafts?limit=${limit}&offset=${offset}`,
      {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      }
    );
    
    return await response.json();
  }
  
  async saveDraft(to, subject, body) {
    const response = await fetch(`${API_BASE_URL}/email/drafts`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        to: Array.isArray(to) ? to : [to],
        subject,
        body
      })
    });
    
    return await response.json();
  }
  
  async updateDraft(draftId, to, subject, body) {
    const response = await fetch(`${API_BASE_URL}/email/drafts/${draftId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        to: Array.isArray(to) ? to : [to],
        subject,
        body
      })
    });
    
    return await response.json();
  }
  
  async deleteDraft(draftId) {
    const response = await fetch(`${API_BASE_URL}/email/drafts/${draftId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`
      }
    });
    
    return await response.json();
  }
  
  async getEmail(emailId) {
    const response = await fetch(`${API_BASE_URL}/email/${emailId}`, {
      headers: {
        'Authorization': `Bearer ${this.accessToken}`
      }
    });
    
    return await response.json();
  }
  
  async unlockEmail(emailId, passcode) {
    const response = await fetch(`${API_BASE_URL}/email/${emailId}/unlock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ passcode })
    });
    
    return await response.json();
  }
  
  async deleteEmail(emailId) {
    const response = await fetch(`${API_BASE_URL}/email/${emailId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${this.accessToken}`
      }
    });
    
    return await response.json();
  }
}

// Usage
const emailService = new EmailService();

// Authenticate
await emailService.authenticate('user@fxmail.ai', 'password');

// Send email
await emailService.sendEmail(
  'recipient@example.com',
  'Hello',
  'This is a test email'
);

// Get inbox
const inbox = await emailService.getInbox();

// Get sent
const sent = await emailService.getSent();

// Get drafts
const drafts = await emailService.getDrafts();

// Save draft
await emailService.saveDraft(
  'recipient@example.com',
  'Draft',
  'This is a draft'
);
```

---

## Troubleshooting & Common Issues

### Error: "Failed to retrieve inbox emails" (500)

**Possible causes:**
1. Backend service needs restart after code updates
2. MongoDB connection issues
3. Missing required fields in email documents

**Solution:**
- Ensure backend is running latest code version
- Check server logs for detailed error messages
- Verify MongoDB connection is active

### Error: "Failed to retrieve sent emails" (500)

**Possible causes:**
1. Backend service needs restart
2. Email service initialization issues

**Solution:**
- Restart backend service: `sudo systemctl restart flashdash-backend`
- Check server logs for specific error details

### Error: "Failed to retrieve draft emails" (500)

**Possible causes:**
1. Backend service needs restart
2. MongoDB query issues

**Solution:**
- Restart backend service
- Verify MongoDB is accessible and collections exist

### Error: "Email not found" (404)

**Possible causes:**
1. Email ID is incorrect
2. Email has expired
3. Email was deleted

**Solution:**
- Verify email ID is correct
- Check if email has expiration date
- Ensure email exists in database

### Error: "Invalid token" (401)

**Possible causes:**
1. Access token expired
2. Token is invalid or malformed
3. Token was revoked

**Solution:**
- Refresh access token using refresh token
- Re-authenticate if refresh token also expired
- Ensure token is included in Authorization header

### Error: "Storage quota exceeded" (507)

**Possible causes:**
1. User has reached 5GB storage limit
2. Too many emails stored

**Solution:**
- Delete old or unnecessary emails
- Check storage usage via quota API
- Consider implementing email cleanup policies

---

## Recent Fixes & Updates

### Email List APIs Fix (January 2026)

**Issue:** Email list endpoints (inbox, sent, drafts) were returning 500 errors due to missing required fields in response data.

**Fixes Applied:**
- ✅ Added `recipient_emails` field to inbox emails response
- ✅ Added `sender_email` field to all email list responses
- ✅ Added `expires_at` field to draft emails response
- ✅ Improved error handling with detailed error messages
- ✅ Added fallback handling for `email_id`/`access_token` fields

**What This Means for Frontend:**
- All email list endpoints now return complete data
- All required fields are always present in responses
- Better error messages help with debugging
- More robust handling of edge cases

**Updated Endpoints:**
- `GET /email/inbox` - Now includes all required fields
- `GET /email/sent` - Now includes all required fields
- `GET /email/drafts` - Now includes all required fields

**Response Structure (All List Endpoints):**
```json
{
  "emails": [
    {
      "email_id": "string",           // ✅ Always present
      "access_token": "string",        // ✅ Always present
      "sender_email": "string",        // ✅ Always present
      "recipient_emails": ["string"],  // ✅ Always present
      "subject": "string",             // Optional
      "created_at": "ISO datetime",    // ✅ Always present
      "expires_at": "ISO datetime",    // ✅ Always present (null if no expiration)
      "has_passcode": false,           // ✅ Always present
      "is_draft": false,               // ✅ Always present
      "status": "inbox|sent|draft"     // ✅ Always present
    }
  ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

**Frontend Implementation Notes:**
- You can safely access all fields without null checks (except `subject` which is optional)
- `expires_at` will be `null` if email has no expiration
- `recipient_emails` is always an array (empty array if none)
- `sender_email` is always present (null only for system emails)

---

## Summary

This Email API provides complete encrypted email functionality with:
- ✅ Send, receive, and manage emails
- ✅ Draft management (save, update, delete)
- ✅ Inbox, Sent, and Drafts organization
- ✅ Passcode protection for sensitive emails
- ✅ Self-destruct and expiration support
- ✅ Full authentication integration
- ✅ Robust error handling and field validation

All emails are encrypted with **3-layer encryption** and stored securely in MongoDB. The server never sees plaintext content.

---

**Base URL:** `https://freedomos.vulcantech.co/api/v1`  
**Authentication:** JWT Bearer Token  
**Storage:** MongoDB (encrypted)  
**Domain:** fxmail.ai

**Last Updated:** January 2026  
**API Version:** v1
