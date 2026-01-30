/**
 * Prepares bundled platform-tools (adb, fastboot) for Electron build.
 * Extracts the correct zip for the current platform into resources/adb/ so
 * extraResources can package them. No dependency on system ADB.
 *
 * Run before build: npm run prebuild (or as part of npm run build)
 * Zips: platform-tools-latest-windows.zip, platform-tools-latest-darwin.zip (at repo root)
 */

const path = require('path');
const fs = require('fs');
const AdmZip = require('adm-zip');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const RESOURCES_ADB = path.join(__dirname, '..', 'resources', 'adb');

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
    for (const name of fs.readdirSync(src)) {
      copyRecursive(path.join(src, name), path.join(dest, name));
    }
  } else {
    fs.copyFileSync(src, dest);
  }
}

function prepare() {
  const override = process.env.PREBUILD_PLATFORM || process.argv[2];
  const platform = override === 'win32' || override === 'darwin' ? override : process.platform;
  let zipName;
  if (platform === 'win32') {
    zipName = 'platform-tools-latest-windows.zip';
  } else if (platform === 'darwin') {
    zipName = 'platform-tools-latest-darwin.zip';
  } else {
    console.log('[prepare-platform-tools] Skipping: no bundled platform-tools for', platform);
    if (!fs.existsSync(RESOURCES_ADB)) {
      fs.mkdirSync(RESOURCES_ADB, { recursive: true });
      console.log('[prepare-platform-tools] Created empty resources/adb for build');
    }
    return;
  }

  const zipPath = path.join(REPO_ROOT, zipName);
  if (!fs.existsSync(zipPath)) {
    console.warn('[prepare-platform-tools] Zip not found:', zipPath);
    return;
  }

  if (fs.existsSync(RESOURCES_ADB)) {
    fs.rmSync(RESOURCES_ADB, { recursive: true });
  }
  fs.mkdirSync(RESOURCES_ADB, { recursive: true });

  const zip = new AdmZip(zipPath);
  const tempDir = path.join(__dirname, '..', 'temp-platform-tools');
  zip.extractAllTo(tempDir, true);

  const extractedPlatformTools = path.join(tempDir, 'platform-tools');
  if (!fs.existsSync(extractedPlatformTools)) {
    console.error('[prepare-platform-tools] Expected platform-tools/ inside zip');
    fs.rmSync(tempDir, { recursive: true, force: true });
    process.exit(1);
  }

  for (const name of fs.readdirSync(extractedPlatformTools)) {
    copyRecursive(
      path.join(extractedPlatformTools, name),
      path.join(RESOURCES_ADB, name)
    );
  }

  fs.rmSync(tempDir, { recursive: true, force: true });

  if (platform === 'darwin') {
    const adbPath = path.join(RESOURCES_ADB, 'adb');
    const fastbootPath = path.join(RESOURCES_ADB, 'fastboot');
    if (fs.existsSync(adbPath)) fs.chmodSync(adbPath, 0o755);
    if (fs.existsSync(fastbootPath)) fs.chmodSync(fastbootPath, 0o755);
    console.log('[prepare-platform-tools] Set executable: adb, fastboot');
  }

  console.log('[prepare-platform-tools] Done:', RESOURCES_ADB);
}

prepare();
