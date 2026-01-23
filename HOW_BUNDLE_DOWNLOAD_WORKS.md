# 📥 How Bundle Download API Works

## Overview

The download API allows you to download GrapheneOS builds from the `bundles/` folder on the server. Based on your bundle structure, here's how it works:

## Your Bundle Structure

```
bundles/
└── panther/
    └── 2025122500/
        ├── image.zip                    ← Main bundle ZIP (downloadable)
        ├── image.zip.sha256            ← Checksum file
        ├── image.zip.sig               ← Signature file
        ├── metadata.json               ← Bundle metadata
        ├── flash-all.sh                ← Flash script (Unix)
        ├── flash-all.bat               ← Flash script (Windows)
        └── panther-install-2025122500/ ← Extracted files directory
            ├── boot.img                 ← Boot partition (downloadable)
            ├── init_boot.img            ← Init boot partition
            ├── dtbo.img                 ← Device tree overlay
            ├── vbmeta.img               ← Verified boot metadata
            ├── vendor_boot.img          ← Vendor boot
            ├── vendor_kernel_boot.img   ← Vendor kernel boot
            ├── pvmfw.img                ← PVM firmware
            ├── bootloader-*.img         ← Bootloader image
            ├── radio-*.img              ← Radio firmware
            ├── super_1.img              ← Super partition (part 1)
            ├── super_2.img              ← Super partition (part 2)
            ├── ...                      ← More super partition parts
            ├── super_14.img             ← Super partition (part 14)
            └── flash-all.sh             ← Flash script
```

## Download API Endpoints

### 1. **Download Complete Bundle ZIP**

**Endpoint**: `GET /bundles/releases/{codename}/{version}/download`

**How it works**:
1. Backend finds bundle: `bundles/panther/2025122500/`
2. Looks for `image.zip` in that directory
3. If found, serves it as a download
4. If not found, checks for `{codename}-factory-{version}.zip`
5. Returns the ZIP file with proper headers

**Example**:
```bash
# Download the complete bundle ZIP
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/download

# This downloads: panther-factory-2025122500.zip (which is actually image.zip)
```

**Frontend Usage**:
```typescript
// Download bundle ZIP in browser
const downloadUrl = `https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/download`;

// Method 1: Direct browser download
window.open(downloadUrl);

// Method 2: Fetch as Blob (for web flasher)
const response = await fetch(downloadUrl);
const blob = await response.blob();
// blob contains the image.zip file
```

**What you get**:
- Complete bundle ZIP file (`image.zip`)
- Contains all partition images and flash scripts
- Ready to extract and use for flashing

---

### 2. **Download Individual Files**

**Endpoint**: `GET /bundles/releases/{codename}/{version}/file/{filename}`

**How it works**:
1. Backend finds bundle: `bundles/panther/2025122500/`
2. Looks for file in bundle directory (including subdirectories)
3. Validates filename (prevents directory traversal attacks)
4. Serves the file with appropriate Content-Type

**Examples**:

```bash
# Download boot.img from root directory (if exists)
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/boot.img

# Download flash-all.sh
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/flash-all.sh

# Download metadata.json
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/metadata.json
```

**Note**: Files in subdirectories (like `panther-install-2025122500/boot.img`) are also accessible:

```bash
# Download boot.img from subdirectory
curl -O "https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/panther-install-2025122500/boot.img"
```

**Frontend Usage**:
```typescript
// Download specific partition file
async function downloadPartition(codename: string, version: string, filename: string) {
  const url = `https://freedomos.vulcantech.co/bundles/releases/${codename}/${version}/file/${filename}`;
  
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download ${filename}: ${response.statusText}`);
  }
  
  return await response.blob();
}

// Download boot.img
const bootImg = await downloadPartition('panther', '2025122500', 'panther-install-2025122500/boot.img');
```

---

### 3. **List All Files in Bundle**

**Endpoint**: `GET /bundles/releases/{codename}/{version}/list`

**How it works**:
1. Backend finds bundle directory
2. Recursively scans all files (including subdirectories)
3. Returns list with file names, sizes, and download paths

**Example**:
```bash
curl https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/list
```

**Response**:
```json
{
  "codename": "panther",
  "version": "2025122500",
  "bundle_path": "/root/graohen_os/bundles/panther/2025122500",
  "files": [
    {
      "name": "image.zip",
      "size": 2147483648,
      "path": "/bundles/releases/panther/2025122500/file/image.zip"
    },
    {
      "name": "flash-all.sh",
      "size": 2048,
      "path": "/bundles/releases/panther/2025122500/file/flash-all.sh"
    },
    {
      "name": "metadata.json",
      "size": 512,
      "path": "/bundles/releases/panther/2025122500/file/metadata.json"
    },
    {
      "name": "panther-install-2025122500/boot.img",
      "size": 67108864,
      "path": "/bundles/releases/panther/2025122500/file/panther-install-2025122500/boot.img"
    },
    {
      "name": "panther-install-2025122500/init_boot.img",
      "size": 8388608,
      "path": "/bundles/releases/panther/2025122500/file/panther-install-2025122500/init_boot.img"
    },
    {
      "name": "panther-install-2025122500/super_1.img",
      "size": 268435456,
      "path": "/bundles/releases/panther/2025122500/file/panther-install-2025122500/super_1.img"
    }
    // ... more files
  ],
  "total_files": 30
}
```

**Frontend Usage**:
```typescript
// List all files in bundle
async function listBundleFiles(codename: string, version: string) {
  const response = await fetch(
    `https://freedomos.vulcantech.co/bundles/releases/${codename}/${version}/list`
  );
  const data = await response.json();
  return data.files;
}

// Get all files
const files = await listBundleFiles('panther', '2025122500');

// Filter for partition images
const partitionImages = files.filter(f => f.name.endsWith('.img'));

// Download all super partition images
const superImages = files.filter(f => f.name.includes('super_'));
for (const file of superImages) {
  const blob = await fetch(file.path).then(r => r.blob());
  // Process blob...
}
```

---

## Complete Download Flow Example

### Scenario: Web Flasher Downloading Bundle

```typescript
// 1. Get bundle info
const bundleInfo = await fetch(
  'https://freedomos.vulcantech.co/bundles/for/panther'
).then(r => r.json());

console.log('Bundle:', bundleInfo);
// {
//   "codename": "panther",
//   "version": "2025122500",
//   "path": "/root/graohen_os/bundles/panther/2025122500",
//   ...
// }

// 2. List all files (optional - to see what's available)
const filesList = await fetch(
  `https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/list`
).then(r => r.json());

console.log(`Found ${filesList.total_files} files`);

// 3. Download complete bundle ZIP
const downloadUrl = `https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/download`;

const response = await fetch(downloadUrl);
if (!response.ok) {
  throw new Error(`Download failed: ${response.status}`);
}

// Get file size from headers
const contentLength = response.headers.get('content-length');
const totalSize = parseInt(contentLength || '0', 10);

// Download with progress tracking
const reader = response.body?.getReader();
const chunks: Uint8Array[] = [];
let downloaded = 0;

if (reader) {
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    chunks.push(value);
    downloaded += value.length;
    
    // Update progress
    const progress = (downloaded / totalSize) * 100;
    console.log(`Downloaded: ${progress.toFixed(2)}%`);
  }
}

// Combine chunks into blob
const blob = new Blob(chunks, { type: 'application/zip' });
console.log(`Download complete! Size: ${blob.size} bytes`);

// 4. Use blob for flashing (extract and flash partitions)
// The blob contains image.zip which can be extracted
```

---

## File Lookup Process

When you request a file, the backend:

1. **Finds Bundle Directory**:
   ```
   bundles/{codename}/{version}/
   → bundles/panther/2025122500/
   ```

2. **For ZIP Download** (`/download`):
   - Checks: `bundles/panther/2025122500/image.zip` ✅ (found)
   - Serves it as `panther-factory-2025122500.zip`

3. **For File Download** (`/file/{filename}`):
   - Checks: `bundles/panther/2025122500/{filename}`
   - Also checks subdirectories recursively
   - Example: `panther-install-2025122500/boot.img` ✅ (found)

4. **Security Checks**:
   - Blocks `..` (directory traversal)
   - Blocks `/` and `\` in filename
   - Validates file is within bundle directory

---

## Real-World Usage Examples

### Example 1: Download Bundle for Web Flasher

```typescript
// In web flasher (useBuildDownloader hook)
async function downloadBundleForFlashing(codename: string, version: string) {
  const url = `https://freedomos.vulcantech.co/bundles/releases/${codename}/${version}/download`;
  
  const response = await fetch(url);
  const blob = await response.blob();
  
  // Extract ZIP in browser using JSZip
  const zip = await JSZip.loadAsync(blob);
  
  // Extract specific partition files
  const bootImg = await zip.file('panther-install-2025122500/boot.img')?.async('blob');
  const super1Img = await zip.file('panther-install-2025122500/super_1.img')?.async('blob');
  
  return { bootImg, super1Img, /* ... */ };
}
```

### Example 2: Download Individual Partitions

```typescript
// Download only needed partitions (saves bandwidth)
async function downloadPartitions(codename: string, version: string, partitions: string[]) {
  const downloaded: Record<string, Blob> = {};
  
  for (const partition of partitions) {
    const url = `https://freedomos.vulcantech.co/bundles/releases/${codename}/${version}/file/panther-install-2025122500/${partition}`;
    const response = await fetch(url);
    downloaded[partition] = await response.blob();
  }
  
  return downloaded;
}

// Download only boot and super partitions
const partitions = await downloadPartitions('panther', '2025122500', [
  'boot.img',
  'super_1.img',
  'super_2.img',
  // ... more super images
]);
```

### Example 3: Check File Availability Before Download

```typescript
// List files first, then download only what exists
async function downloadIfExists(codename: string, version: string, filename: string) {
  // First, list files
  const listResponse = await fetch(
    `https://freedomos.vulcantech.co/bundles/releases/${codename}/${version}/list`
  );
  const { files } = await listResponse.json();
  
  // Check if file exists
  const fileExists = files.some((f: any) => f.name === filename);
  
  if (!fileExists) {
    throw new Error(`File not found: ${filename}`);
  }
  
  // Download file
  const downloadUrl = `https://freedomos.vulcantech.co/bundles/releases/${codename}/${version}/file/${filename}`;
  const response = await fetch(downloadUrl);
  return await response.blob();
}
```

---

## API Response Headers

When downloading files, the API sets proper headers:

```
Content-Type: application/zip (for ZIP files)
Content-Type: application/octet-stream (for .img files)
Content-Type: text/x-shellscript (for .sh files)
Content-Disposition: attachment; filename="panther-factory-2025122500.zip"
Content-Length: 2147483648
```

---

## Error Handling

### Bundle Not Found (404)
```json
{
  "detail": "Bundle not found for codename: panther, version: 2025122500"
}
```

### File Not Found (404)
```json
{
  "detail": "File not found: boot.img"
}
```

### Invalid Filename (400)
```json
{
  "detail": "Invalid filename"
}
```
(Occurs if filename contains `..`, `/`, or `\`)

---

## Summary

1. **Download Bundle ZIP**: `GET /bundles/releases/{codename}/{version}/download`
   - Downloads complete `image.zip` file
   - Best for: Complete bundle download, offline flashing

2. **Download Individual File**: `GET /bundles/releases/{codename}/{version}/file/{filename}`
   - Downloads specific files (partitions, scripts, etc.)
   - Best for: Selective downloads, web flasher

3. **List Files**: `GET /bundles/releases/{codename}/{version}/list`
   - Lists all available files with sizes and paths
   - Best for: Discovering available files, progress tracking

All endpoints work with your current bundle structure at `bundles/panther/2025122500/`!

---

**Last Updated**: 2025-01-23
**Backend Version**: 1.0.0
