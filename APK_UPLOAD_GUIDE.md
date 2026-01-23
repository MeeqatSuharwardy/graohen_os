# APK Upload Guide

This guide explains how to upload APKs to the FlashDash API server.

## API Endpoint

**Endpoint**: `POST /apks/upload`  
**Base URL**: `https://freedomos.vulcantech.co`  
**Full URL**: `https://freedomos.vulcantech.co/apks/upload`

## Authentication

The endpoint uses **HTTP Basic Authentication**:
- **Username**: `admin`
- **Password**: `AllHailToEagle`

## Request Format

- **Content-Type**: `multipart/form-data`
- **Method**: `POST`
- **Required Fields**:
  - `file`: The APK file to upload
  - `username`: `admin` (from form)
  - `password`: `AllHailToEagle` (from form)

## Methods to Upload APKs

### Method 1: Using cURL (Command Line)

```bash
curl -X POST https://freedomos.vulcantech.co/apks/upload \
  -u admin:AllHailToEagle \
  -F "file=@/path/to/your/app.apk" \
  -F "username=admin" \
  -F "password=AllHailToEagle"
```

**Example**:
```bash
curl -X POST https://freedomos.vulcantech.co/apks/upload \
  -u admin:AllHailToEagle \
  -F "file=@/Users/username/Downloads/myapp.apk" \
  -F "username=admin" \
  -F "password=AllHailToEagle"
```

### Method 2: Using Web Browser

1. Navigate to: `https://freedomos.vulcantech.co/apks/upload`
2. Enter credentials when prompted:
   - Username: `admin`
   - Password: `AllHailToEagle`
3. Select your APK file
4. Click "Upload"

### Method 3: Using Postman or Similar Tools

1. Set method to `POST`
2. URL: `https://freedomos.vulcantech.co/apks/upload`
3. Go to **Authorization** tab:
   - Type: `Basic Auth`
   - Username: `admin`
   - Password: `AllHailToEagle`
4. Go to **Body** tab:
   - Select `form-data`
   - Add field `file` (type: File) and select your APK
   - Add field `username` (type: Text) with value `admin`
   - Add field `password` (type: Text) with value `AllHailToEagle`
5. Click **Send**

### Method 4: Using Python (requests library)

```python
import requests

url = "https://freedomos.vulcantech.co/apks/upload"
auth = ("admin", "AllHailToEagle")

files = {
    "file": ("myapp.apk", open("/path/to/myapp.apk", "rb"), "application/vnd.android.package-archive")
}

data = {
    "username": "admin",
    "password": "AllHailToEagle"
}

response = requests.post(url, auth=auth, files=files, data=data)
print(response.text)
```

### Method 5: Using JavaScript/Node.js (fetch API)

```javascript
const FormData = require('form-data');
const fs = require('fs');
const fetch = require('node-fetch');

const form = new FormData();
form.append('file', fs.createReadStream('/path/to/myapp.apk'));
form.append('username', 'admin');
form.append('password', 'AllHailToEagle');

fetch('https://freedomos.vulcantech.co/apks/upload', {
  method: 'POST',
  headers: {
    'Authorization': 'Basic ' + Buffer.from('admin:AllHailToEagle').toString('base64')
  },
  body: form
})
.then(response => response.text())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

## Response

On successful upload, you'll receive an HTML page with:
- Success message
- File name
- File size
- Redirect back to upload form after 3 seconds

## File Requirements

- **File Extension**: Must be `.apk`
- **File Size**: No specific limit mentioned (check server logs if issues occur)
- **Duplicate Files**: If a file with the same name exists, it will be renamed with a counter suffix (e.g., `app_1.apk`, `app_2.apk`)

## Error Responses

- **401 Unauthorized**: Invalid username/password
- **400 Bad Request**: File is not an APK (wrong extension)
- **500 Internal Server Error**: Server-side error during upload

## After Upload

Once uploaded, the APK will appear in the APK list:
- **Endpoint**: `GET /apks/list`
- **Response**: JSON array with APK information (filename, size, upload_time)

## Security Note

⚠️ **Important**: The upload endpoint uses HTTP Basic Authentication with a fixed password. This is suitable for internal/admin use but should be protected in production environments. Consider:
- Using environment variables for the password
- Implementing proper user authentication
- Restricting access to the upload endpoint (IP whitelist, VPN, etc.)
