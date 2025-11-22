# Deploy Workflow

This document describes the workflow for deploying launcher and game builds using the two-repository model.

## Repository Model

- **`maximum_security`** (this repo): Private repository containing the source code.
- **`maximum_security_dist`**: Public repository containing distribution metadata and assets.

## Local Setup

1. Set the `DIST_REPO_REMOTE` environment variable to point to your `maximum_security_dist` repository:
   ```bash
   export DIST_REPO_REMOTE=https://github.com/yourusername/maximum_security_dist.git
   ```

2. Bootstrap the dist repository locally:
   ```bash
   ./scripts/bootstrap_dist_repo.sh
   ```
   This clones or updates `./.dist_repo` with the manifest and metadata.

## Deploying a New Launcher Version

When you want to release a new launcher version:

1. Make sure your launcher code is ready and the version is updated in `launcher/package.json`.

2. Run the deploy script:
   ```bash
   python3 scripts/deploy_launcher.py --notes "Fixed bug X and added feature Y"
   ```

   This will:
   - Build the launcher using `npm run build`
   - Find the resulting `.exe` installer
   - Update the manifest with version, hash, and size information
   - Set a placeholder URL for the download

## Deploying a New Game Build

For game builds (until automated):

1. Build your game and create a distribution zip manually.

2. Register the build in the manifest:
   ```bash
   python3 scripts/deploy_game.py \
     --version "1.2.3" \
     --channel "stable" \
     --label "Maximum Security v1.2.3" \
     --recommended \
     --artifact-path "/path/to/game-v1.2.3.zip" \
     --changelog "Added new weapons and improved AI"
   ```

   This will:
   - Verify the artifact exists
   - Compute SHA256 hash and file size
   - Update or create an entry in `game_builds`
   - Set a placeholder URL

## GitHub Integration (Future)

Currently, all URLs in the manifest are set to `"TO_BE_FILLED_WITH_GITHUB_RELEASE_URL"` placeholders.

In a future iteration, the deploy scripts will be enhanced to:
- Create GitHub Releases automatically
- Upload artifacts as release assets
- Update manifest URLs to point to the actual release assets
- Push manifest changes back to the dist repo

## Manifest Structure

See `.dist_repo/MANIFEST_SCHEMA.md` for detailed information about the manifest format.

The manifest serves as the single source of truth for:
- Latest launcher version and download URL
- Available game builds with their metadata
- Integrity verification (SHA256 hashes and file sizes)
