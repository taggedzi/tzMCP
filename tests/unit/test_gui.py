import ast
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import tzMCP.gui_bits.browser_tab as browser_tab_module
from tzMCP.common_utils import log_config
from tzMCP.gui_bits.browser_tab import BrowserTab
from tzMCP.sessions.models import SessionRecord, SessionState


@pytest.mark.parametrize("outcome", [
    None,
    SessionRecord("20261016T000000Z-01234567", state=SessionState.INTERRUPTED),
    ValueError("malformed session state"),
    json.JSONDecodeError("invalid JSON", "{", 1),
    OSError("session state unavailable"),
    ValueError(),
])
def test_main_app_initializes_after_session_recovery(monkeypatch, tmp_path, outcome):
    # Import only after redirecting logging, so no real runtime files are opened.
    monkeypatch.setattr(log_config, "setup_logging", lambda: None)
    import tzMCP.gui as gui

    monkeypatch.setattr(gui.tk.Tk, "__init__", lambda self: None)
    monkeypatch.setattr(gui.MainApp, "title", lambda *args: None)
    monkeypatch.setattr(gui.MainApp, "protocol", lambda *args: None)
    for name in ("config_dir", "profiles_dir", "logs_dir", "ca_dir"):
        monkeypatch.setattr(gui, name, lambda name=name: tmp_path / name)
    monkeypatch.setattr(gui, "is_appliance_mode", lambda: False)
    for name in ("clean_old_profiles", "clean_old_logs", "start_gui_log_server"):
        monkeypatch.setattr(gui, name, Mock())
    monkeypatch.setattr(gui, "ConfigManager", Mock(return_value=SimpleNamespace(
        load_config=lambda: SimpleNamespace(proxy_port=8080)
    )))
    session_root = tmp_path / "sessions"
    runtime_root = tmp_path / "runtime"
    manager = Mock(wraps=gui.SessionManager(root=session_root, runtime_root=runtime_root))
    if isinstance(outcome, Exception):
        manager.recover_active.side_effect = outcome
    else:
        manager.recover_active.return_value = outcome
    monkeypatch.setattr(gui, "SessionManager", Mock(return_value=manager))
    monkeypatch.setattr(gui, "ProxyController", Mock())
    tab = BrowserTab.__new__(BrowserTab)
    for name in ("start_btn", "stop_btn", "launch_btn", "export_btn", "proxy_state"):
        setattr(tab, name, Mock())
    tab.restore_recovered_session = Mock()
    monkeypatch.setattr(gui.MainApp, "build_ui", lambda self: setattr(self, "browser_tab", tab))
    showerror = Mock()
    monkeypatch.setattr(browser_tab_module.messagebox, "showerror", showerror)
    logger = Mock()
    monkeypatch.setattr(gui, "log_gui", logger)
    evidence_paths = [
        session_root / "session.json", session_root / "processes.json",
        runtime_root / "active-session.json", runtime_root / "active-session.lock",
    ]
    for path in evidence_paths:
        path.write_bytes(b"original evidence")
    before = {path: path.read_bytes() for path in evidence_paths}

    gui.MainApp()

    manager.recover_active.assert_called_once_with()
    assert manager.method_calls == [("recover_active", (), {})]
    assert {path: path.read_bytes() for path in evidence_paths} == before
    if isinstance(outcome, Exception):
        assert type(outcome).__name__ in tab.recovery_error
        assert str(outcome) in tab.recovery_error
        tab._update_launch_state()  # Later refreshes must also keep capture blocked.
        for name in ("start_btn", "stop_btn", "launch_btn", "export_btn"):
            getattr(tab, name).config.assert_called_with(state="disabled")
        tab.restore_recovered_session.assert_not_called()
        showerror.assert_called_once()
        assert tab.recovery_error in showerror.call_args.args[1]
        assert "review the recovery traceback" in showerror.call_args.args[1]
        logger.exception.assert_called_once()
    else:
        assert "recovery_error" not in tab.__dict__
        showerror.assert_not_called()
        if outcome is None:
            tab.restore_recovered_session.assert_not_called()
        else:
            tab.restore_recovered_session.assert_called_once_with(outcome)



def test_gui_module_invokes_main_when_run_as_a_module():
    gui_module = Path(__file__).parents[2] / "src" / "tzMCP" / "gui.py"
    module = ast.parse(gui_module.read_text(encoding="utf-8"))

    main_guards = [
        node
        for node in module.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and len(node.test.ops) == 1
        and isinstance(node.test.ops[0], ast.Eq)
        and len(node.test.comparators) == 1
        and isinstance(node.test.comparators[0], ast.Constant)
        and node.test.comparators[0].value == "__main__"
    ]

    assert any(
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == "main"
        for guard in main_guards
        for statement in guard.body
    )


def test_console_keeps_warnings_visible_when_gui_log_level_is_error(monkeypatch, tmp_path, capsys):
    """GUI support diagnostics must not be hidden by the in-app log level."""
    monkeypatch.setattr(
        log_config,
        "get_config",
        lambda: SimpleNamespace(log_to_file=False, log_level="ERROR"),
    )
    monkeypatch.setattr(log_config, "logs_dir", lambda: tmp_path / "logs")

    log_config.setup_logging()
    log_config.log_gui.warning("Browser executable is missing; re-add it in the GUI.")

    captured = capsys.readouterr()
    assert "[WARNING] Browser executable is missing" in captured.err
    assert log_config.log_gui.level == logging.WARNING


def test_capture_session_requires_a_portable_browser_acknowledgement():
    """The guided UI must make the risky browser choice explicit."""
    browser_tab = Path(__file__).parents[2] / "src" / "tzMCP" / "gui_bits" / "browser_tab.py"
    source = browser_tab.read_text(encoding="utf-8")

    assert "dedicated portable browser" in source
    assert "payment details" in source
    assert "safe_browser_acknowledged" in source


def test_recovered_session_is_exportable_before_a_new_session_starts():
    class Widget:
        def __init__(self):
            self.options = {}

        def config(self, **options):
            self.options.update(options)

    tab = BrowserTab.__new__(BrowserTab)
    tab.session = None
    tab.proxy_controller = SimpleNamespace(process=None)
    tab.safe_browser_acknowledged = SimpleNamespace(get=lambda: False)
    tab.start_btn = Widget()
    tab.stop_btn = Widget()
    tab.launch_btn = Widget()
    tab.export_btn = Widget()
    tab.proxy_state = Widget()
    activities = []
    tab.activity_logger = lambda entry: activities.extend(entry["lines"])

    recovered = SessionRecord(
        "20261016T000000Z-01234567", state=SessionState.INTERRUPTED
    )
    tab.restore_recovered_session(recovered)

    assert tab.session is recovered
    assert tab.start_btn.options["state"] == "disabled"
    assert tab.stop_btn.options["state"] == "disabled"
    assert tab.launch_btn.options["state"] == "disabled"
    assert tab.export_btn.options["state"] == "normal"
    assert "Export it before starting another session" in tab.proxy_state.options["text"]
    assert any("Recovered interrupted session" in line for line in activities)

    tab.session.state = SessionState.EXPORTED
    tab._update_launch_state()
    assert tab.start_btn.options["state"] == "normal"
    assert tab.export_btn.options["state"] == "disabled"


def test_recovery_failure_keeps_controls_disabled_on_later_refresh():
    class Widget:
        def config(self, **options):
            self.state = options["state"]

    tab = BrowserTab.__new__(BrowserTab)
    tab.recovery_error = "Close the original GUI before retrying"
    for name in ("start_btn", "stop_btn", "launch_btn", "export_btn"):
        setattr(tab, name, Widget())
    tab._update_launch_state()
    assert all(getattr(tab, name).state == "disabled" for name in (
        "start_btn", "stop_btn", "launch_btn", "export_btn"
    ))

def test_main_app_attaches_recovered_session_after_building_the_gui():
    gui_module = Path(__file__).parents[2] / "src" / "tzMCP" / "gui.py"
    source = gui_module.read_text(encoding="utf-8")

    build_ui = source.index("self.build_ui()")
    restore_session = source.index("self.browser_tab.restore_recovered_session(recovered)")
    build_ui_method = source.index("    def build_ui(self):")

    assert build_ui < restore_session < build_ui_method


def test_recovered_session_export_publishes_then_marks_session_exported(monkeypatch):
    class Widget:
        def __init__(self):
            self.options = {}

        def config(self, **options):
            self.options.update(options)

    record = SessionRecord("20261016T000000Z-01234567", state=SessionState.INTERRUPTED)
    exported = SessionRecord(record.session_id, state=SessionState.EXPORTED)
    archive = Path("/run/tzmcp/export-ready/20261016T000000Z-01234567.zip")
    export_result = SimpleNamespace(archive_path=archive, size=123, sha256="abc123")
    events = []
    tab = BrowserTab.__new__(BrowserTab)
    tab.session = record
    tab.session_manager = SimpleNamespace(
        complete_export=lambda *args: (events.append(("complete", args)) or exported)
    )
    tab.proxy_controller = SimpleNamespace(process=None)
    tab.firefox_session = None
    tab.export_service = SimpleNamespace(
        create_local_archive=lambda *args: (events.append(("create", args)) or export_result),
        publish=lambda result: events.append(("publish", result)),
    )
    tab.activity_logger = lambda event: events.append(("activity", event))
    tab.safe_browser_acknowledged = SimpleNamespace(get=lambda: False)
    tab.start_btn = Widget()
    tab.stop_btn = Widget()
    tab.launch_btn = Widget()
    tab.export_btn = Widget()

    monkeypatch.setattr(browser_tab_module, "is_appliance_mode", lambda: True)
    monkeypatch.setattr(browser_tab_module, "collect_versions", lambda path: {})

    tab._export_session()

    assert [event[0] for event in events] == ["create", "publish", "complete", "activity"]
    assert events[2][1] == (record.session_id, archive.name, 123, "abc123")
    assert tab.session is exported
    assert tab.start_btn.options["state"] == "normal"
    assert tab.export_btn.options["state"] == "disabled"


def test_export_publication_failure_keeps_local_archive_and_session_retryable(
    monkeypatch, tmp_path
):
    class Widget:
        def __init__(self):
            self.options = {}

        def config(self, **options):
            self.options.update(options)

    record = SessionRecord("20261016T000000Z-01234567", state=SessionState.ENDED)
    archive = tmp_path / "export-ready" / f"{record.session_id}.zip"
    archive.parent.mkdir()
    archive.write_bytes(b"completed archive")
    errors = []
    completed_exports = []

    def raise_publish_error(result):
        raise RuntimeError("host share unavailable")

    tab = BrowserTab.__new__(BrowserTab)
    tab.session = record
    tab.session_manager = SimpleNamespace(
        complete_export=lambda *args: completed_exports.append(args)
    )
    tab.proxy_controller = SimpleNamespace(process=None)
    tab.firefox_session = None
    tab.export_service = SimpleNamespace(
        create_local_archive=lambda *args: SimpleNamespace(
            archive_path=archive, size=archive.stat().st_size, sha256="archive-hash"
        ),
        publish=raise_publish_error,
    )
    tab.safe_browser_acknowledged = SimpleNamespace(get=lambda: False)
    tab.start_btn = Widget()
    tab.stop_btn = Widget()
    tab.launch_btn = Widget()
    tab.export_btn = Widget()
    tab.proxy_state = Widget()
    tab.status_bar = None
    tab.activity_logger = lambda event: None

    monkeypatch.setattr(browser_tab_module, "is_appliance_mode", lambda: True)
    monkeypatch.setattr(browser_tab_module, "collect_versions", lambda path: {})
    monkeypatch.setattr(
        browser_tab_module.messagebox,
        "showerror",
        lambda title, message: errors.append((title, message)),
    )

    tab._update_launch_state()
    tab._export_session()

    assert errors == [("Export failed", "host share unavailable")]
    assert archive.read_bytes() == b"completed archive"
    assert tab.session is record
    assert tab.session.state is SessionState.ENDED
    assert completed_exports == []
    assert tab.start_btn.options["state"] == "disabled"
    assert tab.export_btn.options["state"] == "normal"
