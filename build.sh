#!/usr/bin/env bash
# build.sh – Build NetST with PyInstaller inside an isolated virtual environment
# Usage: bash build.sh [--clean]
#
# Outputs:
#   dist/NetST/       – directory distribution (all platforms)
#   dist/NetST.app    – macOS app bundle (macOS only)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
CLEAN_BUILD=false

for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN_BUILD=true ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done

# ── 1. Create / reuse virtual environment ─────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "[build] Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# ── 2. Install / upgrade dependencies ────────────────────────────────────────
echo "[build] Installing dependencies from requirements.txt ..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# ── 3. Mark external binaries as executable (Linux / macOS) ──────────────────
if [ -d "lib" ]; then
    find lib -type f -not -name "*.py" -exec chmod +x {} \;
fi

# ── 4. Run PyInstaller ────────────────────────────────────────────────────────
PYINSTALLER_ARGS="netst.spec"
if $CLEAN_BUILD; then
    PYINSTALLER_ARGS="$PYINSTALLER_ARGS --clean"
fi

echo "[build] Running PyInstaller ..."
pyinstaller $PYINSTALLER_ARGS

echo "[build] Done. Output is in dist/NetST/"
