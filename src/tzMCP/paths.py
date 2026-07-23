"""Portable locations for tzMCP runtime data."""
from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "tzMCP"


def data_dir() -> Path:
    """Return the user-writable directory used for tzMCP state.

    ``TZMCP_DATA_DIR`` provides an explicit location for portable installs,
    tests, and deployments.  Otherwise follow the conventional data location
    for the current operating system.
    """
    configured_dir = os.environ.get("TZMCP_DATA_DIR")
    if configured_dir:
        return Path(configured_dir).expanduser()

    if sys.platform == "win32":
        base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base_dir / APP_NAME


def config_dir() -> Path:
    return data_dir() / "config"


def logs_dir() -> Path:
    return data_dir() / "logs"


def profiles_dir() -> Path:
    return data_dir() / "profiles"
