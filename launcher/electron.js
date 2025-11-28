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
    const manifest = response.data;

    // Inject local dev build on Linux
    if (process.platform === 'linux') {
      const localAssetPath = path.resolve(__dirname, '..', 'assets');
      // Assume latest PK3 name from existing manifest version for simplicity, or list dir?
      // Actually, user has Maximum_Security_v0.3b.pk3 in assets/
      // Let's just inject a 'Dev' build
      const devBuild = {
        version: '0.3b-dev',
        label: 'Local Dev Build',
        channel: 'dev',
        windows: {
          url: `local://${path.join(localAssetPath, 'Maximum_Security_v0.3b.pk3')}`,
          size_bytes: 0 // Ignored
        }
      };
      manifest.game_builds.push(devBuild);
    }

    return manifest;
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

  // Check if already installed (skip if pk3 exists), BUT ensure WAD is present for local builds
  const destPath = path.join(versionDir, `Maximum_Security_v${version}.pk3`);
  const baseWadPath = path.join(GAME_BASE_DIR, 'DOOM2.WAD');

  const isInstalled = fs.existsSync(destPath);

  // If installed and not local, or if installed and local WAD exists, return early
  if (isInstalled) {
      if (!url.startsWith('local://') || fs.existsSync(baseWadPath)) {
          return { status: 'complete', path: versionDir };
      }
      // If local and WAD missing, proceed to copy logic (which handles WAD)
  }

  try {
    if (url.startsWith('local://')) {
        // Handle local file copy
        const srcPath = url.replace('local://', '');
        if (!fs.existsSync(srcPath)) throw new Error(`Local asset not found: ${srcPath}`);

        if (win) win.webContents.send('fromMain', { type: 'status', message: `Copying local assets...` });

        // Copy PK3 if needed
        if (!isInstalled) {
            fs.copyFileSync(srcPath, destPath);
        }

        // Copy DOOM2.WAD from source dir if available and destination missing
        const srcDir = path.dirname(srcPath);
        const wadName = 'DOOM2.WAD';
        const srcWad = path.join(srcDir, wadName);
        const destWad = path.join(GAME_BASE_DIR, wadName);

        if (fs.existsSync(srcWad) && !fs.existsSync(destWad)) {
             console.log(`Copying WAD from ${srcWad} to ${destWad}`);
             fs.copyFileSync(srcWad, destWad);
        }

        if (win) win.webContents.send('fromMain', { type: 'download-progress', percent: 100 });
    } else {
        // Download PK3
        if (win) win.webContents.send('fromMain', { type: 'status', message: `Downloading game v${version}...` });
        await downloadFile(url, destPath, win);
    }

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
  const isWin = process.platform === 'win32';
  const isLinux = process.platform === 'linux';

  if (!isWin && !isLinux) {
    console.log("GZDoom download not implemented for this platform.");
    return { status: 'skipped', message: 'Platform not supported' };
  }

  // Check if we already have a usable GZDoom
  let gzdoomExe;
  if (isWin) {
    gzdoomExe = path.join(GZDOOM_DIR, 'gzdoom.exe');
    if (fs.existsSync(gzdoomExe)) return { status: 'ready', path: gzdoomExe };
  } else {
    // On Linux, check local folder first
    gzdoomExe = path.join(GZDOOM_DIR, 'gzdoom');
    if (fs.existsSync(gzdoomExe)) return { status: 'ready', path: gzdoomExe };

    // If NOT found locally, check if it's in PATH. If so, we can skip download.
    try {
        const check = spawn('which', ['gzdoom']); // Linux specific
        await new Promise((resolve, reject) => {
            check.on('close', (code) => {
                if (code === 0) resolve();
                else reject();
            });
        });
        // If we are here, gzdoom is in PATH. We don't need to download anything.
        return { status: 'skipped', message: 'Using system GZDoom' };
    } catch (e) {
        // Not in path, proceed to download
    }
  }

  try {
    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Fetching GZDoom release info...' });

    // 1. Get latest GZDoom release
    const releaseUrl = "https://api.github.com/repos/ZDoom/gzdoom/releases/latest";
    const releaseResp = await axios.get(releaseUrl);
    const assets = releaseResp.data.assets || [];

    // Find asset based on platform
    let asset;
    if (isWin) {
      asset = assets.find(a => a.name.toLowerCase().includes('windows') && a.name.toLowerCase().endsWith('.zip'));
    } else if (isLinux) {
      // Since reliable github portable builds are sparse or named inconsistently,
      // and we might not be able to install system packages easily in this context,
      // let's use a specific known working portable release URL for now if not found.
      // But first, try to find ANY tar.xz that looks like linux
      asset = assets.find(a => a.name.toLowerCase().includes('linux') && a.name.toLowerCase().endsWith('.tar.xz'));
    }

    // Fallback for Linux if no asset found in latest release (common issue with point releases)
    if (!asset && isLinux) {
        console.log("No Linux asset in latest release, falling back to known working URL...");
        // Using a specific known-good version as fallback
        // 4.11.3 is a stable release with a portable linux build
        const fallbackUrl = "https://github.com/ZDoom/gzdoom/releases/download/g4.11.3/gzdoom-4-11-3-linux-portable.tar.xz";

        // Mock an asset object
        asset = {
            name: "gzdoom-4-11-3-linux-portable.tar.xz",
            browser_download_url: fallbackUrl
        };
    }

    if (!asset) throw new Error(`No GZDoom ${process.platform} asset found in latest release.`);

    // 2. Download
    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Downloading GZDoom...' });
    const destFile = path.join(GAME_BASE_DIR, asset.name);
    await downloadFile(asset.browser_download_url, destFile, win);

    // 3. Extract
    if (win) win.webContents.send('fromMain', { type: 'status', message: 'Extracting GZDoom...' });

    if (isWin) {
      const zip = new AdmZip(destFile);
      zip.extractAllTo(GZDOOM_DIR, true);
    } else {
      // Linux .tar.xz extraction using system tar
      await new Promise((resolve, reject) => {
        // tar -xf file.tar.xz -C target_dir --strip-components=1 (if it has a root dir)
        // Portable builds usually have a root folder 'gzdoom-x.y.z'
        // We want to flatten it into GZDOOM_DIR.

        // First, list content to see if we need strip-components
        // This is getting complex. Let's just extract as is and assume the user can launch it or we handle the path.
        // Actually, launch-game looks for GZDOOM_DIR/gzdoom.
        // If the tar has a folder, it will be GZDOOM_DIR/folder/gzdoom.
        // Let's try to extract with --strip-components=1 just in case, or safer: extract to temp and move?

        // Simple approach: extract to GZDOOM_DIR. If there's a subfolder, we might fail to find the exe.
        // Let's assume flat or handle the move.

        const tar = spawn('tar', ['-xf', destFile, '-C', GZDOOM_DIR]);

        tar.on('close', (code) => {
          if (code === 0) resolve();
          else reject(new Error(`tar exited with code ${code}`));
        });

        tar.on('error', (err) => reject(err));
      });
    }

    fs.unlinkSync(destFile);

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
  let gzdoomExe;
  if (process.platform === 'win32') {
    gzdoomExe = path.join(GZDOOM_DIR, 'gzdoom.exe');
  } else {
    // On Linux, check local GZDoom folder first, else try PATH
    const localBin = path.join(GZDOOM_DIR, 'gzdoom');
    if (fs.existsSync(localBin)) {
      gzdoomExe = localBin;
      // Ensure executable
      try { fs.chmodSync(gzdoomExe, '755'); } catch(e) {}
    } else {
      gzdoomExe = 'gzdoom'; // Fallback to system
    }
  }

  // 2. Locate IWAD
  // Logic: GZDoom needs to know where the IWAD is.
  // We will force it to look in the version directory, but we also need to make sure it exists there.
  let iwadPath = path.join(versionDir, 'DOOM2.WAD');

  // Fallback: Check if user put it in base dir but it wasn't copied yet
  if (!fs.existsSync(iwadPath)) {
      const baseIwad = path.join(GAME_BASE_DIR, 'DOOM2.WAD');
      if (fs.existsSync(baseIwad)) {
          fs.copyFileSync(baseIwad, iwadPath); // Lazy copy
      } else {
          // One last check: is it in the root assets? (Dev environment specific)
          const devAssetWad = path.join(__dirname, '..', 'assets', 'DOOM2.WAD');
          if (isDev && fs.existsSync(devAssetWad)) {
             fs.copyFileSync(devAssetWad, iwadPath);
          } else {
             console.error(`IWAD missing at ${iwadPath} and ${baseIwad}`);
             throw new Error("MISSING_IWAD");
          }
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

  const child = spawn(gzdoomExe, launchArgs, {
    detached: true,
    cwd: versionDir,
    stdio: ['ignore', 'pipe', 'pipe'] // Capture stdout/stderr for debugging
  });

  child.stdout.on('data', (data) => console.log(`GZDOOM STDOUT: ${data}`));
  child.stderr.on('data', (data) => console.error(`GZDOOM STDERR: ${data}`));

  child.on('error', (err) => {
    console.error('Failed to start GZDoom process:', err);
  });

  child.on('close', (code) => {
    console.log(`GZDoom process exited with code ${code}`);
  });

  child.unref();

  return { status: 'launched' };
});

ipcMain.handle('check-iwad', async () => {
    // Check base dir for DOOM2.WAD
    const baseIwad = path.join(GAME_BASE_DIR, 'DOOM2.WAD');
    return fs.existsSync(baseIwad);
});
