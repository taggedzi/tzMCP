"""Validated, serializable session lifecycle records."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


SESSION_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$", re.ASCII)


class SessionState(StrEnum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    ENDED = "ENDED"
    INTERRUPTED = "INTERRUPTED"
    EXPORTED = "EXPORTED"


class SessionTransitionError(ValueError):
    """Raised when a session state transition is not allowed."""


def validate_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or not SESSION_ID_RE.fullmatch(session_id):
        raise ValueError(f"Invalid session ID: {session_id!r}")
    return session_id


@dataclass
class SessionRecord:
    session_id: str
    state: SessionState = SessionState.NEW
    started_at: str | None = None
    ended_at: str | None = None
    exported_at: str | None = None
    process_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    capture_count: int = 0
    capture_bytes: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    archive_name: str | None = None
    archive_size: int | None = None
    archive_sha256: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_session_id(self.session_id)
        self.state = SessionState(self.state)

    def to_dict(self) -> dict[str, Any]:
        result = self.__dict__.copy()
        result["state"] = self.state.value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionRecord":
        if not isinstance(data, dict):
            raise ValueError("Session state must be an object")
        return cls(**data)

    def transition(self, new_state: SessionState) -> None:
        new_state = SessionState(new_state)
        allowed = {
            SessionState.NEW: {SessionState.RUNNING, SessionState.INTERRUPTED},
            SessionState.RUNNING: {SessionState.ENDED, SessionState.INTERRUPTED},
            SessionState.ENDED: {SessionState.EXPORTED},
            SessionState.INTERRUPTED: {SessionState.EXPORTED},
            SessionState.EXPORTED: set(),
        }
        if new_state not in allowed[self.state]:
            raise SessionTransitionError(f"Cannot transition {self.state} -> {new_state}")
        self.state = new_state
