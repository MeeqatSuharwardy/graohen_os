# FlashDash Electron App

Desktop app for **device detection**, **bundle download**, **local flashing** (flash-all.bat / flash-all.sh), and **APK management**. Same codebase and behavior on **Windows** (exe) and **macOS** (dmg).

---

## How the Electron App Works

### Architecture

- **Main process (Node.js)**  
  - Runs `adb` / `fastboot`, downloads bundles, runs flash scripts, manages window.  
  - Only process that runs shell commands and file I/O.

- **Renderer process (browser)**  
  - UI (HTML/CSS/JS), calls backend over HTTPS, talks to main via **IPC only** (no Node, no shell).

- **Preload**  
  - Exposes a small API to the renderer via `contextBridge` (e.g. `detectDevices`, `downloadBundleLocal`, `executeLocalFlash`, `installApk`).

```
┌─────────────────────────────────────────────────────────────────┐
│                     FlashDash Electron App                       │
├─────────────────────────────────────────────────────────────────┤
│  Main Process                                                    │
│  • adb devices / getprop (device detection)                      │
│  • Download bundle ZIP (http/https) → userData/bundles           │
│  • Unzip (system unzip on Mac/Linux, PowerShell on Windows)      │
│  • Run flash-all.bat (Windows) or flash-all.sh (Mac/Linux)       │
│  • adb install for APK                                           │
│  • IPC to renderer                                                │
├─────────────────────────────────────────────────────────────────┤
│  Renderer                                                        │
│  • UI, theme, device list, OS image dropdown                     │
│  • fetch(BACKEND_URL/...) for list-all, etc.                     │
│  • Calls main via electronAPI.*                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Flow (same on Windows and Mac)

1. **Device detection**  
   Main runs `adb devices -l` and `adb shell getprop`; results are sent to renderer via IPC.

2. **OS image selection**  
   Renderer loads `GET /bundles/list-all` and fills the dropdown (e.g. Pixel 7 (panther) - 2026012100).

3. **Bundle download**  
   - Renderer asks main to download (backend URL or GrapheneOS direct).  
   - Main saves ZIP under **userData/bundles/{codename}/{version}/** (e.g. `.../panther/2026012100/panther-factory-2026012100.zip`).  
   - Paths use `app.getPath('userData')` so they work the same on Windows and Mac.

4. **Extraction**  
   - **Mac/Linux:** `unzip -o '...' -d '...'`  
   - **Windows:** `powershell Expand-Archive -Path '...' -DestinationPath '...'`  
   - Same logic; only the command differs by `process.platform`.

5. **Flashing**  
   - Main runs the script in the **extracted** bundle folder:  
     - **Windows:** `flash-all.bat` (via `cmd.exe /c`)  
     - **Mac/Linux:** `flash-all.sh` (via `sh`)  
   - `FASTBOOT_SERIAL` is set so the correct device is flashed.  
   - Script stdout/stderr is streamed to the app log.

6. **APK**  
   - List from `GET /apks/list`, download via main, install with `adb install -r <path>`.  
   - Output streamed to log. Same on Windows and Mac.

### Platform-specific behavior (kept inside main process)

| Concern           | Windows              | Mac / Linux           |
|------------------|----------------------|------------------------|
| Flash script     | `flash-all.bat`      | `flash-all.sh`         |
| Unzip            | PowerShell Expand-Archive | `unzip -o`       |
| userData         | `%APPDATA%/flashdash-client` | `~/Library/Application Support/flashdash-client` |
| adb/fastboot     | Must be in PATH      | Must be in PATH        |

The renderer and preload are platform-agnostic; only `main.js` branches on `process.platform` where needed so **behavior stays the same** on Windows and Mac.

---

## Keeping It Working the Same on Windows and Mac Builds

- **One codebase:** All platform checks are in the main process (`process.platform === 'win32'` vs `'darwin'` / Linux).
- **Same features:** Device detection, bundle download, unzip, flash script, APK download/install work on both.
- **Builds:**
  - **Windows:** Build produces an **exe** (NSIS installer). Run the same app; it uses `.bat` and PowerShell.
  - **macOS:** Build produces **dmg** (Intel x64 and/or Apple Silicon arm64). Run the same app; it uses `.sh` and system `unzip`.

No separate code paths for “dev” vs “built” app; only packaging differs.

---

## Prerequisites

- **Node.js** 18+ and **npm**
- **adb** (and **fastboot** for flashing) in PATH  
  - Windows: [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools) and add to PATH  
  - Mac: `brew install android-platform-tools`
- **Windows build:** Run on Windows (or Windows VM/CI) for `.exe`
- **Mac build:** Run on macOS for `.dmg` (Intel and/or Apple Silicon)

---

## Project layout

```
frontend/
├── electron/
│   ├── main.js          # Main process (adb, download, unzip, flash script, APK install)
│   ├── preload.js       # IPC bridge (electronAPI)
│   ├── flasher.js       # Fallback flasher (if script missing)
│   ├── package.json     # Scripts, electron-builder config
│   └── ...
├── renderer/
│   ├── index.html
│   ├── app.js           # UI, fetch list-all, startFlashing, APK list/install
│   └── styles.css
├── assets/
│   ├── icon.png         # Windows / Linux
│   └── icon.icns        # macOS (for DMG)
├── README.md            # This file
├── BUILD_README.md      # Detailed build steps (SmartScreen, DMG, etc.)
└── build/               # Output: exe, dmg (created by electron-builder)
```

---

## Install and run (dev)

```bash
cd frontend/electron
npm install
npm start
```

Runs the app in development; behavior matches the built app (same main/renderer, same paths and scripts).

---

## Build: exe (Windows) and dmg (Mac)

From **`frontend/electron/`**:

| Goal              | Command                          | Output (in `frontend/build/`)     |
|-------------------|----------------------------------|-----------------------------------|
| Windows exe       | `npm run build:win` or `npx electron-builder --win` | `FlashDash Setup 1.0.0.exe` (NSIS) |
| Mac Intel         | `npx electron-builder --mac --x64`        | `FlashDash-1.0.0-x64.dmg`        |
| Mac Apple Silicon | `npx electron-builder --mac --arm64`     | `FlashDash-1.0.0-arm64.dmg`      |
| Mac both          | `npx electron-builder --mac --x64 --arm64`| Both DMGs                         |

- **Windows:** Unsigned exe may trigger SmartScreen; user can “Unblock” / “Run anyway”. See `BUILD_README.md` for details.
- **macOS:** For DMG you need `icon.icns` in `frontend/assets/`. Build on a Mac for DMG.

The built app uses the same logic as in dev: same backend URL, same userData paths, same flash script and unzip behavior per platform.

---

## Backend / config

- **Backend URL** is set in:
  - **Renderer:** `frontend/renderer/app.js` → `BACKEND_URL`
  - **Main:** `frontend/electron/main.js` → `BACKEND_URL`  
  Change both if you point to another server.
- **Bundles** are stored under `app.getPath('userData')/bundles/` (and APKs under `.../apks/`). Same on Windows and Mac.

---

## More build details

- **Unsigned Windows exe, SmartScreen, portable build:** see **`BUILD_README.md`**.
- **macOS code signing, universal build:** see **`BUILD_README.md`**.

---

## Quick reference: same behavior on Windows and Mac

- One codebase; platform only affects flash script name (`.bat` vs `.sh`), unzip command, and userData path.
- Build **exe** on Windows and **dmg** on Mac; the resulting app works the same from the user’s perspective (detect device → choose image → download → flash; APK download/install).
