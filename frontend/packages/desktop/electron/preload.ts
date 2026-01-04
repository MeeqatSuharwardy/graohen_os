import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  startService: () => ipcRenderer.invoke('start-service'),
  stopService: () => ipcRenderer.invoke('stop-service'),
  getServiceStatus: () => ipcRenderer.invoke('get-service-status'),
  openFolderPicker: () => ipcRenderer.invoke('open-folder-picker'),
});

declare global {
  interface Window {
    electronAPI: {
      startService: () => Promise<{ success: boolean; message: string }>;
      stopService: () => Promise<{ success: boolean; message: string }>;
      getServiceStatus: () => Promise<{ running: boolean }>;
      openFolderPicker: () => Promise<string | null>;
    };
  }
}

