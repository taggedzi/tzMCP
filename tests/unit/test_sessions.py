import json

import pytest

from tzMCP.gui_bits.config_manager import Config
from tzMCP.sessions.manager import SessionManager
from tzMCP.sessions.models import SessionState, SessionTransitionError, validate_session_id
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


@pytest.mark.parametrize("value", ["../x", "", "20260723T184512Z-xyz", "2026-07-23"])
def test_session_ids_are_strict(value):
    with pytest.raises(ValueError):
        validate_session_id(value)
