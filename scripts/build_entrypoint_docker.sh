#!/bin/bash
set -e

# Directory definitions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENTRYPOINT_DIR="$PROJECT_ROOT/entrypoint"

echo "=========================================="
echo "Building Windows Entrypoint using Docker..."
echo "=========================================="

cd "$ENTRYPOINT_DIR"

# Debug: show current dir
echo "Working in: $(pwd)"

# Run PyInstaller in Docker
# explicit entrypoint to avoid image default behavior issues
docker run --rm \
  --entrypoint /bin/bash \
  -v "$(pwd):/src/" \
  -w /src \
  cdrx/pyinstaller-windows:python3 \
  -c "pip install -r requirements.txt && pyinstaller --clean --onefile --windowed --name MaximumSecurity entrypoint.py && ls -la dist/"

echo "=========================================="
echo "Build complete."
if [ -f "dist/MaximumSecurity.exe" ]; then
    echo "Artifact found at: entrypoint/dist/MaximumSecurity.exe"
else
    echo "ERROR: Artifact not found!"
    exit 1
fi
echo "=========================================="
