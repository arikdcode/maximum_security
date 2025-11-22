@echo off
REM Simple Windows batch file to build the entrypoint exe
REM Run this on Windows with Python and PyInstaller installed

echo Maximum Security Entrypoint Builder
echo ====================================

echo Installing dependencies...
pip install -r requirements.txt

echo Installing PyInstaller...
pip install pyinstaller

echo Building exe...
pyinstaller --onefile --name MaximumSecurity entrypoint.py

echo.
echo Build complete! Check the 'dist' folder for MaximumSecurity.exe
pause
