#!/bin/bash
set -e

# Directory definitions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAUNCHER_DIR="$PROJECT_ROOT/launcher"

echo "=========================================="
echo "Building Windows Launcher using Docker..."
echo "=========================================="

# Ensure the image exists (optional, run will pull it, but nice to show explicitly)
# docker pull electronuserland/builder:wine

# Run the build inside the container
# We map:
# - LAUNCHER_DIR to /project
# - Electron caches to accelerate future builds
# - We run npm install to ensure deps are ready (and correct for the container env)
# - We run the build command targeting Windows

docker run --rm \
  --env-file <(env | grep -iE 'DEBUG|NODE_|ELECTRON_|YARN_|NPM_|CI|CIRCLE|TRAVIS_TAG|TRAVIS|TRAVIS_REPO_|TRAVIS_BUILD_|TRAVIS_BRANCH|TRAVIS_PULL_REQUEST_SHA') \
  --env ELECTRON_CACHE="/root/.cache/electron" \
  --env ELECTRON_BUILDER_CACHE="/root/.cache/electron-builder" \
  -v "$LAUNCHER_DIR":/project \
  -v "$HOME/.cache/electron":/root/.cache/electron \
  -v "$HOME/.cache/electron-builder":/root/.cache/electron-builder \
  -w /project \
  electronuserland/builder:wine \
  /bin/bash -c "npm install && npm run build -- --win"

echo "=========================================="
echo "Build complete."
echo "Artifacts should be in launcher/dist-electron/"
echo "=========================================="
