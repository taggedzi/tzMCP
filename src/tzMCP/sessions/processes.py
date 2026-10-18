"""PID-reuse-safe process identity checks for session recovery."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Callable

import psutil


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    executable: str
    start_time: float
    owner: str | None = None
    session_id: int | None = None

    @classmethod
    def from_process(cls, process: psutil.Process) -> "ProcessIdentity":
        return cls(
            pid=process.pid,
            executable=str(Path(process.exe()).resolve()),
            start_time=process.create_time(),
            owner=process.username(),
            session_id=os.getsid(process.pid) if os.name == "posix" else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "executable": self.executable,
            "start_time": self.start_time,
            "owner": self.owner,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProcessIdentity":
        return cls(int(value["pid"]), str(value["executable"]), float(value["start_time"]),
                   value.get("owner"), value.get("session_id"))


def verify_process_identity(
    identity: ProcessIdentity,
    process_factory: Callable[[int], psutil.Process] | None = None,
    time_tolerance: float = 0.01,
) -> bool:
    """Return true only when the current process still matches the record."""
    try:
        process = (process_factory or psutil.Process)(identity.pid)
        executable_matches = Path(process.exe()).resolve() == Path(identity.executable).resolve()
        start_matches = abs(process.create_time() - identity.start_time) <= time_tolerance
        owner_matches = identity.owner is None or process.username() == identity.owner
        return executable_matches and start_matches and owner_matches
    except (psutil.Error, OSError, ValueError):
        return False


def _session_members(identity: ProcessIdentity) -> list[psutil.Process]:
    """Find reparented descendants of a separately launched POSIX session."""
    if os.name != "posix" or identity.session_id is None:
        return []
    if identity.session_id != identity.pid:
        raise RuntimeError("Capture process was not launched in its own OS session")
    members = []
    for process in psutil.process_iter():
        try:
            if os.getsid(process.pid) != identity.session_id:
                continue
            current = ProcessIdentity.from_process(process)
            if current.owner != identity.owner or current.start_time < identity.start_time:
                raise RuntimeError("Capture OS session ownership changed")
            if current.pid == identity.pid and abs(current.start_time - identity.start_time) > 0.01:
                raise RuntimeError("Capture OS session leader PID was reused")
            if process.status() != psutil.STATUS_ZOMBIE:
                members.append(process)
        except (psutil.NoSuchProcess, ProcessLookupError):
            continue
    return members


def stop_owned_process_tree(identity: ProcessIdentity, timeout: float = 5) -> None:
    """Stop a verified tree and confirm exit; uncertainty blocks finalization."""
    try:
        root = psutil.Process(identity.pid)
    except psutil.NoSuchProcess:
        root = None
    try:
        if root is not None and not verify_process_identity(identity):
            raise RuntimeError(f"Cannot verify process {identity.pid}; close it manually and retry recovery")
        if identity.owner is None:
            raise RuntimeError(f"Missing owner for process {identity.pid}")
        targets = [root, *root.children(recursive=True)] if root is not None else []
        targets = list({process.pid: process for process in [*targets, *_session_members(identity)]}.values())
        identities = [(process, ProcessIdentity.from_process(process)) for process in targets]
        for _, child_identity in identities:
            if child_identity.owner != identity.owner:
                raise RuntimeError("Process tree ownership changed; manual attention required")
        # psutil Process objects also guard signals against PID reuse. Recheck
        # executable/owner immediately before each signal as well.
        for process, child_identity in reversed(identities):
            try:
                if not verify_process_identity(child_identity):
                    if process.is_running():
                        raise RuntimeError(f"Process identity changed: {process.pid}")
                    continue
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(targets, timeout=timeout)
        for process in alive:
            child_identity = next(item for candidate, item in identities if candidate is process)
            if not verify_process_identity(child_identity):
                raise RuntimeError(f"Process identity changed: {process.pid}")
            process.kill()
        _, alive = psutil.wait_procs(alive, timeout=timeout)
        if alive:
            raise RuntimeError("Capture processes did not exit; close them manually and retry recovery")
        if _session_members(identity):
            raise RuntimeError("Capture spawned more processes during shutdown; retry recovery")
    except psutil.NoSuchProcess as exc:
        raise RuntimeError("Process tree changed during shutdown; retry recovery") from exc
