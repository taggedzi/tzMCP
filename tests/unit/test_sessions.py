import json

import pytest

from tzMCP.gui_bits.config_manager import Config
from tzMCP.sessions import storage as storage_module
from tzMCP.sessions.manager import SessionManager
from tzMCP.sessions.models import (
    SessionState,
    SessionTransitionError,
    validate_session_id,
)
from tzMCP.sessions.processes import ProcessIdentity


def test_session_lifecycle_writes_atomic_state_and_counts_capture(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    session_dir = tmp_path / "sessions" / record.session_id
    (session_dir / "capture" / "image.png").write_bytes(b"1234")

    running = manager.transition(record.session_id, SessionState.RUNNING)
    ended = manager.transition(record.session_id, SessionState.ENDED)

    assert running.state is SessionState.RUNNING
    assert ended.capture_count == 1
    assert ended.capture_bytes == 4
    assert json.loads((session_dir / "state.json").read_text())['state'] == "ENDED"
    assert not (tmp_path / "runtime" / "active-session.json").exists()


def test_invalid_transitions_are_rejected_without_state_change(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    with pytest.raises(SessionTransitionError):
        manager.transition(record.session_id, SessionState.EXPORTED)
    assert manager.get(record.session_id).state is SessionState.NEW


def test_live_summary_counts_captures_without_rewriting_state(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.RUNNING)
    state_path = manager.storage.state_path(record.session_id)
    before = state_path.read_bytes()
    capture = manager.storage.session_dir(record.session_id) / "capture"
    (capture / "first.png").write_bytes(b"1234")
    (capture / "second.png").write_bytes(b"56789")

    summary = manager.get_summary(record.session_id)

    assert summary.state is SessionState.RUNNING
    assert (summary.capture_count, summary.capture_bytes) == (2, 9)
    assert state_path.read_bytes() == before


def test_only_one_active_session_is_allowed(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    manager.create_session(Config(save_dir=tmp_path / "unused"))
    with pytest.raises(RuntimeError, match="already active"):
        manager.create_session(Config(save_dir=tmp_path / "unused"))


def test_recovery_is_idempotent_and_preserves_capture(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.RUNNING)
    capture = tmp_path / "sessions" / record.session_id / "capture" / "keep.bin"
    capture.write_bytes(b"evidence")

    recovered = manager.recover_active()
    again = manager.recover_active()

    assert recovered.state is SessionState.INTERRUPTED
    assert recovered.capture_bytes == len(b"evidence")
    assert again is None
    assert capture.read_bytes() == b"evidence"


def test_process_identity_is_persisted_only_for_active_sessions(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    identity = ProcessIdentity(42, str(tmp_path / "firefox"), 123.0, "tzmcp")
    updated = manager.record_process(record.session_id, "firefox", identity)
    assert updated.process_records["firefox"]["pid"] == 42
    manager.transition(record.session_id, SessionState.INTERRUPTED)
    with pytest.raises(RuntimeError):
        manager.record_process(record.session_id, "proxy", identity)


def test_session_errors_are_persisted_only_while_active(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))

    updated = manager.record_error(record.session_id, "Proxy startup failed: port busy")

    assert updated.errors == ["Proxy startup failed: port busy"]
    assert manager.get(record.session_id).errors == updated.errors
    manager.transition(record.session_id, SessionState.INTERRUPTED)
    with pytest.raises(RuntimeError, match="active session"):
        manager.record_error(record.session_id, "late failure")


def test_failed_state_write_preserves_previous_file_and_removes_partial_file(
    tmp_path, monkeypatch
):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    state_path = manager.storage.state_path(record.session_id)
    original = state_path.read_bytes()

    def fail_after_partial_write(data, handle, **kwargs):
        handle.write("{")
        raise OSError("disk full")

    monkeypatch.setattr(storage_module.json, "dump", fail_after_partial_write)
    with pytest.raises(OSError, match="disk full"):
        manager.storage.write_state(record)

    assert state_path.read_bytes() == original
    assert list(state_path.parent.glob(".state-*.tmp")) == []


def test_failed_end_transition_keeps_session_recoverable(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.RUNNING)
    capture = manager.storage.session_dir(record.session_id) / "capture" / "keep.bin"
    capture.write_bytes(b"evidence")

    def fail_write(_record):
        raise OSError("disk full")

    monkeypatch.setattr(manager.storage, "write_state", fail_write)
    with pytest.raises(OSError, match="disk full"):
        manager.transition(record.session_id, SessionState.ENDED)

    assert manager.get(record.session_id).state is SessionState.RUNNING
    assert manager.active_path.read_text(encoding="ascii").strip() == record.session_id
    assert manager.lock_path.exists()
    assert capture.read_bytes() == b"evidence"


def test_failed_session_initialization_releases_exclusive_lock(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")

    def fail_write(_record):
        raise OSError("disk full")

    monkeypatch.setattr(manager.storage, "write_state", fail_write)
    with pytest.raises(OSError, match="disk full"):
        manager.create_session(Config(save_dir=tmp_path / "unused"))

    assert not manager.active_path.exists()
    assert not manager.lock_path.exists()


def test_failed_active_pointer_replace_preserves_previous_marker(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    manager.active_path.write_text("20260723T184512Z-abcdef12\n", encoding="ascii")
    original = manager.active_path.read_bytes()

    def fail_replace(_temporary, _target):
        raise OSError("disk full")

    monkeypatch.setattr("tzMCP.sessions.manager.os.replace", fail_replace)
    with pytest.raises(OSError, match="disk full"):
        manager._write_active_pointer("20260723T184513Z-abcdef12")

    assert manager.active_path.read_bytes() == original
    assert list(manager.runtime_root.glob(".active-session-*.tmp")) == []


def test_corrupt_active_state_is_preserved_for_recovery(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    state_path = manager.storage.state_path(record.session_id)
    capture = manager.storage.session_dir(record.session_id) / "capture" / "keep.bin"
    capture.write_bytes(b"evidence")
    state_path.write_text("{partial", encoding="utf-8")
    marker_before = manager.active_path.read_bytes()

    with pytest.raises(json.JSONDecodeError):
        manager.recover_active()

    assert state_path.read_text(encoding="utf-8") == "{partial"
    assert capture.read_bytes() == b"evidence"
    assert manager.active_path.read_bytes() == marker_before
    assert manager.lock_path.exists()


@pytest.mark.parametrize("value", ["../x", "", "20260723T184512Z-xyz", "2026-07-23"])
def test_session_ids_are_strict(value):
    with pytest.raises(ValueError):
        validate_session_id(value)
