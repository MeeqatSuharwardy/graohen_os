"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const child_process_1 = require("child_process");
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
let mainWindow = null;
let pythonService = null;
const isDev = process.env.NODE_ENV === 'development' || !electron_1.app.isPackaged;
function createWindow() {
    mainWindow = new electron_1.BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1200,
        minHeight: 700,
        webPreferences: {
            preload: path_1.default.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
        },
        titleBarStyle: 'hiddenInset',
        backgroundColor: '#0a0a0a',
    });
    if (isDev) {
        mainWindow.loadURL('http://localhost:5174');
        mainWindow.webContents.openDevTools();
    }
    else {
        mainWindow.loadFile(path_1.default.join(__dirname, '../dist/index.html'));
    }
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}
// Register custom protocol handler
electron_1.app.setAsDefaultProtocolClient('flashdash');
// Handle protocol URLs
electron_1.app.on('open-url', (event, url) => {
    event.preventDefault();
    if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
    }
    else {
        createWindow();
    }
});
// Windows/Linux protocol handling
electron_1.app.on('second-instance', () => {
    if (mainWindow) {
        if (mainWindow.isMinimized())
            mainWindow.restore();
        mainWindow.focus();
    }
});
function startPythonService() {
    return new Promise((resolve) => {
        const backendPath = path_1.default.join(__dirname, '../../../../backend/py-service');
        const pythonPath = isDev
            ? path_1.default.join(__dirname, '../../../../backend/.venv/bin/python')
            : 'python3';
        if (!fs_1.default.existsSync(backendPath)) {
            console.error('Backend path not found:', backendPath);
            resolve(false);
            return;
        }
        pythonService = (0, child_process_1.spawn)(pythonPath, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '17890'], {
            cwd: backendPath,
            stdio: 'pipe',
            env: { ...process.env, PYTHONUNBUFFERED: '1' },
        });
        pythonService.stdout?.on('data', (data) => {
            console.log(`[Python] ${data}`);
        });
        pythonService.stderr?.on('data', (data) => {
            console.error(`[Python Error] ${data}`);
        });
        pythonService.on('exit', (code) => {
            console.log(`Python service exited with code ${code}`);
            pythonService = null;
        });
        // Wait a bit to see if service starts
        setTimeout(() => {
            resolve(pythonService !== null);
        }, 2000);
    });
}
function stopPythonService() {
    if (pythonService) {
        pythonService.kill();
        pythonService = null;
    }
}
// IPC Handlers
electron_1.ipcMain.handle('start-service', async () => {
    if (pythonService) {
        return { success: true, message: 'Service already running' };
    }
    const success = await startPythonService();
    return { success, message: success ? 'Service started' : 'Failed to start service' };
});
electron_1.ipcMain.handle('stop-service', () => {
    stopPythonService();
    return { success: true, message: 'Service stopped' };
});
electron_1.ipcMain.handle('get-service-status', async () => {
    if (!pythonService) {
        return { running: false };
    }
    // Check if service is responding
    try {
        const response = await fetch('http://127.0.0.1:17890/health');
        return { running: response.ok };
    }
    catch {
        return { running: false };
    }
});
electron_1.ipcMain.handle('open-folder-picker', async () => {
    const { dialog } = await Promise.resolve().then(() => __importStar(require('electron')));
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory'],
    });
    return result.canceled ? null : result.filePaths[0];
});
electron_1.app.whenReady().then(() => {
    createWindow();
    // Auto-start Python service in production
    if (!isDev) {
        startPythonService();
    }
    electron_1.app.on('activate', () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});
electron_1.app.on('window-all-closed', () => {
    stopPythonService();
    if (process.platform !== 'darwin') {
        electron_1.app.quit();
    }
});
electron_1.app.on('before-quit', () => {
    stopPythonService();
});
// Prevent multiple instances
const gotTheLock = electron_1.app.requestSingleInstanceLock();
if (!gotTheLock) {
    electron_1.app.quit();
}
