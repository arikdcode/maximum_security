#!/usr/bin/env python3
"""
Deploy script for the Maximum Security game assets.

Creates a GitHub release for the game data, uploads the zip,
and updates the manifest with the new version info.
"""

import sys
import argparse
from pathlib import Path

# Import our utilities
from dist_utils import (
    REPO_ROOT,
    ensure_dist_repo,
    load_manifest,
    save_manifest,
    compute_sha256,
    compute_size_bytes,
    commit_and_push_manifest,
    get_github_token,
    get_github_repo_from_remote,
    create_github_release,
    upload_release_asset,
)

ASSETS_DIR = REPO_ROOT / "assets"
GAME_ZIP_NAME = "Maximum_Security_V0.3b.1.zip"
GAME_ZIP_PATH = ASSETS_DIR / GAME_ZIP_NAME

def get_current_game_version(manifest: dict) -> str:
    """Get the current game version from manifest."""
    game_builds = manifest.get("game_builds", [])
    if not game_builds:
        return "0.0.0"
    return game_builds[-1].get("version", "0.0.0")

def main():
    parser = argparse.ArgumentParser(description="Deploy game assets")
    parser.add_argument("--version", required=True, help="Version string (e.g. 0.3.1)")
    parser.add_argument("--label", default="Beta Release", help="Display label")
    parser.add_argument("--notes", default="", help="Release notes")
    args = parser.parse_args()

    try:
        if not GAME_ZIP_PATH.exists():
            raise FileNotFoundError(f"Game zip not found: {GAME_ZIP_PATH}")

        # Step 1: Ensure dist repo is ready
        print("Ensuring dist repo is ready...")
        ensure_dist_repo()

        # Step 2: Compute metadata
        print("Computing file metadata...")
        sha256 = compute_sha256(GAME_ZIP_PATH)
        size_bytes = compute_size_bytes(GAME_ZIP_PATH)
        print(f"File: {GAME_ZIP_NAME}")
        print(f"SHA256: {sha256}")
        print(f"Size: {size_bytes} bytes")

        # Step 3: Get GitHub token and repo info
        print("Preparing GitHub release...")
        token = get_github_token()
        repo = get_github_repo_from_remote()
        print(f"Repository: {repo}")

        # Step 4: Create GitHub release
        tag = f"game-{args.version}"
        print(f"Creating GitHub release with tag: {tag}")

        # We need a custom create_release because the shared one assumes "Launcher {tag}" name
        # and might need adjustment, but let's stick to the shared one or modify it if needed.
        # Actually, dist_utils.create_github_release sets name to f"Launcher {tag}".
        # We should probably update dist_utils or duplicate logic here.
        # For now, I'll duplicate logic to set a correct name.

        import requests
        url = f"https://api.github.com/repos/{repo}/releases"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "tag_name": tag,
            "name": f"Maximum Security Game {args.version}",
            "body": args.notes,
            "draft": False,
            "prerelease": False
        }
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        release = response.json()

        release_id = release["id"]
        print(f"Release created: {release['html_url']}")

        # Step 5: Upload release asset
        print(f"Uploading {GAME_ZIP_NAME}...")
        asset = upload_release_asset(repo, release_id, GAME_ZIP_PATH, token)
        download_url = asset["browser_download_url"]
        print(f"Asset uploaded: {download_url}")

        # Step 6: Update manifest
        print("Updating manifest...")
        manifest = load_manifest()

        if "game_builds" not in manifest:
            manifest["game_builds"] = []

        new_build = {
            "version": args.version,
            "label": args.label,
            "channel": "stable",
            "recommended": True,
            "windows": {
                "url": download_url,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "filename": GAME_ZIP_NAME
            },
            "changelog": args.notes
        }

        # Append or replace if version exists
        existing_idx = next((i for i, b in enumerate(manifest["game_builds"]) if b["version"] == args.version), -1)
        if existing_idx >= 0:
            manifest["game_builds"][existing_idx] = new_build
        else:
            manifest["game_builds"].append(new_build)

        save_manifest(manifest)
        print("Manifest updated successfully.")

        # Step 7: Commit and push
        commit_message = f"Add game build {args.version}"
        commit_and_push_manifest(commit_message)

        print(f"\n✓ Game deployment completed successfully!")
        print(f"  Version: {args.version}")
        print(f"  Download: {download_url}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
