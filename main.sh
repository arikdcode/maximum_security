#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
  echo "Setting up virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U requests beautifulsoup4

python3 main.py --mod-url "https://www.moddb.com/mods/maximum-security"

pip install -U pyinstaller
pyinstaller --noconsole --onefile --name MaxSecBootstrap main.py
