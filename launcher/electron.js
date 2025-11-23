const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const https = require('https');
const axios = require('axios'); // You'll need to install axios
const AdmZip = require('adm-zip'); // You'll need to install adm-zip
const crypto = require('crypto');
const { spawn } = require('child_process');

// Check if we're in development by looking for the dev server
const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';

// Paths
const MANIFEST_URL = "https://raw.githubusercontent.com/arikdcode/maximum_security_dist/main/manifest.json";
const APP_DATA = app.getPath('userData');
const GAME_DIR = path.join(APP_DATA, 'game');
const BIN_DIR = path.join(APP_DATA, 'bin');

// Ensure directories exist
if (!fs.existsSync(GAME_DIR)) fs.mkdirSync(GAME_DIR, { recursive: true });
if (!fs.existsSync(BIN_DIR)) fs.mkdirSync(BIN_DIR, { recursive: true });

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'Maximum Security Launcher',
    icon: path.join(__dirname, 'assets/icon.png'),
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));
  }
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});


// ------------------ IPC HANDLERS ------------------

ipcMain.handle('fetch-manifest', async () => {
  try {
    const response = await axios.get(MANIFEST_URL);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch manifest:", error);
    throw error;
  }
});

ipcMain.handle('download-game', async (event, url, version) => {
  const win = BrowserWindow.getFocusedWindow();
  const destPath = path.join(GAME_DIR, `game-${version}.zip`);
  const extractPath = path.join(GAME_DIR, version);

  // If already installed, return true
  if (fs.existsSync(extractPath)) {
    return { status: 'installed', path: extractPath };
  }

  try {
    // Download
    const writer = fs.createWriteStream(destPath);
    const response = await axios({
      url,
      method: 'GET',
      responseType: 'stream'
    });

    const totalLength = parseInt(response.headers['content-length'], 10);
    let receivedBytes = 0;

    response.data.on('data', (chunk) => {
      receivedBytes += chunk.length;
      if (win) {
        win.webContents.send('fromMain', {
          type: 'download-progress',
          percent: Math.round((receivedBytes / totalLength) * 100)
        });
      }
    });

    response.data.pipe(writer);

    return new Promise((resolve, reject) => {
      writer.on('finish', async () => {
        // Extract
        if (win) win.webContents.send('fromMain', { type: 'status', message: 'Extracting...' });

        try {
          const zip = new AdmZip(destPath);
          zip.extractAllTo(extractPath, true);

          // Cleanup zip
          fs.unlinkSync(destPath);

          resolve({ status: 'complete', path: extractPath });
        } catch (e) {
          reject(e);
        }
      });
      writer.on('error', reject);
    });

  } catch (error) {
    console.error("Download failed:", error);
    throw error;
  }
});

ipcMain.handle('download-gzdoom', async () => {
  // Placeholder for GZDoom logic - likely similar to game download
  // Checks platform (win32/linux)
  // Downloads from GZDoom github or zdoom.org
  // Extracts to BIN_DIR
  return { status: 'skipped', message: 'Not implemented yet' };
});

ipcMain.handle('launch-game', async (event, args) => {
  // Placeholder for launch logic
  // Would invoke GZDoom exe from BIN_DIR with args pointing to IWAD/MOD in GAME_DIR
  return { status: 'launched' };
});
