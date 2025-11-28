#!/usr/bin/env python3
"""
Dead simple entrypoint for Maximum Security.

This script:
1. Fetches the latest launcher release from GitHub
2. Checks if the installed launcher is up to date
3. Downloads the new launcher executable if needed (with GUI progress)
4. Runs the launcher
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import hashlib
import logging
import traceback

try:
    import requests
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Install with: pip install requests")
    sys.exit(1)

# Configuration
GITHUB_REPO = "arikdcode/maximum_security_dist"
LAUNCHER_FILENAME = "MaximumSecurityLauncher.exe"
VERSION_FILENAME = "launcher_version.json"
GITHUB_LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

class ProgressWindow:
    """Simple GUI progress window for downloads."""

    def __init__(self, title="Updating Launcher"):
        self.root = tk.Tk()
        self.root.title(f"Maximum Security - {title}")
        self.root.geometry("400x120")
        self.root.resizable(False, False)

        # Center the window
        self.root.eval('tk::PlaceWindow . center')

        # Title label
        title_label = tk.Label(self.root, text=title, font=("Arial", 12, "bold"))
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
    """Get the download URL, size, and tag_name for the latest launcher from GitHub releases."""
    try:
        # First try the 'latest' endpoint
        logging.info(f"Checking latest release at: {GITHUB_LATEST_RELEASE_URL}")
        response = requests.get(GITHUB_LATEST_RELEASE_URL, timeout=30)
        response.raise_for_status()
        latest_release = response.json()

        # Check if the launcher is in the latest release
        info = extract_launcher_info(latest_release)
        if info:
            logging.info(f"Found launcher in latest release: {latest_release.get('tag_name')}")
            return info

        logging.info("Launcher not found in latest release (probably a game asset release). Checking recent releases...")

        # If not, fetch recent releases list
        response = requests.get(GITHUB_RELEASES_URL, params={"per_page": 5}, timeout=30)
        response.raise_for_status()
        releases = response.json()

        for release in releases:
            info = extract_launcher_info(release)
            if info:
                logging.info(f"Found launcher in release: {release.get('tag_name')}")
                return info

        raise RuntimeError(f"Could not find launcher asset '{LAUNCHER_FILENAME}' in any recent releases")

    except requests.RequestException as e:
        # If we can't reach GitHub, we might still want to run the local version if it exists
        logging.warning(f"Failed to fetch release info: {e}")
        print(f"Warning: Failed to fetch release info: {e}")
        return None

def extract_launcher_info(release_data):
    """Extract launcher info from a release object if present."""
    tag_name = release_data.get("tag_name", "0")

    for asset in release_data.get("assets", []):
        if asset["name"] == LAUNCHER_FILENAME:
            return {
                "url": asset["browser_download_url"],
                "size": asset["size"],
                "tag_name": tag_name
            }
    return None

def get_launcher_dir():
    """Get the directory where the launcher should be stored."""
    # Ensure we use a persistent directory relative to the executable if possible,
    # or fallback to APPDATA if we are running from a temp location (e.g. onefile)
    # But the user requested "./app" behavior relative to where the exe is run.

    # If running as a PyInstaller bundle
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent

    # The user said: "install the launcher and the version file directly to the app root"
    # So we return the base_path directly.

    return base_path

def setup_logging(base_path):
    """Setup file and console logging."""
    log_file = base_path / "debug.log"

    # Configure logging to file
    logging.basicConfig(
        filename=str(log_file),
        filemode='w', # Overwrite each run to keep it clean, or 'a' to append
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Also log to stderr for console visibility
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.info("Entrypoint started")
    logging.info(f"Log file: {log_file}")
    logging.info(f"Python version: {sys.version}")
    logging.info(f"Executable: {sys.executable}")

def load_local_version(version_file):
    """Load the locally installed version info."""
    if not version_file.exists():
        return None
    try:
        with open(version_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def save_local_version(version_file, info):
    """Save the version info to disk."""
    try:
        with open(version_file, 'w') as f:
            json.dump(info, f)
    except Exception as e:
        print(f"Failed to save version info: {e}")

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
            progress_window.root.after(2000, progress_window.close)
            os.remove(dest_path)
            sys.exit(1)

        progress_window.update_progress(100, "Download complete!")

    except requests.RequestException as e:
        progress_window.update_progress(0, f"Download failed: {str(e)[:50]}...")
        progress_window.root.after(3000, progress_window.close)
        sys.exit(1)

def run_launcher(launcher_path):
    """Run the launcher and exit."""
    try:
        if os.name == 'nt':  # Windows
            # Use subprocess to run the launcher from its directory
            subprocess.Popen([str(launcher_path)], cwd=os.path.dirname(launcher_path))
        else:
            # Fallback for testing on Linux
            subprocess.Popen([str(launcher_path)], cwd=os.path.dirname(launcher_path))
    except subprocess.SubprocessError as e:
        print(f"Failed to start launcher: {e}")
        sys.exit(1)

def main():
    """Main entrypoint logic."""
    try:
        launcher_dir = get_launcher_dir()
        setup_logging(launcher_dir)

        launcher_path = launcher_dir / LAUNCHER_FILENAME
        version_path = launcher_dir / VERSION_FILENAME

        logging.info(f"Launcher directory: {launcher_dir}")
        logging.info(f"Launcher path: {launcher_path}")

        # 1. Check for updates
        logging.info("Checking for updates...")
        latest_info = get_latest_launcher_info()
        local_info = load_local_version(version_path)

        needs_update = False

        if latest_info:
            logging.info(f"Latest version info: {latest_info.get('tag_name')}")
            if not launcher_path.exists():
                needs_update = True
                logging.info("Launcher not found locally. Downloading...")
                print("Launcher not found locally. Downloading...")
            elif not local_info:
                needs_update = True
                logging.info("Local version info missing. Downloading...")
                print("Local version info missing. Downloading...")
            elif local_info.get("tag_name") != latest_info["tag_name"]:
                needs_update = True
                logging.info(f"New version available ({latest_info['tag_name']}). Updating...")
                print(f"New version available ({latest_info['tag_name']}). Updating...")
            else:
                # Tag matches, check if file size matches (sanity check)
                try:
                    current_size = launcher_path.stat().st_size
                    if current_size != latest_info["size"]:
                        needs_update = True
                        logging.info(f"File size mismatch (local: {current_size}, remote: {latest_info['size']}). Repairing...")
                        print("File size mismatch. Repairing...")
                    else:
                        logging.info("Launcher is up to date.")
                except OSError as e:
                    needs_update = True
                    logging.error(f"Error checking file size: {e}")
        else:
            # Offline or GitHub API failure
            logging.warning("Could not fetch latest info (offline or API error).")
            if launcher_path.exists():
                logging.info("Launching local version...")
                print("Could not check for updates. Launching local version...")
            else:
                # No local version and no internet
                # Create a simple error window since we can't proceed
                logging.critical("Offline and no local launcher found. Cannot proceed.")
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Error", "Could not connect to update server and no local launcher found.\nCheck your internet connection.")
                sys.exit(1)

        # 2. Update if needed
        if needs_update and latest_info:
            logging.info("Starting update process...")
            progress_window = ProgressWindow()
            try:
                download_launcher(latest_info["url"], launcher_path, latest_info["size"], progress_window)
                save_local_version(version_path, latest_info)
                logging.info("Update complete.")
                progress_window.root.after(1000, progress_window.close)
                progress_window.root.mainloop()
            except Exception as e:
                logging.error(f"Update failed: {e}", exc_info=True)
                print(f"Update failed: {e}")
                # If update failed but we have a local file, try to run it?
                # Or just crash. Let's exit to be safe.
                messagebox.showerror("Update Failed", f"Failed to update launcher:\n{e}")
                sys.exit(1)

        # 3. Run launcher
        if launcher_path.exists():
            logging.info(f"Running launcher: {launcher_path}")
            run_launcher(launcher_path)
        else:
            logging.error("Launcher not found and update failed.")
            print("Error: Launcher not found and update failed.")
            sys.exit(1)

    except Exception as e:
        # Catch-all for any unhandled exceptions
        error_msg = f"An unexpected error occurred:\n{e}\n\nSee debug.log for details."
        print(error_msg)

        # Try to log it if logging is set up
        try:
            logging.critical("Unhandled exception", exc_info=True)
        except:
            pass

        # Try to show a GUI error
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", error_msg)
        except:
            pass

        sys.exit(1)

if __name__ == "__main__":
    main()
