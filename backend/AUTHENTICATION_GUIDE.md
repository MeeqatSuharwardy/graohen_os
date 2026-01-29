# Authentication Guide for Frontend Developers

Complete guide for implementing user registration and login in your mobile/web applications.

## Table of Contents

- [Overview](#overview)
- [How Registration Works (API Side)](#how-registration-works-api-side)
- [How Login Works (API Side)](#how-login-works-api-side)
- [Frontend Implementation](#frontend-implementation)
- [Token Management](#token-management)
- [Error Handling](#error-handling)
- [Security Best Practices](#security-best-practices)
- [Code Examples](#code-examples)

---

## Overview

The authentication system uses **JWT (JSON Web Tokens)** with two types of tokens:
- **Access Token**: Short-lived (30 minutes), used for API requests
- **Refresh Token**: Long-lived (7 days), used to get new access tokens

### Base URL

**Production:**
```
https://freedomos.vulcantech.co/api/v1
```

**Development:**
```
http://localhost:8000/api/v1
```

---

## How Registration Works (API Side)

### Registration Flow

```
1. Frontend sends registration request
   ↓
2. API validates input (email format, password strength)
   ↓
3. API checks rate limits (5 registrations/hour per IP)
   ↓
4. API checks if email already exists
   ↓
5. API hashes password using Argon2
   ↓
6. API creates user record
   ↓
7. API generates device ID (if not provided)
   ↓
8. API creates JWT access token (30 min expiry)
   ↓
9. API creates JWT refresh token (7 days expiry)
   ↓
10. API stores refresh token metadata in Redis
   ↓
11. API logs security event
   ↓
12. API returns tokens to frontend
```

### Registration Endpoint

**Endpoint:** `POST /auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "device_id": "optional-device-identifier"
}
```

**Request Fields:**
- `email` (required): Valid email address
- `password` (required): Minimum 8 characters, max 128 characters
- `full_name` (optional): User's full name
- `device_id` (optional): Unique device identifier for multi-device support

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_id": "device-id-generated"
}
```

### What Happens on the Server

1. **Input Validation**
   - Email format validation
   - Password length check (min 8 chars)
   - Rate limiting check (5 registrations/hour per IP)

2. **Password Security**
   - Password is hashed using **Argon2** (memory-hard hashing algorithm)
   - Original password is never stored
   - Hash is stored securely

3. **User Creation**
   - Unique user ID is generated
   - User data is stored (email, hashed password, full_name)
   - Email is normalized to lowercase

4. **Token Generation**
   - **Access Token** contains:
     - `sub`: User ID
     - `email`: User email
     - `jti`: Unique token identifier (for revocation)
     - `device_id`: Device identifier
     - `exp`: Expiration timestamp (30 minutes)
     - `type`: "access"
   
   - **Refresh Token** contains:
     - Same fields as access token
     - `exp`: Expiration timestamp (7 days)
     - `type`: "refresh"

5. **Token Storage**
   - Refresh token metadata stored in Redis
   - Device ID linked to refresh token
   - Enables token revocation and multi-device management

6. **Security Logging**
   - Registration event logged
   - IP address tracked
   - Device ID recorded

### Error Responses

**400 Bad Request** - Email already registered:
```json
{
  "detail": "Email already registered"
}
```

**429 Too Many Requests** - Rate limit exceeded:
```json
{
  "detail": "Too many registration attempts. Please try again later."
}
```

**422 Validation Error** - Invalid input:
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters long",
      "type": "value_error"
    }
  ]
}
```

---

## How Login Works (API Side)

### Login Flow

```
1. Frontend sends login request
   ↓
2. API checks brute force protection
   ↓
3. API validates email format
   ↓
4. API looks up user by email
   ↓
5. If user not found → record failed attempt → return error
   ↓
6. API verifies password using Argon2
   ↓
7. If password incorrect → record failed attempt → return error
   ↓
8. After 5 failed attempts → account locked for 1 hour
   ↓
9. If password correct → reset brute force counter
   ↓
10. API checks if user account is active
   ↓
11. API generates device ID (if not provided)
   ↓
12. API creates JWT access token (30 min expiry)
   ↓
13. API creates JWT refresh token (7 days expiry)
   ↓
14. API stores refresh token metadata in Redis
   ↓
15. API logs successful login event
   ↓
16. API returns tokens to frontend
```

### Login Endpoint

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "device_id": "optional-device-identifier"
}
```

**Request Fields:**
- `email` (required): User's email address
- `password` (required): User's password
- `device_id` (optional): Unique device identifier

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_id": "device-id-generated"
}
```

### What Happens on the Server

1. **Brute Force Protection**
   - Tracks failed login attempts per email+IP combination
   - Maximum 5 attempts per hour
   - After 5 failures, account locked for 1 hour
   - Prevents automated attacks

2. **User Lookup**
   - Searches for user by email (case-insensitive)
   - If user not found, returns generic error (prevents email enumeration)

3. **Password Verification**
   - Compares provided password with stored Argon2 hash
   - Uses constant-time comparison (prevents timing attacks)
   - If incorrect, records failed attempt

4. **Account Status Check**
   - Verifies user account is active
   - Disabled accounts cannot login

5. **Token Generation**
   - Same process as registration
   - New tokens generated for each login
   - Old tokens remain valid until expiration

6. **Security Logging**
   - Successful logins logged
   - Failed attempts logged
   - IP address and device ID tracked

### Error Responses

**401 Unauthorized** - Invalid credentials:
```json
{
  "detail": "Incorrect email or password"
}
```

**429 Too Many Requests** - Account locked:
```json
{
  "detail": "Too many failed login attempts. Account locked for 1 hour."
}
```

**403 Forbidden** - Account disabled:
```json
{
  "detail": "User account is disabled"
}
```

---

## Frontend Implementation

### Step 1: Store Tokens Securely

**React Native (Expo):**
```javascript
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  DEVICE_ID: 'device_id',
};

// Store tokens
async function storeTokens(accessToken, refreshToken, deviceId) {
  await SecureStore.setItemAsync(TOKEN_KEYS.ACCESS_TOKEN, accessToken);
  await SecureStore.setItemAsync(TOKEN_KEYS.REFRESH_TOKEN, refreshToken);
  if (deviceId) {
    await SecureStore.setItemAsync(TOKEN_KEYS.DEVICE_ID, deviceId);
  }
}

// Get tokens
async function getTokens() {
  const accessToken = await SecureStore.getItemAsync(TOKEN_KEYS.ACCESS_TOKEN);
  const refreshToken = await SecureStore.getItemAsync(TOKEN_KEYS.REFRESH_TOKEN);
  const deviceId = await SecureStore.getItemAsync(TOKEN_KEYS.DEVICE_ID);
  return { accessToken, refreshToken, deviceId };
}

// Delete tokens (logout)
async function clearTokens() {
  await SecureStore.deleteItemAsync(TOKEN_KEYS.ACCESS_TOKEN);
  await SecureStore.deleteItemAsync(TOKEN_KEYS.REFRESH_TOKEN);
  await SecureStore.deleteItemAsync(TOKEN_KEYS.DEVICE_ID);
}
```

**Web (LocalStorage - Less Secure):**
```javascript
const TOKEN_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  DEVICE_ID: 'device_id',
};

// Store tokens
function storeTokens(accessToken, refreshToken, deviceId) {
  localStorage.setItem(TOKEN_KEYS.ACCESS_TOKEN, accessToken);
  localStorage.setItem(TOKEN_KEYS.REFRESH_TOKEN, refreshToken);
  if (deviceId) {
    localStorage.setItem(TOKEN_KEYS.DEVICE_ID, deviceId);
  }
}

// Get tokens
function getTokens() {
  return {
    accessToken: localStorage.getItem(TOKEN_KEYS.ACCESS_TOKEN),
    refreshToken: localStorage.getItem(TOKEN_KEYS.REFRESH_TOKEN),
    deviceId: localStorage.getItem(TOKEN_KEYS.DEVICE_ID),
  };
}

// Delete tokens (logout)
function clearTokens() {
  localStorage.removeItem(TOKEN_KEYS.ACCESS_TOKEN);
  localStorage.removeItem(TOKEN_KEYS.REFRESH_TOKEN);
  localStorage.removeItem(TOKEN_KEYS.DEVICE_ID);
}
```

### Step 2: Generate Device ID

**React Native:**
```javascript
import * as Device from 'expo-device';
import * as Crypto from 'expo-crypto';

async function getOrCreateDeviceId() {
  // Try to get existing device ID
  const existingId = await SecureStore.getItemAsync('device_id');
  if (existingId) {
    return existingId;
  }
  
  // Generate new device ID
  const deviceInfo = `${Device.modelName}-${Device.osName}-${Device.osVersion}`;
  const deviceId = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    deviceInfo + Date.now().toString()
  );
  
  await SecureStore.setItemAsync('device_id', deviceId);
  return deviceId;
}
```

**Web:**
```javascript
function getOrCreateDeviceId() {
  let deviceId = localStorage.getItem('device_id');
  
  if (!deviceId) {
    // Generate device ID from browser fingerprint
    const fingerprint = navigator.userAgent + 
                       navigator.language + 
                       screen.width + 
                       screen.height + 
                       new Date().getTimezoneOffset();
    
    // Simple hash (use crypto.subtle for production)
    deviceId = btoa(fingerprint).substring(0, 32);
    localStorage.setItem('device_id', deviceId);
  }
  
  return deviceId;
}
```

### Step 3: Implement Registration

```javascript
const API_BASE_URL = 'https://freedomos.vulcantech.co/api/v1';

async function registerUser(email, password, fullName) {
  try {
    // Get or create device ID
    const deviceId = await getOrCreateDeviceId();
    
    // Make registration request
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: email.toLowerCase().trim(),
        password: password,
        full_name: fullName || null,
        device_id: deviceId,
      }),
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Store tokens securely
      await storeTokens(
        data.access_token,
        data.refresh_token,
        data.device_id
      );
      
      return {
        success: true,
        tokens: data,
      };
    } else {
      // Handle errors
      return {
        success: false,
        error: data.detail || 'Registration failed',
        statusCode: response.status,
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Network error',
    };
  }
}
```

### Step 4: Implement Login

```javascript
async function loginUser(email, password) {
  try {
    // Get or create device ID
    const deviceId = await getOrCreateDeviceId();
    
    // Make login request
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: email.toLowerCase().trim(),
        password: password,
        device_id: deviceId,
      }),
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Store tokens securely
      await storeTokens(
        data.access_token,
        data.refresh_token,
        data.device_id
      );
      
      return {
        success: true,
        tokens: data,
      };
    } else {
      // Handle errors
      let errorMessage = data.detail || 'Login failed';
      
      // Provide user-friendly messages
      if (response.status === 401) {
        errorMessage = 'Incorrect email or password';
      } else if (response.status === 429) {
        errorMessage = 'Too many failed attempts. Please try again later.';
      } else if (response.status === 403) {
        errorMessage = 'Your account has been disabled. Please contact support.';
      }
      
      return {
        success: false,
        error: errorMessage,
        statusCode: response.status,
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error.message || 'Network error',
    };
  }
}
```

---

## Token Management

### Using Access Token for API Requests

```javascript
async function makeAuthenticatedRequest(url, options = {}) {
  const { accessToken } = await getTokens();
  
  if (!accessToken) {
    throw new Error('Not authenticated');
  }
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });
  
  // Handle token expiration
  if (response.status === 401) {
    // Try to refresh token
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry request with new token
      return makeAuthenticatedRequest(url, options);
    } else {
      // Refresh failed, redirect to login
      await clearTokens();
      throw new Error('Session expired. Please login again.');
    }
  }
  
  return response;
}
```

### Refresh Access Token

```javascript
async function refreshAccessToken() {
  try {
    const { refreshToken } = await getTokens();
    
    if (!refreshToken) {
      return false;
    }
    
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });
    
    if (response.ok) {
      const data = await response.json();
      await storeTokens(
        data.access_token,
        data.refresh_token,
        data.device_id
      );
      return true;
    } else {
      // Refresh token expired or invalid
      await clearTokens();
      return false;
    }
  } catch (error) {
    return false;
  }
}
```

### Check Token Expiration

```javascript
function isTokenExpired(token) {
  try {
    // Decode JWT (without verification)
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    return Date.now() >= exp;
  } catch {
    return true; // Assume expired if can't decode
  }
}

async function getValidAccessToken() {
  const { accessToken, refreshToken } = await getTokens();
  
  if (!accessToken) {
    return null;
  }
  
  // Check if access token is expired
  if (isTokenExpired(accessToken)) {
    // Try to refresh
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      const { accessToken: newToken } = await getTokens();
      return newToken;
    }
    return null;
  }
  
  return accessToken;
}
```

---

## Error Handling

### Common Error Scenarios

```javascript
async function handleAuthError(error, statusCode) {
  switch (statusCode) {
    case 400:
      // Bad request - validation error
      return 'Please check your input and try again.';
    
    case 401:
      // Unauthorized - invalid credentials or expired token
      return 'Invalid email or password.';
    
    case 403:
      // Forbidden - account disabled
      return 'Your account has been disabled. Please contact support.';
    
    case 429:
      // Too many requests - rate limited
      return 'Too many attempts. Please wait before trying again.';
    
    case 500:
      // Server error
      return 'Server error. Please try again later.';
    
    default:
      return error || 'An unexpected error occurred.';
  }
}
```

### User-Friendly Error Messages

```javascript
function getUserFriendlyError(error, statusCode) {
  const errorMessages = {
    400: {
      'Email already registered': 'This email is already registered. Please login instead.',
      'Password must be at least 8 characters': 'Password must be at least 8 characters long.',
    },
    401: {
      'Incorrect email or password': 'The email or password you entered is incorrect.',
    },
    429: {
      'Too many registration attempts': 'Too many registration attempts. Please wait 1 hour before trying again.',
      'Too many failed login attempts': 'Too many failed login attempts. Your account is locked for 1 hour.',
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

### 1. Never Store Passwords

```javascript
// ❌ BAD - Never do this
localStorage.setItem('password', password);

// ✅ GOOD - Only store tokens
await SecureStore.setItemAsync('access_token', accessToken);
```

### 2. Always Use HTTPS

```javascript
// ✅ Always use HTTPS in production
const API_BASE_URL = 'https://freedomos.vulcantech.co/api/v1';
```

### 3. Validate Input on Frontend

```javascript
function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function validatePassword(password) {
  return password.length >= 8 && password.length <= 128;
}

function validateRegistration(email, password) {
  const errors = [];
  
  if (!validateEmail(email)) {
    errors.push('Please enter a valid email address.');
  }
  
  if (!validatePassword(password)) {
    errors.push('Password must be between 8 and 128 characters.');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  };
}
```

### 4. Handle Token Expiration Gracefully

```javascript
async function apiRequest(url, options = {}) {
  let accessToken = await getValidAccessToken();
  
  if (!accessToken) {
    // Redirect to login
    navigateToLogin();
    throw new Error('Please login to continue');
  }
  
  // Make request with token
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  // Handle 401 (token expired)
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry with new token
      accessToken = await getValidAccessToken();
      return fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${accessToken}`,
        },
      });
    } else {
      navigateToLogin();
      throw new Error('Session expired');
    }
  }
  
  return response;
}
```

### 5. Clear Sensitive Data on Logout

```javascript
async function logout() {
  try {
    const { refreshToken } = await getTokens();
    
    // Call logout endpoint to revoke tokens on server
    if (refreshToken) {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      });
    }
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Always clear local tokens
    await clearTokens();
    // Navigate to login screen
    navigateToLogin();
  }
}
```

---

## Code Examples

### Complete Registration Component (React Native)

```javascript
import React, { useState } from 'react';
import { View, TextInput, Button, Text, Alert } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const RegisterScreen = ({ navigation }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    // Validate input
    const validation = validateRegistration(email, password);
    if (!validation.isValid) {
      Alert.alert('Validation Error', validation.errors.join('\n'));
      return;
    }

    setLoading(true);

    try {
      const result = await registerUser(email, password, fullName);
      
      if (result.success) {
        Alert.alert('Success', 'Account created successfully!', [
          { text: 'OK', onPress: () => navigation.navigate('Home') }
        ]);
      } else {
        const friendlyError = getUserFriendlyError(result.error, result.statusCode);
        Alert.alert('Registration Failed', friendlyError);
      }
    } catch (error) {
      Alert.alert('Error', 'An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ padding: 20 }}>
      <TextInput
        placeholder="Email"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        style={{ borderWidth: 1, padding: 10, marginBottom: 10 }}
      />
      <TextInput
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        style={{ borderWidth: 1, padding: 10, marginBottom: 10 }}
      />
      <TextInput
        placeholder="Full Name (Optional)"
        value={fullName}
        onChangeText={setFullName}
        style={{ borderWidth: 1, padding: 10, marginBottom: 10 }}
      />
      <Button
        title={loading ? 'Registering...' : 'Register'}
        onPress={handleRegister}
        disabled={loading}
      />
    </View>
  );
};
```

### Complete Login Component (React Native)

```javascript
import React, { useState } from 'react';
import { View, TextInput, Button, Text, Alert } from 'react-native';

const LoginScreen = ({ navigation }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please enter both email and password');
      return;
    }

    setLoading(true);

    try {
      const result = await loginUser(email, password);
      
      if (result.success) {
        navigation.navigate('Home');
      } else {
        const friendlyError = getUserFriendlyError(result.error, result.statusCode);
        Alert.alert('Login Failed', friendlyError);
      }
    } catch (error) {
      Alert.alert('Error', 'An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ padding: 20 }}>
      <TextInput
        placeholder="Email"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        style={{ borderWidth: 1, padding: 10, marginBottom: 10 }}
      />
      <TextInput
        placeholder="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        style={{ borderWidth: 1, padding: 10, marginBottom: 10 }}
      />
      <Button
        title={loading ? 'Logging in...' : 'Login'}
        onPress={handleLogin}
        disabled={loading}
      />
    </View>
  );
};
```

---

## Summary

### Key Points

1. **Registration Process:**
   - Send email, password, full_name, device_id to `/auth/register`
   - Receive access_token, refresh_token, device_id
   - Store tokens securely (SecureStore for mobile, localStorage for web)
   - User is automatically logged in after registration

2. **Login Process:**
   - Send email, password, device_id to `/auth/login`
   - Receive access_token, refresh_token, device_id
   - Store tokens securely
   - Use access_token for authenticated API requests

3. **Token Management:**
   - Access tokens expire in 30 minutes
   - Refresh tokens expire in 7 days
   - Use refresh token to get new access token when expired
   - Always include `Authorization: Bearer {access_token}` header

4. **Security:**
   - Never store passwords
   - Always use HTTPS
   - Validate input on frontend
   - Handle errors gracefully
   - Clear tokens on logout

### Quick Reference

**Registration:**
```javascript
POST /auth/register
Body: { email, password, full_name?, device_id? }
Response: { access_token, refresh_token, token_type, expires_in, device_id }
```

**Login:**
```javascript
POST /auth/login
Body: { email, password, device_id? }
Response: { access_token, refresh_token, token_type, expires_in, device_id }
```

**Using Tokens:**
```javascript
GET /api/v1/email/inbox
Headers: { Authorization: "Bearer {access_token}" }
```

---

For more information, see the main [API Documentation](./API_README.md).
