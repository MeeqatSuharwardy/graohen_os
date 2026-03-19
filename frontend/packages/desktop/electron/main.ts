import { app, BrowserWindow, ipcMain } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import fs from 'fs';
import { promisify } from 'util';

const readFile = promisify(fs.readFile);
const writeFile = promisify(fs.writeFile);

let mainWindow: BrowserWindow | null = null;
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

// Load environment variables
let envConfig: Record<string, string> = {};
try {
  const envPath = path.join(app.getPath('userData'), '.env');
  if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf-8');
    envContent.split('\n').forEach(line => {
      const [key, ...valueParts] = line.split('=');
      if (key && valueParts.length) {
        envConfig[key.trim()] = valueParts.join('=').trim();
      }
    });
  }
} catch (e) {
  console.error('Failed to load .env:', e);
}

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

// IPC Handlers
ipcMain.handle('download-bundle', async (event, { device, buildId, apiBase, apiKey, cacheDir }) => {
  return new Promise((resolve, reject) => {
    const downloaderPath = path.join(__dirname, '../../../../backend/downloader.py');
    const pythonPath = process.platform === 'darwin' 
      ? '/usr/bin/python3' 
      : 'python3';

    const downloadProcess = spawn(pythonPath, [
      downloaderPath,
      '--api-base', apiBase,
      '--api-key', apiKey,
      '--cache-dir', cacheDir,
      '--device', device,
      '--build-id', buildId,
      '--format', 'zip'
    ], {
      cwd: path.dirname(downloaderPath),
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    let stdout = '';
    let stderr = '';

    downloadProcess.stdout.on('data', (data: Buffer) => {
      const text = data.toString();
      stdout += text;
      
      // Emit progress updates
      const lines = text.split('\n').filter((l: string) => l.trim());
      lines.forEach((line: string) => {
        if (line.includes('Progress:')) {
          const match = line.match(/(\d+\.\d+)%/);
          if (match) {
            mainWindow?.webContents.send('download-progress', {
              percent: parseFloat(match[1]),
              message: line
            });
          }
        } else if (line.includes('✓') || line.includes('ERROR')) {
          mainWindow?.webContents.send('download-log', line);
        }
      });
    });

    downloadProcess.stderr.on('data', (data: Buffer) => {
      stderr += data.toString();
      const lines = data.toString().split('\n').filter((l: string) => l.trim());
      lines.forEach((line: string) => {
        mainWindow?.webContents.send('download-log', line);
      });
    });

    downloadProcess.on('close', (code: number | null) => {
      if (code === 0) {
        try {
          // Parse JSON result from stdout
          const jsonMatch = stdout.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            const result = JSON.parse(jsonMatch[0]);
            resolve(result);
          } else {
            reject(new Error('No JSON result found'));
          }
        } catch (e) {
          reject(new Error(`Failed to parse result: ${e}`));
        }
      } else {
        reject(new Error(`Downloader exited with code ${code}: ${stderr}`));
      }
    });

    downloadProcess.on('error', (error: Error) => {
      reject(new Error(`Failed to start downloader: ${error.message}`));
    });
  });
});

ipcMain.handle('flash-device', async (event, { bundlePath, deviceSerial, fastbootPath, adbPath, confirm }) => {
  return new Promise((resolve, reject) => {
    const flasherPath = path.join(__dirname, '../../../../backend/flasher.py');
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

    const flashProcess = spawn(pythonPath, args, {
      cwd: path.dirname(flasherPath),
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    let stdout = '';
    let stderr = '';

    flashProcess.stdout.on('data', (data: Buffer) => {
      const text = data.toString();
      stdout += text;
      
      // Parse JSON logs
      const lines = text.split('\n').filter((l: string) => l.trim());
      lines.forEach((line: string) => {
        try {
          const log = JSON.parse(line);
          mainWindow?.webContents.send('flash-log', log);
        } catch (e) {
          // Not JSON, send as plain message
          mainWindow?.webContents.send('flash-log', {
            type: 'info',
            message: line
          });
        }
      });
    });

    flashProcess.stderr.on('data', (data: Buffer) => {
      stderr += data.toString();
      const lines = data.toString().split('\n').filter((l: string) => l.trim());
      lines.forEach((line: string) => {
        mainWindow?.webContents.send('flash-log', {
          type: 'error',
          message: line
        });
      });
    });

    flashProcess.on('close', (code: number | null) => {
      if (code === 0) {
        try {
          const jsonMatch = stdout.match(/\{[\s\S]*"success"[\s\S]*\}/);
          if (jsonMatch) {
            const result = JSON.parse(jsonMatch[0]);
            resolve(result);
          } else {
            resolve({ success: true, message: 'Flash completed' });
          }
        } catch (e) {
          resolve({ success: true, message: 'Flash completed' });
        }
      } else {
        reject(new Error(`Flasher exited with code ${code}: ${stderr}`));
      }
    });

    flashProcess.on('error', (error: Error) => {
      reject(new Error(`Failed to start flasher: ${error.message}`));
    });
  });
});

ipcMain.handle('get-env-config', async () => {
  return envConfig;
});

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
