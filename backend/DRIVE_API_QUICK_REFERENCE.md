# Drive API Quick Reference

## Upload File API

### Endpoint
`POST /api/v1/drive/upload`

### Authentication
Required: Bearer token in `Authorization` header

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | ✅ Yes | File to upload (any type: PDF, Word, images, text, etc.) |
| `passcode` | String | ❌ No | Optional passcode for additional protection |
| `never_expire` | Boolean | ❌ No | If `true`, file never expires. Default: `false` |
| `expires_in_hours` | Integer | ❌ No | Expiration in hours (1-8760). Only used if `never_expire=false` |
| `expires_in_days` | Integer | ❌ No | Expiration in days (1-365). Takes precedence over hours. Only used if `never_expire=false` |

### Expiration Logic

1. **If `never_expire=true`**:
   - File never expires
   - `expires_at` will be `null` in response
   - `expires_in_hours` and `expires_in_days` are ignored

2. **If `never_expire=false`** (or not provided):
   - If `expires_in_days` is provided: Use days (converted to hours)
   - Else if `expires_in_hours` is provided: Use hours
   - Else: No expiration (same as `never_expire=true`)

### Supported File Types

✅ **All file types are supported:**
- Documents: PDF, Word (.doc, .docx), Text (.txt, .md)
- Images: PNG, JPG, JPEG, GIF, WebP, SVG
- Spreadsheets: Excel (.xls, .xlsx), CSV
- Archives: ZIP, RAR, TAR, GZ
- Any other file format

**No file type restrictions** - upload any file type you need.

### File Size Limits

- **Max file size**: 100MB per file
- **Storage quota**: 5GB per user (total across all files)

### Example Requests

#### Example 1: Upload PDF (Never Expires)
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "never_expire=true"
```

#### Example 2: Upload Word Document (30 Days)
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@report.docx" \
  -F "never_expire=false" \
  -F "expires_in_days=30"
```

#### Example 3: Upload Image (24 Hours)
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@photo.jpg" \
  -F "never_expire=false" \
  -F "expires_in_hours=24"
```

#### Example 4: Upload with Passcode (Never Expires)
```bash
curl -X POST "https://freedomos.vulcantech.co/api/v1/drive/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@secret.txt" \
  -F "never_expire=true" \
  -F "passcode=my-secret-passcode"
```

### Response Format

**Success (201 Created):**
```json
{
  "file_id": "abc123xyz...",
  "filename": "document.pdf",
  "size": 1024000,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": null,  // null if never_expire=true
  "created_at": "2026-01-29T12:00:00Z"
}
```

**Error (400/413/500):**
```json
{
  "detail": "Error message"
}
```

## Upload Encrypted File API

### Endpoint
`POST /api/v1/drive/upload-encrypted`

### Request Body
```json
{
  "filename": "document.pdf",
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
  "content_type": "application/pdf",
  "size": 1024000,
  "passcode": "optional-passcode",
  "never_expire": false,
  "expires_in_days": 30,
  "expires_in_hours": null
}
```

### Expiration Fields

- `never_expire`: Boolean - If `true`, file never expires
- `expires_in_days`: Integer (1-365) - Days until expiration (takes precedence)
- `expires_in_hours`: Integer (1-8760) - Hours until expiration (used if days not provided)

## Other Drive APIs

### List Files
`GET /api/v1/drive/files?limit=50&offset=0`

### Get File Info
`GET /api/v1/drive/file/{file_id}`

### Download File
`GET /api/v1/drive/file/{file_id}/download?token={signed_token}`

### Delete File
`DELETE /api/v1/drive/file/{file_id}`

### Get Storage Quota
`GET /api/v1/drive/storage/quota`

### Unlock Passcode-Protected File
`POST /api/v1/drive/file/{file_id}/unlock`

---

**Last Updated**: January 29, 2026
