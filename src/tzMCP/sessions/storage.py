"""Safe session paths and atomic state persistence."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from tzMCP.sessions.models import SessionRecord, validate_session_id


class SessionStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        validate_session_id(session_id)
        path = (self.root / session_id).resolve()
        if path.parent != self.root:
            raise ValueError("Session path escaped session root")
        return path

    def state_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "state.json"

    def create_layout(self, session_id: str) -> Path:
        directory = self.session_dir(session_id)
        for name in ("capture", "logs", "metadata", "browser", "staging"):
            (directory / name).mkdir(parents=True, exist_ok=False)
        return directory

    def write_state(self, record: SessionRecord) -> None:
        target = self.state_path(record.session_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(record.to_dict(), handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def read_state(self, session_id: str) -> SessionRecord:
        with self.state_path(session_id).open("r", encoding="utf-8") as handle:
            return SessionRecord.from_dict(json.load(handle))
