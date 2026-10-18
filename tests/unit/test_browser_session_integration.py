from types import SimpleNamespace

import pytest

import tzMCP.gui_bits.browser_tab as browser_tab_module
from tzMCP.gui_bits.browser_tab import BrowserTab
from tzMCP.gui_bits.config_manager import Config
from tzMCP.save_media import MediaSaver
from tzMCP.sessions.manager import SessionManager
from tzMCP.sessions.models import SessionState
from tzMCP.sessions.processes import ProcessIdentity


def test_session_manager_assigns_capture_config_to_proxy(
    tmp_path, monkeypatch, make_flow, make_png
):
    # Avoid constructing Tk; exercise the controller methods with a minimal
    # object because the lifecycle logic is deliberately kept in the view.
    tab = BrowserTab.__new__(BrowserTab)
    tab.session_manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    tab.config = Config(
        save_dir=tmp_path / "unused",
        proxy_port=9191,
        allowed_mime_groups=["image"],
        whitelist=["allowed.example"],
        blacklist=[],
        filter_file_size={"enabled": True, "min_bytes": 0, "max_bytes": 10_000_000},
        filter_pixel_dimensions={
            "min_width": 1, "min_height": 1,
            "max_width": 10_000, "max_height": 10_000,
        },
        auto_reload_config=False,
    )
    tab.proxy_controller = SimpleNamespace(
        config_path=tmp_path / "persistent.yaml",
        # MainApp synchronizes this from ConfigManager when the rules tab is
        # selected; the session must retain the same configured listener.
        proxy_port=9191,
        process=None,
        start_proxy=lambda: None,
        stop_proxy=lambda: None,
    )
    tab.persistent_config_path = tmp_path / "persistent.yaml"
    identity = ProcessIdentity(42, str(tmp_path / "proxy"), 123, "owner")
    tab.proxy_controller.start_proxy = lambda: tab.proxy_controller.on_process_started(identity)
    tab.session = None
    tab.start_btn = SimpleNamespace(config=lambda **_: None)
    tab.stop_btn = SimpleNamespace(config=lambda **_: None)
    tab.proxy_state = SimpleNamespace(config=lambda **_: None)
    tab.status_bar = None
    tab.safe_browser_acknowledged = SimpleNamespace(get=lambda: False)
    tab._append_activity = lambda *_: None
    monkeypatch.setattr(tab, "_update_launch_state", lambda: None)

    tab._start_proxy()

    assert tab.session.state is SessionState.RUNNING
    assert tab.session.process_records["proxy"] == identity.to_dict()
    assert tab.proxy_controller.config_path.name == "capture-config.yaml"
    assert tab.proxy_controller.proxy_port == 9191
    monkeypatch.setenv("TZMCP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TZMCP_AUTO_RELOAD", "0")
    addon = MediaSaver(config_path=tab.proxy_controller.config_path)
    addon.response(make_flow("http://img.allowed.example/pic.png", make_png(500, 500)))
    addon.response(make_flow("http://blocked.example/ignored.png", make_png(500, 500)))

    capture_dir = tab.session_manager.storage.session_dir(tab.session.session_id) / "capture"
    assert [path.name for path in capture_dir.iterdir()] == ["pic.png"]


def test_proxy_start_failure_is_recorded_and_preserves_exportable_session(
    tmp_path, monkeypatch
):
    class Widget:
        def __init__(self):
            self.options = {}

        def config(self, **options):
            self.options.update(options)

        def set_state(self, state):
            self.options["state"] = state

    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")

    def fail_start():
        raise RuntimeError("Port 8888 is already in use")

    tab = BrowserTab.__new__(BrowserTab)
    tab.session_manager = manager
    tab.config = Config(allowed_mime_groups=["image"])
    tab.proxy_controller = SimpleNamespace(
        config_path=tmp_path / "persistent.yaml",
        proxy_port=8888,
        process=None,
        start_proxy=fail_start,
    )
    tab.persistent_config_path = tmp_path / "persistent.yaml"
    tab.session = None
    tab.start_btn = Widget()
    tab.stop_btn = Widget()
    tab.launch_btn = Widget()
    tab.export_btn = Widget()
    tab.proxy_state = Widget()
    tab.status_bar = Widget()
    tab.safe_browser_acknowledged = SimpleNamespace(get=lambda: False)
    tab._append_activity = lambda *_args: None
    monkeypatch.setattr(browser_tab_module, "is_appliance_mode", lambda: True)

    tab._start_proxy()

    saved = manager.get(tab.session.session_id)
    assert saved.state is SessionState.INTERRUPTED
    assert saved.errors == ["Proxy startup failed: Port 8888 is already in use"]
    assert not manager.active_path.exists()
    assert tab.proxy_controller.config_path == tab.persistent_config_path.resolve()
    assert tab.status_bar.options["state"] == "error"
    assert tab.export_btn.options["state"] == "normal"
    assert "Port 8888 is already in use" in tab.proxy_state.options["text"]


@pytest.mark.parametrize("error", ["Firefox executable not found", "certutil failed (1)"])
def test_browser_start_failure_interrupts_session_and_preserves_capture(
    tmp_path, monkeypatch, error
):
    class Widget:
        def __init__(self):
            self.options = {}

        def config(self, **options):
            self.options.update(options)

        def set_state(self, state):
            self.options["state"] = state

    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(allowed_mime_groups=["image"]))
    record = manager.transition(record.session_id, SessionState.RUNNING)
    capture = manager.storage.session_dir(record.session_id) / "capture" / "original.png"
    capture.write_bytes(b"original capture")

    def fail_start(_url):
        raise RuntimeError(error)

    firefox = SimpleNamespace(start=fail_start, stop=lambda: None, cleanup=lambda: None)
    monkeypatch.setattr(browser_tab_module, "FirefoxSession", lambda *_args: firefox)
    monkeypatch.setattr(browser_tab_module.messagebox, "showerror", lambda *_args: None)
    monkeypatch.setattr(browser_tab_module, "is_appliance_mode", lambda: True)
    monkeypatch.setenv("TZMCP_FIREFOX_PATH", str(tmp_path / "firefox"))
    tab = BrowserTab.__new__(BrowserTab)
    tab.session_manager = manager
    tab.session = record
    tab.firefox_session = None
    tab.launch_url = SimpleNamespace(get=lambda: "about:blank")
    tab.proxy_controller = SimpleNamespace(
        proxy_port=8888, process=SimpleNamespace(poll=lambda: None)
    )

    def stop_proxy():
        tab.proxy_controller.process = None

    tab.proxy_controller.stop_proxy = stop_proxy
    tab.persistent_config_path = tmp_path / "persistent.yaml"
    for name in ("start_btn", "stop_btn", "launch_btn", "export_btn", "proxy_state", "status_bar"):
        setattr(tab, name, Widget())
    tab._append_activity = lambda *_args: None

    tab._launch_managed_firefox()

    saved = manager.get(record.session_id)
    assert saved.state is SessionState.INTERRUPTED
    assert error in saved.errors[0]
    assert saved.capture_count == 1
    assert capture.read_bytes() == b"original capture"
    assert not manager.active_path.exists()
    assert tab.proxy_controller.process is None
    assert tab.export_btn.options["state"] == "normal"
    assert tab.launch_btn.options["state"] == "disabled"


def test_second_firefox_launch_preserves_the_owned_browser(monkeypatch):
    tab = BrowserTab.__new__(BrowserTab)
    tab.session_manager = object()
    tab.session = object()
    owned = SimpleNamespace(process=object())
    tab.firefox_session = owned

    def unexpected_browser(*_args):
        pytest.fail("A second launch must not replace the owned Firefox session")

    monkeypatch.setattr(browser_tab_module, "FirefoxSession", unexpected_browser)

    tab._launch_managed_firefox()

    assert tab.firefox_session is owned
