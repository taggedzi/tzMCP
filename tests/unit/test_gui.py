import ast
import logging
from pathlib import Path
from types import SimpleNamespace

import tzMCP.gui_bits.browser_tab as browser_tab_module
from tzMCP.common_utils import log_config
from tzMCP.gui_bits.browser_tab import BrowserTab
from tzMCP.sessions.models import SessionRecord, SessionState



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
