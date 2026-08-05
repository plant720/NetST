"""Resolve application resources in source and PyInstaller builds."""

from __future__ import annotations

import os
import sys


def application_root() -> str:
    """Return the directory containing the bundled ``static`` and ``lib`` trees."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.abspath(sys._MEIPASS)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
