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

// We need to be portable. Everything should be relative to the executable.
// On Windows, process.execPath is the .exe.
// In production (portable), we want a 'game' folder next to the launcher exe.
let ROOT_DIR;
if (isDev) {
  ROOT_DIR = app.getPath('userData');
} else {
  // Electron-builder portable apps set process.env.PORTABLE_EXECUTABLE_DIR
  const LAUNCHER_EXE_DIR = process.env.PORTABLE_EXECUTABLE_DIR || path.dirname(process.execPath);
  ROOT_DIR = LAUNCHER_EXE_DIR;
}

// Base directories
const GAME_BASE_DIR = path.join(ROOT_DIR, 'game');
const GZDOOM_DIR = path.join(GAME_BASE_DIR, 'gzdoom'); // Shared GZDoom installation
const SAVES_DIR = path.join(GAME_BASE_DIR, 'saves');
const CONFIG_PATH = path.join(GAME_BASE_DIR, 'gzdoom.ini');

// Ensure base directories exist
[GAME_BASE_DIR, GZDOOM_DIR, SAVES_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    minWidth: 800,
    minHeight: 600,
    autoHideMenuBar: true, // Hide menu bar (File, Edit, etc.)
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'Maximum Security Launcher',
    icon: path.join(__dirname, 'assets/icon.png'),
  });

  // Specifically remove menu for production
  if (!isDev) {
    mainWindow.removeMenu();
  }

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

// Check if a specific version is installed
ipcMain.handle('check-installed-versions', async () => {
  if (!fs.existsSync(GAME_BASE_DIR)) return [];

  // Look for folders that might correspond to versions
  // We trust folders that have the pk3 file inside
  const versions = [];
  const entries = fs.readdirSync(GAME_BASE_DIR, { withFileTypes: true });

  for (const entry of entries) {
    if (entry.isDirectory() && entry.name !== 'gzdoom' && entry.name !== 'saves') {
      const versionPath = path.join(GAME_BASE_DIR, entry.name);
      const pk3Path = path.join(versionPath, `Maximum_Security_v${entry.name}.pk3`);
      if (fs.existsSync(pk3Path)) {
        versions.push(entry.name);
      }
    }
  }

  return versions;
});

// Check for save files
ipcMain.handle('get-saves', async () => {
  if (!fs.existsSync(SAVES_DIR)) return [];

  const files = fs.readdirSync(SAVES_DIR)
    .filter(f => f.endsWith('.zds'))
    .map(f => {
      const stat = fs.statSync(path.join(SAVES_DIR, f));
      return {
        name: f,
        mtime: stat.mtime.getTime()
      };
    })
    .sort((a, b) => b.mtime - a.mtime); // Newest first

  return files.map(f => f.name);
});

ipcMain.handle('download-game', async (event, url, version) => {
  const win = BrowserWindow.getFocusedWindow();

  // Create version-specific folder: game/0.3b
  const versionDir = path.join(GAME_BASE_DIR, version);
  if (!fs.existsSync(versionDir)) {
    fs.mkdirSync(versionDir, { recursive: true });
  }

  // Check if already installed (skip if pk3 exists)
  const destPath = path.join(versionDir, `Maximum_Security_v${version}.pk3`);
  if (fs.existsSync(destPath)) {
    return { status: 'complete', path: versionDir };
  }

  try {
    // Download PK3
    if (win) win.webContents.send('fromMain', { type: 'status', message: `Downloading game v${version}...` });
    await downloadFile(url, destPath, win);

    // Copy DOOM2.WAD from base game dir if it exists
    // This allows sharing the IWAD across versions
    const baseIwad = path.join(GAME_BASE_DIR, 'DOOM2.WAD');
    if (fs.existsSync(baseIwad)) {
      fs.copyFileSync(baseIwad, path.join(versionDir, 'DOOM2.WAD'));
    }

    return { status: 'complete', path: versionDir };

  } catch (error) {
    console.error("Game download/install failed:", error);
    // Clean up partial download
    if (fs.existsSync(destPath)) fs.unlinkSync(destPath);
    throw error;
  }
});

ipcMain.handle('download-gzdoom', async () => {
  const win = BrowserWindow.getFocusedWindow();

  // Detect Platform
  // Only implementing Windows logic fully as per requirements
  if (process.platform !== 'win32' && !isDev) {
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
    const destZip = path.join(GAME_BASE_DIR, 'gzdoom.zip');
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
  const versionDir = path.join(GAME_BASE_DIR, version);

  // 1. Locate GZDoom (Shared)
  let gzdoomExe = path.join(GZDOOM_DIR, 'gzdoom.exe');
  if (process.platform !== 'win32') {
     // Fallback for linux dev env
     gzdoomExe = 'gzdoom';
  }

  // 2. Locate IWAD
  // Logic: Check version dir first, then base dir
  let iwadPath = path.join(versionDir, 'DOOM2.WAD');

  // Fallback: Check if user put it in base dir but it wasn't copied yet
  if (!fs.existsSync(iwadPath)) {
      const baseIwad = path.join(GAME_BASE_DIR, 'DOOM2.WAD');
      if (fs.existsSync(baseIwad)) {
          fs.copyFileSync(baseIwad, iwadPath); // Lazy copy
      } else {
          throw new Error("MISSING_IWAD");
      }
  }

  // 3. Identify Game PK3
  const pk3Path = path.join(versionDir, `Maximum_Security_v${version}.pk3`);
  if (!fs.existsSync(pk3Path)) {
      throw new Error("MISSING_GAME_FILES");
  }

  // 4. Launch
  const launchArgs = [
    '-iwad', iwadPath,
    '-file', pk3Path,
    '-savedir', SAVES_DIR,
    '-config', CONFIG_PATH
  ];

  if (args.quickStart) {
    launchArgs.push('+map', 'MAP01');
  }

  if (args.saveGame) {
    launchArgs.push('-loadgame', path.join(SAVES_DIR, args.saveGame));
  }

  if (args.difficulty !== undefined) {
    launchArgs.push('+skill', args.difficulty);
  }

  if (args.warp) {
    launchArgs.push('+map', args.warp);
  }

  console.log(`Launching: ${gzdoomExe} ${launchArgs.join(' ')}`);

  const child = spawn(gzdoomExe, launchArgs, { detached: true, stdio: 'ignore', cwd: versionDir });
  child.unref();

  return { status: 'launched' };
});

ipcMain.handle('check-iwad', async () => {
    // Check base dir for DOOM2.WAD
    const baseIwad = path.join(GAME_BASE_DIR, 'DOOM2.WAD');
    return fs.existsSync(baseIwad);
});
