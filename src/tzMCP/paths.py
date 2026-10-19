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


def default_logs_dir() -> Path:
    """Return the persistent logs directory under the data root.

    Native GUI, CLI, and the deduplication database use this path.
    ``TZMCP_LOG_DIR`` does not move it.
    """
    return data_dir() / "logs"


def logs_dir() -> Path:
    """Return the component-log directory for this process.

    ``TZMCP_LOG_DIR`` selects the active session directory when a proxy
    launch sets it before logging starts. An empty value is ignored.
    Native and CLI launches pass ``default_logs_dir()`` instead, so their
    logs stay under the data root.
    """
    override = os.environ.get("TZMCP_LOG_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return default_logs_dir()


def profiles_dir() -> Path:
    return data_dir() / "profiles"


def appliance_browser_dir(session_id: str) -> Path:
    """Keep managed Firefox profiles outside captured session data."""
    from tzMCP.sessions.models import validate_session_id

    return data_dir() / "browser-profiles" / validate_session_id(session_id)


def sessions_dir() -> Path:
    """Return the root for isolated capture sessions."""
    return data_dir() / "sessions"


def ca_dir() -> Path:
    """Return the persistent, VM-specific mitmproxy CA directory."""
    return data_dir() / "ca" / "mitmproxy"


def runtime_dir() -> Path:
    """Return short-lived process and launch metadata storage."""
    return data_dir() / "runtime"


def export_ready_dir() -> Path:
    """Return the local archive handoff directory."""
    return data_dir() / "export-ready"


def ensure_private_dir(path: Path) -> Path:
    """Create a runtime directory and restrict it to its owner where supported."""
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)
        if path.stat().st_mode & 0o077:
            raise PermissionError(f"Directory is not owner-only: {path}")
    return path


def ensure_runtime_dirs() -> None:
    """Create appliance runtime roots without creating session or CA contents."""
    for path in (sessions_dir(), ca_dir(), runtime_dir(), export_ready_dir(), data_dir() / "browser-profiles"):
        ensure_private_dir(path)
