# 🌐 Web Flasher - Complete Browser-Based Flashing Solution

## ✅ What's Been Created

A complete **web-based flasher** that works entirely in the browser, matching the Electron app functionality:

### Features

1. **✅ Local Device Detection** (WebUSB)
   - Detects devices connected to user's computer
   - Uses browser WebUSB API (Chrome/Edge)
   - No backend device detection needed

2. **✅ Backend API Integration**
   - Uses backend at `https://freedomos.vulcantech.co` for operations
   - Calls `/flash/unlock-and-flash` endpoint (like Electron)
   - Polls job status for real-time updates

3. **✅ Complete Flash Process**
   - Device detection → Build selection → Flash
   - Unlock bootloader (if needed)
   - Flash GrapheneOS images
   - Real-time progress and logs

## 📁 Files Created/Updated

### New Files:
- `frontend/apps/web-flasher/src/lib/api.ts` - API client for backend
- `frontend/apps/web-flasher/src/hooks/useBackendFlasher.ts` - Backend-based flash hook

### Updated Files:
- `frontend/apps/web-flasher/src/pages/FlasherPage.tsx` - Uses backend API
- `frontend/apps/web-flasher/vite.config.ts` - Configured for production

## 🔧 How It Works

### Architecture:

```
Browser (Frontend)
  ↓ WebUSB
Detects Device Locally
  ↓
Sends Device Info to Backend
  ↓
Backend API (https://freedomos.vulcantech.co)
  ↓
/flash/unlock-and-flash endpoint
  ↓
Backend handles flashing
  ↓
Frontend polls job status
  ↓
Real-time progress updates
```

### Flow:

1. **User connects device** via USB
2. **Browser detects device** using WebUSB
3. **User selects build** from backend
4. **Frontend calls backend** `/flash/unlock-and-flash`
5. **Backend starts flash job** and returns `job_id`
6. **Frontend polls** `/flash/jobs/{job_id}` for status
7. **Real-time logs** and progress displayed

## 🌐 Backend API Endpoints Used

- `GET /bundles/releases/{codename}` - Get available builds
- `GET /bundles/find-latest/{codename}` - Get latest build
- `GET /devices/{serial}/identify` - Identify device codename
- `POST /devices/{serial}/reboot/bootloader` - Reboot to fastboot
- `POST /flash/unlock-and-flash` - Start flash process
- `GET /flash/jobs/{job_id}` - Get job status
- `GET /flash/jobs/{job_id}/stream` - SSE stream (if available)

## 📦 Build & Deploy

### Build:
```bash
cd frontend/apps/web-flasher
VITE_API_BASE_URL=https://freedomos.vulcantech.co pnpm build
```

### Output:
- `frontend/apps/web-flasher/dist/` - Built files ready for deployment

### Deploy:
Upload `dist/` folder contents to your shared hosting at `/flash/` route.

## ✅ Key Differences from Electron App

| Feature | Electron App | Web Flasher |
|---------|-------------|-------------|
| Device Detection | Backend API | WebUSB (Browser) |
| Flash Process | Backend API | Backend API ✅ |
| Job Polling | Backend API | Backend API ✅ |
| Build Selection | Backend API | Backend API ✅ |
| Real-time Logs | Backend API | Backend API ✅ |

**Both use the same backend API** - only device detection differs!

## 🚀 Next Steps

1. **Build the web flasher**:
   ```bash
   cd frontend/apps/web-flasher
   VITE_API_BASE_URL=https://freedomos.vulcantech.co pnpm build
   ```

2. **Deploy to shared hosting**:
   - Upload `dist/` folder to `/flash/` route
   - Ensure `.htaccess` handles routing

3. **Test**:
   - Open `https://your-domain.com/flash/`
   - Connect device via USB
   - Click "Connect Device"
   - Select build and flash!

---

**Status**: ✅ Complete! Web flasher now uses backend API like Electron app, with local WebUSB device detection.
