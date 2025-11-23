#!/usr/bin/env python3
"""
Utilities for managing the dist repo and manifest operations.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

# Helper to load .env manually since we can't install dotenv easily
def load_dotenv(path):
    if not path.exists():
        return
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

# Repository root path (resolved relative to this script)
REPO_ROOT = Path(__file__).parent.parent

# Load creds
load_dotenv(REPO_ROOT / "zdump" / ".creds.env")

# Dist repo path

# Dist repo path
DIST_REPO_DIR = REPO_ROOT / ".dist_repo"

# Bootstrap script path
BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts" / "bootstrap_dist_repo.sh"

# Manifest file path
MANIFEST_FILE = DIST_REPO_DIR / "manifest.json"


def ensure_dist_repo():
    """
    Ensure the dist repo exists and is up to date by running the bootstrap script.

    Raises:
        subprocess.CalledProcessError: If the bootstrap script fails.
        FileNotFoundError: If the bootstrap script doesn't exist.
    """
    if not BOOTSTRAP_SCRIPT.exists():
        raise FileNotFoundError(f"Bootstrap script not found: {BOOTSTRAP_SCRIPT}")

    try:
        result = subprocess.run(
            [str(BOOTSTRAP_SCRIPT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        print("Dist repo is ready.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Bootstrap script failed with exit code {e.returncode}", file=sys.stderr)
        print(f"stdout: {e.stdout}", file=sys.stderr)
        print(f"stderr: {e.stderr}", file=sys.stderr)
        raise


def load_manifest() -> dict:
    """
    Load the manifest from .dist_repo/manifest.json.

    Returns:
        dict: The manifest data.

    Raises:
        FileNotFoundError: If the manifest file doesn't exist.
        json.JSONDecodeError: If the manifest is not valid JSON.
    """
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Manifest file not found: {MANIFEST_FILE}")

    with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_manifest(manifest: dict):
    """
    Save the manifest to .dist_repo/manifest.json.

    Args:
        manifest (dict): The manifest data to save.

    Raises:
        OSError: If writing to the file fails.
    """
    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def compute_sha256(path: Path) -> str:
    """
    Compute the SHA256 hash of a file.

    Args:
        path (Path): Path to the file.

    Returns:
        str: The SHA256 hash as a hexadecimal string.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        OSError: If reading the file fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        # Read in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def compute_size_bytes(path: Path) -> int:
    """
    Get the size of a file in bytes.

    Args:
        path (Path): Path to the file.

    Returns:
        int: Size of the file in bytes.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        OSError: If accessing the file fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return path.stat().st_size


def get_current_launcher_revision() -> int:
    """
    Get the current launcher revision number from the manifest.

    Returns:
        int: Current revision number, or 0 if not found or manifest doesn't exist.

    Raises:
        FileNotFoundError: If the manifest file doesn't exist.
        json.JSONDecodeError: If the manifest is not valid JSON.
    """
    try:
        manifest = load_manifest()
        launcher = manifest.get("launcher", {})
        version_str = launcher.get("version", "0")

        # Try to parse as integer
        try:
            return int(version_str)
        except (ValueError, TypeError):
            # If version is not a simple integer, default to 0
            return 0
    except FileNotFoundError:
        # Manifest doesn't exist yet, start at 0
        return 0


def commit_and_push_manifest(commit_message: str):
    """
    Commit and push manifest changes to the dist repo.

    Args:
        commit_message (str): Git commit message.

    Raises:
        subprocess.CalledProcessError: If git commands fail.
        RuntimeError: If not in a git repository or git is not configured.
    """
    if not DIST_REPO_DIR.exists():
        raise FileNotFoundError(f"Dist repo directory not found: {DIST_REPO_DIR}")

    # Check if there are changes to commit
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=DIST_REPO_DIR,
        capture_output=True,
        text=True,
        check=True
    )

    if not result.stdout.strip():
        print("No changes to commit.")
        return

    # Add manifest.json
    subprocess.run(
        ["git", "add", "manifest.json"],
        cwd=DIST_REPO_DIR,
        check=True
    )

    # Commit
    subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=DIST_REPO_DIR,
        check=True
    )

    # Push
    print("Pushing changes to remote...")
    try:
        subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=DIST_REPO_DIR,
            check=True
        )
        print("Changes pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to push changes: {e}", file=sys.stderr)
        print("You may need to pull and merge remote changes first.", file=sys.stderr)
        raise


def get_github_token() -> str:
    """
    Get GitHub token from environment variable.

    Returns:
        str: GitHub token.

    Raises:
        RuntimeError: If GITHUB_TOKEN is not set.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is not set.\n"
            "Please create a GitHub Personal Access Token with 'repo' scope and set it:\n"
            "  export GITHUB_TOKEN=your_token_here"
        )
    return token


def get_github_repo_from_remote() -> str:
    """
    Extract GitHub repository name from dist repo remote URL.

    Returns:
        str: Repository name in format 'owner/repo'.

    Raises:
        RuntimeError: If unable to determine repository name.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=DIST_REPO_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()

        # Handle both SSH and HTTPS URLs
        # SSH: git@github.com:owner/repo.git
        # HTTPS: https://github.com/owner/repo.git
        if url.startswith("git@github.com:"):
            repo = url.replace("git@github.com:", "").replace(".git", "")
            return repo
        elif "github.com" in url:
            # Extract from HTTPS URL
            parts = url.split("github.com/")[1].replace(".git", "").split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"

        raise RuntimeError(f"Unable to parse repository name from URL: {url}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get git remote URL: {e}")


def create_github_release(repo: str, tag: str, token: str) -> dict:
    """
    Create a GitHub release.

    Args:
        repo (str): Repository name in format 'owner/repo'.
        tag (str): Tag name for the release.
        token (str): GitHub personal access token.

    Returns:
        dict: Release data from GitHub API.

    Raises:
        RuntimeError: If requests library is not available.
        requests.RequestException: If API call fails.
    """
    if requests is None:
        raise RuntimeError("requests library is not installed. Install it with: pip install requests")

    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "tag_name": tag,
        "name": f"Launcher {tag}",
        "body": "",
        "draft": False,
        "prerelease": False
    }

    response = requests.post(url, json=data, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def upload_release_asset(repo: str, release_id: int, file_path: Path, token: str) -> dict:
    """
    Upload a file as a release asset.

    Args:
        repo (str): Repository name in format 'owner/repo'.
        release_id (int): GitHub release ID.
        file_path (Path): Path to the file to upload.
        token (str): GitHub personal access token.

    Returns:
        dict: Asset data from GitHub API.

    Raises:
        RuntimeError: If requests library is not available.
        requests.RequestException: If API call fails.
        FileNotFoundError: If file doesn't exist.
    """
    if requests is None:
        raise RuntimeError("requests library is not installed. Install it with: pip install requests")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # GitHub uploads API endpoint
    url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets"

    # Extract filename from path
    filename = file_path.name

    # GitHub requires raw binary data with Content-Type header
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/octet-stream"
    }

    # Read file content as binary
    with open(file_path, 'rb') as f:
        file_content = f.read()

    # GitHub requires filename as query parameter
    params = {'name': filename}

    response = requests.post(url, headers=headers, data=file_content, params=params, timeout=300)
    response.raise_for_status()
    return response.json()
