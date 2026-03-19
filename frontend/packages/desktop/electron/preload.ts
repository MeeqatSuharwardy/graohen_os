import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  downloadBundle: (params: {
    device: string;
    buildId: string;
    apiBase: string;
    apiKey: string;
    cacheDir: string;
  }) => ipcRenderer.invoke('download-bundle', params),
  
  flashDevice: (params: {
    bundlePath: string;
    deviceSerial?: string;
    fastbootPath: string;
    adbPath: string;
    confirm: boolean;
  }) => ipcRenderer.invoke('flash-device', params),
  
  getEnvConfig: () => ipcRenderer.invoke('get-env-config'),
  
  onDownloadProgress: (callback: (data: { percent: number; message: string }) => void) => {
    ipcRenderer.on('download-progress', (_, data) => callback(data));
  },
  
  onDownloadLog: (callback: (message: string) => void) => {
    ipcRenderer.on('download-log', (_, message) => callback(message));
  },
  
  onFlashLog: (callback: (log: { type: string; message: string }) => void) => {
    ipcRenderer.on('flash-log', (_, log) => callback(log));
  },
  
  removeAllListeners: (channel: string) => {
    ipcRenderer.removeAllListeners(channel);
  },
});

declare global {
  interface Window {
    electronAPI: {
      downloadBundle: (params: any) => Promise<any>;
      flashDevice: (params: any) => Promise<any>;
      getEnvConfig: () => Promise<Record<string, string>>;
      onDownloadProgress: (callback: (data: any) => void) => void;
      onDownloadLog: (callback: (message: string) => void) => void;
      onFlashLog: (callback: (log: any) => void) => void;
      removeAllListeners: (channel: string) => void;
    };
  }
}
