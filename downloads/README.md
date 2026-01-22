# FlashDash Desktop Downloads

This directory contains pre-built Electron desktop applications for Windows, macOS, and Linux.

## Directory Structure

```
downloads/
├── windows/
│   └── @flashdashdesktop Setup 1.0.0.exe
├── mac/
│   └── FlashDash-1.0.0.dmg
└── linux/
    ├── flashdash-1.0.0.AppImage
    └── flashdash_1.0.0_amd64.deb
```

## Building

To build all platforms, run from the `frontend/packages/desktop` directory:

```bash
# Build all platforms
./scripts/build-all.sh

# Or build individually:
pnpm build:win    # Windows
pnpm build:mac    # macOS (macOS only)
pnpm build:linux  # Linux
```

## Uploading Builds

After building, copy the builds to this directory:

```bash
# From frontend/packages/desktop
cp dist/@flashdashdesktop*.exe ../../../downloads/windows/
cp dist/FlashDash-*.dmg ../../../downloads/mac/
cp dist/flashdash-*.AppImage ../../../downloads/linux/
cp dist/flashdash_*_amd64.deb ../../../downloads/linux/
```

## Versioning

Update the version in `frontend/packages/desktop/package.json` before building new releases.

## Download URLs

- Windows: `https://os.fxmail.ai/download/@flashdashdesktop%20Setup%201.0.0.exe`
- macOS: (configure in environment variables)
- Linux: (configure in environment variables)
