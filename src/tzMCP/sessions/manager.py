"""Session lifecycle orchestration without GUI dependencies."""
from __future__ import annotations

import copy
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path

from tzMCP.gui_bits.config_manager import Config
from tzMCP.paths import runtime_dir, sessions_dir
from tzMCP.proxy_runtime import write_config_snapshot
from tzMCP.sessions.models import SessionRecord, SessionState, validate_session_id
from tzMCP.sessions.processes import ProcessIdentity, verify_process_identity
from tzMCP.sessions.storage import SessionStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SessionManager:
    def __init__(self, root: Path | None = None, runtime_root: Path | None = None):
        self.storage = SessionStorage(root or sessions_dir())
        self.runtime_root = (runtime_root or runtime_dir()).resolve()
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.active_path = self.runtime_root / "active-session.json"
        self.lock_path = self.runtime_root / "active-session.lock"

    def _new_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)

    def create_session(self, config: Config) -> SessionRecord:
        try:
            fd = self.lock_path.open("x", encoding="ascii")
            fd.close()
        except FileExistsError as exc:
            raise RuntimeError("Another tzMCP session is already active") from exc
        session_id = self._new_id()
        directory = self.storage.create_layout(session_id)
        effective = copy.deepcopy(config)
        effective.save_dir = directory / "capture"
        snapshot = write_config_snapshot(effective, directory / "metadata")
        # Keep the snapshot path discoverable without making it part of the
        # public state schema yet; its contents are the authoritative config.
        record = SessionRecord(session_id=session_id, started_at=_utc_now())
        self.storage.write_state(record)
        self.active_path.write_text(session_id + "\n", encoding="ascii")
        return record

    def get(self, session_id: str) -> SessionRecord:
        return self.storage.read_state(validate_session_id(session_id))

    def transition(self, session_id: str, state: SessionState) -> SessionRecord:
        record = self.get(session_id)
        record.transition(state)
        now = _utc_now()
        if state in (SessionState.ENDED, SessionState.INTERRUPTED):
            record.ended_at = record.ended_at or now
            self._count_capture_files(record)
            self._release_active()
        elif state is SessionState.EXPORTED:
            record.exported_at = record.exported_at or now
        self.storage.write_state(record)
        return record

    def record_process(self, session_id: str, name: str, identity: ProcessIdentity) -> SessionRecord:
        """Persist an owned process identity for later safe recovery."""
        record = self.get(session_id)
        if record.state not in (SessionState.NEW, SessionState.RUNNING):
            raise RuntimeError("Process records can only be attached to an active session")
        if not name or "/" in name or "\\" in name:
            raise ValueError("Invalid process record name")
        record.process_records[name] = identity.to_dict()
        self.storage.write_state(record)
        return record

    def complete_export(self, session_id: str, archive_name: str, archive_size: int, archive_sha256: str) -> SessionRecord:
        record = self.get(session_id)
        record.archive_name = archive_name
        record.archive_size = archive_size
        record.archive_sha256 = archive_sha256
        record.transition(SessionState.EXPORTED)
        record.exported_at = record.exported_at or _utc_now()
        self.storage.write_state(record)
        return record

    def _count_capture_files(self, record: SessionRecord) -> None:
        capture = self.storage.session_dir(record.session_id) / "capture"
        files = [path for path in capture.rglob("*") if path.is_file() and not path.is_symlink()]
        record.capture_count = len(files)
        record.capture_bytes = sum(path.stat().st_size for path in files)

    def _release_active(self) -> None:
        try:
            self.active_path.unlink()
        except FileNotFoundError:
            pass
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass

    def recover_active(self) -> SessionRecord | None:
        if not self.active_path.exists():
            return None
        session_id = self.active_path.read_text(encoding="ascii").strip()
        validate_session_id(session_id)
        record = self.get(session_id)
        for name, raw_identity in record.process_records.items():
            identity = ProcessIdentity.from_dict(raw_identity)
            # Recovery only reports verified ownership here. Actual process
            # termination is supplied by the caller once it has a live process
            # controller; an unverified PID is never treated as owned.
            if not verify_process_identity(identity):
                record.warnings.append(f"Could not verify recorded process: {name}")
        if record.state in (SessionState.NEW, SessionState.RUNNING):
            record.transition(SessionState.INTERRUPTED)
            record.ended_at = record.ended_at or _utc_now()
            self._count_capture_files(record)
            record.warnings.append("Session recovered after an abnormal shutdown")
            self.storage.write_state(record)
        self._release_active()
        return record
