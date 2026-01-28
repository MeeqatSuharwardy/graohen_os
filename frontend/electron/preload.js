/**
 * FlashDash Client - Preload Script
 * 
 * This script runs in a context that has access to both Node.js APIs
 * and the renderer's window object. It creates a secure bridge between
 * the main process and renderer process using contextBridge.
 * 
 * SECURITY: Only exposes specific, safe APIs to the renderer.
 * Renderer cannot access Node.js directly or execute shell commands.
 */

const { contextBridge, ipcRenderer } = require('electron');

/**
 * Expose protected methods that allow the renderer process
 * to communicate with the main process via IPC
 */
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Detect connected Android devices via adb
   * @returns {Promise<{success: boolean, devices: Array, error?: string}>}
   */
  detectDevices: () => ipcRenderer.invoke('detect-devices'),

  /**
   * Get detailed information for a specific device
   * @param {string} serial - Device serial number
   * @returns {Promise<{success: boolean, device?: Object, error?: string}>}
   */
  getDeviceDetails: (serial) => ipcRenderer.invoke('get-device-details', serial),

  /**
   * Reboot device into fastboot mode
   * @param {string} serial - Device serial number
   * @returns {Promise<{success: boolean, error?: string, message?: string}>}
   */
  rebootToFastboot: (serial) => ipcRenderer.invoke('reboot-to-fastboot', serial),

  /**
   * Download bundle to local storage
   * @param {string} codename - Device codename
   * @param {string} version - Bundle version
   * @param {string} downloadUrl - URL to download from
   * @returns {Promise<{success: boolean, path?: string, cached?: boolean, error?: string}>}
   */
  downloadBundleLocal: (codename, version, downloadUrl) => ipcRenderer.invoke('download-bundle-local', codename, version, downloadUrl),

  /**
   * Listen for download progress updates
   * @param {function} callback - Callback function receiving progress updates
   * @returns {function} - Unsubscribe function
   */
  onDownloadProgress: (callback) => {
    const handler = (event, progress) => callback(progress);
    ipcRenderer.on('download-progress', handler);
    return () => ipcRenderer.removeListener('download-progress', handler);
  },

  /**
   * Check if bundle exists locally
   * @param {string} codename - Device codename
   * @param {string} version - Bundle version
   * @returns {Promise<{exists: boolean, path?: string, size?: number}>}
   */
  checkLocalBundle: (codename, version) => ipcRenderer.invoke('check-local-bundle', codename, version),

  /**
   * Get local bundles directory path
   * @returns {Promise<{path: string}>}
   */
  getLocalBundlesPath: () => ipcRenderer.invoke('get-local-bundles-path'),

  /**
   * Execute flash locally from extracted bundle
   * @param {string} deviceSerial - Device serial number
   * @param {string} codename - Device codename
   * @param {string} version - Bundle version
   * @param {boolean} skipUnlock - Skip bootloader unlock
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  executeLocalFlash: (deviceSerial, codename, version, skipUnlock) => 
    ipcRenderer.invoke('execute-local-flash', deviceSerial, codename, version, skipUnlock),

  /**
   * Listen for local flash progress updates
   * @param {function} callback - Callback function receiving progress updates
   * @returns {function} - Unsubscribe function
   */
  onFlashProgress: (callback) => {
    const handler = (event, progress) => callback(progress);
    ipcRenderer.on('flash-progress', handler);
    return () => ipcRenderer.removeListener('flash-progress', handler);
  },

  /**
   * Install APK on connected device
   * @param {string} deviceSerial - Device serial number
   * @param {string} apkFilename - APK filename
   * @returns {Promise<{success: boolean, error?: string, message?: string}>}
   */
  installApk: (deviceSerial, apkFilename) => 
    ipcRenderer.invoke('install-apk', deviceSerial, apkFilename),

  /**
   * Upload APK file to server (opens file dialog)
   * @returns {Promise<{success: boolean, error?: string, message?: string}>}
   */
  uploadApk: () => 
    ipcRenderer.invoke('upload-apk'),

  /**
   * Get auto-flash configuration
   * @returns {Promise<Object>}
   */
  getAutoFlashConfig: () => 
    ipcRenderer.invoke('get-auto-flash-config'),

  /**
   * Update auto-flash configuration
   * @param {Object} config - Configuration object
   * @returns {Promise<{success: boolean, config?: Object, error?: string}>}
   */
  updateAutoFlashConfig: (config) => 
    ipcRenderer.invoke('update-auto-flash-config', config),

  /**
   * Start auto-flash for a device
   * @param {Object} params - Flash parameters
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  autoFlashStart: (params) => 
    ipcRenderer.invoke('auto-flash-start', params),

  /**
   * Listen for auto device detection events
   * @param {function} callback - Callback function
   * @returns {function} - Unsubscribe function
   */
  onAutoDeviceDetected: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('auto-device-detected', handler);
    return () => ipcRenderer.removeListener('auto-device-detected', handler);
  },

  /**
   * Listen for auto-flash start events
   * @param {function} callback - Callback function
   * @returns {function} - Unsubscribe function
   */
  onAutoFlashStart: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on('auto-flash-start', handler);
    return () => ipcRenderer.removeListener('auto-flash-start', handler);
  },
});

/**
 * Log that preload script has loaded (for debugging)
 */
console.log('FlashDash preload script loaded');
