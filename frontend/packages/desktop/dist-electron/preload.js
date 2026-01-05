"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    startService: () => electron_1.ipcRenderer.invoke('start-service'),
    stopService: () => electron_1.ipcRenderer.invoke('stop-service'),
    getServiceStatus: () => electron_1.ipcRenderer.invoke('get-service-status'),
    openFolderPicker: () => electron_1.ipcRenderer.invoke('open-folder-picker'),
});
