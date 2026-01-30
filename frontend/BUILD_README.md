# FlashDash Electron Build Guide

Build the FlashDash Electron app for **Windows** (unsigned exe, SmartScreen bypass) and **macOS** (DMG for Intel and Apple Silicon).

---

## Prerequisites

- **Node.js** 18+ and **npm**
- **Electron Builder**: `npm install` in `electron/` (already in devDependencies)
- **Windows**: Build on Windows or use a Windows VM/CI for `.exe`
- **macOS**: Build on macOS for DMG (Intel and/or Apple Silicon)
- **Platform-tools zips** at repo root (used by prebuild):
  - `platform-tools-latest-windows.zip` (for Windows build)
  - `platform-tools-latest-darwin.zip` (for macOS build)  
  Download: [Android platform-tools](https://developer.android.com/tools/releases/platform-tools). The build runs `npm run prebuild` (or `prebuild:win` / `prebuild:mac`) to extract adb/fastboot into `electron/resources/adb/` so the app works without system ADB.

---

## Project layout

```
frontend/
├── electron/          # Main process, package.json, build config
├── renderer/          # UI (HTML, CSS, JS)
├── assets/            # icon.png, icon.icns (Mac)
└── BUILD_README.md    # This file
```

Build output goes to `frontend/build/` (or as set in `electron/package.json` → `build.directories.output`).

---

## Windows: Unsigned EXE (bypass SmartScreen)

### 1. Build unsigned Windows exe

From `frontend/electron/`:

```bash
cd frontend/electron
npm run build:win
```

Or to produce a **portable/unsigned** installer that does not require code signing:

```bash
# Build Windows, no signing (omit sign script)
npx electron-builder --win --config.win.sign=null
```

To **fully disable signing** for the exe, ensure in `package.json` under `build.win` you do **not** set `sign` to a script, or use a no-op. Example for unsigned:

```json
"win": {
  "target": [{"target": "nsis", "arch": ["x64"]}],
  "sign": null,
  "signingHashAlgorithms": ["sha256"]
}
```

Then:

```bash
npx electron-builder --win
```

Output: `frontend/build/FlashDash Setup 1.0.0.exe` (or similar).

### 2. Bypass Windows SmartScreen for unsigned exe

SmartScreen may block unsigned executables. Users can:

1. **Right-click the .exe** → **Properties** → check **Unblock** (if present) → Apply.
2. When SmartScreen appears: **More info** → **Run anyway**.
3. **(Optional)** For IT admins: deploy via Group Policy or allow the app hash in Defender/SmartScreen so it’s trusted.

The app does **not** need to be signed for this; the user just has to bypass SmartScreen once.

### 3. Optional: Portable / dir build (no installer)

```bash
npx electron-builder --win --dir
```

Produces an unpacked app in `frontend/build/win-unpacked/`. You can zip that folder and distribute it; running the exe inside still may trigger SmartScreen once (same bypass as above).

---

## macOS: DMG for Intel and Apple Silicon

### 1. Icon

You need a Mac icon: `frontend/assets/icon.icns`.  
If you only have `icon.png`, create `.icns` with `iconutil` or an online converter and place it in `frontend/assets/`.

### 2. Build both architectures (Intel + Silicon)

From `frontend/electron/`:

```bash
cd frontend/electron
# Build for current machine arch only
npm run build
# Or explicitly both
npx electron-builder --mac --x64 --arm64
```

To build **only Intel (x64)**:

```bash
npx electron-builder --mac --x64
```

To build **only Apple Silicon (arm64)**:

```bash
npx electron-builder --mac --arm64
```

Outputs in `frontend/build/`:

- `FlashDash-1.0.0-arm64.dmg` (Apple Silicon)
- `FlashDash-1.0.0-x64.dmg` (Intel)
- Or a **universal** DMG if you use a universal build in `electron-builder` config.

### 3. DMG config in package.json

Example `build.mac`:

```json
"mac": {
  "target": "dmg",
  "icon": "../assets/icon.icns",
  "category": "public.app-category.utilities"
}
```

For both architectures in one go, you can set:

```json
"mac": {
  "target": ["dmg"],
  "arch": ["x64", "arm64"],
  "icon": "../assets/icon.icns"
}
```

Then run:

```bash
npx electron-builder --mac
```

---

## Quick reference

| Platform   | Command (from `frontend/electron/`)     | Output                          |
|-----------|-----------------------------------------|----------------------------------|
| Windows   | `npx electron-builder --win`           | NSIS installer (.exe)            |
| Windows   | `npx electron-builder --win --dir`     | Unpacked app in `win-unpacked/`  |
| Mac Intel | `npx electron-builder --mac --x64`     | `*.x64.dmg`                      |
| Mac Silicon | `npx electron-builder --mac --arm64` | `*.arm64.dmg`                    |
| Mac both  | `npx electron-builder --mac --x64 --arm64` | Both DMGs                   |

---

## Summary

- **Windows**: Build unsigned exe with `electron-builder --win` (with `sign: null` or no sign script). Users bypass SmartScreen via “Unblock” or “Run anyway”.
- **macOS**: Build DMG for Intel (`--x64`), Apple Silicon (`--arm64`), or both. Put `icon.icns` in `frontend/assets/` for the Mac build.

All builds are produced from the same Electron app; device detection, bundle download, and running `flash-all.bat` (Windows) or `flash-all.sh` (Mac) from the download path are handled inside the app.
