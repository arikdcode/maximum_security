#!/usr/bin/env python3
"""
Utilities for managing the dist repo and manifest operations.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path


# Repository root path (resolved relative to this script)
REPO_ROOT = Path(__file__).parent.parent

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
