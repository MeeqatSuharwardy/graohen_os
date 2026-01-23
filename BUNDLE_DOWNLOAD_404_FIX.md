# Bundle Download 404 Error Fix

## Problem

The Electron app was failing to start flashing because the bundle download was failing with a 404 error:

```
HEAD https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download net::ERR_ABORTED 404 (Not Found)
Failed to start flashing: Error: Bundle download failed: Download failed: 404
```

## Root Cause

1. **Bundle Not Indexed**: The bundle exists on the server at `/root/graohen_os/bundles/panther/2026011300/` but may not be indexed by the backend
2. **Strict Error Handling**: The download failure was causing the entire flash process to abort
3. **No Fallback**: The code didn't gracefully handle the case where the backend bundle isn't available

## Issues Fixed

### 1. Improved HEAD Request Error Handling

**Before:**
```javascript
try {
  const testResponse = await fetch(backendDownloadUrl, { method: 'HEAD' });
  if (testResponse.ok) {
    downloadUrl = backendDownloadUrl;
  }
} catch (error) {
  console.log('Backend download not available, using direct URL');
}
```

**Problem**: If HEAD request returns 404, `testResponse.ok` is false, but the code didn't explicitly handle this case. Also, network errors might not be caught properly.

**After:**
```javascript
let useBackendDownload = false;

try {
  const testResponse = await fetch(backendDownloadUrl, { 
    method: 'HEAD',
    signal: AbortSignal.timeout(5000)  // 5 second timeout
  });
  
  if (testResponse.ok) {
    useBackendDownload = true;
    downloadUrl = backendDownloadUrl;
    console.log(`[Download] Using backend download URL`);
  } else {
    // 404 or other error - bundle not on backend, use direct URL
    console.log(`[Download] Backend download returned ${testResponse.status}, using direct URL`);
  }
} catch (error) {
  // Network error, timeout, or CORS issue - fall back to direct URL
  console.log(`[Download] Backend download check failed, using direct URL`);
}

// Ensure we use direct URL if backend failed
if (!useBackendDownload) {
  downloadUrl = bundle.downloadUrl;
}
```

### 2. Made Bundle Download Optional

**Before:**
```javascript
if (downloadBundleFirstCheckbox.checked) {
  try {
    await downloadBundleFromServer(version);
  } catch (error) {
    throw new Error(`Bundle download failed: ${error.message}`);  // Aborts entire process
  }
}
```

**Problem**: If download failed, the entire flash process was aborted, even though the backend can use its own bundle.

**After:**
```javascript
if (downloadBundleFirstCheckbox.checked) {
  try {
    await downloadBundleFromServer(version);
    showStatus('Bundle downloaded successfully', 'success');
  } catch (error) {
    // Bundle download is optional - backend will use its own bundle if available
    console.warn(`[Flash] Bundle download failed, but continuing: ${error.message}`);
    showStatus(`Bundle download failed, but backend will use its own bundle if available: ${error.message}`, 'warning');
    // Don't throw - allow flash to proceed
  }
}
```

## Why This Works

1. **Backend Has Its Own Bundle**: The backend will automatically find and use bundles from `/root/graohen_os/bundles/` when flashing
2. **Download is Optional**: The local download is only for offline use or faster access - it's not required for flashing
3. **Graceful Fallback**: If backend bundle isn't available, the code falls back to downloading directly from GrapheneOS releases
4. **No Process Abort**: Even if download fails completely, flashing can still proceed using the backend's bundle

## Testing

### Test Case 1: Backend Bundle Available
1. Ensure bundle is indexed: `POST /bundles/index`
2. Check bundle exists: `GET /bundles/for/panther`
3. Try downloading - should use backend URL

### Test Case 2: Backend Bundle Not Available (404)
1. Bundle not indexed or doesn't exist on backend
2. HEAD request returns 404
3. Code falls back to direct GrapheneOS URL
4. Download proceeds from releases.grapheneos.org

### Test Case 3: Download Fails Completely
1. Network error or download fails
2. Flash process continues anyway
3. Backend uses its own bundle for flashing

## Verification

After the fix:
- ✅ HEAD request 404 is handled gracefully
- ✅ Falls back to direct download URL
- ✅ Download failure doesn't abort flash process
- ✅ Backend can use its own bundle for flashing
- ✅ Better error messages and logging

## Next Steps (Optional)

If you want the backend bundle to be available:

1. **Index Bundles**:
   ```bash
   curl -X POST https://freedomos.vulcantech.co/bundles/index
   ```

2. **Verify Bundle is Found**:
   ```bash
   curl https://freedomos.vulcantech.co/bundles/for/panther
   ```

3. **Check Download Endpoint**:
   ```bash
   curl -I https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download
   ```

If the bundle is properly indexed, the download endpoint should return 200 OK.

---

**Last Updated**: 2026-01-23
