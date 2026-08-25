"""Application logging with platform-appropriate, user-writable paths."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys


_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def user_log_path() -> Path:
    """Return NetST's per-user log file without requiring a GUI dependency."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "NetST" / "logs" / "netst.log"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "NetST" / "netst.log"
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "NetST" / "netst.log"


def configure_logging(level: int = logging.INFO) -> Path:
    """Configure one rotating file handler and return the active log path.

    Repeated calls are idempotent. The file contains diagnostic tracebacks that
    are intentionally kept out of user-facing message boxes and GUI log text.
    """
    path = user_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)
    resolved = path.resolve()
    for handler in root.handlers:
        if isinstance(handler, RotatingFileHandler):
            try:
                if Path(handler.baseFilename).resolve() == resolved:
                    return path
            except (OSError, RuntimeError):
                continue

    handler = RotatingFileHandler(
        path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
    return path
