#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
WIN_HOST="${WIN_HOST:-winbox}"  # ssh alias for your Windows box (in ~/.ssh/config)
MOD_URL="${1:-https://www.moddb.com/mods/maximum-security}"

# Remote paths (POSIX-style for scp; PowerShell uses backslashes inside)
REMOTE_ROOT_POSIX="~/Home/Code/MaximumSecurity"
REMOTE_BUILD_POSIX="$REMOTE_ROOT_POSIX/build"
REMOTE_SRC_POSIX="$REMOTE_BUILD_POSIX/src"
REMOTE_IWADS_POSIX="$REMOTE_BUILD_POSIX/iwads"
REMOTE_PS_POSIX="$REMOTE_ROOT_POSIX/run_on_windows.ps1"

# --- sanity ---
command -v ssh >/dev/null || { echo "ssh missing"; exit 1; }
command -v scp >/dev/null || { echo "scp missing"; exit 1; }

echo "==> Resetting Windows build directory…"
ssh "$WIN_HOST" 'pwsh -NoProfile -Command "
  Remove-Item -Path $HOME\Home\Code\MaximumSecurity\build -Recurse -Force -ErrorAction SilentlyContinue;
  New-Item -ItemType Directory -Force -Path $HOME\Home\Code\MaximumSecurity\build\src  | Out-Null;
  New-Item -ItemType Directory -Force -Path $HOME\Home\Code\MaximumSecurity\build\iwads | Out-Null
"'


echo "==> Pushing source (app_src/)…"
# Everything that will be bundled into the exe lives in app_src/
scp -r app_src/* "$WIN_HOST:$REMOTE_SRC_POSIX/"

echo "==> Pushing IWAD assets (assets/* -> build/iwads)…"
# Optional local IWAD(s) you want pre-shipped (e.g. DOOM2.WAD)
if compgen -G "assets/*" >/dev/null; then
  scp assets/* "$WIN_HOST:$REMOTE_IWADS_POSIX/" || true
fi

echo "==> Pushing Windows build script…"
scp windows/run_on_windows.ps1 "$WIN_HOST:$REMOTE_PS_POSIX"

echo "==> Building + launching on Windows (PyInstaller onefile)…"
ssh "$WIN_HOST" 'pwsh -NoProfile -File "$HOME/Home/Code/MaximumSecurity/run_on_windows.ps1" -ModUrl "'"$MOD_URL"'" -Launch'
