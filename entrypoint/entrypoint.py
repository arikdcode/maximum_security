#!/usr/bin/env python3
"""
Dead simple entrypoint for Maximum Security.

This script:
1. Fetches the latest launcher release from GitHub
2. Downloads the launcher executable
3. Runs it

This entrypoint never changes and lives on customer machines.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library is required. Install with: pip install requests")
    sys.exit(1)

# Configuration - these should never change
GITHUB_REPO = "arikdcode/maximum_security_dist"
LAUNCHER_FILENAME = "Maximum.Security.Launcher.exe"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def get_latest_launcher_info():
    """Get the download URL and size for the latest launcher from GitHub releases."""
    print("Checking for latest launcher release...")

    try:
        response = requests.get(GITHUB_API_URL, timeout=30)
        response.raise_for_status()
        release_data = response.json()

        # Find the launcher asset
        for asset in release_data.get("assets", []):
            if asset["name"] == LAUNCHER_FILENAME:
                return {
                    "url": asset["browser_download_url"],
                    "size": asset["size"]
                }

        raise RuntimeError(f"Could not find launcher asset '{LAUNCHER_FILENAME}' in latest release")

    except requests.RequestException as e:
        print(f"Error: Failed to fetch release info: {e}")
        sys.exit(1)

def download_launcher(url, dest_path, expected_size):
    """Download the launcher to the specified path and verify size."""
    print(f"Downloading launcher from {url}...")

    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        downloaded_size = 0
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)

        # Verify size
        if downloaded_size != expected_size:
            print(f"Error: Downloaded file size ({downloaded_size}) doesn't match expected size ({expected_size})")
            os.remove(dest_path)  # Clean up corrupted download
            sys.exit(1)

        print(f"Downloaded {dest_path} ({downloaded_size} bytes)")

    except requests.RequestException as e:
        print(f"Error: Failed to download launcher: {e}")
        sys.exit(1)

def run_launcher(launcher_path):
    """Run the launcher and exit."""
    print(f"Starting launcher: {launcher_path}")

    try:
        if os.name == 'nt':  # Windows
            # Use subprocess to run the launcher
            # We don't wait for it since this entrypoint should exit
            subprocess.Popen([str(launcher_path)], cwd=os.path.dirname(launcher_path))
        else:
            print(f"Warning: Not running launcher on non-Windows platform ({os.name})")
            print("This entrypoint is designed for Windows systems.")
            return

        print("Launcher started successfully!")
    except subprocess.SubprocessError as e:
        print(f"Error: Failed to start launcher: {e}")
        sys.exit(1)

def main():
    """Main entrypoint logic."""
    print("Maximum Security Entrypoint")
    print("=" * 30)

    # Get the download URL and expected size
    launcher_info = get_latest_launcher_info()

    # Create a temporary directory for the launcher
    with tempfile.TemporaryDirectory() as temp_dir:
        launcher_path = Path(temp_dir) / LAUNCHER_FILENAME

        # Download the launcher
        download_launcher(launcher_info["url"], launcher_path, launcher_info["size"])

        # Run the launcher
        run_launcher(launcher_path)

        # Note: The temporary directory will be cleaned up when we exit,
        # but the launcher should be running by then

if __name__ == "__main__":
    main()
