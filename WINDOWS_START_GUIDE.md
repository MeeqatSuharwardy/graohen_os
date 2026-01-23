# Windows Startup Guide

## How to Start FlashDash on Windows

### Option 1: Run from Unpacked Build (Development/Testing)

1. **Navigate to the build directory:**
   ```cmd
   cd C:\path\to\graohen_os\frontend\build\win-unpacked
   ```

2. **Run the executable:**
   ```cmd
   FlashDash.exe
   ```

   Or simply double-click `FlashDash.exe` in Windows Explorer.

### Option 2: Install Using Installer

1. **Run the installer:**
   ```cmd
   FlashDash Setup 1.0.0.exe
   ```

2. **Follow the installation wizard:**
   - Choose installation directory (default: `C:\Users\<YourUser>\AppData\Local\Programs\flashdash-client`)
   - Select whether to create desktop shortcut
   - Complete installation

3. **Launch from:**
   - Desktop shortcut (if created)
   - Start Menu → FlashDash
   - Or run: `C:\Users\<YourUser>\AppData\Local\Programs\flashdash-client\FlashDash.exe`

### Option 3: Run from Command Line

```cmd
cd C:\path\to\graohen_os\frontend\build\win-unpacked
FlashDash.exe
```

## Troubleshooting

### Blank Screen Issue

If you see a blank screen:

1. **Check the console output:**
   - The app should show debug logs in the console/terminal
   - Look for `[Window]` messages showing path resolution

2. **Verify files are present:**
   ```
   C:\path\to\build\win-unpacked\resources\app\renderer\index.html
   C:\path\to\build\win-unpacked\resources\app\preload.js
   ```

3. **Check file permissions:**
   - Ensure the app has read permissions to all files
   - Try running as Administrator if needed

### "Not allowed to load local resource" Error

This error occurs when:
- Files are not in the expected location
- Path resolution is incorrect
- Security settings block file access

**Solution:** The updated code now handles path resolution correctly for both development and production builds.

### Debug Mode

To see debug output:

1. **Run from command line:**
   ```cmd
   cd C:\path\to\build\win-unpacked
   FlashDash.exe
   ```

2. **Check console output** for:
   - `[Window]` messages showing paths
   - File existence checks
   - Any error messages

### Manual File Check

Verify these files exist in your build:

```
win-unpacked/
├── FlashDash.exe
├── resources/
│   └── app/
│       ├── main.js
│       ├── preload.js
│       ├── flasher.js
│       ├── renderer/
│       │   ├── index.html
│       │   ├── app.js
│       │   └── styles.css
│       └── assets/
│           └── icon.png
```

## Building for Windows

### Prerequisites

1. **Node.js** (v16 or higher)
2. **npm** or **pnpm**
3. **Windows SDK** (for code signing, optional)

### Build Steps

1. **Install dependencies:**
   ```cmd
   cd frontend\electron
   npm install
   ```

2. **Build Windows executable:**
   ```cmd
   npm run build:win
   ```

3. **Output location:**
   ```
   frontend\build\FlashDash Setup 1.0.0.exe  (Installer)
   frontend\build\win-unpacked\              (Unpacked app)
   ```

### Code Signing (Optional)

To sign the executable and bypass SmartScreen:

1. **Set environment variables:**
   ```cmd
   set CSC_LINK=C:\path\to\certificate.pfx
   set CSC_KEY_PASSWORD=your_password
   ```

2. **Build signed executable:**
   ```cmd
   npm run build:win:signed
   ```

See `WINDOWS_BUILD_GUIDE.md` for detailed signing instructions.

## Requirements

- **Windows 10** or later
- **ADB/Fastboot** installed and in PATH (for device operations)
- **Internet connection** (for downloading bundles and APKs)

## First Run

1. Launch the application
2. Connect your Android device via USB
3. Enable USB debugging on your device
4. Click "Detect Devices" in the app
5. Select your device and start flashing!
