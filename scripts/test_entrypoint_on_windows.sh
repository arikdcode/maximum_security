#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
WIN_HOST="${WIN_HOST:-winbox}"  # ssh alias or raw IP for your Windows box

# Remote paths (POSIX-style for scp; PowerShell uses backslashes inside)
REMOTE_ROOT_POSIX="~/Home/Code/MaximumSecurity"
REMOTE_APP_DIR_POSIX="$REMOTE_ROOT_POSIX/app"
LOCAL_ARTIFACT="entrypoint/dist/MaximumSecurity.exe"

# --- sanity ---
if [ ! -f "$LOCAL_ARTIFACT" ]; then
    echo "Error: Local artifact not found at $LOCAL_ARTIFACT"
    echo "Please run scripts/build_entrypoint_docker.sh first."
    exit 1
fi

command -v ssh >/dev/null || { echo "ssh missing"; exit 1; }
command -v scp >/dev/null || { echo "scp missing"; exit 1; }

echo "==> Preparing remote test environment..."
ssh "$WIN_HOST" 'pwsh -NoProfile -Command "
  # Clean up previous app directory
  Remove-Item -Path $HOME\Home\Code\MaximumSecurity\app -Recurse -Force -ErrorAction SilentlyContinue;

  # Create fresh app directory
  New-Item -ItemType Directory -Force -Path $HOME\Home\Code\MaximumSecurity\app | Out-Null;
"'

echo "==> Deploying entrypoint to test machine..."
scp "$LOCAL_ARTIFACT" "$WIN_HOST:$REMOTE_APP_DIR_POSIX/MaximumSecurity.exe"

echo "==> Deployment complete!"
echo "The entrypoint is ready to run at: $REMOTE_APP_DIR_POSIX/MaximumSecurity.exe"
echo "You can now test it on the Windows machine."
