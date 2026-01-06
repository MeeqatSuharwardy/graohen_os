"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    downloadBundle: (params) => electron_1.ipcRenderer.invoke('download-bundle', params),
    flashDevice: (params) => electron_1.ipcRenderer.invoke('flash-device', params),
    getEnvConfig: () => electron_1.ipcRenderer.invoke('get-env-config'),
    onDownloadProgress: (callback) => {
        electron_1.ipcRenderer.on('download-progress', (_, data) => callback(data));
    },
    onDownloadLog: (callback) => {
        electron_1.ipcRenderer.on('download-log', (_, message) => callback(message));
    },
    onFlashLog: (callback) => {
        electron_1.ipcRenderer.on('flash-log', (_, log) => callback(log));
    },
    removeAllListeners: (channel) => {
        electron_1.ipcRenderer.removeAllListeners(channel);
    },
});
