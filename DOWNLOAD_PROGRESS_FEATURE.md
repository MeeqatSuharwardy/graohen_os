# Download Progress Bar and Logs Feature

## Overview

Added real-time download progress tracking with visual progress bar and detailed log messages for bundle downloads in the Electron app.

## Features Added

### 1. **Real-Time Progress Bar**
- Visual progress bar showing download percentage
- Displays downloaded/total bytes
- Shows download status (downloading, completed, cached, error)
- Updates every 100ms for smooth animation

### 2. **Detailed Download Logs**
- Shows what file is being downloaded
- Logs download source (backend server or GrapheneOS releases)
- Progress updates every 10%
- Shows total file size at start
- Completion and error messages

### 3. **Progress Updates**
- Progress updates sent from Electron main process to renderer via IPC
- Real-time updates without polling
- Automatic cleanup of listeners

## Implementation Details

### Backend Changes

**File**: `backend/py-service/app/routes/bundles.py`
- Added HEAD method support for bundle download endpoint
- Creates ZIP archive on-the-fly if bundle folder exists but no zip file

### Electron Main Process Changes

**File**: `frontend/electron/main.js`

1. **Updated `downloadBundleToLocal()` function**:
   - Added `progressCallback` parameter
   - Sends progress updates via IPC
   - Tracks downloaded bytes and total size
   - Updates every 100ms (throttled)

2. **Updated IPC handler**:
   - Sends progress updates to renderer via `download-progress` event
   - Includes percentage, downloaded bytes, total bytes, status, filename

### Preload Script Changes

**File**: `frontend/electron/preload.js`

Added `onDownloadProgress()` method:
```javascript
onDownloadProgress: (callback) => {
  const handler = (event, progress) => callback(progress);
  ipcRenderer.on('download-progress', handler);
  return () => ipcRenderer.removeListener('download-progress', handler);
}
```

### Frontend Renderer Changes

**File**: `frontend/renderer/app.js`

1. **Updated `downloadBundleFromServer()` function**:
   - Sets up progress listener
   - Shows progress bar
   - Logs download start, source, and URL
   - Updates progress bar in real-time
   - Shows completion/error messages

2. **Added `updateDownloadProgress()` function**:
   - Updates progress bar UI
   - Logs progress every 10%
   - Handles different statuses (downloading, completed, cached, error)
   - Formats bytes for display

3. **Updated flash flow**:
   - Shows progress bar when downloading before flash
   - Logs download progress in flash logs
   - Handles download errors gracefully

**File**: `frontend/renderer/index.html`

- Added progress bar to flash section (for downloads before flashing)

## Progress Bar Display

### Visual Elements

1. **Progress Bar**: Animated fill showing percentage
2. **Progress Text**: Shows percentage and bytes (e.g., "45% - 900 MB / 2 GB")
3. **Status Messages**: Color-coded status updates

### Progress States

- **Starting**: 0% - "Starting..."
- **Downloading**: Updates from 0-100% with bytes
- **Completed**: 100% - Shows total size
- **Cached**: 100% - "(cached)" indicator
- **Error**: Shows error message

## Log Messages

### Download Start
```
[Log] Starting download: panther-factory-2026011300.zip
[Log] Source: backend server
[Log] URL: https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download
[Log] Total size: 2.0 GB
```

### Progress Updates (every 10%)
```
[Log] Downloading panther-factory-2026011300.zip: 10% (200 MB / 2.0 GB)
[Log] Downloading panther-factory-2026011300.zip: 20% (400 MB / 2.0 GB)
...
[Log] Downloading panther-factory-2026011300.zip: 90% (1.8 GB / 2.0 GB)
```

### Completion
```
[Log] ✓ Download completed: panther-factory-2026011300.zip (2.0 GB)
```

### Error
```
[Log] ✗ Download error: Network timeout
```

## Usage

### During Flash Process

1. User selects "Download bundle to local storage before flashing"
2. Progress bar appears in flash section
3. Logs show download progress
4. Progress bar updates in real-time
5. Download completes, flash proceeds

### Manual Bundle Download

1. User clicks "Download Bundle ZIP" in bundle section
2. Progress bar appears
3. Logs show download progress
4. Progress bar updates in real-time
5. Download completes

## Technical Details

### Progress Update Frequency

- **UI Updates**: Every 100ms (throttled in main process)
- **Log Updates**: Every 10% progress
- **Status Updates**: On state changes (starting, downloading, completed, error)

### Memory Management

- Progress listeners are cleaned up after download completes or fails
- Unsubscribe function returned from `onDownloadProgress()` is called
- No memory leaks from event listeners

### Error Handling

- Progress bar shows error state
- Logs show error details
- Download can fail gracefully without breaking flash process
- Progress listener is cleaned up on error

## Testing

### Test Case 1: Download from Backend
1. Select device and version
2. Check "Download bundle before flashing"
3. Click "Start Flashing"
4. Verify progress bar appears
5. Verify logs show download progress
6. Verify progress bar updates smoothly

### Test Case 2: Download from GrapheneOS
1. Backend bundle not available (404)
2. Falls back to direct download
3. Verify progress bar works
4. Verify logs show correct source

### Test Case 3: Cached Bundle
1. Bundle already downloaded
2. Verify progress bar shows "100% (cached)"
3. Verify logs show cached message
4. No download occurs

### Test Case 4: Download Error
1. Network error during download
2. Verify progress bar shows error
3. Verify logs show error message
4. Flash process continues (if optional download)

## Files Modified

1. `backend/py-service/app/routes/bundles.py` - Added HEAD support, zip creation
2. `frontend/electron/main.js` - Added progress tracking
3. `frontend/electron/preload.js` - Added progress listener API
4. `frontend/renderer/app.js` - Added progress UI and logs
5. `frontend/renderer/index.html` - Added progress bar to flash section

---

**Last Updated**: 2026-01-23
