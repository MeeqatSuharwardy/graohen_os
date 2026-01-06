"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const child_process_1 = require("child_process");
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const util_1 = require("util");
const readFile = (0, util_1.promisify)(fs_1.default.readFile);
const writeFile = (0, util_1.promisify)(fs_1.default.writeFile);
let mainWindow = null;
const isDev = process.env.NODE_ENV === 'development' || !electron_1.app.isPackaged;
// Load environment variables
let envConfig = {};
try {
    const envPath = path_1.default.join(electron_1.app.getPath('userData'), '.env');
    if (fs_1.default.existsSync(envPath)) {
        const envContent = fs_1.default.readFileSync(envPath, 'utf-8');
        envContent.split('\n').forEach(line => {
            const [key, ...valueParts] = line.split('=');
            if (key && valueParts.length) {
                envConfig[key.trim()] = valueParts.join('=').trim();
            }
        });
    }
}
catch (e) {
    console.error('Failed to load .env:', e);
}
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
// IPC Handlers
electron_1.ipcMain.handle('download-bundle', async (event, { device, buildId, apiBase, apiKey, cacheDir }) => {
    return new Promise((resolve, reject) => {
        const downloaderPath = path_1.default.join(__dirname, '../../../../backend/downloader.py');
        const pythonPath = process.platform === 'darwin'
            ? '/usr/bin/python3'
            : 'python3';
        const downloadProcess = (0, child_process_1.spawn)(pythonPath, [
            downloaderPath,
            '--api-base', apiBase,
            '--api-key', apiKey,
            '--cache-dir', cacheDir,
            '--device', device,
            '--build-id', buildId,
            '--format', 'zip'
        ], {
            cwd: path_1.default.dirname(downloaderPath),
            env: { ...process.env, PYTHONUNBUFFERED: '1' }
        });
        let stdout = '';
        let stderr = '';
        downloadProcess.stdout.on('data', (data) => {
            const text = data.toString();
            stdout += text;
            // Emit progress updates
            const lines = text.split('\n').filter((l) => l.trim());
            lines.forEach((line) => {
                if (line.includes('Progress:')) {
                    const match = line.match(/(\d+\.\d+)%/);
                    if (match) {
                        mainWindow?.webContents.send('download-progress', {
                            percent: parseFloat(match[1]),
                            message: line
                        });
                    }
                }
                else if (line.includes('✓') || line.includes('ERROR')) {
                    mainWindow?.webContents.send('download-log', line);
                }
            });
        });
        downloadProcess.stderr.on('data', (data) => {
            stderr += data.toString();
            const lines = data.toString().split('\n').filter((l) => l.trim());
            lines.forEach((line) => {
                mainWindow?.webContents.send('download-log', line);
            });
        });
        downloadProcess.on('close', (code) => {
            if (code === 0) {
                try {
                    // Parse JSON result from stdout
                    const jsonMatch = stdout.match(/\{[\s\S]*\}/);
                    if (jsonMatch) {
                        const result = JSON.parse(jsonMatch[0]);
                        resolve(result);
                    }
                    else {
                        reject(new Error('No JSON result found'));
                    }
                }
                catch (e) {
                    reject(new Error(`Failed to parse result: ${e}`));
                }
            }
            else {
                reject(new Error(`Downloader exited with code ${code}: ${stderr}`));
            }
        });
        downloadProcess.on('error', (error) => {
            reject(new Error(`Failed to start downloader: ${error.message}`));
        });
    });
});
electron_1.ipcMain.handle('flash-device', async (event, { bundlePath, deviceSerial, fastbootPath, adbPath, confirm }) => {
    return new Promise((resolve, reject) => {
        const flasherPath = path_1.default.join(__dirname, '../../../../backend/flasher.py');
        const pythonPath = process.platform === 'darwin'
            ? '/usr/bin/python3'
            : 'python3';
        const args = [
            flasherPath,
            '--fastboot-path', fastbootPath,
            '--adb-path', adbPath,
            '--bundle-path', bundlePath,
        ];
        if (deviceSerial) {
            args.push('--device-serial', deviceSerial);
        }
        if (confirm) {
            args.push('--confirm');
        }
        const flashProcess = (0, child_process_1.spawn)(pythonPath, args, {
            cwd: path_1.default.dirname(flasherPath),
            env: { ...process.env, PYTHONUNBUFFERED: '1' }
        });
        let stdout = '';
        let stderr = '';
        flashProcess.stdout.on('data', (data) => {
            const text = data.toString();
            stdout += text;
            // Parse JSON logs
            const lines = text.split('\n').filter((l) => l.trim());
            lines.forEach((line) => {
                try {
                    const log = JSON.parse(line);
                    mainWindow?.webContents.send('flash-log', log);
                }
                catch (e) {
                    // Not JSON, send as plain message
                    mainWindow?.webContents.send('flash-log', {
                        type: 'info',
                        message: line
                    });
                }
            });
        });
        flashProcess.stderr.on('data', (data) => {
            stderr += data.toString();
            const lines = data.toString().split('\n').filter((l) => l.trim());
            lines.forEach((line) => {
                mainWindow?.webContents.send('flash-log', {
                    type: 'error',
                    message: line
                });
            });
        });
        flashProcess.on('close', (code) => {
            if (code === 0) {
                try {
                    const jsonMatch = stdout.match(/\{[\s\S]*"success"[\s\S]*\}/);
                    if (jsonMatch) {
                        const result = JSON.parse(jsonMatch[0]);
                        resolve(result);
                    }
                    else {
                        resolve({ success: true, message: 'Flash completed' });
                    }
                }
                catch (e) {
                    resolve({ success: true, message: 'Flash completed' });
                }
            }
            else {
                reject(new Error(`Flasher exited with code ${code}: ${stderr}`));
            }
        });
        flashProcess.on('error', (error) => {
            reject(new Error(`Failed to start flasher: ${error.message}`));
        });
    });
});
electron_1.ipcMain.handle('get-env-config', async () => {
    return envConfig;
});
electron_1.app.whenReady().then(() => {
    createWindow();
    electron_1.app.on('activate', () => {
        if (electron_1.BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});
electron_1.app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        electron_1.app.quit();
    }
});
