import { app, BrowserWindow, ipcMain, protocol, shell } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import fs from 'fs';

let mainWindow: BrowserWindow | null = null;
let pythonService: ChildProcess | null = null;
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0a0a0a',
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5174');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Register custom protocol handler
app.setAsDefaultProtocolClient('flashdash');

// Handle protocol URLs
app.on('open-url', (event, url) => {
  event.preventDefault();
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  } else {
    createWindow();
  }
});

// Windows/Linux protocol handling
app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

function startPythonService(): Promise<boolean> {
  return new Promise((resolve) => {
    const backendPath = path.join(__dirname, '../../../../backend/py-service');
    const pythonPath = isDev
      ? path.join(__dirname, '../../../../backend/.venv/bin/python')
      : 'python3';

    if (!fs.existsSync(backendPath)) {
      console.error('Backend path not found:', backendPath);
      resolve(false);
      return;
    }

    pythonService = spawn(pythonPath, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '17890'], {
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
ipcMain.handle('start-service', async () => {
  if (pythonService) {
    return { success: true, message: 'Service already running' };
  }
  const success = await startPythonService();
  return { success, message: success ? 'Service started' : 'Failed to start service' };
});

ipcMain.handle('stop-service', () => {
  stopPythonService();
  return { success: true, message: 'Service stopped' };
});

ipcMain.handle('get-service-status', async () => {
  if (!pythonService) {
    return { running: false };
  }
  // Check if service is responding
  try {
    const response = await fetch('http://127.0.0.1:17890/health');
    return { running: response.ok };
  } catch {
    return { running: false };
  }
});

ipcMain.handle('open-folder-picker', async () => {
  const { dialog } = await import('electron');
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory'],
  });
  return result.canceled ? null : result.filePaths[0];
});

app.whenReady().then(() => {
  createWindow();
  // Auto-start Python service in production
  if (!isDev) {
    startPythonService();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopPythonService();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopPythonService();
});

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
}

