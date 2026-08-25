"""Resolve application resources in source and PyInstaller builds."""

from __future__ import annotations

from pathlib import Path
import sys


def application_root() -> str:
    """Return the directory containing the bundled ``static`` and ``lib`` trees.

    PyInstaller uses ``_MEIPASS`` for Windows directory/one-file builds. A
    macOS app can instead expose data under ``Contents/Resources``. Selecting
    the first candidate with both resource trees avoids depending on the
    process working directory or one particular PyInstaller bundle layout.
    """
    source_root = Path(__file__).resolve().parents[1]
    if not getattr(sys, "frozen", False):
        return str(source_root)

    candidates = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root).resolve())

    executable = Path(sys.executable).resolve()
    if sys.platform == "darwin" and executable.parent.name == "MacOS":
        candidates.append(executable.parent.parent / "Resources")
    candidates.append(executable.parent)

    for candidate in candidates:
        if (candidate / "static").is_dir() and (candidate / "lib").is_dir():
            return str(candidate)
    return str(candidates[0] if candidates else source_root)
