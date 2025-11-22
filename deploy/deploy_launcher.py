#!/usr/bin/env python3
"""
Deploy script for the Maximum Security launcher.

Builds the launcher using Electron Builder and updates the manifest with the new version.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Import our utilities
from dist_utils import (
    REPO_ROOT,
    ensure_dist_repo,
    load_manifest,
    save_manifest,
    compute_sha256,
    compute_size_bytes
)

# Launcher directory and build settings
LAUNCHER_DIR = REPO_ROOT / "launcher"
LAUNCHER_PACKAGE_JSON = LAUNCHER_DIR / "package.json"
BUILD_COMMAND = ["npm", "run", "build"]
DIST_DIR = LAUNCHER_DIR / "dist-electron"


def get_launcher_version() -> str:
    """Get the launcher version from package.json."""
    if not LAUNCHER_PACKAGE_JSON.exists():
        raise FileNotFoundError(f"Launcher package.json not found: {LAUNCHER_PACKAGE_JSON}")

    with open(LAUNCHER_PACKAGE_JSON, 'r', encoding='utf-8') as f:
        package_data = json.load(f)

    return package_data.get('version', '0.0.0')


def find_launcher_exe() -> Path:
    """
    Find the launcher .exe file in the dist directory.

    Returns the most recently modified .exe file.

    Raises:
        FileNotFoundError: If no .exe files are found.
    """
    if not DIST_DIR.exists():
        raise FileNotFoundError(f"Dist directory not found: {DIST_DIR}")

    exe_files = list(DIST_DIR.glob("**/*.exe"))

    if not exe_files:
        raise FileNotFoundError(f"No .exe files found in {DIST_DIR}")

    # Return the most recently modified .exe file
    return max(exe_files, key=lambda p: p.stat().st_mtime)


def build_launcher():
    """Build the launcher using npm run build."""
    print("Building launcher...")

    try:
        result = subprocess.run(
            BUILD_COMMAND,
            cwd=LAUNCHER_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        print("Launcher build completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed with exit code {e.returncode}", file=sys.stderr)
        print(f"stdout: {e.stdout}", file=sys.stderr)
        print(f"stderr: {e.stderr}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description="Deploy the Maximum Security launcher")
    parser.add_argument(
        "--notes",
        default="",
        help="Release notes for this launcher version"
    )

    args = parser.parse_args()

    try:
        # Step 1: Ensure dist repo is ready
        print("Ensuring dist repo is ready...")
        ensure_dist_repo()

        # Step 2: Build the launcher
        build_launcher()

        # Step 3: Find the launcher artifact
        launcher_exe = find_launcher_exe()
        print(f"Found launcher artifact: {launcher_exe}")

        # Step 4: Get launcher version
        version = get_launcher_version()
        print(f"Launcher version: {version}")

        # Step 5: Compute metadata
        sha256 = compute_sha256(launcher_exe)
        size_bytes = compute_size_bytes(launcher_exe)
        print(f"SHA256: {sha256}")
        print(f"Size: {size_bytes} bytes")

        # Step 6: Load and update manifest
        print("Updating manifest...")
        manifest = load_manifest()

        # Update launcher section
        manifest["launcher"] = {
            "version": version,
            "windows": {
                "url": "TO_BE_FILLED_WITH_GITHUB_RELEASE_URL",
                "sha256": sha256,
                "size_bytes": size_bytes
            },
            "notes": args.notes
        }

        # Step 7: Save manifest
        save_manifest(manifest)
        print("Manifest updated successfully.")

        print("\nLauncher deployment completed!")
        print("TODO: Upload launcher artifact to GitHub Release and update manifest URL.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
