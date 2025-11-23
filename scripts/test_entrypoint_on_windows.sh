#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
WIN_HOST="${WIN_HOST:-winbox}"  # ssh alias or raw IP for your Windows box

# Remote paths (POSIX-style for scp; PowerShell uses backslashes inside)
REMOTE_ROOT_POSIX="~/Home/Code/MaximumSecurity"
LOCAL_ARTIFACT="entrypoint/dist/MaximumSecurity.exe"
LOCAL_DOOM_WAD="assets/DOOM2.WAD"

# --- sanity ---
if [ ! -f "$LOCAL_ARTIFACT" ]; then
    echo "Error: Local artifact not found at $LOCAL_ARTIFACT"
    echo "Please run scripts/build_entrypoint_docker.sh first."
    exit 1
fi

if [ ! -f "$LOCAL_DOOM_WAD" ]; then
    echo "Error: DOOM2.WAD not found at $LOCAL_DOOM_WAD"
    exit 1
fi

command -v ssh >/dev/null || { echo "ssh missing"; exit 1; }
command -v scp >/dev/null || { echo "scp missing"; exit 1; }

echo "==> Preparing remote test environment..."
ssh "$WIN_HOST" 'pwsh -NoProfile -Command "
  # Clean up previous app directory
  Remove-Item -Path $HOME\Home\Code\MaximumSecurity -Recurse -Force -ErrorAction SilentlyContinue;

  # Create fresh directories
  New-Item -ItemType Directory -Force -Path $HOME\Home\Code\MaximumSecurity | Out-Null;
  New-Item -ItemType Directory -Force -Path $HOME\Home\Code\MaximumSecurity\game | Out-Null;
"'

echo "==> Deploying entrypoint to test machine..."
scp "$LOCAL_ARTIFACT" "$WIN_HOST:$REMOTE_ROOT_POSIX/MaximumSecurity.exe"

echo "==> Deploying DOOM2.WAD..."
scp "$LOCAL_DOOM_WAD" "$WIN_HOST:$REMOTE_ROOT_POSIX/game/DOOM2.WAD"

echo "==> Deployment complete!"
echo "The entrypoint is ready at: $REMOTE_ROOT_POSIX/MaximumSecurity.exe"
echo "DOOM2.WAD is at: $REMOTE_ROOT_POSIX/game/DOOM2.WAD"
echo "You can now test it on the Windows machine."
