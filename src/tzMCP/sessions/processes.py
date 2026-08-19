"""PID-reuse-safe process identity checks for session recovery."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import psutil


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    executable: str
    start_time: float
    owner: str | None = None

    @classmethod
    def from_process(cls, process: psutil.Process) -> "ProcessIdentity":
        return cls(
            pid=process.pid,
            executable=str(Path(process.exe()).resolve()),
            start_time=process.create_time(),
            owner=process.username(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "executable": self.executable,
            "start_time": self.start_time,
            "owner": self.owner,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProcessIdentity":
        return cls(int(value["pid"]), str(value["executable"]), float(value["start_time"]), value.get("owner"))


def verify_process_identity(
    identity: ProcessIdentity,
    process_factory: Callable[[int], psutil.Process] = psutil.Process,
    time_tolerance: float = 0.01,
) -> bool:
    """Return true only when the current process still matches the record."""
    try:
        process = process_factory(identity.pid)
        executable_matches = Path(process.exe()).resolve() == Path(identity.executable).resolve()
        start_matches = abs(process.create_time() - identity.start_time) <= time_tolerance
        owner_matches = identity.owner is None or process.username() == identity.owner
        return executable_matches and start_matches and owner_matches
    except (psutil.Error, OSError, ValueError):
        return False
