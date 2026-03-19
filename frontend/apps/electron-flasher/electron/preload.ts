/**
 * Electron Preload Script - Exposes safe APIs to renderer
 */

import { contextBridge } from 'electron';

// Expose protected methods that allow the renderer process to use
// WebUSB and WebADB APIs safely
contextBridge.exposeInMainWorld('electron', {
  // Add any Electron-specific APIs here if needed
  // WebUSB/WebADB APIs are accessed directly in renderer
});

