@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: Build script for NetST  (Windows)
::
:: Usage:  double-click build.bat  or  run from a Command Prompt / PowerShell
::
:: Output:
::   dist\NetST\   – portable directory to zip and distribute
:: ─────────────────────────────────────────────────────────────────────────────
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo =^=^> Installing / upgrading PyInstaller...
pip install --upgrade pyinstaller
if errorlevel 1 (
    echo [ERROR] pip install failed. Make sure Python and pip are on PATH.
    pause
    exit /b 1
)

echo =^=^> Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo =^=^> Running PyInstaller...
pyinstaller netst.spec --clean
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed. Check the output above.
    pause
    exit /b 1
)

echo.
echo =^=^> Build complete!
echo     Distribution directory: dist\NetST\
echo.
echo     Create a ZIP archive for distribution:
echo       powershell Compress-Archive -Path dist\NetST -DestinationPath dist\NetST-windows.zip
echo.
pause
