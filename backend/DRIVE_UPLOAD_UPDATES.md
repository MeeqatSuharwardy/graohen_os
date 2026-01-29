# Drive Upload API Updates

## Overview

Updated the Drive upload APIs to support:
1. **Flexible expiration options**: Never expire OR set expiration in hours/days
2. **All file types**: PDF, Word, text, images, spreadsheets, and any other format
3. **Improved API structure**: Better parameter handling and validation

## Changes Made

### 1. Updated Expiration Model

**Before:**
- Only `expires_in_hours` (optional)
- If not provided, file expires based on default settings

**After:**
- `never_expire`: Boolean flag
  - `true`: File never expires (no expiration date)
  - `false`: Use expiration time (hours or days)
- `expires_in_days`: Optional (1-365 days, takes precedence over hours)
- `expires_in_hours`: Optional (1-8760 hours, used if days not provided)

### 2. File Type Support

**All file types are now supported:**
- ✅ PDF documents (`.pdf`)
- ✅ Word documents (`.doc`, `.docx`)
- ✅ Text files (`.txt`, `.md`, etc.)
- ✅ Images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, etc.)
- ✅ Spreadsheets (`.xls`, `.xlsx`, `.csv`)
- ✅ Archives (`.zip`, `.rar`, `.tar`, `.gz`)
- ✅ Any other file format

**No file type restrictions** - the API accepts any `content_type` or auto-detects from file extension.

### 3. Updated API Endpoints

#### `POST /api/v1/drive/upload`

**New Parameters:**
```python
never_expire: bool = False  # If True, file never expires
expires_in_hours: Optional[int] = None  # Hours (1-8760, only if never_expire=False)
expires_in_days: Optional[int] = None  # Days (1-365, takes precedence over hours)
```

**Example Request:**
```bash
# Upload file that never expires
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "never_expire=true"

# Upload file with 7 days expiration
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "never_expire=false" \
  -F "expires_in_days=7"

# Upload file with 24 hours expiration
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "never_expire=false" \
  -F "expires_in_hours=24"
```

#### `POST /api/v1/drive/upload-encrypted`

**Updated Request Model:**
```python
class FileUploadEncryptedRequest(BaseModel):
    filename: str
    encrypted_content: Dict[str, str]
    encrypted_content_key: Dict[str, str]
    content_type: Optional[str] = None  # Supports any MIME type
    size: int
    passcode: Optional[str] = None
    never_expire: bool = False  # NEW
    expires_in_hours: Optional[int] = None  # Only if never_expire=False
    expires_in_days: Optional[int] = None  # NEW - takes precedence over hours
```

**Example Request:**
```json
{
  "filename": "document.pdf",
  "encrypted_content": {...},
  "encrypted_content_key": {...},
  "content_type": "application/pdf",
  "size": 1024000,
  "never_expire": false,
  "expires_in_days": 30
}
```

### 4. Updated Service Layer

**File**: `backend/py-service/app/services/drive_service_mongodb.py`

**Updated Function Signature:**
```python
async def encrypt_and_store_file(
    file_content: bytes,
    filename: str,
    file_size: int,
    owner_email: str,
    content_type: Optional[str] = None,  # Accepts any file type
    passcode: Optional[str] = None,
    expires_in_hours: Optional[int] = None,
    never_expire: bool = False,  # NEW
) -> Dict[str, Any]:
```

## API Usage Examples

### Example 1: Upload PDF (Never Expires)

```python
import requests

url = "https://freedomos.vulcantech.co/api/v1/drive/upload"
headers = {"Authorization": f"Bearer {access_token}"}

files = {"file": open("document.pdf", "rb")}
data = {
    "never_expire": True
}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

### Example 2: Upload Word Document (30 Days Expiration)

```python
files = {"file": open("report.docx", "rb")}
data = {
    "never_expire": False,
    "expires_in_days": 30
}

response = requests.post(url, headers=headers, files=files, data=data)
```

### Example 3: Upload Image (24 Hours Expiration)

```python
files = {"file": open("photo.jpg", "rb")}
data = {
    "never_expire": False,
    "expires_in_hours": 24
}

response = requests.post(url, headers=headers, files=files, data=data)
```

### Example 4: Upload Text File (Never Expires, with Passcode)

```python
files = {"file": open("notes.txt", "rb")}
data = {
    "never_expire": True,
    "passcode": "my-secret-passcode"
}

response = requests.post(url, headers=headers, files=files, data=data)
```

## Response Format

**Success Response (201 Created):**
```json
{
  "file_id": "abc123...",
  "filename": "document.pdf",
  "size": 1024000,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": null,  // null if never_expire=true
  "created_at": "2026-01-29T12:00:00Z"
}
```

## File Size Limits

- **Max file size**: 100MB per file
- **Storage quota**: 5GB per user (total)
- **No file type restrictions**: All file types accepted

## Security Features

- ✅ Multi-layer encryption (3 layers)
- ✅ Optional passcode protection
- ✅ End-to-end encryption support (client-side encryption)
- ✅ Storage quota enforcement
- ✅ Access control (owner-only access)

## Files Modified

1. **`backend/py-service/app/api/v1/endpoints/drive.py`**
   - Updated `FileUploadEncryptedRequest` model
   - Updated `upload_file` endpoint
   - Updated `upload_encrypted_file` endpoint
   - Added support for `never_expire`, `expires_in_days`, `expires_in_hours`

2. **`backend/py-service/app/services/drive_service_mongodb.py`**
   - Updated `encrypt_and_store_file` function
   - Added `never_expire` parameter
   - Updated expiration calculation logic

## Testing

After deployment, test with:

```bash
# Test 1: Upload PDF (never expires)
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.pdf" \
  -F "never_expire=true"

# Test 2: Upload Word doc (7 days)
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.docx" \
  -F "never_expire=false" \
  -F "expires_in_days=7"

# Test 3: Upload image (24 hours)
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.jpg" \
  -F "never_expire=false" \
  -F "expires_in_hours=24"
```

---

**Status**: ✅ Updates complete and ready for deployment  
**Last Updated**: January 29, 2026
