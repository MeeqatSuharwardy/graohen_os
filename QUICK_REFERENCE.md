# Quick Reference: Download URL & Storage Path

## 📥 Download URL Format

```
https://releases.grapheneos.org/{codename}-factory-{version}.zip
```

### Example URLs:
- **Pixel 7 Pro**: `https://releases.grapheneos.org/cheetah-factory-2024122200.zip`
- **Pixel 7**: `https://releases.grapheneos.org/panther-factory-2024122200.zip`
- **Pixel 8 Pro**: `https://releases.grapheneos.org/husky-factory-2024122200.zip`

Replace:
- `{codename}` with your device codename (see table below)
- `{version}` with the version number (format: `YYYYMMDDXX`, e.g., `2024122200`)

## 📁 Storage Path

**Configure in `.env` file:**
```bash
GRAPHENE_BUNDLES_ROOT=/path/to/your/bundles
```

**Recommended path:**
```bash
GRAPHENE_BUNDLES_ROOT=/Users/vt_dev/upwork_graphene/graohen_os/bundles
```

**Folder structure after extraction:**
```
{GRAPHENE_BUNDLES_ROOT}/
└── {codename}/
    └── {version}/
        ├── image.zip
        ├── image.zip.sha256
        ├── image.zip.sig
        ├── flash-all.sh
        └── flash-all.bat
```

### Example:
```
/Users/vt_dev/upwork_graphene/graohen_os/bundles/
└── cheetah/
    └── 2024122200/
        ├── image.zip
        ├── image.zip.sha256
        ├── image.zip.sig
        ├── flash-all.sh
        └── flash-all.bat
```

## 🔄 Auto-Flash with Serial Number

When you enter a device serial number (e.g., `100016754321`):

1. **The app will automatically:**
   - Detect device codename from serial
   - Find latest bundle in `{GRAPHENE_BUNDLES_ROOT}/{codename}/`
   - Start flashing process

2. **Requirements:**
   - Device connected via USB
   - Device in ADB or Fastboot mode
   - Bundle extracted in correct folder structure
   - `GRAPHENE_BUNDLES_ROOT` configured in `.env`

## 📱 Device Codenames

| Codename | Device |
|----------|--------|
| `cheetah` | Pixel 7 Pro |
| `panther` | Pixel 7 |
| `husky` | Pixel 8 Pro |
| `shiba` | Pixel 8 |
| `raven` | Pixel 6 Pro |
| `oriole` | Pixel 6 |
| `lynx` | Pixel 7a |
| `akita` | Pixel 6a |
| `felix` | Pixel Fold |
| `tangorpro` | Pixel Tablet |

## 🚀 Quick Setup

1. **Set the path in `.env`:**
   ```bash
   cd backend/py-service
   cp env.example .env
   # Edit .env and set GRAPHENE_BUNDLES_ROOT
   ```

2. **Download manually:**
   ```bash
   # Example for Pixel 7 Pro
   wget https://releases.grapheneos.org/cheetah-factory-2024122200.zip
   ```

3. **Extract to correct location:**
   ```bash
   mkdir -p bundles/cheetah/2024122200
   unzip cheetah-factory-2024122200.zip -d bundles/cheetah/2024122200/
   cd bundles/cheetah/2024122200/
   mv cheetah-factory-2024122200.zip image.zip
   ```

4. **Enter serial number in app:**
   - Type: `100016754321`
   - App auto-detects device and finds bundle
   - Starts flashing automatically

