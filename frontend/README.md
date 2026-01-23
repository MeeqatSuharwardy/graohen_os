# FlashDash Client

**Production-ready Electron desktop application** that acts as a trusted frontend for flashing Android OS images (GrapheneOS-based) to Pixel devices.

## Architecture Overview

FlashDash Client is built with **strict security boundaries** to ensure that flashing operations are performed exclusively by the backend server. The Electron application only handles device detection and provides a user interface for monitoring flashing progress.

### Security Model

- **Backend is the single source of truth** for all flashing operations
- **Electron main process** only executes `adb` commands for device detection
- **Renderer process** has NO access to Node.js APIs or shell execution
- **No flashing logic** is implemented in Electron
- **No direct fastboot/adb calls** for flashing from the renderer

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Electron App                         │
├─────────────────────────────────────────────────────────┤
│  Main Process (Node.js)                                 │
│  • Device detection via adb                             │
│  • Secure IPC bridge                                    │
│  • Window management                                    │
├─────────────────────────────────────────────────────────┤
│  Preload Script                                         │
│  • contextBridge API exposure                           │
│  • Secure IPC communication                             │
├─────────────────────────────────────────────────────────┤
│  Renderer Process (Browser Context)                    │
│  • UI rendering                                         │
│  • Backend API calls (HTTPS)                            │
│  • Real-time log streaming (SSE)                        │
│  • NO shell access                                      │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTPS API Calls
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Backend Server                             │
│         https://freedomos.vulcantech.co                 │
│  • Device validation                                    │
│  • Flashing logic (adb + fastboot)                      │
│  • Job management                                       │
│  • Log streaming                                        │
└─────────────────────────────────────────────────────────┘
```

## How Device Detection Works

The Electron main process uses `adb` commands to detect connected Android devices:

1. **List Devices**: Executes `adb devices -l` to get connected devices
2. **Get Device Properties**: For each device, queries:
   - `adb shell getprop ro.product.device` (codename)
   - `adb shell getprop ro.product.model` (model name)
   - `adb shell getprop ro.product.manufacturer` (manufacturer)
   - `adb shell getprop ro.boot.flash.locked` (bootloader status)
3. **Parse Output**: Extracts serial numbers, states, and device metadata
4. **Send to Backend**: Device information is sent to backend via `POST /devices`

### Example Device Detection Flow

```javascript
// Main process executes:
adb devices -l
// Output: "emulator-5554    device product:sdk_gphone64_x86_64 model:sdk_gphone64_x86_64"

// For each device:
adb -s emulator-5554 shell getprop ro.product.device
// Output: "panther"

// Device object created:
{
  serial: "emulator-5554",
  state: "device",
  codename: "panther",
  model: "Pixel 7",
  manufacturer: "Google",
  bootloader_unlocked: false
}
```

## How Backend Flashing Works

The backend server handles all flashing operations:

1. **Device Registration**: Client sends device info via `POST /devices`
2. **Flash Job Creation**: Client requests flashing via:
   - `POST /flash/device-flash` (for unlocked bootloaders)
   - `POST /flash/unlock-and-flash` (for locked bootloaders)
3. **Job Execution**: Backend:
   - Validates device compatibility
   - Downloads required OS bundles
   - Executes `fastboot` and `adb` commands
   - Manages the flashing state machine
   - Streams logs in real-time
4. **Progress Monitoring**: Client connects to `GET /flash/jobs/{job_id}/stream` (SSE)
5. **Completion**: Backend returns final status (success/failure)

### Why Flashing is Backend-Only

- **Security**: Backend validates all operations and prevents unauthorized flashing
- **Reliability**: Centralized state management and error handling
- **Consistency**: Single implementation of flashing logic (no client-side variations)
- **Audit Trail**: All flashing operations are logged server-side
- **Update Management**: Backend can update flashing logic without client updates

## System Dependencies

FlashDash Client requires the following system tools to be installed and available in your PATH:

### Required Tools

1. **adb** (Android Debug Bridge)
   - Used for device detection only
   - Download: [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)
   - Verify: `adb --version`

2. **fastboot**
   - Used by backend for flashing (not called directly by Electron)
   - Included with Android Platform Tools
   - Verify: `fastboot --version`

### Installation

#### macOS
```bash
# Using Homebrew
brew install android-platform-tools

# Or download from Google
# https://developer.android.com/studio/releases/platform-tools
```

#### Windows
1. Download [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. Extract ZIP file
3. Add platform-tools directory to your PATH environment variable
4. Restart terminal/command prompt

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install android-tools-adb android-tools-fastboot

# Or download from Google
# https://developer.android.com/studio/releases/platform-tools
```

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Electron 28+
- adb and fastboot in PATH

### Installation

```bash
# Navigate to project directory
cd flashdash-client

# Install Electron dependencies
cd electron
npm install

# Return to project root
cd ..
```

### Running in Development

```bash
cd electron
npm run dev
```

This will:
- Start Electron with DevTools open
- Enable hot reloading (if configured)
- Show debug console output

### Project Structure

```
flashdash-client/
├── electron/
│   ├── main.js          # Main process (device detection)
│   ├── preload.js       # IPC bridge
│   └── package.json     # Electron dependencies
├── renderer/
│   ├── index.html       # UI structure
│   ├── app.js           # Frontend logic
│   └── styles.css       # Styling
├── public/
│   └── downloads/
│       └── windows.html # Windows download page
├── build/
│   └── FlashDash-Setup.exe  # Built installer (placeholder)
└── README.md
```

## Building for Production

### Windows Installer

```bash
cd electron
npm run build:win
```

This creates a Windows installer (NSIS) in `../build/FlashDash-Setup.exe`.

### macOS DMG

```bash
cd electron
npm run build
# Select macOS target
```

### Linux AppImage

```bash
cd electron
npm run build
# Select Linux target
```

### Build Configuration

Build settings are configured in `electron/package.json` under the `build` section:

- **Windows**: NSIS installer with custom installation directory option
- **macOS**: DMG with code signing (configure signing ID)
- **Linux**: AppImage format

## Backend API Endpoints

FlashDash Client uses the following backend endpoints:

### Device Management
- `POST /devices` - Register detected devices
- `GET /bundles/for/{codename}` - Get available OS versions

### Flashing Operations
- `POST /flash/device-flash` - Start flashing (unlocked bootloader)
- `POST /flash/unlock-and-flash` - Unlock bootloader and flash
- `GET /flash/jobs/{job_id}` - Get job status
- `GET /flash/jobs/{job_id}/stream` - Stream job logs (SSE)

### Bundle Downloads
- `GET /bundles/releases/{codename}/{version}/download` - Download bundle ZIP
- `GET /bundles/releases/{codename}/{version}/list` - List bundle contents

### Authentication (Optional)
- `POST /api/v1/auth/login` - Token-based authentication

## Usage Flow

1. **Launch FlashDash Client**
2. **Connect Pixel Device** via USB
3. **Enable USB Debugging** on device
4. **Click "Detect Devices"** - Electron detects connected devices
5. **Select Device** - Choose device from list
6. **Select OS Version** (optional) - Or use latest available
7. **Start Flashing**:
   - If bootloader unlocked: Click "Start Flashing"
   - If bootloader locked: Click "Unlock Bootloader & Flash"
8. **Monitor Progress** - Real-time logs stream from backend
9. **Completion** - Success or error message displayed

## Security Features

### Electron Security

- **contextIsolation: true** - Renderer cannot access Node.js
- **nodeIntegration: false** - No Node.js APIs in renderer
- **enableRemoteModule: false** - No remote module access
- **Content Security Policy** - Restricts resource loading
- **No arbitrary command execution** - Only predefined adb commands

### IPC Security

- **Preload script** uses `contextBridge` to expose safe APIs only
- **Main process** validates all IPC messages
- **No shell access** exposed to renderer

### Backend Communication

- **HTTPS only** - All API calls use encrypted connections
- **No authentication bypass** - Backend validates all requests
- **Job-based operations** - Each flash operation requires backend approval

## Troubleshooting

### Device Not Detected

1. Verify `adb` is installed: `adb --version`
2. Check USB connection
3. Enable USB debugging on device
4. Authorize computer on device (check device screen)
5. Try `adb devices` in terminal to verify

### Flashing Fails

1. Check backend logs (if accessible)
2. Verify device compatibility (supported Pixel models)
3. Ensure bootloader is unlockable (some devices are permanently locked)
4. Check network connection to backend

### Build Issues

1. Ensure all dependencies are installed: `npm install`
2. Check Node.js version: `node --version` (requires 18+)
3. Verify electron-builder is installed: `npm list electron-builder`

## Contributing

When contributing to FlashDash Client:

1. **Never add flashing logic** to Electron code
2. **Never expose shell execution** to renderer
3. **Always use backend APIs** for flashing operations
4. **Maintain security boundaries** between main and renderer processes
5. **Test device detection** with real Pixel devices

## License

MIT License - See LICENSE file for details

## Support

- **Backend**: https://freedomos.vulcantech.co
- **Issues**: Report via project repository
- **Security**: Report security issues privately

---

**Remember**: FlashDash Client is a trusted frontend only. All flashing operations are performed securely by the backend server. Never bypass backend validation or implement flashing logic in the Electron application.
