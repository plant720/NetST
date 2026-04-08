#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Build script for NetST  (Linux / macOS)
#
# Usage:
#   chmod +x build.sh
#   ./build.sh
#
# Output:
#   dist/NetST/       – portable directory (Linux / macOS)
#   dist/NetST.app    – macOS app bundle  (macOS only)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing / upgrading PyInstaller..."
pip install --upgrade pyinstaller

echo "==> Cleaning previous build artifacts..."
rm -rf build/ dist/

echo "==> Running PyInstaller..."
pyinstaller netst.spec --clean

echo ""
if [[ "${OSTYPE:-}" == "darwin"* ]]; then
    echo "==> Build complete!"
    echo "    App bundle : dist/NetST.app"
    echo "    Directory  : dist/NetST/"
    echo ""
    echo "    Create a DMG for distribution:"
    echo "      hdiutil create -volname NetST -srcfolder dist/NetST.app \\"
    echo "              -ov -format UDZO dist/NetST.dmg"
else
    echo "==> Build complete!"
    echo "    Distribution directory: dist/NetST/"
    echo ""
    echo "    Create a tar.gz archive for distribution:"
    echo "      tar -czf dist/NetST-linux-x86_64.tar.gz -C dist NetST"
fi
