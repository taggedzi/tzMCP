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


def test_recovery_is_idempotent_and_preserves_capture(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.RUNNING)
    manager.record_process(record.session_id, "proxy", ProcessIdentity(42, "/proxy", 123, "owner"))
    monkeypatch.setattr("tzMCP.sessions.manager.stop_owned_process_tree", lambda identity: None)
    capture = tmp_path / "sessions" / record.session_id / "capture" / "keep.bin"
    capture.write_bytes(b"evidence")

    recovered = manager.recover_active()
    again = manager.recover_active()

    assert recovered.state is SessionState.INTERRUPTED
    assert recovered.capture_bytes == len(b"evidence")
    assert again is None
    assert capture.read_bytes() == b"evidence"


def test_legacy_running_session_without_proxy_identity_requires_manual_attention(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.RUNNING)
    with pytest.raises(RuntimeError, match="no recorded proxy identity"):
        manager.recover_active()
    assert manager.get(record.session_id).state is SessionState.RUNNING
    assert manager.active_path.exists()


def test_second_gui_cannot_recover_a_live_owner(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    second = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    with pytest.raises(RuntimeError, match="Another tzMCP GUI"):
        second.recover_active()
    assert manager.get(record.session_id).state is SessionState.NEW
    assert manager.active_path.exists()
    # Losing the GUI releases its OS lock, while the durable marker survives.
    manager._release_owner()
    assert second.recover_active().state is SessionState.INTERRUPTED


def test_recovery_waits_for_processes_before_counting_or_releasing(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    identity = ProcessIdentity(42, str(tmp_path / "proxy"), 123.0, "tzmcp")
    manager.record_process(record.session_id, "proxy", identity)
    capture = manager.storage.session_dir(record.session_id) / "capture" / "last.bin"

    def stop(saved):
        assert saved == identity
        assert manager.get(record.session_id).state is SessionState.NEW
        assert manager.active_path.exists()
        capture.write_bytes(b"last write before exit")

    monkeypatch.setattr("tzMCP.sessions.manager.stop_owned_process_tree", stop)
    recovered = manager.recover_active()
    assert recovered.capture_bytes == len(b"last write before exit")
    assert not manager.active_path.exists()


def test_failed_recovery_preserves_state_lock_and_profile(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.record_process(record.session_id, "proxy", ProcessIdentity(42, "/proxy", 1, "owner"))
    before = manager.storage.state_path(record.session_id).read_bytes()

    def fail(_identity):
        raise RuntimeError("termination failed")

    monkeypatch.setattr("tzMCP.sessions.manager.stop_owned_process_tree", fail)
    with pytest.raises(RuntimeError, match="Recovery blocked for proxy"):
        manager.recover_active()
    assert manager.storage.state_path(record.session_id).read_bytes() == before
    assert manager.active_path.exists()
    assert manager.lock_path.exists()


@pytest.mark.parametrize("proxy_fails", [False, True])
def test_recovery_cleans_browser_profile_only_after_all_processes_stop(tmp_path, monkeypatch, proxy_fails):
    from tzMCP.browser.firefox_session import FirefoxSession
    from tzMCP import paths

    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    browser_dir = tmp_path / "browser" / record.session_id
    profile = browser_dir / "profile"
    profile.mkdir(parents=True)
    (profile / "cookies.sqlite").write_bytes(b"private profile")
    capture = manager.storage.session_dir(record.session_id) / "capture" / "keep.bin"
    capture.write_bytes(b"preserved capture")
    identity = ProcessIdentity(42, "/firefox", 123, "owner")
    manager.record_process(record.session_id, "firefox", identity)
    manager.record_process(record.session_id, "proxy", identity)
    monkeypatch.setattr(paths, "appliance_browser_dir", lambda sid: browser_dir)
    events = []

    def stop_browser(browser):
        events.append("browser")
        browser.identity = None

    def stop_proxy(saved):
        assert profile.exists()
        events.append("proxy")
        if proxy_fails:
            raise RuntimeError("proxy still alive")

    monkeypatch.setattr(FirefoxSession, "stop", stop_browser)
    monkeypatch.setattr("tzMCP.sessions.manager.stop_owned_process_tree", stop_proxy)
    if proxy_fails:
        with pytest.raises(RuntimeError, match="proxy still alive"):
            manager.recover_active()
        assert profile.exists()
        assert manager.active_path.exists()
    else:
        recovered = manager.recover_active()
        assert recovered.state is SessionState.INTERRUPTED
        assert not profile.exists()
    assert events == ["browser", "proxy"]
    assert capture.read_bytes() == b"preserved capture"


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


def test_ended_sessions_remain_pending_after_the_active_lock_is_released(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    ids = iter(["20261016T000000Z-00000002", "20261016T000000Z-00000001"])
    monkeypatch.setattr(manager, "_new_id", lambda: next(ids))
    newer = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(newer.session_id, SessionState.INTERRUPTED)
    older = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(older.session_id, SessionState.RUNNING)
    manager.transition(older.session_id, SessionState.ENDED)
    (manager.storage.root / "notes").mkdir()
    (manager.storage.root / "20261016T000000Z-00000003").mkdir()
    assert not manager.active_path.exists()
    assert not manager.lock_path.exists()

    restarted = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    pending = restarted.list_pending_exports()

    assert [(record.session_id, record.state) for record in pending] == [
        (older.session_id, SessionState.ENDED),
        (newer.session_id, SessionState.INTERRUPTED),
    ]
    assert not restarted.active_path.exists()
    assert not restarted.lock_path.exists()
    assert restarted.recover_active() is None
    assert [record.session_id for record in restarted.list_pending_exports()] == [
        older.session_id,
        newer.session_id,
    ]


def test_recovered_session_stays_discoverable_after_restart(tmp_path, monkeypatch):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.RUNNING)
    manager.record_process(record.session_id, "proxy", ProcessIdentity(42, "/proxy", 123, "owner"))
    monkeypatch.setattr("tzMCP.sessions.manager.stop_owned_process_tree", lambda identity: None)
    capture = manager.storage.session_dir(record.session_id) / "capture" / "keep.bin"
    capture.write_bytes(b"evidence")

    recovered = manager.recover_active()
    assert recovered.state is SessionState.INTERRUPTED
    assert not manager.active_path.exists()

    restarted = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    pending = restarted.list_pending_exports()
    assert [item.session_id for item in pending] == [record.session_id]
    assert pending[0].state is SessionState.INTERRUPTED
    assert capture.read_bytes() == b"evidence"
    assert not restarted.active_path.exists()


def test_exported_session_is_omitted_from_pending_discovery(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.INTERRUPTED)
    assert len(manager.list_pending_exports()) == 1

    manager.complete_export(record.session_id, f"{record.session_id}.zip", 4, "ab" * 32)

    assert manager.list_pending_exports() == []
    follow_up = manager.create_session(Config(save_dir=tmp_path / "unused"))
    assert follow_up.state is SessionState.NEW
    assert manager.active_path.exists()


def test_unreadable_pending_state_is_not_skipped(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.INTERRUPTED)
    state_path = manager.storage.state_path(record.session_id)
    state_path.write_text("{", encoding="utf-8")

    with pytest.raises(RuntimeError, match=record.session_id):
        manager.list_pending_exports()

    assert state_path.read_text(encoding="utf-8") == "{"
    assert not manager.active_path.exists()


def test_mismatched_session_identity_fails_discovery(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.INTERRUPTED)
    state_path = manager.storage.state_path(record.session_id)
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload["session_id"] = "20261016T000000Z-00000099"
    state_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="does not match"):
        manager.list_pending_exports()


def test_symlinked_session_directory_fails_discovery(tmp_path):
    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    manager.transition(record.session_id, SessionState.INTERRUPTED)
    link = manager.storage.root / "20261016T000000Z-00000009"
    try:
        link.symlink_to(tmp_path / "outside", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")

    with pytest.raises(RuntimeError, match="00000009"):
        manager.list_pending_exports()
    assert manager.get(record.session_id).state is SessionState.INTERRUPTED


@pytest.mark.parametrize("value", ["../x", "", "20260723T184512Z-xyz", "2026-07-23"])
def test_session_ids_are_strict(value):
    with pytest.raises(ValueError):
        validate_session_id(value)
