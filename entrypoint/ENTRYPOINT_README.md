# Maximum Security Entrypoint

This is the dead-simple entrypoint executable that customers will download and run. It has one job: fetch and run the latest launcher from the distribution repository.

## How It Works

1. **Fetches Latest Release**: Calls GitHub API to get the latest launcher release from `arikdcode/maximum_security_dist`
2. **Shows Progress**: Displays a clean progress bar window showing download status
3. **Downloads Launcher**: Downloads the `Maximum.Security.Launcher.exe` asset to `%APPDATA%/MaximumSecurity/`
4. **Verifies Download**: Checks file size matches expected size from GitHub
5. **Runs Launcher**: Starts the downloaded launcher and closes the progress window

## Key Features

- **Never Changes**: This entrypoint code never needs to be updated
- **Always Current**: Will always download and run the latest launcher version
- **Clean UI**: Minimal progress bar window instead of ugly console
- **Persistent Storage**: Downloads to user app data directory so dependencies are available
- **Secure**: Verifies download integrity via file size
- **Simple**: Single-purpose, minimal code

## Building the Executable

### From Linux (Recommended - Remote Build)

If you're developing on Linux but have SSH access to a Windows PC:

```bash
# From the project root
./scripts/build_entrypoint_remote.sh
```

This will:
- Copy the entrypoint folder to your Windows PC at `~/Home/Code/MaximumSecurity/entrypoint`
- Run the build remotely
- Leave `MaximumSecurity.exe` ready for testing

### On Windows Directly

**Option 1: Python Build Script (Recommended)**
1. Install Python 3.8+ from python.org
2. Navigate to the `entrypoint` directory
3. Run the build script:

```bash
cd entrypoint
python build_entrypoint_exe.py
```

**Option 2: Manual Build**
1. Install Python 3.8+ and PyInstaller
2. Navigate to the `entrypoint` directory
3. Run:

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --name MaximumSecurity entrypoint.py
```

**Option 3: Batch File**
Double-click `build_windows.bat` in the entrypoint directory.

All methods create `dist/MaximumSecurity.exe` - this is the file you distribute to customers.

### Requirements

- Python 3.8+
- Internet connection (for downloading dependencies and the launcher)

## Files

- `entrypoint.py` - Main entrypoint script
- `requirements.txt` - Python dependencies
- `build_entrypoint_exe.py` - Build script for Windows exe
- `ENTRYPOINT_README.md` - This documentation

## Distribution

The `MaximumSecurity.exe` file is what customers should download and run. It will:

1. Show a simple console window with progress messages
2. Download the latest launcher (may take a minute on slow connections)
3. Start the launcher
4. Exit (the launcher takes over)

## Updating Customers

Since the entrypoint never changes, customers never need to redownload it. When you release new launcher versions through the deploy process, existing entrypoints will automatically download and run the new version.

## Technical Details

- Uses GitHub Releases API (no authentication required for public repos)
- Downloads to temporary directory that gets cleaned up
- File size verification prevents corrupted downloads
- Compatible with Windows 10/11
