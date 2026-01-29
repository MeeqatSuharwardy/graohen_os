/**
 * FlashDash Client - Electron Main Process
 * 
 * This process runs in Node.js and handles:
 * - Device detection via adb commands
 * - Secure IPC communication with renderer
 * - Window management
 * 
 * SECURITY: This is the ONLY process that executes shell commands.
 * Renderer process has NO access to Node.js APIs or shell execution.
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { exec, spawn } = require('child_process');
const { promisify } = require('util');
const fs = require('fs').promises;
const fsSync = require('fs');
const https = require('https');
const http = require('http');
const { glob } = require('glob');
const { GrapheneFlasher } = require('./flasher');
const FormData = require('form-data');

// Try to load adm-zip, fallback to manual extraction if not available
let AdmZip;
try {
  AdmZip = require('adm-zip');
} catch (error) {
  console.warn('adm-zip not available, will use system unzip command');
  AdmZip = null;
}

const execAsync = promisify(exec);

// Backend API base URL
const BACKEND_URL = 'https://freedomos.vulcantech.co';

// Local bundles directory (in Electron app data)
const USER_DATA_PATH = app.getPath('userData');
const LOCAL_BUNDLES_DIR = path.join(USER_DATA_PATH, 'bundles');

let mainWindow;

// Ensure bundles directory exists
async function ensureBundlesDirectory() {
  try {
    await fs.mkdir(LOCAL_BUNDLES_DIR, { recursive: true });
  } catch (error) {
    console.error('Failed to create bundles directory:', error);
  }
}

// Initialize bundles directory on app start
ensureBundlesDirectory();

/**
 * Create the main application window
 */
function createWindow() {
  // Determine if we're in development or production
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

  // Get the app path - works in both dev and production
  const appPath = app.getAppPath();

  // Resolve paths - app.getAppPath() returns the correct path in both dev and production
  // In dev: returns the actual directory path
  // In production: returns path to app.asar or resources/app/
  const preloadPath = path.join(appPath, 'preload.js');
  const htmlPath = path.join(appPath, 'renderer', 'index.html');
  const iconPath = path.join(appPath, 'assets', 'icon.png');

  // Fallback paths for development (when appPath might not include renderer)
  const devPreloadPath = path.join(__dirname, 'preload.js');
  const devHtmlPath = path.join(__dirname, '../renderer/index.html');
  const devIconPath = path.join(__dirname, '../assets/icon.png');

  // Use dev paths if production paths don't exist (development mode)
  const finalPreloadPath = fsSync.existsSync(preloadPath) ? preloadPath : devPreloadPath;
  const finalHtmlPath = fsSync.existsSync(htmlPath) ? htmlPath : devHtmlPath;
  const finalIconPath = fsSync.existsSync(iconPath) ? iconPath : devIconPath;

  console.log('[Window] Creating window...');
  console.log('[Window] isDev:', isDev);
  console.log('[Window] isPackaged:', app.isPackaged);
  console.log('[Window] appPath:', appPath);
  console.log('[Window] __dirname:', __dirname);
  console.log('[Window] preloadPath:', finalPreloadPath, 'exists:', fsSync.existsSync(finalPreloadPath));
  console.log('[Window] htmlPath:', finalHtmlPath, 'exists:', fsSync.existsSync(finalHtmlPath));

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: finalPreloadPath,
      contextIsolation: true,  // CRITICAL: Isolate renderer from Node.js
      nodeIntegration: false,  // CRITICAL: No Node.js in renderer
      enableRemoteModule: false, // CRITICAL: No remote module access
      sandbox: false, // Preload needs access to Node.js APIs
      webSecurity: true, // Enable web security
    },
    icon: fsSync.existsSync(finalIconPath) ? finalIconPath : undefined, // Optional icon
    show: false, // Don't show until ready
  });

  // Load the HTML file using loadFile (handles file:// protocol correctly)
  console.log('[Window] Loading HTML from:', finalHtmlPath);

  mainWindow.loadFile(finalHtmlPath)
    .then(() => {
      console.log('[Window] HTML loaded successfully');
      mainWindow.show(); // Show window after content loads
    })
    .catch((error) => {
      console.error('[Window] Failed to load HTML:', error);
      // Try alternative paths
      const altPaths = [
        path.join(__dirname, '..', 'renderer', 'index.html'),
        path.join(appPath, 'renderer', 'index.html'),
        path.join(process.resourcesPath || '', 'app', 'renderer', 'index.html'),
      ];

      let loaded = false;
      for (const altPath of altPaths) {
        if (fsSync.existsSync(altPath)) {
          console.log('[Window] Trying alternative path:', altPath);
          mainWindow.loadFile(altPath)
            .then(() => {
              console.log('[Window] Successfully loaded from alternative path');
              mainWindow.show();
            })
            .catch((fallbackError) => {
              console.error('[Window] Alternative path also failed:', fallbackError);
            });
          loaded = true;
          break;
        }
      }

      if (!loaded) {
        console.error('[Window] All paths failed, showing error page');
        const errorHtml = `
          <!DOCTYPE html>
          <html>
          <head>
            <title>FlashDash - Error</title>
            <style>
              body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
              h1 { color: #e74c3c; }
              pre { background: #f5f5f5; padding: 20px; border-radius: 5px; text-align: left; }
            </style>
          </head>
          <body>
            <h1>Failed to load application</h1>
            <p>Expected HTML at: ${finalHtmlPath}</p>
            <p>Alternative paths tried:</p>
            <pre>${altPaths.join('\n')}</pre>
            <p>Please check the console for more details.</p>
          </body>
          </html>
        `;
        mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(errorHtml));
        mainWindow.show();
      }
    });

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * Execute adb command and return parsed output
 * @param {string} command - adb command to execute
 * @returns {Promise<string>} - Command output
 */
async function executeAdbCommand(command) {
  try {
    const { stdout, stderr } = await execAsync(command, {
      timeout: 10000, // 10 second timeout
      maxBuffer: 1024 * 1024, // 1MB buffer
    });

    if (stderr && !stderr.includes('daemon')) {
      // adb often writes to stderr even on success, ignore daemon messages
      console.warn('adb stderr:', stderr);
    }

    return stdout.trim();
  } catch (error) {
    throw new Error(`adb command failed: ${error.message}`);
  }
}

/**
 * Parse fastboot devices output
 * Returns array of device objects with serial and state "fastboot"
 */
async function parseFastbootDevices() {
  try {
    const output = await executeAdbCommand('fastboot devices');
    const lines = output.split('\n').filter(line => line.trim());

    const devices = [];

    for (const line of lines) {
      const parts = line.trim().split(/\s+/);
      if (parts.length < 1) continue;

      const serial = parts[0];
      devices.push({
        serial,
        state: 'fastboot',
        model: 'Unknown',
        codename: null,
      });
    }

    return devices;
  } catch (error) {
    // fastboot may not be available or no devices in fastboot mode
    return [];
  }
}

/**
 * Parse adb devices -l output
 * Returns array of device objects with serial and state
 */
async function parseAdbDevices() {
  const output = await executeAdbCommand('adb devices -l');
  const lines = output.split('\n').filter(line => line.trim());

  const devices = [];

  // Skip header line "List of devices attached"
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Parse format: "serial    state    device:model:..."
    const parts = line.split(/\s+/);
    if (parts.length < 2) continue;

    const serial = parts[0];
    const state = parts[1]; // "device" or "offline"

    // Extract model from device property if present
    let model = null;
    let codename = null;

    for (let j = 2; j < parts.length; j++) {
      if (parts[j].startsWith('device:')) {
        const deviceParts = parts[j].split(':');
        if (deviceParts.length >= 2) {
          model = deviceParts[1];
        }
      }
      if (parts[j].startsWith('model:')) {
        const modelParts = parts[j].split(':');
        if (modelParts.length >= 2) {
          model = modelParts.slice(1).join(':');
        }
      }
    }

    devices.push({
      serial,
      state,
      model: model || 'Unknown',
      codename: null, // Will be fetched separately
    });
  }

  return devices;
}

/**
 * Get device details for a specific serial
 * Fetches codename, model, manufacturer, and bootloader status
 * Handles both adb (device mode) and fastboot mode
 */
async function getDeviceDetails(serial, state) {
  const details = {
    serial,
    codename: null,
    model: null,
    manufacturer: 'Google',
    bootloader_unlocked: false,
  };

  try {
    // If device is in fastboot mode, use fastboot commands
    if (state === 'fastboot') {
      try {
        // Try to get product name (codename) from fastboot
        const productOutput = await executeAdbCommand(`fastboot -s ${serial} getvar product 2>&1`);
        if (productOutput.includes('product:')) {
          const match = productOutput.match(/product:\s*(\S+)/);
          if (match) {
            details.codename = match[1];
          }
        }
      } catch (error) {
        console.warn(`Failed to get product from fastboot for ${serial}:`, error.message);
      }

      // Check bootloader unlock status in fastboot
      try {
        const unlockedOutput = await executeAdbCommand(`fastboot -s ${serial} getvar unlocked 2>&1`);
        if (unlockedOutput.includes('unlocked: yes')) {
          details.bootloader_unlocked = true;
        }
      } catch (error) {
        console.warn(`Failed to get unlock status from fastboot for ${serial}:`, error.message);
      }

      return details;
    }

    // Device is in adb mode (normal or offline)
    // Get codename (ro.product.device)
    try {
      const codenameOutput = await executeAdbCommand(`adb -s ${serial} shell getprop ro.product.device`);
      details.codename = codenameOutput.trim();
    } catch (error) {
      console.warn(`Failed to get codename for ${serial}:`, error.message);
    }

    // Get model (ro.product.model)
    try {
      const modelOutput = await executeAdbCommand(`adb -s ${serial} shell getprop ro.product.model`);
      details.model = modelOutput.trim() || details.model;
    } catch (error) {
      console.warn(`Failed to get model for ${serial}:`, error.message);
    }

    // Get manufacturer (ro.product.manufacturer)
    try {
      const manufacturerOutput = await executeAdbCommand(`adb -s ${serial} shell getprop ro.product.manufacturer`);
      details.manufacturer = manufacturerOutput.trim() || 'Google';
    } catch (error) {
      console.warn(`Failed to get manufacturer for ${serial}:`, error.message);
    }

    // Check bootloader unlock status
    try {
      const lockedOutput = await executeAdbCommand(`adb -s ${serial} shell getprop ro.boot.flash.locked`);
      const locked = lockedOutput.trim();
      details.bootloader_unlocked = locked === '0' || locked.toLowerCase() === 'unlocked';
    } catch (error) {
      console.warn(`Failed to get bootloader status for ${serial}:`, error.message);
    }

  } catch (error) {
    console.error(`Error getting device details for ${serial}:`, error);
  }

  return details;
}

/**
 * Detect all connected devices (both adb and fastboot)
 * Returns full device information including codename and bootloader status
 */
async function detectDevices() {
  try {
    // Get devices from both adb and fastboot
    const [adbDevices, fastbootDevices] = await Promise.all([
      parseAdbDevices(),
      parseFastbootDevices(),
    ]);

    // Combine devices, prioritizing adb devices (if same serial exists in both)
    const deviceMap = new Map();

    // Add fastboot devices first
    fastbootDevices.forEach(device => {
      deviceMap.set(device.serial, device);
    });

    // Add adb devices (will overwrite fastboot if same serial)
    adbDevices.forEach(device => {
      deviceMap.set(device.serial, device);
    });

    const allDevices = Array.from(deviceMap.values());

    if (allDevices.length === 0) {
      return [];
    }

    // Enrich each device with details
    const enrichedDevices = await Promise.all(
      allDevices.map(async (device) => {
        // Skip offline devices
        if (device.state === 'offline') {
          return {
            ...device,
            codename: null,
            bootloader_unlocked: false,
            error: 'Device is offline',
          };
        }

        try {
          const details = await getDeviceDetails(device.serial, device.state);
          return {
            ...device,
            ...details,
          };
        } catch (error) {
          return {
            ...device,
            codename: null,
            bootloader_unlocked: false,
            error: error.message,
          };
        }
      })
    );

    return enrichedDevices;
  } catch (error) {
    throw new Error(`Device detection failed: ${error.message}`);
  }
}

// IPC Handlers - Secure communication bridge

/**
 * Handle device detection request from renderer
 */
ipcMain.handle('detect-devices', async () => {
  try {
    const devices = await detectDevices();
    return { success: true, devices };
  } catch (error) {
    return { success: false, error: error.message, devices: [] };
  }
});

/**
 * Handle device details request for a specific serial
 */
ipcMain.handle('get-device-details', async (event, serial, state) => {
  try {
    if (!serial) {
      throw new Error('Serial number is required');
    }
    const details = await getDeviceDetails(serial, state || 'device');
    return { success: true, device: details };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * Reboot device into fastboot mode
 * @param {string} serial - Device serial number
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function rebootToFastboot(serial) {
  try {
    if (!serial) {
      throw new Error('Serial number is required');
    }

    // Check if device is already in fastboot mode
    const fastbootDevices = await parseFastbootDevices();
    const isAlreadyInFastboot = fastbootDevices.some(d => d.serial === serial);

    if (isAlreadyInFastboot) {
      return { success: true, message: 'Device already in fastboot mode' };
    }

    // Reboot to bootloader using adb
    await executeAdbCommand(`adb -s ${serial} reboot bootloader`);

    // Wait for device to enter fastboot mode (polling)
    const maxAttempts = 30; // 30 seconds max wait
    const pollInterval = 1000; // Check every second

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise(resolve => setTimeout(resolve, pollInterval));

      const fastbootDevices = await parseFastbootDevices();
      const isInFastboot = fastbootDevices.some(d => d.serial === serial);

      if (isInFastboot) {
        return { success: true, message: 'Device entered fastboot mode' };
      }
    }

    throw new Error('Device did not enter fastboot mode within timeout period');
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Handle reboot to fastboot request from renderer
 */
ipcMain.handle('reboot-to-fastboot', async (event, serial) => {
  try {
    console.log(`[IPC] reboot-to-fastboot called for serial: ${serial}`);
    return await rebootToFastboot(serial);
  } catch (error) {
    console.error(`[IPC] reboot-to-fastboot error:`, error);
    return { success: false, error: error.message };
  }
});

/**
 * Find extracted bundle directory (handles subdirectories)
 * Prefers subdirectories with image files over base directory with just scripts
 */
async function findExtractedBundlePath(bundleDir, codename) {
  console.log(`[findExtractedBundlePath] Searching in: ${bundleDir}`);

  // First check subdirectories (they usually contain the actual image files)
  try {
    const entries = await fs.readdir(bundleDir);
    console.log(`[findExtractedBundlePath] Directory entries:`, entries);

    for (const entry of entries) {
      if (entry.startsWith(`${codename}-install-`) || entry.includes('install')) {
        const entryPath = path.join(bundleDir, entry);
        const stat = await fs.stat(entryPath);
        if (stat.isDirectory()) {
          console.log(`[findExtractedBundlePath] Checking subdirectory: ${entryPath}`);

          // Check if subdirectory has flash-all script
          const entryFlashAllSh = path.join(entryPath, 'flash-all.sh');
          const entryFlashAllBat = path.join(entryPath, 'flash-all.bat');
          const entryShExists = await fs.access(entryFlashAllSh).then(() => true).catch(() => false);
          const entryBatExists = await fs.access(entryFlashAllBat).then(() => true).catch(() => false);

          console.log(`[findExtractedBundlePath] flash-all.sh exists: ${entryShExists}, flash-all.bat exists: ${entryBatExists}`);

          if (entryShExists || entryBatExists) {
            // Verify it has image files (bootloader or radio) - use fs.readdir for reliability
            try {
              const files = await fs.readdir(entryPath);
              const hasBootloader = files.some(f => f.includes('bootloader') && f.endsWith('.img'));
              const hasRadio = files.some(f => f.includes('radio') && f.endsWith('.img'));

              console.log(`[findExtractedBundlePath] Subdirectory ${entry}: hasBootloader=${hasBootloader}, hasRadio=${hasRadio}, totalFiles=${files.length}`);

              if (hasBootloader || hasRadio) {
                // This subdirectory has both scripts and image files - prefer it
                console.log(`[findExtractedBundlePath] Returning subdirectory: ${entryPath}`);
                return entryPath;
              }
            } catch (readError) {
              console.error(`[findExtractedBundlePath] Error reading subdirectory:`, readError);
            }
          }
        }
      }
    }
  } catch (error) {
    console.error(`[findExtractedBundlePath] Error reading directory:`, error);
  }

  // Fallback: Check directly in bundle directory
  console.log(`[findExtractedBundlePath] Checking base directory...`);
  const flashAllSh = path.join(bundleDir, 'flash-all.sh');
  const flashAllBat = path.join(bundleDir, 'flash-all.bat');
  const shExists = await fs.access(flashAllSh).then(() => true).catch(() => false);
  const batExists = await fs.access(flashAllBat).then(() => true).catch(() => false);

  if (shExists || batExists) {
    console.log(`[findExtractedBundlePath] Base directory has flash-all scripts`);
    // Verify base directory has image files - use fs.readdir for reliability
    try {
      const files = await fs.readdir(bundleDir);
      const hasBootloader = files.some(f => f.includes('bootloader') && f.endsWith('.img'));
      const hasRadio = files.some(f => f.includes('radio') && f.endsWith('.img'));

      console.log(`[findExtractedBundlePath] Base directory: hasBootloader=${hasBootloader}, hasRadio=${hasRadio}, totalFiles=${files.length}`);

      if (hasBootloader || hasRadio) {
        console.log(`[findExtractedBundlePath] Returning base directory: ${bundleDir}`);
        return bundleDir;
      }

      // Base directory has scripts but no images - check if there's a subdirectory we missed
      // (This handles cases where extraction put scripts in base but images in subdirectory)
      console.log(`[findExtractedBundlePath] Base has scripts but no images, checking for any subdirectory with images...`);
      try {
        for (const entry of files) {
          const entryPath = path.join(bundleDir, entry);
          try {
            const stat = await fs.stat(entryPath);
            if (stat.isDirectory()) {
              const subdirFiles = await fs.readdir(entryPath);
              const subdirHasBootloader = subdirFiles.some(f => f.includes('bootloader') && f.endsWith('.img'));
              const subdirHasRadio = subdirFiles.some(f => f.includes('radio') && f.endsWith('.img'));
              console.log(`[findExtractedBundlePath] Subdirectory ${entry}: hasBootloader=${subdirHasBootloader}, hasRadio=${subdirHasRadio}`);
              if (subdirHasBootloader || subdirHasRadio) {
                console.log(`[findExtractedBundlePath] Found subdirectory with images: ${entryPath}`);
                return entryPath;
              }
            }
          } catch (e) {
            // Skip entries we can't process
            console.log(`[findExtractedBundlePath] Error checking ${entry}:`, e.message);
          }
        }
      } catch (e) {
        console.error(`[findExtractedBundlePath] Error checking subdirectories:`, e);
      }

      // No subdirectory with images found - return null so caller can handle
      console.log(`[findExtractedBundlePath] Base directory has scripts but no images, and no subdirectory found with images`);
      return null;
    } catch (readError) {
      console.error(`[findExtractedBundlePath] Error reading base directory:`, readError);
    }
  }

  console.log(`[findExtractedBundlePath] No bundle found, returning null`);
  return null;
}

/**
 * Download bundle from URL and save locally with progress updates
 * Also extracts the bundle after download
 */
async function downloadBundleToLocal(codename, version, downloadUrl, progressCallback) {
  try {
    await ensureBundlesDirectory();

    const bundleDir = path.join(LOCAL_BUNDLES_DIR, codename, version);
    await fs.mkdir(bundleDir, { recursive: true });

    const zipPath = path.join(bundleDir, `${codename}-factory-${version}.zip`);
    const extractedPath = bundleDir; // Extract to same directory

    // Check if bundle is already extracted and ready to use
    const extractedBundlePath = await findExtractedBundlePath(bundleDir, codename);
    if (extractedBundlePath) {
      // Verify bundle has required files (bootloader or radio images)
      try {
        const bootloaderFiles = await glob('bootloader-*.img', { cwd: extractedBundlePath, absolute: true }).catch(() => []);
        const radioFiles = await glob('radio-*.img', { cwd: extractedBundlePath, absolute: true }).catch(() => []);

        if (bootloaderFiles.length > 0 || radioFiles.length > 0) {
          console.log(`[Download] Bundle already extracted and ready at: ${extractedBundlePath}`);
          if (progressCallback) {
            progressCallback({
              percentage: 100,
              downloaded: 0,
              total: 0,
              status: 'extracted',
              message: 'Bundle already present, skipping download'
            });
          }
          return { success: true, path: extractedBundlePath, cached: true, extracted: true };
        } else {
          console.log(`[Download] Bundle directory exists but missing image files, will re-extract`);
        }
      } catch (error) {
        console.warn(`[Download] Error checking extracted bundle: ${error.message}, will proceed with download`);
      }
    }

    // Check if zip already downloaded
    let zipDownloaded = false;
    try {
      const stats = await fs.stat(zipPath);
      if (stats.size > 0) {
        zipDownloaded = true;
        console.log(`[Download] ZIP file already exists: ${zipPath} (${stats.size} bytes)`);
        if (progressCallback) {
          progressCallback({ percentage: 50, downloaded: stats.size, total: stats.size, status: 'extracting', message: 'ZIP file found, extracting...' });
        }
      }
    } catch (error) {
      // File doesn't exist, proceed with download
      console.log(`[Download] ZIP file not found, will download`);
    }

    // Download zip if not already downloaded and URL provided
    // If URL is empty, skip download and just extract existing ZIP
    if (!zipDownloaded && downloadUrl && downloadUrl.trim() !== '') {
      await new Promise((resolve, reject) => {
        const url = new URL(downloadUrl);
        const protocol = url.protocol === 'https:' ? https : http;

        const file = fsSync.createWriteStream(zipPath);
        let downloadedBytes = 0;
        let totalBytes = 0;
        let lastProgressUpdate = 0;
        const progressUpdateInterval = 100; // Update every 100ms

        const request = protocol.get(downloadUrl, (response) => {
          if (response.statusCode !== 200) {
            file.close();
            fsSync.unlink(zipPath, () => { });
            reject(new Error(`Download failed: ${response.statusCode}`));
            return;
          }

          totalBytes = parseInt(response.headers['content-length'] || '0', 10);

          if (progressCallback) {
            progressCallback({
              percentage: 0,
              downloaded: 0,
              total: totalBytes,
              status: 'downloading',
              filename: `${codename}-factory-${version}.zip`
            });
          }

          response.pipe(file);

          response.on('data', (chunk) => {
            downloadedBytes += chunk.length;

            // Throttle progress updates
            const now = Date.now();
            if (now - lastProgressUpdate >= progressUpdateInterval || downloadedBytes === totalBytes) {
              lastProgressUpdate = now;
              const percentage = totalBytes > 0 ? Math.round((downloadedBytes / totalBytes) * 50) : 0; // 0-50% for download

              if (progressCallback) {
                progressCallback({
                  percentage,
                  downloaded: downloadedBytes,
                  total: totalBytes,
                  status: 'downloading',
                  filename: `${codename}-factory-${version}.zip`
                });
              }
            }
          });

          file.on('finish', () => {
            file.close();
            resolve({ size: downloadedBytes, total: totalBytes });
          });
        });

        request.on('error', (error) => {
          file.close();
          fsSync.unlink(zipPath, () => { });
          reject(error);
        });

        file.on('error', (error) => {
          file.close();
          fsSync.unlink(zipPath, () => { });
          reject(error);
        });
      });
      zipDownloaded = true; // Download completed; proceed to extraction
    }

    // Extract zip file (if ZIP exists, either downloaded or already present)
    if (zipDownloaded || (downloadUrl && downloadUrl.trim() === '')) {
      // ZIP exists, proceed to extraction
      if (progressCallback) {
        progressCallback({ percentage: 50, downloaded: 0, total: 0, status: 'extracting', message: 'Extracting bundle...' });
      }
    } else {
      // No ZIP and no download - error
      throw new Error('ZIP file not found and no download URL provided');
    }

    try {
      const isWindows = process.platform === 'win32';
      const isMac = process.platform === 'darwin';
      let zipSize = 0;
      try {
        const st = await fs.stat(zipPath);
        zipSize = st.size || 0;
      } catch (_) {}

      // Prefer system unzip on macOS (and when AdmZip unavailable) - more reliable for large bundles (1.5GB+)
      const useSystemUnzip = !AdmZip || isMac || zipSize > 400 * 1024 * 1024; // >400MB or Mac or no AdmZip

      if (useSystemUnzip) {
        console.log(`[Extract] Using system unzip command`);
        if (isWindows) {
          await execAsync(`powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${extractedPath}' -Force"`);
        } else {
          // macOS/Linux: ensure extractedPath exists, then unzip (quote paths for spaces)
          await fs.mkdir(extractedPath, { recursive: true });
          const safeZip = zipPath.replace(/'/g, "'\\''");
          const safeDest = extractedPath.replace(/'/g, "'\\''");
          await execAsync(`unzip -o '${safeZip}' -d '${safeDest}'`);
        }
        console.log(`[Extract] System extraction completed`);
      } else if (AdmZip) {
        console.log(`[Extract] Extracting ${zipPath} to ${extractedPath}`);
        const zip = new AdmZip(zipPath);
        zip.extractAllTo(extractedPath, true);
        console.log(`[Extract] Extraction completed`);
      } else {
        throw new Error('No unzip method available (install unzip or adm-zip)');
      }

      // After extraction, check where files actually ended up
      const finalPath = await findExtractedBundlePath(extractedPath, codename);

      if (!finalPath) {
        // List directory contents for debugging
        try {
          const entries = await fs.readdir(extractedPath);
          console.log(`[Extract] Directory contents after extraction:`, entries);
          throw new Error(`Bundle extracted but flash-all.sh not found. Directory contents: ${entries.join(', ')}`);
        } catch (listError) {
          throw new Error(`Bundle extracted but flash-all.sh not found. Could not list directory: ${listError.message}`);
        }
      }

      console.log(`[Extract] Found bundle at: ${finalPath}`);

      if (progressCallback) {
        progressCallback({
          percentage: 100,
          downloaded: 0,
          total: 0,
          status: 'completed',
          filename: `${codename}-factory-${version}.zip`,
          message: 'Bundle extracted successfully'
        });
      }

      return {
        success: true,
        path: finalPath,
        zipPath: zipPath,
        cached: false,
        extracted: true
      };
    } catch (extractError) {
      console.error(`[Extract] Extraction failed:`, extractError);
      throw new Error(`Failed to extract bundle: ${extractError.message}`);
    }
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Check if bundle exists locally (ZIP or extracted)
 */
async function checkLocalBundle(codename, version) {
  try {
    const bundleDir = path.join(LOCAL_BUNDLES_DIR, codename, version);

    // First check if bundle is already extracted and ready
    const extractedBundlePath = await findExtractedBundlePath(bundleDir, codename);
    if (extractedBundlePath) {
      // Verify it has required files
      try {
        const bootloaderFiles = await glob('bootloader-*.img', { cwd: extractedBundlePath, absolute: true }).catch(() => []);
        const radioFiles = await glob('radio-*.img', { cwd: extractedBundlePath, absolute: true }).catch(() => []);

        if (bootloaderFiles.length > 0 || radioFiles.length > 0) {
          // Calculate total size of extracted files
          let totalSize = 0;
          try {
            const files = await fs.readdir(extractedBundlePath);
            for (const file of files) {
              try {
                const filePath = path.join(extractedBundlePath, file);
                const stat = await fs.stat(filePath);
                if (stat.isFile()) {
                  totalSize += stat.size;
                }
              } catch (error) {
                // Skip files we can't stat
              }
            }
          } catch (error) {
            // If we can't calculate size, use a default
            totalSize = 0;
          }

          return {
            exists: true,
            path: extractedBundlePath,
            size: totalSize,
            extracted: true
          };
        }
      } catch (error) {
        // Error checking extracted files, fall through to check ZIP
      }
    }

    // Check if ZIP exists
    const zipPath = path.join(bundleDir, `${codename}-factory-${version}.zip`);
    try {
      const stats = await fs.stat(zipPath);
      if (stats.size > 0) {
        return { exists: true, path: zipPath, size: stats.size, extracted: false };
      }
    } catch (error) {
      // ZIP doesn't exist
    }

    return { exists: false };
  } catch (error) {
    return { exists: false };
  }
}

/**
 * Get local bundles directory path
 */
function getLocalBundlesPath() {
  return LOCAL_BUNDLES_DIR;
}

/**
 * Handle download bundle request from renderer with progress updates
 */
ipcMain.handle('download-bundle-local', async (event, codename, version, downloadUrl) => {
  try {
    console.log(`[IPC] download-bundle-local: ${codename}/${version}`);

    // Create a progress callback that sends updates to renderer
    const progressCallback = (progress) => {
      event.sender.send('download-progress', {
        codename,
        version,
        ...progress
      });
    };

    const result = await downloadBundleToLocal(codename, version, downloadUrl, progressCallback);
    return result;
  } catch (error) {
    console.error(`[IPC] download-bundle-local error:`, error);
    return { success: false, error: error.message };
  }
});

/**
 * Handle check local bundle request
 */
ipcMain.handle('check-local-bundle', async (event, codename, version) => {
  try {
    return await checkLocalBundle(codename, version);
  } catch (error) {
    return { exists: false, error: error.message };
  }
});

/**
 * Handle get local bundles path request
 */
ipcMain.handle('get-local-bundles-path', async () => {
  return { path: LOCAL_BUNDLES_DIR };
});

/**
 * Find fastboot executable path
 */
async function findFastbootPath() {
  const isWindows = process.platform === 'win32';

  // Check USB tools directory first (for portable mode)
  const usbToolsPath = path.join(path.dirname(process.execPath), '..', 'tools', isWindows ? 'fastboot.exe' : 'fastboot');
  if (fsSync.existsSync(usbToolsPath)) {
    console.log('[Tools] Found Fastboot in USB tools directory:', usbToolsPath);
    return usbToolsPath;
  }

  // Check relative to app directory (for portable builds)
  const relativeToolsPath = path.join(__dirname, '..', 'tools', isWindows ? 'fastboot.exe' : 'fastboot');
  if (fsSync.existsSync(relativeToolsPath)) {
    console.log('[Tools] Found Fastboot in relative tools directory:', relativeToolsPath);
    return relativeToolsPath;
  }

  // First, try direct command lookup
  try {
    const command = isWindows ? 'where fastboot' : 'which fastboot';
    const { stdout } = await execAsync(command);
    const resolved = stdout.trim().split('\n')[0].trim(); // Take first result
    if (resolved && fsSync.existsSync(resolved)) {
      return resolved;
    }
  } catch (error) {
    // Continue to try common paths
  }

  // Common paths to check
  const commonPaths = isWindows
    ? [
      'fastboot.exe',
      'C:\\platform-tools\\fastboot.exe',
      path.join(process.env.ProgramFiles || 'C:\\Program Files', 'Android', 'android-sdk', 'platform-tools', 'fastboot.exe'),
      path.join(process.env.LOCALAPPDATA || '', 'Android', 'Sdk', 'platform-tools', 'fastboot.exe')
    ]
    : [
      'fastboot',
      '/usr/bin/fastboot',
      '/usr/local/bin/fastboot',
      path.join(process.env.HOME || '', 'Android', 'Sdk', 'platform-tools', 'fastboot'),
      path.join(process.env.HOME || '', 'Library', 'Android', 'sdk', 'platform-tools', 'fastboot')
    ];

  for (const fastbootPath of commonPaths) {
    if (fsSync.existsSync(fastbootPath)) {
      return fastbootPath;
    }
  }

  throw new Error('Fastboot not found. Please install Android platform-tools or add to USB tools folder.');
}

/**
 * Find ADB executable path
 */
async function findAdbPath() {
  const isWindows = process.platform === 'win32';

  // Check USB tools directory first (for portable mode)
  const usbToolsPath = path.join(path.dirname(process.execPath), '..', 'tools', isWindows ? 'adb.exe' : 'adb');
  if (fsSync.existsSync(usbToolsPath)) {
    console.log('[Tools] Found ADB in USB tools directory:', usbToolsPath);
    return usbToolsPath;
  }

  // Check relative to app directory (for portable builds)
  const relativeToolsPath = path.join(__dirname, '..', 'tools', isWindows ? 'adb.exe' : 'adb');
  if (fsSync.existsSync(relativeToolsPath)) {
    console.log('[Tools] Found ADB in relative tools directory:', relativeToolsPath);
    return relativeToolsPath;
  }

  // First, try direct command lookup
  try {
    const command = isWindows ? 'where adb' : 'which adb';
    const { stdout } = await execAsync(command);
    const resolved = stdout.trim().split('\n')[0].trim(); // Take first result
    if (resolved && fsSync.existsSync(resolved)) {
      return resolved;
    }
  } catch (error) {
    // Continue to try common paths
  }

  // Common paths to check
  const commonPaths = isWindows
    ? [
      'adb.exe',
      'C:\\platform-tools\\adb.exe',
      path.join(process.env.ProgramFiles || 'C:\\Program Files', 'Android', 'android-sdk', 'platform-tools', 'adb.exe'),
      path.join(process.env.LOCALAPPDATA || '', 'Android', 'Sdk', 'platform-tools', 'adb.exe')
    ]
    : [
      'adb',
      '/usr/bin/adb',
      '/usr/local/bin/adb',
      path.join(process.env.HOME || '', 'Android', 'Sdk', 'platform-tools', 'adb'),
      path.join(process.env.HOME || '', 'Library', 'Android', 'sdk', 'platform-tools', 'adb')
    ];

  for (const adbPath of commonPaths) {
    if (fsSync.existsSync(adbPath)) {
      return adbPath;
    }
  }

  throw new Error('ADB not found. Please install Android platform-tools or add to USB tools folder.');
}

/**
 * Run flash script from the downloaded bundle directory:
 * - Windows: runs flash-all.bat (via cmd.exe)
 * - Mac and Linux: runs flash-all.sh (via sh)
 * Uses bundle path; passes device serial via FASTBOOT_SERIAL so the script flashes the correct device.
 */
function runFlashScript(bundlePath, deviceSerial, progressCallback) {
  return new Promise((resolve, reject) => {
    const isWindows = process.platform === 'win32';
    const scriptName = isWindows ? 'flash-all.bat' : 'flash-all.sh';
    const scriptPath = path.join(bundlePath, scriptName);

    if (!fsSync.existsSync(scriptPath)) {
      reject(new Error(`${scriptName} not found at ${scriptPath}`));
      return;
    }

    if (progressCallback) {
      progressCallback({ message: `Running ${scriptName} from bundle path...`, status: 'starting' });
      progressCallback({ message: `Path: ${bundlePath}`, status: 'info' });
      progressCallback({ message: `Device: ${deviceSerial}`, status: 'info' });
    }

    const env = { ...process.env, FASTBOOT_SERIAL: deviceSerial };
    const opts = { cwd: bundlePath, env, shell: isWindows };

    const child = spawn(isWindows ? 'cmd.exe' : 'sh', isWindows ? ['/c', scriptPath] : [scriptPath], opts);

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (data) => {
      const line = data.toString();
      stdout += line;
      if (progressCallback) {
        line.split('\n').filter(Boolean).forEach(l => progressCallback({ message: l, status: 'info' }));
      }
    });

    child.stderr.on('data', (data) => {
      const line = data.toString();
      stderr += line;
      if (progressCallback) {
        line.split('\n').filter(Boolean).forEach(l => progressCallback({ message: l, status: 'info' }));
      }
    });

    child.on('close', (code) => {
      if (code === 0) {
        if (progressCallback) progressCallback({ message: 'Flash completed successfully!', status: 'completed' });
        resolve({ success: true });
      } else {
        const err = new Error(`Flash script exited with code ${code}. ${stderr || stdout}`.slice(0, 500));
        if (progressCallback) progressCallback({ message: err.message, status: 'error' });
        reject(err);
      }
    });

    child.on('error', (err) => {
      if (progressCallback) progressCallback({ message: `Script error: ${err.message}`, status: 'error' });
      reject(err);
    });
  });
}

/**
 * Execute flash locally: run bundle script from downloaded bundle dir first, then fallback to GrapheneFlasher.
 * Windows: flash-all.bat | Mac/Linux: flash-all.sh
 */
async function executeLocalFlash(deviceSerial, bundlePath, skipUnlock, progressCallback) {
  try {
    // Run the bundle script from the downloaded bundle directory (flash-all.bat on Windows, flash-all.sh on Mac/Linux)
    const scriptPathWin = path.join(bundlePath, 'flash-all.bat');
    const scriptPathMac = path.join(bundlePath, 'flash-all.sh');
    const hasScript = fsSync.existsSync(scriptPathWin) || fsSync.existsSync(scriptPathMac);

    if (hasScript) {
      try {
        await runFlashScript(bundlePath, deviceSerial, progressCallback);
        return { success: true };
      } catch (scriptErr) {
        if (progressCallback) {
          progressCallback({ message: `Script flash failed, trying internal flasher: ${scriptErr.message}`, status: 'warning' });
        }
        // Fall through to GrapheneFlasher
      }
    }

    // Fallback: GrapheneFlasher (direct fastboot commands)
    const fastbootPath = await findFastbootPath();
    const adbPath = await findAdbPath();

    if (progressCallback) {
      progressCallback({ message: `Starting local flash execution...`, status: 'starting' });
      progressCallback({ message: `Bundle path: ${bundlePath}`, status: 'info' });
      progressCallback({ message: `Device serial: ${deviceSerial}`, status: 'info' });
      progressCallback({ message: `Fastboot: ${fastbootPath}`, status: 'info' });
      progressCallback({ message: `ADB: ${adbPath}`, status: 'info' });
    }

    const flasher = new GrapheneFlasher(
      fastbootPath,
      adbPath,
      bundlePath,
      deviceSerial,
      (logData) => {
        if (progressCallback) {
          progressCallback({
            message: logData.message,
            status: logData.status,
            step: logData.step,
            partition: logData.partition
          });
        }
      }
    );

    await flasher.flash();

    if (progressCallback) {
      progressCallback({ message: `Flash completed successfully!`, status: 'completed' });
    }

    return { success: true };
  } catch (error) {
    if (progressCallback) {
      progressCallback({ message: `Flash failed: ${error.message}`, status: 'error' });
    }
    throw error;
  }
}

/**
 * Handle execute local flash request
 */
ipcMain.handle('execute-local-flash', async (event, deviceSerial, codename, version, skipUnlock) => {
  try {
    const bundlePath = path.join(LOCAL_BUNDLES_DIR, codename, version);

    // Verify bundle directory exists
    if (!fsSync.existsSync(bundlePath)) {
      throw new Error(`Bundle directory not found: ${bundlePath}`);
    }

    console.log(`[Flash] Looking for bundle in: ${bundlePath}`);

    // Find the actual bundle directory (might be in a subdirectory)
    // Use the same helper function that download uses - checks for flash-all.sh
    let actualBundlePath = await findExtractedBundlePath(bundlePath, codename);

    // Verify the found path actually has image files - use fs.readdir for reliability
    if (actualBundlePath) {
      try {
        const files = await fs.readdir(actualBundlePath);
        const hasBootloader = files.some(f => f.includes('bootloader') && f.endsWith('.img'));
        const hasRadio = files.some(f => f.includes('radio') && f.endsWith('.img'));
        console.log(`[Flash] Path from findExtractedBundlePath: ${actualBundlePath}`);
        console.log(`[Flash] Has bootloader: ${hasBootloader}, has radio: ${hasRadio}, total files: ${files.length}`);

        if (!hasBootloader && !hasRadio) {
          // Path found but no images - need to search subdirectories
          console.log(`[Flash] Found path but no images, searching subdirectories...`);
          actualBundlePath = null; // Reset to trigger subdirectory search
        } else {
          console.log(`[Flash] Using bundle path from findExtractedBundlePath: ${actualBundlePath}`);
        }
      } catch (readError) {
        console.error(`[Flash] Error reading path:`, readError);
        actualBundlePath = null; // Reset to trigger search
      }
    }

    if (!actualBundlePath) {
      // If not found via flash-all.sh check, try finding by image files
      console.log(`[Flash] Bundle path not found via flash-all.sh, searching for image files...`);

      // Check if files are directly in bundle directory - use fs.readdir for reliability
      try {
        const baseFiles = await fs.readdir(bundlePath);
        const hasBootloader = baseFiles.some(f => f.includes('bootloader') && f.endsWith('.img'));
        const hasRadio = baseFiles.some(f => f.includes('radio') && f.endsWith('.img'));
        console.log(`[Flash] Base directory: hasBootloader=${hasBootloader}, hasRadio=${hasRadio}, totalFiles=${baseFiles.length}`);

        // If not found, check ALL subdirectories (not just install ones)
        if (!hasBootloader && !hasRadio) {
          console.log(`[Flash] Checking all subdirectories:`, baseFiles.filter(f => !f.includes('.zip') && !f.includes('.sha256') && !f.includes('.sig')));
          for (const entry of baseFiles) {
            // Skip zip files and other non-directory entries
            if (entry.includes('.zip') || entry.includes('.sha256') || entry.includes('.sig') || entry === 'metadata.json') {
              continue;
            }

            const subdirPath = path.join(bundlePath, entry);
            try {
              const stat = await fs.stat(subdirPath);
              if (stat.isDirectory()) {
                console.log(`[Flash] Checking subdirectory: ${entry}`);
                const subdirFiles = await fs.readdir(subdirPath);
                const subdirHasBootloader = subdirFiles.some(f => f.includes('bootloader') && f.endsWith('.img'));
                const subdirHasRadio = subdirFiles.some(f => f.includes('radio') && f.endsWith('.img'));
                console.log(`[Flash] ${entry}: hasBootloader=${subdirHasBootloader}, hasRadio=${subdirHasRadio}, totalFiles=${subdirFiles.length}`);
                if (subdirHasBootloader || subdirHasRadio) {
                  actualBundlePath = subdirPath;
                  console.log(`[Flash] Using subdirectory: ${actualBundlePath}`);
                  break;
                }
              }
            } catch (statError) {
              // Skip entries we can't stat
              console.log(`[Flash] Could not stat ${entry}:`, statError.message);
            }
          }
        } else {
          // Files found directly in bundle directory
          actualBundlePath = bundlePath;
          console.log(`[Flash] Using base directory: ${actualBundlePath}`);
        }
      } catch (error) {
        console.error(`[Flash] Error reading bundle directory:`, error);
      }
    } else {
      console.log(`[Flash] Found bundle via findExtractedBundlePath: ${actualBundlePath}`);
    }

    if (!actualBundlePath) {
      // Last resort: try to find ANY subdirectory with image files
      console.log(`[Flash] No bundle path found, doing final search of all subdirectories...`);
      try {
        const entries = await fs.readdir(bundlePath);
        console.log(`[Flash] All entries in bundle directory:`, entries);

        for (const entry of entries) {
          const subdirPath = path.join(bundlePath, entry);
          try {
            const stat = await fs.stat(subdirPath);
            if (stat.isDirectory()) {
              console.log(`[Flash] Final check - subdirectory: ${entry}`);
              // Use fs.readdir to check for files directly (more reliable than glob)
              const subdirFiles = await fs.readdir(subdirPath);
              const hasBootloader = subdirFiles.some(f => f.includes('bootloader') && f.endsWith('.img'));
              const hasRadio = subdirFiles.some(f => f.includes('radio') && f.endsWith('.img'));
              console.log(`[Flash] ${entry} - hasBootloader: ${hasBootloader}, hasRadio: ${hasRadio}`);

              if (hasBootloader || hasRadio) {
                actualBundlePath = subdirPath;
                console.log(`[Flash] Found bundle in subdirectory: ${actualBundlePath}`);
                break;
              }
            }
          } catch (statError) {
            console.log(`[Flash] Could not check ${entry}:`, statError.message);
          }
        }
      } catch (error) {
        console.error(`[Flash] Error in final search:`, error);
      }

      if (!actualBundlePath) {
        // List directory for debugging
        try {
          const entries = await fs.readdir(bundlePath);
          throw new Error(`Bundle appears to be empty or not extracted: ${bundlePath}. Directory contents: ${entries.join(', ')}`);
        } catch (listError) {
          throw new Error(`Bundle appears to be empty or not extracted: ${bundlePath}. Could not list directory: ${listError.message}`);
        }
      }
    }

    console.log(`[Flash] Using bundle path: ${actualBundlePath}`);

    // Verify the path has required files (using fs.readdir for more reliable check)
    try {
      const files = await fs.readdir(actualBundlePath);
      const hasBootloader = files.some(f => f.includes('bootloader') && f.endsWith('.img'));
      const hasRadio = files.some(f => f.includes('radio') && f.endsWith('.img'));
      const hasFlashAll = files.some(f => f === 'flash-all.sh' || f === 'flash-all.bat');

      console.log(`[Flash] Verified files in ${actualBundlePath}:`);
      console.log(`[Flash]   - flash-all.sh/bat: ${hasFlashAll}`);
      console.log(`[Flash]   - bootloader: ${hasBootloader}`);
      console.log(`[Flash]   - radio: ${hasRadio}`);
      console.log(`[Flash]   - Total files: ${files.length}`);

      if (!hasBootloader && !hasRadio) {
        throw new Error(`Bundle path found but missing image files: ${actualBundlePath}. Files: ${files.slice(0, 10).join(', ')}${files.length > 10 ? '...' : ''}`);
      }
    } catch (verifyError) {
      console.error(`[Flash] Error verifying bundle:`, verifyError);
      throw verifyError;
    }

    // Create progress callback
    const progressCallback = (progress) => {
      event.sender.send('flash-progress', {
        deviceSerial,
        codename,
        version,
        ...progress
      });
    };

    const result = await executeLocalFlash(deviceSerial, actualBundlePath, skipUnlock, progressCallback);
    return { success: true, result };
  } catch (error) {
    console.error('[IPC] execute-local-flash error:', error);
    return { success: false, error: error.message };
  }
});

/**
 * Send a log line to the renderer (for adb install / flash script output)
 */
function sendLogLine(webContents, message, level = 'info') {
  if (webContents && !webContents.isDestroyed()) {
    webContents.send('log-line', { message, level });
  }
}

/**
 * Handle download APK request - download from backend to userData/apks
 */
ipcMain.handle('download-apk', async (event, apkFilename) => {
  console.log(`[IPC] download-apk handler called for ${apkFilename}`);
  try {
    const downloadUrl = `${BACKEND_URL}/apks/download/${encodeURIComponent(apkFilename)}`;
    const apkStorageDir = path.join(app.getPath('userData'), 'apks');
    await fs.mkdir(apkStorageDir, { recursive: true });
    const localApkPath = path.join(apkStorageDir, apkFilename);

    try {
      await fs.access(localApkPath);
      console.log(`[APK] Already downloaded: ${localApkPath}`);
      return { success: true, path: localApkPath, cached: true };
    } catch (_) {
      // not found, download
    }

    await new Promise((resolve, reject) => {
      const parsedUrl = new URL(downloadUrl);
      const httpModule = parsedUrl.protocol === 'https:' ? https : http;
      const file = fsSync.createWriteStream(localApkPath);

      const request = httpModule.get(downloadUrl, (response) => {
        if (response.statusCode !== 200) {
          file.close();
          fsSync.unlink(localApkPath, () => {});
          reject(new Error(`Failed to download APK: HTTP ${response.statusCode}`));
          return;
        }
        response.pipe(file);
        file.on('finish', () => {
          file.close();
          console.log(`[APK] Downloaded to: ${localApkPath}`);
          resolve();
        });
      });

      request.on('error', (err) => {
        file.close();
        fsSync.unlink(localApkPath, () => {});
        reject(err);
      });
      file.on('error', (err) => {
        file.close();
        fsSync.unlink(localApkPath, () => {});
        reject(err);
      });
    });

    return { success: true, path: localApkPath, cached: false };
  } catch (error) {
    console.error('[APK] Download error:', error);
    return { success: false, error: error.message };
  }
});

/**
 * Handle install APK request
 * Downloads APK if needed, runs adb install, streams output to app log
 */
ipcMain.handle('install-apk', async (event, deviceSerial, apkFilename) => {
  console.log(`[IPC] install-apk handler called for device ${deviceSerial}, APK ${apkFilename}`);
  const sendLog = (msg, level) => sendLogLine(event.sender, msg, level);

  try {
    sendLog(`[APK] Installing ${apkFilename} on device ${deviceSerial}`, 'info');

    const adbPath = await findAdbPath();
    sendLog(`[APK] Using ADB: ${adbPath}`, 'info');

    const downloadUrl = `${BACKEND_URL}/apks/download/${encodeURIComponent(apkFilename)}`;
    const apkStorageDir = path.join(app.getPath('userData'), 'apks');
    await fs.mkdir(apkStorageDir, { recursive: true });
    const localApkPath = path.join(apkStorageDir, apkFilename);

    let apkExists = false;
    try {
      await fs.access(localApkPath);
      apkExists = true;
      sendLog(`[APK] Using local file: ${localApkPath}`, 'info');
    } catch (_) {}

    if (!apkExists) {
      sendLog(`[APK] Downloading from server...`, 'info');
      await new Promise((resolve, reject) => {
        const parsedUrl = new URL(downloadUrl);
        const httpModule = parsedUrl.protocol === 'https:' ? https : http;
        const file = fsSync.createWriteStream(localApkPath);

        const request = httpModule.get(downloadUrl, (response) => {
          if (response.statusCode !== 200) {
            file.close();
            fsSync.unlink(localApkPath, () => {});
            reject(new Error(`Failed to download APK: HTTP ${response.statusCode}`));
            return;
          }
          response.pipe(file);
          file.on('finish', () => {
            file.close();
            sendLog(`[APK] Downloaded to: ${localApkPath}`, 'info');
            resolve();
          });
        });

        request.on('error', (err) => {
          file.close();
          fsSync.unlink(localApkPath, () => {});
          reject(err);
        });
        file.on('error', (err) => {
          file.close();
          fsSync.unlink(localApkPath, () => {});
          reject(err);
        });
      });
    }

    const installCmd = [adbPath, '-s', deviceSerial, 'install', '-r', localApkPath];
    const cmdStr = `adb -s ${deviceSerial} install -r "${localApkPath}"`;
    sendLog(`[APK] Running: ${cmdStr}`, 'info');

    return new Promise((resolve) => {
      const proc = spawn(installCmd[0], installCmd.slice(1), {
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: false
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data) => {
        const text = data.toString();
        stdout += text;
        text.split('\n').filter(Boolean).forEach((line) => sendLog(line, 'info'));
      });

      proc.stderr.on('data', (data) => {
        const text = data.toString();
        stderr += text;
        text.split('\n').filter(Boolean).forEach((line) => sendLog(line, 'info'));
      });

      proc.on('close', (code) => {
        if (code === 0) {
          sendLog(`[APK] Installation successful`, 'success');
          resolve({ success: true, message: `APK ${apkFilename} installed successfully` });
        } else {
          const errorMsg = stderr || stdout || `ADB install failed with code ${code}`;
          sendLog(`[APK] Install failed: ${errorMsg}`, 'error');
          resolve({ success: false, error: `Failed to install APK: ${errorMsg}` });
        }
      });

      proc.on('error', (err) => {
        sendLog(`[APK] Process error: ${err.message}`, 'error');
        resolve({ success: false, error: `Failed to execute ADB: ${err.message}` });
      });
    });
  } catch (error) {
    console.error('[APK] Install error:', error);
    sendLog(`[APK] Error: ${error.message}`, 'error');
    return { success: false, error: error.message };
  }
});

console.log('[IPC] ✓ install-apk handler registered at line', 1183);

/**
 * Handle upload APK request - opens file dialog and uploads selected file
 */
ipcMain.handle('upload-apk', async (event) => {
  try {
    // Get the window that sent the request, or use mainWindow
    const targetWindow = BrowserWindow.fromWebContents(event.sender) || mainWindow;

    // Show file dialog to select APK
    const result = await dialog.showOpenDialog(targetWindow, {
      title: 'Select APK File',
      filters: [
        { name: 'APK Files', extensions: ['apk'] },
        { name: 'All Files', extensions: ['*'] }
      ],
      properties: ['openFile']
    });

    if (result.canceled || !result.filePaths || result.filePaths.length === 0) {
      return { success: false, error: 'No file selected' };
    }

    const filePath = result.filePaths[0];
    console.log(`[APK] Uploading APK: ${filePath}`);

    // Read file
    const fileBuffer = await fs.readFile(filePath);
    const fileName = path.basename(filePath);

    // Validate file extension
    if (!fileName.endsWith('.apk')) {
      throw new Error('File must be an APK file (.apk)');
    }

    // Create form data
    const form = new FormData();
    form.append('file', fileBuffer, {
      filename: fileName,
      contentType: 'application/vnd.android.package-archive'
    });
    form.append('username', 'admin');
    form.append('password', 'AllHailToEagle');

    // Make request to backend API
    const url = `${BACKEND_URL}/apks/upload`;
    const parsedUrl = new URL(url);
    const isHttps = parsedUrl.protocol === 'https:';
    const httpModule = isHttps ? https : http;

    return new Promise((resolve, reject) => {
      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: parsedUrl.pathname,
        method: 'POST',
        headers: {
          ...form.getHeaders(),
          'Authorization': 'Basic ' + Buffer.from('admin:AllHailToEagle').toString('base64')
        }
      };

      const req = httpModule.request(options, (res) => {
        let data = '';

        res.on('data', (chunk) => {
          data += chunk;
        });

        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            console.log(`[APK] Upload successful: ${fileName}`);
            resolve({ success: true, message: `APK ${fileName} uploaded successfully` });
          } else {
            let errorMessage = `HTTP ${res.statusCode}`;
            try {
              // Try to parse error response
              const errorMatch = data.match(/detail["\s:]+([^"<]+)/i);
              if (errorMatch) {
                errorMessage = errorMatch[1];
              }
            } catch (e) {
              // Use default error message
            }
            console.error(`[APK] Upload failed:`, errorMessage);
            resolve({ success: false, error: errorMessage });
          }
        });
      });

      req.on('error', (error) => {
        console.error(`[APK] Request error:`, error);
        resolve({ success: false, error: error.message });
      });

      // Pipe form data to request
      form.pipe(req);
    });
  } catch (error) {
    console.error('[APK] Upload error:', error);
    return { success: false, error: error.message };
  }
});

// Log registered IPC handlers (for debugging)
/**
 * Handle auto-flash start request
 */
ipcMain.handle('auto-flash-start', async (event, { deviceSerial, codename, bundlePath, skipUnlock }) => {
  try {
    console.log(`[AutoFlash] Starting flash for device ${deviceSerial}`);

    // Find bundle version from path
    const pathParts = bundlePath.split(path.sep);
    const versionIndex = pathParts.findIndex(part => /^\d{10}$/.test(part)); // YYYYMMDDHH format
    const version = versionIndex >= 0 ? pathParts[versionIndex] : null;

    if (!version) {
      throw new Error('Could not determine bundle version from path');
    }

    // Execute local flash
    const progressCallback = (progress) => {
      event.sender.send('flash-progress', progress);
    };

    const result = await executeLocalFlash(deviceSerial, bundlePath, skipUnlock, progressCallback);
    return result;
  } catch (error) {
    console.error('[AutoFlash] Flash error:', error);
    return { success: false, error: error.message };
  }
});

/**
 * Handle get auto-flash config request
 */
ipcMain.handle('get-auto-flash-config', async () => {
  return autoFlashConfig || {};
});

/**
 * Handle update auto-flash config request
 */
ipcMain.handle('update-auto-flash-config', async (event, newConfig) => {
  try {
    autoFlashConfig = { ...autoFlashConfig, ...newConfig };

    // Save to file
    const configPath = path.join(__dirname, 'auto-flash-config.json');
    await fs.writeFile(configPath, JSON.stringify(autoFlashConfig, null, 2));

    console.log('[AutoFlash] Configuration updated:', autoFlashConfig);

    // Restart auto-detection if needed
    if (autoDetectInterval) {
      clearInterval(autoDetectInterval);
      autoDetectInterval = null;
    }

    if (autoFlashConfig && autoFlashConfig.autoDetect) {
      await startAutoDetection();
    }

    return { success: true, config: autoFlashConfig };
  } catch (error) {
    console.error('[AutoFlash] Failed to update config:', error);
    return { success: false, error: error.message };
  }
});

console.log('[IPC] Registering IPC handlers...');
console.log('[IPC] Registered handlers:', [
  'detect-devices',
  'get-device-details',
  'reboot-to-fastboot',
  'download-bundle-local',
  'check-local-bundle',
  'get-local-bundles-path',
  'execute-local-flash',
  'install-apk',
  'upload-apk',
  'auto-flash-start',
  'get-auto-flash-config',
  'update-auto-flash-config'
]);

// Verify install-apk handler is actually registered
if (ipcMain.listenerCount('install-apk') > 0 || ipcMain._handlers && ipcMain._handlers.has('install-apk')) {
  console.log('[IPC] ✓ install-apk handler is registered');
} else {
  console.error('[IPC] ✗ install-apk handler NOT registered!');
}

// Auto-flash configuration
let autoFlashConfig = null;
let autoDetectInterval = null;

async function loadAutoFlashConfig() {
  try {
    const configPath = path.join(__dirname, 'auto-flash-config.json');
    if (fsSync.existsSync(configPath)) {
      const configData = await fs.readFile(configPath, 'utf-8');
      autoFlashConfig = JSON.parse(configData);
      console.log('[AutoFlash] Configuration loaded:', autoFlashConfig);
    } else {
      // Default config
      autoFlashConfig = {
        autoDetect: false,
        autoFlash: false,
        autoFlashDelay: 5000,
        targetCodename: null,
        targetVersion: null,
        skipUnlock: true,
        bundlesPath: './bundles',
        showWindow: true,
        minimizeToTray: false
      };
    }
  } catch (error) {
    console.error('[AutoFlash] Failed to load config:', error);
    autoFlashConfig = { autoDetect: false, autoFlash: false };
  }
}

async function startAutoDetection() {
  if (!autoFlashConfig || !autoFlashConfig.autoDetect) {
    return;
  }

  console.log('[AutoFlash] Starting auto-detection...');

  autoDetectInterval = setInterval(async () => {
    try {
      const devices = await detectDevices();

      if (devices.length > 0) {
        console.log(`[AutoFlash] Detected ${devices.length} device(s)`);

        // Send notification to renderer if window exists
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('auto-device-detected', devices);
        }

        // Auto-flash if enabled
        if (autoFlashConfig.autoFlash && devices.length > 0) {
          const device = devices[0]; // Flash first device

          // Check if target codename matches (if specified)
          if (autoFlashConfig.targetCodename && device.codename !== autoFlashConfig.targetCodename) {
            console.log(`[AutoFlash] Device codename ${device.codename} doesn't match target ${autoFlashConfig.targetCodename}`);
            return;
          }

          console.log(`[AutoFlash] Auto-flashing device ${device.serial} in ${autoFlashConfig.autoFlashDelay}ms...`);

          setTimeout(async () => {
            try {
              // Find bundle
              const bundlesPath = path.isAbsolute(autoFlashConfig.bundlesPath)
                ? autoFlashConfig.bundlesPath
                : path.join(path.dirname(process.execPath), autoFlashConfig.bundlesPath);

              // Look for bundle matching codename and version
              const bundleDir = path.join(bundlesPath, device.codename || 'unknown', autoFlashConfig.targetVersion || 'latest');

              if (fsSync.existsSync(bundleDir)) {
                console.log(`[AutoFlash] Found bundle at: ${bundleDir}`);
                // Trigger flash via IPC
                if (mainWindow && !mainWindow.isDestroyed()) {
                  mainWindow.webContents.send('auto-flash-start', {
                    deviceSerial: device.serial,
                    codename: device.codename,
                    bundlePath: bundleDir,
                    skipUnlock: autoFlashConfig.skipUnlock
                  });
                }
              } else {
                console.log(`[AutoFlash] Bundle not found at: ${bundleDir}`);
              }
            } catch (error) {
              console.error('[AutoFlash] Auto-flash error:', error);
            }
          }, autoFlashConfig.autoFlashDelay);
        }
      }
    } catch (error) {
      console.error('[AutoFlash] Detection error:', error);
    }
  }, 3000); // Check every 3 seconds
}

// App lifecycle

app.whenReady().then(async () => {
  // Load auto-flash configuration
  await loadAutoFlashConfig();

  // Verify handlers are registered before creating window
  console.log('[IPC] App ready - verifying handlers...');
  console.log('[IPC] install-apk handler registered:', typeof ipcMain._handlers !== 'undefined' && ipcMain._handlers.has('install-apk'));

  // Create window (or minimize if configured)
  if (autoFlashConfig && !autoFlashConfig.showWindow) {
    // Don't show window, but still create it for IPC
    createWindow();
    if (mainWindow) {
      mainWindow.hide();
    }
  } else {
    createWindow();
  }

  // Start auto-detection if enabled
  if (autoFlashConfig && autoFlashConfig.autoDetect) {
    await startAutoDetection();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Security: Prevent new window creation from renderer
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
  });

  contents.on('will-navigate', (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl);

    // Only allow navigation to our renderer HTML or backend API
    if (parsedUrl.origin !== 'file://' && parsedUrl.origin !== BACKEND_URL) {
      event.preventDefault();
    }
  });
});
