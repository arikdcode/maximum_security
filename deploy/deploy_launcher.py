#!/usr/bin/env python3
"""
Deploy script for the Maximum Security launcher.

Builds the launcher using Electron Builder, creates a GitHub release,
uploads the artifact, and updates the manifest with the new revision number.
"""

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
    compute_size_bytes,
    get_current_launcher_revision,
    commit_and_push_manifest,
    get_github_token,
    get_github_repo_from_remote,
    create_github_release,
    upload_release_asset,
)

# Launcher directory and build settings
LAUNCHER_DIR = REPO_ROOT / "launcher"
DOCKER_BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_launcher_docker.sh"
DIST_DIR = LAUNCHER_DIR / "dist-electron"


def find_launcher_exe() -> Path:
    """
    Find the launcher .exe file in the dist directory.

    For portable builds, looks for the main exe file (not in win-unpacked).

    Returns the most recently modified .exe file outside win-unpacked.

    Raises:
        FileNotFoundError: If no .exe files are found.
    """
    if not DIST_DIR.exists():
        raise FileNotFoundError(f"Dist directory not found: {DIST_DIR}")

    # Look for exe files, but exclude those in win-unpacked since we want portable
    exe_files = []
    for exe_path in DIST_DIR.glob("**/*.exe"):
        if "win-unpacked" not in str(exe_path):
            exe_files.append(exe_path)

    if not exe_files:
        raise FileNotFoundError(f"No .exe files found in {DIST_DIR} (excluding win-unpacked)")

    # Return the most recently modified .exe file
    return max(exe_files, key=lambda p: p.stat().st_mtime)


def build_launcher():
    """
    Build the launcher.

    If scripts/build_launcher_docker.sh exists, use it (Docker + Wine).
    Otherwise, fall back to 'npm run build' (local).
    """
    print("Building launcher...")

    if DOCKER_BUILD_SCRIPT.exists():
        print(f"Using Docker build script: {DOCKER_BUILD_SCRIPT}")
        cmd = [str(DOCKER_BUILD_SCRIPT)]
        # The script handles its own CWD/paths
        cwd = REPO_ROOT
    else:
        print("Docker build script not found, falling back to local npm run build...")
        cmd = ["npm", "run", "build"]
        cwd = LAUNCHER_DIR

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        print("Launcher build completed successfully.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed with exit code {e.returncode}", file=sys.stderr)
        print(f"stdout: {e.stdout}", file=sys.stderr)
        print(f"stderr: {e.stderr}", file=sys.stderr)
        raise


def main():
    """Main deployment workflow."""
    try:
        # Step 1: Ensure dist repo is ready
        print("Ensuring dist repo is ready...")
        ensure_dist_repo()

        # Step 2: Get current launcher revision and increment
        current_revision = get_current_launcher_revision()
        new_revision = current_revision + 1
        print(f"Current launcher revision: {current_revision}")
        print(f"New launcher revision: {new_revision}")

        # Step 3: Build the launcher
        build_launcher()

        # Step 4: Find the launcher artifact
        launcher_exe = find_launcher_exe()
        print(f"Found launcher artifact: {launcher_exe}")

        # Step 5: Compute metadata
        print("Computing file metadata...")
        sha256 = compute_sha256(launcher_exe)
        size_bytes = compute_size_bytes(launcher_exe)
        print(f"SHA256: {sha256}")
        print(f"Size: {size_bytes} bytes")

        # Step 6: Get GitHub token and repo info
        print("Preparing GitHub release...")
        token = get_github_token()
        repo = get_github_repo_from_remote()
        print(f"Repository: {repo}")

        # Step 7: Create GitHub release
        tag = str(new_revision)
        print(f"Creating GitHub release with tag: {tag}")
        release = create_github_release(repo, tag, token)
        release_id = release["id"]
        print(f"Release created: {release['html_url']}")

        # Step 8: Upload release asset
        print(f"Uploading {launcher_exe.name} as release asset...")
        asset = upload_release_asset(repo, release_id, launcher_exe, token)
        download_url = asset["browser_download_url"]
        print(f"Asset uploaded: {download_url}")

        # Step 9: Load and update manifest
        print("Updating manifest...")
        manifest = load_manifest()

        # Update launcher section
        manifest["launcher"] = {
            "version": str(new_revision),
            "windows": {
                "url": download_url,
                "sha256": sha256,
                "size_bytes": size_bytes
            },
            "notes": ""
        }

        # Step 10: Save manifest
        save_manifest(manifest)
        print("Manifest updated successfully.")

        # Step 11: Commit and push changes
        commit_message = f"Update launcher to revision {new_revision}"
        commit_and_push_manifest(commit_message)

        print(f"\n✓ Launcher deployment completed successfully!")
        print(f"  Revision: {new_revision}")
        print(f"  Release: {release['html_url']}")
        print(f"  Download: {download_url}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
