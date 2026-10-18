"""Session lifecycle orchestration without GUI dependencies."""
from __future__ import annotations

import copy
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tzMCP.gui_bits.config_manager import Config
from tzMCP.paths import runtime_dir, sessions_dir
from tzMCP.proxy_runtime import write_config_snapshot
from tzMCP.sessions.models import SessionRecord, SessionState, validate_session_id
from tzMCP.sessions.processes import ProcessIdentity, stop_owned_process_tree
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
        self._owner_lock = None

    def _claim_owner(self) -> None:
        """Hold an OS lock which is released automatically if the GUI dies."""
        if self._owner_lock is not None:
            return
        handle = (self.runtime_root / "session-owner.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                if not handle.read(1):
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise RuntimeError("Another tzMCP GUI owns this session. Close it before retrying.") from exc
        self._owner_lock = handle

    def _release_owner(self) -> None:
        if self._owner_lock is not None:
            self._owner_lock.close()
            self._owner_lock = None

    def _new_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)

    def create_session(self, config: Config) -> SessionRecord:
        already_owned = self._owner_lock is not None
        self._claim_owner()
        try:
            fd = self.lock_path.open("x", encoding="ascii")
            fd.close()
        except FileExistsError as exc:
            if not already_owned:
                self._release_owner()
            raise RuntimeError("Another tzMCP session is already active") from exc
        try:
            session_id = self._new_id()
            directory = self.storage.create_layout(session_id)
            effective = copy.deepcopy(config)
            effective.save_dir = directory / "capture"
            write_config_snapshot(effective, directory / "metadata")
            # Keep the snapshot path discoverable without making it part of
            # the public state schema yet; its contents are authoritative.
            record = SessionRecord(session_id=session_id, started_at=_utc_now())
            self.storage.write_state(record)
            self._write_active_pointer(session_id)
            return record
        except Exception:
            # A failed initialization must not strand the exclusive lock. The
            # incomplete session directory is left intact for diagnosis; no
            # capture process has started at this point.
            self._release_lock()
            raise

    def _write_active_pointer(self, session_id: str) -> None:
        fd, temporary = tempfile.mkstemp(
            prefix=".active-session-", suffix=".tmp", dir=self.runtime_root
        )
        try:
            with os.fdopen(fd, "w", encoding="ascii", newline="\n") as handle:
                handle.write(session_id + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.active_path)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def get(self, session_id: str) -> SessionRecord:
        return self.storage.read_state(validate_session_id(session_id))

    def get_summary(self, session_id: str) -> SessionRecord:
        """Read current capture totals without rewriting the persisted state."""
        record = self.get(session_id)
        if record.state in (SessionState.NEW, SessionState.RUNNING):
            self._count_capture_files(record)
        return record

    def list_pending_exports(self) -> list[SessionRecord]:
        """Return ended and interrupted sessions, oldest session ID first.

        This reads durable session state. It does not use or recreate the
        active-session pointer or exclusive lock.
        """
        try:
            session_ids = self.storage.list_session_ids()
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Session discovery failed: {exc}") from exc
        pending: list[SessionRecord] = []
        for session_id in session_ids:
            state_path = self.storage.state_path(session_id)
            if state_path.is_symlink() or (state_path.exists() and not state_path.is_file()):
                raise RuntimeError(f"Session {session_id} state path is not a regular file")
            if not state_path.is_file():
                continue
            try:
                record = self.storage.read_state(session_id)
            except (OSError, ValueError, TypeError) as exc:
                raise RuntimeError(
                    f"Session {session_id} is awaiting inspection but its state could not be read: {exc}"
                ) from exc
            if record.session_id != session_id:
                raise RuntimeError(f"Session {session_id} state does not match its directory")
            if record.state in (SessionState.ENDED, SessionState.INTERRUPTED):
                pending.append(record)
        pending.sort(key=lambda record: record.session_id)
        return pending

    def transition(self, session_id: str, state: SessionState) -> SessionRecord:
        record = self.get(session_id)
        record.transition(state)
        now = _utc_now()
        release_active = state in (SessionState.ENDED, SessionState.INTERRUPTED)
        if release_active:
            record.ended_at = record.ended_at or now
            self._count_capture_files(record)
        elif state is SessionState.EXPORTED:
            record.exported_at = record.exported_at or now
        self.storage.write_state(record)
        if release_active:
            self._release_active()
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

    def record_error(self, session_id: str, error: str) -> SessionRecord:
        """Persist an actionable failure while a session is being initialized or run."""
        message = str(error).strip()
        if not message:
            raise ValueError("Session error must not be empty")
        record = self.get(session_id)
        if record.state not in (SessionState.NEW, SessionState.RUNNING):
            raise RuntimeError("Errors can only be attached to an active session")
        record.errors.append(message)
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
        self._release_lock()

    def _release_lock(self) -> None:
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        self._release_owner()

    def recover_active(self) -> SessionRecord | None:
        self._claim_owner()
        try:
            return self._recover_active()
        except Exception:
            self._release_owner()
            raise

    def _recover_active(self) -> SessionRecord | None:
        if not self.active_path.exists():
            self._release_owner()
            return None
        session_id = self.active_path.read_text(encoding="ascii").strip()
        validate_session_id(session_id)
        record = self.get(session_id)
        if record.state is SessionState.RUNNING and "proxy" not in record.process_records:
            raise RuntimeError(
                "The running session has no recorded proxy identity. Capture shutdown cannot be verified; "
                "keep the captures and have an administrator inspect the remaining processes before export."
            )
        recovered_browser = None
        for name, raw_identity in record.process_records.items():
            identity = ProcessIdentity.from_dict(raw_identity)
            try:
                if name == "firefox":
                    from tzMCP.browser.firefox_session import FirefoxSession
                    from tzMCP.paths import appliance_browser_dir
                    recovered_browser = FirefoxSession(
                        Path(identity.executable), appliance_browser_dir(session_id),
                        self.runtime_root / "unused-ca.pem", 8080,
                    )
                    recovered_browser.identity = identity
                    recovered_browser.stop()
                else:
                    stop_owned_process_tree(identity)
            except Exception as exc:
                raise RuntimeError(f"Recovery blocked for {name}: {exc}. Captures and profile preserved.") from exc
        if recovered_browser is not None:
            recovered_browser.cleanup()
        if record.state in (SessionState.NEW, SessionState.RUNNING):
            record.transition(SessionState.INTERRUPTED)
            record.ended_at = record.ended_at or _utc_now()
            self._count_capture_files(record)
            record.warnings.append("Session recovered after an abnormal shutdown")
            self.storage.write_state(record)
        self._release_active()
        return record
