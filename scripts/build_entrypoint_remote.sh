#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
WIN_HOST="${WIN_HOST:-winbox}"  # ssh alias or raw IP for your Windows box

# Remote paths (POSIX-style for scp; PowerShell uses backslashes inside)
REMOTE_ROOT_POSIX="~/Home/Code/MaximumSecurity"
REMOTE_ENTRYPOINT_POSIX="$REMOTE_ROOT_POSIX/entrypoint"

# --- sanity ---
command -v ssh >/dev/null || { echo "ssh missing"; exit 1; }
command -v scp >/dev/null || { echo "scp missing"; exit 1; }

echo "==> Resetting Windows entrypoint directory…"
ssh "$WIN_HOST" 'pwsh -NoProfile -Command "
  Remove-Item -Path $HOME\Home\Code\MaximumSecurity\entrypoint -Recurse -Force -ErrorAction SilentlyContinue;
  New-Item -ItemType Directory -Force -Path $HOME\Home\Code\MaximumSecurity\entrypoint | Out-Null
"'

echo "==> Pushing entrypoint source…"
# Copy the entire entrypoint directory
scp -r entrypoint/* "$WIN_HOST:$REMOTE_ENTRYPOINT_POSIX/"

echo "==> Building MaximumSecurity.exe on Windows…"
ssh "$WIN_HOST" 'pwsh -NoProfile -Command "
  Set-Location $HOME\Home\Code\MaximumSecurity\entrypoint;
  Write-Host \"Building entrypoint exe...\";
  python build_entrypoint_exe.py
"'

echo "==> Build complete!"
echo "MaximumSecurity.exe should now be at: $REMOTE_ROOT_POSIX/entrypoint/dist/MaximumSecurity.exe"
echo ""
echo "To copy it back to Linux for testing (optional):"
echo "  scp '$WIN_HOST:$REMOTE_ROOT_POSIX/entrypoint/dist/MaximumSecurity.exe' ./MaximumSecurity.exe"
