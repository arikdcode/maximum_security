#!/usr/bin/env python3
"""
Dead simple entrypoint for Maximum Security.

This script:
1. Fetches the latest launcher release from GitHub
2. Downloads the launcher executable with a GUI progress bar
3. Runs it

This entrypoint never changes and lives on customer machines.
"""

import os
import sys
import subprocess
from pathlib import Path

try:
    import requests
    import tkinter as tk
    from tkinter import ttk
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Install with: pip install requests")
    sys.exit(1)

# Configuration - these should never change
GITHUB_REPO = "arikdcode/maximum_security_dist"
LAUNCHER_FILENAME = "Maximum.Security.Launcher.exe"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

class ProgressWindow:
    """Simple GUI progress window for downloads."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Maximum Security - Updating Launcher")
        self.root.geometry("400x120")
        self.root.resizable(False, False)

        # Center the window
        self.root.eval('tk::PlaceWindow . center')

        # Title label
        title_label = tk.Label(self.root, text="Updating launcher...", font=("Arial", 12, "bold"))
        title_label.pack(pady=(20, 10))

        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=(0, 10))

        # Status label
        self.status_label = tk.Label(self.root, text="Checking for updates...", font=("Arial", 9))
        self.status_label.pack()

        self.root.update()

    def update_progress(self, value, status_text=""):
        """Update progress bar value and status text."""
        self.progress['value'] = value
        if status_text:
            self.status_label.config(text=status_text)
        self.root.update()

    def close(self):
        """Close the progress window."""
        self.root.destroy()

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

def download_launcher(url, dest_path, expected_size, progress_window):
    """Download the launcher to the specified path and verify size."""
    progress_window.update_progress(0, "Connecting to download server...")

    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        downloaded_size = 0
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    # Update progress
                    progress = min(100, (downloaded_size / expected_size) * 100)
                    progress_window.update_progress(progress, f"Downloading... {downloaded_size//1024//1024}MB / {expected_size//1024//1024}MB")

        # Verify size
        if downloaded_size != expected_size:
            progress_window.update_progress(0, "Error: Download verification failed")
            progress_window.root.after(2000, progress_window.close)  # Show error for 2 seconds
            os.remove(dest_path)  # Clean up corrupted download
            sys.exit(1)

        progress_window.update_progress(100, "Download complete!")

    except requests.RequestException as e:
        progress_window.update_progress(0, f"Download failed: {str(e)[:50]}...")
        progress_window.root.after(3000, progress_window.close)
        sys.exit(1)

def run_launcher(launcher_path, progress_window):
    """Run the launcher and exit."""
    progress_window.update_progress(100, "Starting launcher...")

    try:
        if os.name == 'nt':  # Windows
            # Use subprocess to run the launcher from its directory
            # We don't wait for it since this entrypoint should exit
            subprocess.Popen([str(launcher_path)], cwd=os.path.dirname(launcher_path))
            progress_window.update_progress(100, "Launcher started!")
            progress_window.root.after(1000, progress_window.close)  # Close after 1 second
        else:
            progress_window.update_progress(100, "This entrypoint is designed for Windows systems.")
            progress_window.root.after(2000, progress_window.close)
            return

    except subprocess.SubprocessError as e:
        progress_window.update_progress(0, f"Failed to start launcher: {str(e)[:30]}...")
        progress_window.root.after(3000, progress_window.close)
        sys.exit(1)

def get_launcher_dir():
    """Get the directory where the launcher should be stored."""
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        launcher_dir = Path(appdata) / "MaximumSecurity"
    else:
        launcher_dir = Path.home() / ".maximum_security"

    launcher_dir.mkdir(parents=True, exist_ok=True)
    return launcher_dir

def main():
    """Main entrypoint logic."""
    # Create progress window
    progress_window = ProgressWindow()

    try:
        # Get the download URL and expected size
        progress_window.update_progress(0, "Checking for launcher updates...")
        launcher_info = get_latest_launcher_info()

        # Get persistent launcher directory
        launcher_dir = get_launcher_dir()
        launcher_path = launcher_dir / LAUNCHER_FILENAME

        # Download the launcher
        download_launcher(launcher_info["url"], launcher_path, launcher_info["size"], progress_window)

        # Run the launcher
        run_launcher(launcher_path, progress_window)

        # Keep the GUI alive until it closes itself
        progress_window.root.mainloop()

    except Exception as e:
        progress_window.update_progress(0, f"Error: {str(e)[:40]}...")
        progress_window.root.after(4000, progress_window.close)
        progress_window.root.mainloop()
        sys.exit(1)

if __name__ == "__main__":
    main()
