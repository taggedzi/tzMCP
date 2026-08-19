"""Appliance-mode feature detection and stable appliance metadata."""
from __future__ import annotations

import os


def is_appliance_mode() -> bool:
    """Return whether appliance mode was explicitly enabled.

    Only the documented value ``1`` enables appliance behavior.  This keeps
    malformed or legacy environments in the native/developer mode.
    """
    return os.environ.get("TZMCP_APPLIANCE") == "1"


def appliance_version() -> str:
    """Return the image version supplied by the appliance environment."""
    return os.environ.get("TZMCP_APPLIANCE_VERSION", "development")
