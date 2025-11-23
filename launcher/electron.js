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
  // In portable mode, "MaximumSecurityLauncher.exe" is in a temp dir when running?
  // No, if it's a portable exe from electron-builder, it extracts to temp.
  // BUT we want the data to persist next to the EXE the user downloaded.
  //
  // Electron-builder portable apps set process.env.PORTABLE_EXECUTABLE_DIR
  const LAUNCHER_EXE_DIR = process.env.PORTABLE_EXECUTABLE_DIR || path.dirname(process.execPath);
  // Structure:
  // Root/
  //   MaximumSecurity.exe (Entrypoint)
  //   MaximumSecurityLauncher.exe (Launcher)
  //   game/
  //
  // So ROOT_DIR is the same as the launcher executable directory
  ROOT_DIR = LAUNCHER_EXE_DIR;
}

const GAME_DIR = path.join(ROOT_DIR, 'game');
const BIN_DIR = GAME_DIR; // Flat structure
const GZDOOM_DIR = GAME_DIR; // Flat structure
const IWADS_DIR = GAME_DIR; // Flat structure
const SAVES_DIR = path.join(GAME_DIR, 'saves');
const CONFIG_PATH = path.join(GAME_DIR, 'gzdoom.ini');

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
  // Use a temporary name for the zip
  const destPath = path.join(GAME_DIR, `game-${version}.zip`);
  // Extract directly to GAME_DIR (flattened)
  // We use a marker file to detect version? Or just trust manifest?
  // Let's check if the version folder exists as a marker, or check manifest content?
  // Since the user requested flattening: "all gzdoom files need to be in 'game' in the root of 'game' as does the WAD file"

  // Actually, the user said: "The all gzdoom files need to be in 'game' in the root of 'game' as does the WAD file."
  // But wait, they also said: "game folder has to contain everything together... No separate iwads."
  // This implies GZDoom, IWAD, and Mod files all in ONE folder: `game/`.
  // My previous path setup:
  // GAME_DIR = ROOT/game
  // GZDOOM_DIR = GAME_DIR (merged)
  // IWADS_DIR = GAME_DIR (merged)

  // Let's readjust the constants first.
  // If everything is siblings in `game/`:
  // GZDOOM_DIR should be GAME_DIR
  // IWADS_DIR should be GAME_DIR

  // But wait, GZDoom download logic currently extracts to GZDOOM_DIR.
  // If I set GZDOOM_DIR = GAME_DIR, it extracts there. Perfect.

  // Game download:
  // The zip contains the mod files.
  // If we extract to GAME_DIR, they sit there.

  // Re-reading the instruction carefully:
  // "The all gzdoom files need to be in 'game' in the root of 'game' as does the WAD file. No separate iwads. And the MaximumSecurity mod files also have to be in there... They all have to be siblings"

  // So yes, flat structure in `game/`.

  try {
    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Downloading game...' });
    await downloadFile(url, destPath, win);

    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Extracting game...' });
    const zip = new AdmZip(destPath);

    // Extract all to GAME_DIR
    zip.extractAllTo(GAME_DIR, true);

    fs.unlinkSync(destPath);

    // Create a marker file for the version
    fs.writeFileSync(path.join(GAME_DIR, `version-${version}.txt`), 'installed');

    return { status: 'complete', path: GAME_DIR };

  } catch (error) {
    console.error("Game download/install failed:", error);
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
  // gamePath is just GAME_DIR now
  const gamePath = GAME_DIR;

  // 1. Locate GZDoom
  let gzdoomExe = path.join(GZDOOM_DIR, 'gzdoom.exe');
  if (process.platform !== 'win32') {
     // Fallback for linux dev env
     gzdoomExe = 'gzdoom';
  }

  // 2. Locate IWAD
  // Logic: Check IWADS_DIR (which is GAME_DIR) for *.wad.
  let iwadPath = null;
  const localWads = fs.existsSync(IWADS_DIR) ? fs.readdirSync(IWADS_DIR).filter(f => f.toLowerCase().endsWith('.wad')) : [];

  if (localWads.length > 0) {
    // Sort preference: doom2 > tnt > plutonia > doom
    localWads.sort((a, b) => {
      const score = (name) => {
        const n = name.toLowerCase();
        if (n === 'doom2.wad') return 0;
        if (n === 'tnt.wad') return 1;
        if (n === 'plutonia.wad') return 2;
        if (n === 'doom.wad') return 3;
        return 10;
      };
      return score(a) - score(b);
    });
    iwadPath = path.join(IWADS_DIR, localWads[0]);
  }

  if (!iwadPath) {
    throw new Error("MISSING_IWAD");
  }

  // 3. Identify Game WAD/PK3
  // We need to find the mod files in GAME_DIR
  // BUT exclude the IWAD we just found so we don't double load it (GZDoom might handle it but better safe)
  let gameFiles = [];
  if (fs.existsSync(gamePath)) {
    gameFiles = fs.readdirSync(gamePath)
      .filter(f => f.match(/\.(wad|pk3|pk7)$/i))
      .map(f => path.join(gamePath, f))
      .filter(f => f !== iwadPath); // Exclude the chosen IWAD
  }

  // 4. Launch
  const launchArgs = [
    '-iwad', iwadPath,
    '-savedir', SAVES_DIR,
    '-config', CONFIG_PATH
  ];

  if (gameFiles.length > 0) {
    launchArgs.push('-file', ...gameFiles);
  }

  console.log(`Launching: ${gzdoomExe} ${launchArgs.join(' ')}`);

  const child = spawn(gzdoomExe, launchArgs, { detached: true, stdio: 'ignore' });
  child.unref();

  return { status: 'launched' };
});

ipcMain.handle('check-iwad', async () => {
  if (!fs.existsSync(IWADS_DIR)) return false;
  const wads = fs.readdirSync(IWADS_DIR).filter(f => f.toLowerCase().endsWith('.wad'));
  return wads.length > 0;
});
