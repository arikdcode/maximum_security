#!/usr/bin/env python3
"""
Deploy script for Maximum Security game builds.

Registers a game build artifact in the manifest.
"""

import argparse
import sys
from pathlib import Path

# Import our utilities
from dist_utils import (
    ensure_dist_repo,
    load_manifest,
    save_manifest,
    compute_sha256,
    compute_size_bytes
)


def find_or_create_game_build(manifest: dict, version: str) -> dict:
    """
    Find an existing game build by version, or create a new one.

    Args:
        manifest (dict): The manifest data.
        version (str): The game version to find or create.

    Returns:
        dict: The game build entry (modified in place in manifest).
    """
    game_builds = manifest["game_builds"]

    # Look for existing build with this version
    for build in game_builds:
        if build.get("version") == version:
            return build

    # Create new build entry
    new_build = {
        "version": version,
        "label": "",
        "channel": "",
        "recommended": False,
        "windows": {
            "url": "",
            "sha256": "",
            "size_bytes": 0
        },
        "changelog": ""
    }

    game_builds.append(new_build)
    return new_build


def main():
    parser = argparse.ArgumentParser(description="Deploy a Maximum Security game build")
    parser.add_argument(
        "--version",
        required=True,
        help="Game version identifier"
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Release channel (e.g. 'stable' or 'experimental')"
    )
    parser.add_argument(
        "--label",
        required=True,
        help="Human-friendly name for this build"
    )
    parser.add_argument(
        "--recommended",
        action="store_true",
        default=False,
        help="Mark this build as recommended"
    )
    parser.add_argument(
        "--artifact-path",
        required=True,
        type=Path,
        help="Path to the game build artifact (zip file)"
    )
    parser.add_argument(
        "--changelog",
        default="",
        help="Changelog or release notes for this version"
    )
    parser.add_argument(
        "--url",
        default="TO_BE_FILLED_WITH_GITHUB_RELEASE_URL",
        help="URL for the artifact (defaults to placeholder)"
    )

    args = parser.parse_args()

    try:
        # Step 1: Ensure dist repo is ready
        print("Ensuring dist repo is ready...")
        ensure_dist_repo()

        # Step 2: Verify artifact exists
        artifact_path = args.artifact_path
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        if not artifact_path.is_file():
            raise ValueError(f"Artifact path is not a file: {artifact_path}")

        print(f"Found artifact: {artifact_path}")

        # Step 3: Compute metadata
        sha256 = compute_sha256(artifact_path)
        size_bytes = compute_size_bytes(artifact_path)
        print(f"SHA256: {sha256}")
        print(f"Size: {size_bytes} bytes")

        # Step 4: Load manifest
        print("Loading manifest...")
        manifest = load_manifest()

        # Step 5: Find or create game build entry
        game_build = find_or_create_game_build(manifest, args.version)
        print(f"Updating game build: {args.version}")

        # Step 6: Update the build entry
        game_build.update({
            "version": args.version,
            "label": args.label,
            "channel": args.channel,
            "recommended": args.recommended,
            "windows": {
                "url": args.url,
                "sha256": sha256,
                "size_bytes": size_bytes
            },
            "changelog": args.changelog
        })

        # Step 7: Save manifest
        save_manifest(manifest)
        print("Manifest updated successfully.")

        print("\nGame deployment completed!")
        print("TODO: Upload game artifact to GitHub Release and update manifest URL.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
