const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const https = require('https');
const axios = require('axios');
const AdmZip = require('adm-zip');
const crypto = require('crypto');
const { spawn } = require('child_process');

// Check if we're in development by looking for the dev server
const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';

// Paths
const MANIFEST_URL = "https://raw.githubusercontent.com/arikdcode/maximum_security_dist/refs/heads/master/manifest.json";
const APP_DATA = app.getPath('userData');
const GAME_DIR = path.join(APP_DATA, 'game');
const BIN_DIR = path.join(APP_DATA, 'bin');
const GZDOOM_DIR = path.join(BIN_DIR, 'gzdoom');
const IWADS_DIR = path.join(APP_DATA, 'iwads');

// Ensure directories exist
[GAME_DIR, BIN_DIR, GZDOOM_DIR, IWADS_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

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


// ------------------ HELPER: Download File ------------------
async function downloadFile(url, destPath, win, channelName = 'download-progress') {
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
        type: channelName,
        percent: totalLength ? Math.round((receivedBytes / totalLength) * 100) : 0
      });
    }
  });

  response.data.pipe(writer);

  return new Promise((resolve, reject) => {
    writer.on('finish', resolve);
    writer.on('error', reject);
  });
}

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
    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Downloading game...' });
    await downloadFile(url, destPath, win);

    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Extracting game...' });
    const zip = new AdmZip(destPath);
    zip.extractAllTo(extractPath, true);

    fs.unlinkSync(destPath);
    return { status: 'complete', path: extractPath };

  } catch (error) {
    console.error("Game download/install failed:", error);
    throw error;
  }
});

ipcMain.handle('download-gzdoom', async () => {
  const win = BrowserWindow.getFocusedWindow();

  // Detect Platform
  // Only implementing Windows logic fully as per requirements
  if (process.platform !== 'win32') {
    console.log("GZDoom download only fully implemented for Windows for now.");
    return { status: 'skipped', message: 'Linux GZDoom setup not automated' };
  }

  const gzdoomExe = path.join(GZDOOM_DIR, 'gzdoom.exe');
  if (fs.existsSync(gzdoomExe)) {
    return { status: 'ready', path: gzdoomExe };
  }

  try {
    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Fetching GZDoom release info...' });

    // 1. Get latest GZDoom release
    const releaseUrl = "https://api.github.com/repos/ZDoom/gzdoom/releases/latest";
    const releaseResp = await axios.get(releaseUrl);
    const assets = releaseResp.data.assets || [];

    // Find Windows zip
    const asset = assets.find(a => a.name.toLowerCase().includes('windows') && a.name.toLowerCase().endsWith('.zip'));
    if (!asset) throw new Error("No GZDoom Windows zip found");

    // 2. Download
    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Downloading GZDoom...' });
    const destZip = path.join(BIN_DIR, 'gzdoom.zip');
    await downloadFile(asset.browser_download_url, destZip, win);

    // 3. Extract
    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Extracting GZDoom...' });
    const zip = new AdmZip(destZip);
    zip.extractAllTo(GZDOOM_DIR, true);
    fs.unlinkSync(destZip);

    return { status: 'ready', path: gzdoomExe };

  } catch (error) {
    console.error("GZDoom setup failed:", error);
    throw error;
  }
});

ipcMain.handle('launch-game', async (event, args) => {
  // args: { version: string }
  const version = args.version;
  const gamePath = path.join(GAME_DIR, version);

  // 1. Locate GZDoom
  let gzdoomExe = path.join(GZDOOM_DIR, 'gzdoom.exe');
  if (process.platform !== 'win32') {
     // Fallback for linux dev env
     gzdoomExe = 'gzdoom';
  }

  // 2. Locate IWAD
  // Logic: Check IWADS_DIR for *.wad. If none, download Freedoom (ported from python)
  let iwadPath = null;
  const localWads = fs.readdirSync(IWADS_DIR).filter(f => f.toLowerCase().endsWith('.wad'));
  if (localWads.length > 0) {
    // Sort preference: doom2 > freedoom2 > others
    localWads.sort((a, b) => {
      const score = (name) => {
        const n = name.toLowerCase();
        if (n === 'doom2.wad') return 0;
        if (n === 'freedoom2.wad') return 1;
        return 10;
      };
      return score(a) - score(b);
    });
    iwadPath = path.join(IWADS_DIR, localWads[0]);
  }

  if (!iwadPath) {
    const win = BrowserWindow.getFocusedWindow();
    try {
      if (win) win.webContents.send('fromMain', { type: 'status', message: 'Downloading Freedoom (IWAD)...' });

      // Fetch Freedoom release
      const fdUrl = "https://api.github.com/repos/freedoom/freedoom/releases/latest";
      const fdResp = await axios.get(fdUrl);
      const asset = fdResp.data.assets.find(a => a.name.endsWith('.zip') && a.name.toLowerCase().includes('freedoom'));
      if (!asset) throw new Error("Freedoom zip not found");

      const destZip = path.join(IWADS_DIR, 'freedoom.zip');
      await downloadFile(asset.browser_download_url, destZip, win);

      const zip = new AdmZip(destZip);
      zip.extractAllTo(IWADS_DIR, true); // This might create a subdir
      fs.unlinkSync(destZip);

      // Find wad recursively if needed, but freedoom zip usually has a subdir
      // Simplest: just flatten or find first wad in IWADS_DIR again
      // Re-scan
      const newWads = fs.readdirSync(IWADS_DIR).flatMap(f => {
         const full = path.join(IWADS_DIR, f);
         if (fs.statSync(full).isDirectory()) {
             return fs.readdirSync(full).map(sub => path.join(full, sub));
         }
         return [full];
      }).filter(f => f.toLowerCase().endsWith('.wad'));

      if (newWads.length > 0) iwadPath = newWads.find(w => w.toLowerCase().includes('doom2')) || newWads[0];
    } catch (e) {
      console.error("Freedoom download failed:", e);
      throw e;
    }
  }

  if (!iwadPath) throw new Error("No IWAD found or downloaded.");

  // 3. Identify Game WAD/PK3
  // The game zip extracts to GAME_DIR/version/
  // We need to pass these files to -file
  let gameFiles = [];
  if (fs.existsSync(gamePath)) {
    gameFiles = fs.readdirSync(gamePath)
      .filter(f => f.match(/\.(wad|pk3|pk7)$/i))
      .map(f => path.join(gamePath, f));
  }

  // 4. Launch
  const launchArgs = [
    '-iwad', iwadPath,
    '-savedir', path.join(APP_DATA, 'saves'),
    '-config', path.join(APP_DATA, 'gzdoom.ini')
  ];

  if (gameFiles.length > 0) {
    launchArgs.push('-file', ...gameFiles);
  }

  console.log(`Launching: ${gzdoomExe} ${launchArgs.join(' ')}`);

  const child = spawn(gzdoomExe, launchArgs, { detached: true, stdio: 'ignore' });
  child.unref();

  return { status: 'launched' };
});
