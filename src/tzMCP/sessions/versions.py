"""Collect component versions without including host paths or secrets."""
from __future__ import annotations

import platform
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from tzMCP.appliance import appliance_version


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _executable_version(executable: Path | None) -> str:
    if executable is None:
        return "unknown"
    try:
        result = subprocess.run([str(executable), "--version"], check=False, capture_output=True, text=True, timeout=5)
        output = (result.stdout or result.stderr).strip().splitlines()
        return output[0] if result.returncode == 0 and output else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def collect_versions(firefox_executable: Path | None = None) -> dict[str, str]:
    """Return stable component labels suitable for exported session metadata."""
    return {
        "tzMCP": _package_version("tzMCP"),
        "appliance": appliance_version(),
        "python": platform.python_version(),
        "mitmproxy": _package_version("mitmproxy"),
        "ubuntu": platform.freedesktop_os_release().get("PRETTY_NAME", "unknown")
        if hasattr(platform, "freedesktop_os_release") and platform.system() == "Linux"
        else platform.system(),
        "firefox": _executable_version(firefox_executable),
    }
