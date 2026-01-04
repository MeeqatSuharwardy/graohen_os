// This file will be generated from preload.ts during build
// For development, we'll use a simple bridge
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  startService: () => ipcRenderer.invoke('start-service'),
  stopService: () => ipcRenderer.invoke('stop-service'),
  getServiceStatus: () => ipcRenderer.invoke('get-service-status'),
  openFolderPicker: () => ipcRenderer.invoke('open-folder-picker'),
});

