# How to Make Bundle Folder Downloadable on Server

## Your Bundle Location
```
/root/graohen_os/bundles/panther/2026011300/
├── flash-all.bat
├── flash-all.sh
├── image.zip
├── image.zip.sha256
├── image.zip.sha256.new
├── image.zip.sig
├── metadata.json
└── panther-install-2026011300/
```

## How the System Works

The bundle download system is **already built** and will automatically discover bundles in the correct structure. Your bundle is already in the correct location!

### Bundle Discovery

The system checks bundles in this order:
1. **From config**: `GRAPHENE_BUNDLES_ROOT` environment variable (if set)
2. **From project root**: `{project_root}/bundles` (automatic)
   - Since your project is at `/root/graohen_os`, it will check `/root/graohen_os/bundles` ✅

### Your Bundle Structure ✅

Your bundle matches the expected structure:
- **Codename**: `panther`
- **Version**: `2026011300`
- **Path**: `/root/graohen_os/bundles/panther/2026011300/`
- **Required file**: `image.zip` ✅ (exists)

## Steps to Make It Downloadable

### Step 1: Ensure Backend Can Access Bundles

The backend automatically finds bundles at `/root/graohen_os/bundles` if:
- The backend is running from `/root/graohen_os` (or can find the project root)
- OR you set the `GRAPHENE_BUNDLES_ROOT` environment variable

**Option A: Automatic (Recommended)**
If your backend runs from `/root/graohen_os`, it will automatically find bundles at `/root/graohen_os/bundles`. No configuration needed!

**Option B: Set Environment Variable**
If you want to be explicit, set in your `.env` file or environment:
```bash
GRAPHENE_BUNDLES_ROOT=/root/graohen_os/bundles
```

### Step 2: Index Bundles (Optional - Auto-Discovery)

The system automatically discovers bundles when accessed, but you can manually index:

```bash
# Via API endpoint
curl -X POST http://localhost:8000/bundles/index

# Or check if bundle is found
curl http://localhost:8000/bundles/for/panther
```

### Step 3: Verify Bundle is Discovered

Check if the bundle is found:

```bash
# Get bundle info
curl http://localhost:8000/bundles/for/panther

# Should return:
# {
#   "codename": "panther",
#   "version": "2026011300",
#   "path": "/root/graohen_os/bundles/panther/2026011300",
#   ...
# }
```

### Step 4: Download the Bundle

Once discovered, the bundle is downloadable via these endpoints:

#### **1. Download Complete Bundle ZIP**

```bash
# Download image.zip
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download

# Or with progress
curl -L -o panther-bundle.zip https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download
```

**API Endpoint**: `GET /bundles/releases/{codename}/{version}/download`

#### **2. Download Individual Files**

```bash
# Download specific file
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/file/image.zip
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/file/flash-all.sh
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/file/metadata.json

# Download file from subdirectory
curl -O "https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/file/panther-install-2026011300/boot.img"
```

**API Endpoint**: `GET /bundles/releases/{codename}/{version}/file/{filename}`

#### **3. List All Files**

```bash
# List all files in bundle
curl https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/list
```

**API Endpoint**: `GET /bundles/releases/{codename}/{version}/list`

## Quick Test Commands

Run these on your server to verify everything works:

```bash
# 1. Check if bundle is discovered
curl http://localhost:8000/bundles/for/panther | jq

# 2. List all files in bundle
curl http://localhost:8000/bundles/releases/panther/2026011300/list | jq

# 3. Test download (should return image.zip)
curl -I http://localhost:8000/bundles/releases/panther/2026011300/download

# 4. Download a test file
curl -O http://localhost:8000/bundles/releases/panther/2026011300/file/metadata.json
```

## Frontend Usage

In your frontend/web flasher, you can download the bundle like this:

```typescript
// Download complete bundle
const downloadUrl = `https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download`;

const response = await fetch(downloadUrl);
const blob = await response.blob();
// blob contains image.zip

// Download individual file
const fileUrl = `https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/file/flash-all.sh`;
const fileResponse = await fetch(fileUrl);
const fileBlob = await fileResponse.blob();
```

## Troubleshooting

### Bundle Not Found (404)

**Problem**: Bundle exists but API returns 404

**Solutions**:
1. **Check bundle path**: Ensure bundle is at `/root/graohen_os/bundles/panther/2026011300/`
2. **Check permissions**: Backend must have read access to `/root/graohen_os/bundles/`
3. **Index bundles**: Call `POST /bundles/index` to force re-indexing
4. **Check config**: Verify `GRAPHENE_BUNDLES_ROOT` is set correctly (or let it auto-detect)

### Permission Denied

**Problem**: Backend can't read bundle files

**Solution**:
```bash
# Ensure backend user can read bundles
chmod -R 755 /root/graohen_os/bundles
# Or if backend runs as different user:
chmod -R 755 /root/graohen_os/bundles
chown -R <backend-user>:<backend-group> /root/graohen_os/bundles
```

### image.zip Not Found

**Problem**: Bundle folder exists but `image.zip` is missing

**Solution**: The bundle must contain `image.zip` for the download endpoint to work. Check:
```bash
ls -lh /root/graohen_os/bundles/panther/2026011300/image.zip
```

## Summary

✅ **Your bundle is already in the correct location!**

The system will automatically discover it at:
- `/root/graohen_os/bundles/panther/2026011300/`

**To make it downloadable:**

1. ✅ Bundle is in correct location (already done)
2. ✅ Bundle contains `image.zip` (already done)
3. Ensure backend has read access to `/root/graohen_os/bundles/`
4. Access via: `GET /bundles/releases/panther/2026011300/download`

**That's it!** The bundle should be downloadable immediately once the backend can access the folder.

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/bundles/index` | POST | Index all bundles |
| `/bundles/for/{codename}` | GET | Get newest bundle for codename |
| `/bundles/releases/{codename}/{version}/download` | GET | Download bundle ZIP (image.zip) |
| `/bundles/releases/{codename}/{version}/file/{filename}` | GET | Download specific file |
| `/bundles/releases/{codename}/{version}/list` | GET | List all files in bundle |

---

**Last Updated**: 2026-01-23
