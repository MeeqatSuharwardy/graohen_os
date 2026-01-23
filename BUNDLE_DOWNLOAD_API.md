# 📦 Bundle Download API

## Overview

The backend provides APIs to download bundles and files from the local `bundles/` folder. This allows the frontend to download builds that are already stored on the server.

## Endpoints

### 1. **Download Bundle ZIP File**

**Endpoint**: `GET /bundles/releases/{codename}/{version}/download`

**Purpose**: Download the complete bundle ZIP file (image.zip or factory ZIP).

**Parameters**:
- `codename` (path): Device codename (e.g., `panther`)
- `version` (path): Bundle version (e.g., `2025122500`)

**Response**: 
- Returns the ZIP file as a download
- Content-Type: `application/zip`
- Filename: `{codename}-factory-{version}.zip`

**Example**:
```bash
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/download
```

**File Lookup Order**:
1. `bundles/{codename}/{version}/image.zip`
2. `bundles/{codename}/{version}/{codename}-factory-{version}.zip`
3. Bundle path itself if it's a ZIP file

**Error Responses**:
- `404`: Bundle not found
- `404`: Bundle ZIP file not found

---

### 2. **Download Specific File from Bundle**

**Endpoint**: `GET /bundles/releases/{codename}/{version}/file/{filename}`

**Purpose**: Download a specific file from a bundle (e.g., `boot.img`, `system.img`, `flash-all.sh`).

**Parameters**:
- `codename` (path): Device codename
- `version` (path): Bundle version
- `filename` (path): Name of the file to download

**Response**:
- Returns the file as a download
- Content-Type determined by file extension:
  - `.img` → `application/octet-stream`
  - `.zip` → `application/zip`
  - `.sh` → `text/x-shellscript`
  - `.bat` → `text/plain`
  - `.json` → `application/json`
  - Default → `application/octet-stream`

**Example**:
```bash
# Download boot.img
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/boot.img

# Download flash-all.sh
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/flash-all.sh
```

**Security**:
- Prevents directory traversal (`..`, `/`, `\` are blocked)
- Ensures file is within bundle directory
- Validates file path

**Error Responses**:
- `400`: Invalid filename (directory traversal attempt)
- `404`: Bundle not found
- `404`: File not found

---

### 3. **List Files in Bundle**

**Endpoint**: `GET /bundles/releases/{codename}/{version}/list`

**Purpose**: List all files available in a bundle directory.

**Parameters**:
- `codename` (path): Device codename
- `version` (path): Bundle version

**Response**:
```json
{
  "codename": "panther",
  "version": "2025122500",
  "bundle_path": "/path/to/bundles/panther/2025122500",
  "files": [
    {
      "name": "boot.img",
      "size": 67108864,
      "path": "/bundles/releases/panther/2025122500/file/boot.img"
    },
    {
      "name": "system.img",
      "size": 4294967296,
      "path": "/bundles/releases/panther/2025122500/file/system.img"
    },
    {
      "name": "flash-all.sh",
      "size": 2048,
      "path": "/bundles/releases/panther/2025122500/file/flash-all.sh"
    }
  ],
  "total_files": 15
}
```

**Features**:
- Lists all files in bundle directory
- Includes subdirectories (recursive)
- Provides download paths for each file
- Shows file sizes

**Example**:
```bash
curl https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/list
```

**Error Responses**:
- `404`: Bundle not found
- `404`: Bundle directory not found
- `500`: Error listing files

---

## Existing Endpoints (Reference)

### Download from GrapheneOS Releases

**Endpoint**: `POST /bundles/download`

**Purpose**: Download a bundle from GrapheneOS releases (external download).

**Request**:
```json
{
  "codename": "panther",
  "version": "2025122500"
}
```

**Response**:
```json
{
  "download_id": "panther-2025122500",
  "status": "started",
  "message": "Download started"
}
```

**Status Check**: `GET /bundles/download/{download_id}/status`

---

## Usage Examples

### Frontend Integration

#### 1. List Available Bundles

```typescript
// Get bundle info
const bundle = await apiClient.get(`/bundles/for/panther`);

// List files in bundle
const files = await apiClient.get(`/bundles/releases/panther/${bundle.version}/list`);
```

#### 2. Download Bundle ZIP

```typescript
// Direct download link
const downloadUrl = `https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/download`;

// Use in browser
window.open(downloadUrl);

// Or fetch for processing
const response = await fetch(downloadUrl);
const blob = await response.blob();
```

#### 3. Download Specific File

```typescript
// Download boot.img
const bootImgUrl = `https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/boot.img`;

const response = await fetch(bootImgUrl);
const blob = await response.blob();
```

#### 4. Download Bundle in Browser (Web Flasher)

```typescript
// For web flasher - download bundle ZIP
async function downloadBundle(codename: string, version: string) {
  const downloadUrl = `${API_BASE_URL}/bundles/releases/${codename}/${version}/download`;
  
  const response = await fetch(downloadUrl);
  if (!response.ok) {
    throw new Error(`Failed to download bundle: ${response.statusText}`);
  }
  
  const blob = await response.blob();
  return blob;
}

// Use in web flasher
const bundleBlob = await downloadBundle('panther', '2025122500');
// Use blob for flashing
```

---

## Bundle Structure

Bundles are stored in:
```
bundles/
├── {codename}/
│   ├── {version}/
│   │   ├── image.zip (or {codename}-factory-{version}.zip)
│   │   ├── boot.img
│   │   ├── system.img
│   │   ├── vendor.img
│   │   ├── flash-all.sh
│   │   ├── flash-all.bat
│   │   ├── metadata.json
│   │   └── ...
```

---

## Error Handling

### Common Errors

1. **Bundle Not Found (404)**
   ```json
   {
     "detail": "Bundle not found for codename: panther, version: 2025122500"
   }
   ```

2. **File Not Found (404)**
   ```json
   {
     "detail": "File not found: boot.img"
   }
   ```

3. **Invalid Filename (400)**
   ```json
   {
     "detail": "Invalid filename"
   }
   ```

---

## Security Considerations

1. **Directory Traversal Prevention**
   - Blocks `..`, `/`, `\` in filenames
   - Validates file path is within bundle directory

2. **File Access Control**
   - Only files within bundle directory are accessible
   - No access to files outside bundles folder

3. **Content-Type Headers**
   - Proper MIME types set for different file types
   - Prevents browser execution of binary files

---

## Code References

- **Bundle Download**: `backend/py-service/app/routes/bundles.py:download_bundle_file()`
- **File Download**: `backend/py-service/app/routes/bundles.py:download_bundle_file_item()`
- **List Files**: `backend/py-service/app/routes/bundles.py:list_bundle_files()`
- **Bundle Management**: `backend/py-service/app/utils/bundles.py`

---

## API Routes Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/bundles/releases/{codename}/{version}/download` | Download bundle ZIP |
| `GET` | `/bundles/releases/{codename}/{version}/file/{filename}` | Download specific file |
| `GET` | `/bundles/releases/{codename}/{version}/list` | List all files |
| `POST` | `/bundles/download` | Download from GrapheneOS (external) |
| `GET` | `/bundles/download/{download_id}/status` | Check download status |
| `GET` | `/bundles/for/{codename}` | Get bundle info |
| `GET` | `/bundles/index` | List all bundles |

---

**Last Updated**: 2025-01-22
**Backend Version**: 1.0.0
