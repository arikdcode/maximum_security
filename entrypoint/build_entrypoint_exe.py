#!/usr/bin/env python3
"""
Build script to create Windows exe for the Maximum Security entrypoint.

Run this on a Windows machine with Python and PyInstaller installed.
"""

import subprocess
import sys
import os
from pathlib import Path

def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    try:
        import PyInstaller
        print("PyInstaller already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

def build_exe():
    """Build the Windows exe using PyInstaller."""
    print("Building Windows exe...")

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",  # Single exe file
        "--windowed",  # GUI app, no console window
        "--name", "MaximumSecurity",
        "entrypoint.py"
    ]

    subprocess.run(cmd, check=True)
    print("Exe built successfully!")

    # Check if exe was created
    exe_path = Path("dist") / "MaximumSecurity.exe"
    if exe_path.exists():
        print(f"[SUCCESS] Exe created at: {exe_path.absolute()}")
        print(f"  File size: {exe_path.stat().st_size} bytes")
        print(f"  Ready for distribution: {exe_path.name}")
    else:
        print("Warning: Exe not found in dist directory")

def main():
    """Main build process."""
    print("Maximum Security Entrypoint Builder")
    print("=" * 40)

    try:
        install_dependencies()
        install_pyinstaller()
        build_exe()
        print("\n✓ Build completed successfully!")
        print("📦 The MaximumSecurity.exe file is ready for distribution.")
        print("   This is the entrypoint customers will download and run.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
