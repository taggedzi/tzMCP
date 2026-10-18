from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import tzMCP.gui_bits.browser_tab as browser_tab_module
from tzMCP.gui_bits.browser_tab import BrowserTab
from tzMCP.gui_bits.config_manager import Config, ConfigManager
from tzMCP.save_media import MediaSaver
from tzMCP.sessions.manager import SessionManager
from tzMCP.sessions.models import SessionState
from tzMCP.sessions.processes import ProcessIdentity
from tzMCP.gui_bits import proxy_control
from tzMCP.gui_bits.proxy_control import ProxyController


@pytest.mark.parametrize("action", ["_stop_proxy", "shutdown"])
def test_shutdown_retry_checks_children_after_parent_exit_before_enabling_export(tmp_path, monkeypatch, action):
    class Widget:
        def __init__(self):
            self.options = {}

        def config(self, **options):
            self.options.update(options)

    manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    record = manager.create_session(Config(save_dir=tmp_path / "unused"))
    identity = ProcessIdentity(42, "/proxy", 123, "owner", session_id=42)
    manager.record_process(record.session_id, "proxy", identity)
    record = manager.transition(record.session_id, SessionState.RUNNING)
    capture = manager.storage.session_dir(record.session_id) / "capture" / "keep.bin"
    capture.write_bytes(b"captured evidence")
    controller = ProxyController(str(tmp_path / "addon.py"))
    process = Mock()
    process.poll.return_value = None
    controller.process = process
    controller.identity = identity
    stop_tree = Mock(side_effect=[
        RuntimeError("Capture spawned more processes"),
        RuntimeError("Capture children still alive"),
        None,
    ])
    monkeypatch.setattr(proxy_control, "stop_owned_process_tree", stop_tree)
    monkeypatch.setattr(browser_tab_module, "is_appliance_mode", lambda: True)

    tab = BrowserTab.__new__(BrowserTab)
    tab.session_manager = manager
    tab.session = record
    tab.firefox_session = None
    tab.proxy_controller = controller
    tab.persistent_config_path = tmp_path / "persistent.yaml"
    tab.status_bar = None
    tab._append_activity = lambda *_args: None
    for name in ("start_btn", "stop_btn", "launch_btn", "export_btn", "proxy_state"):
        setattr(tab, name, Widget())

    for attempt in range(2):
        if action == "shutdown":
            with pytest.raises(RuntimeError, match="Capture"):
                tab.shutdown()
        else:
            tab._stop_proxy()
        tab._update_launch_state()
        assert stop_tree.call_count == attempt + 1
        assert controller.identity is identity
        assert controller.process is process
        assert manager.get(record.session_id).state is SessionState.RUNNING
        assert manager.active_path.exists()
        assert manager.lock_path.exists()
        assert tab.export_btn.options["state"] == "disabled"
        assert capture.read_bytes() == b"captured evidence"
        process.poll.return_value = 0

    getattr(tab, action)()
    tab._update_launch_state()
    assert stop_tree.call_count == 3
    assert controller.identity is None
    assert controller.process is None
    expected = SessionState.INTERRUPTED if action == "shutdown" else SessionState.ENDED
    assert manager.get(record.session_id).state is expected
    assert not manager.active_path.exists()
    assert tab.export_btn.options["state"] == "normal"


def test_session_manager_assigns_capture_config_to_proxy(
    tmp_path, monkeypatch, make_flow, make_png
):
    # Avoid constructing Tk; exercise the controller methods with a minimal
    # object because the lifecycle logic is deliberately kept in the view.
    monkeypatch.setattr(browser_tab_module, "is_appliance_mode", lambda: True)
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
    tab.firefox_session = None
    tab._stop_proxy()
    assert tab.proxy_controller.config_path == tab.persistent_config_path.resolve()


def test_native_capture_restarts_with_persistent_config_and_reloads_rules(
    tmp_path, monkeypatch, make_flow, make_png
):
    import tzMCP.save_media as save_media

    monkeypatch.delenv("TZMCP_APPLIANCE", raising=False)
    monkeypatch.delenv("TZMCP_AUTO_RELOAD", raising=False)
    monkeypatch.setenv("TZMCP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(browser_tab_module.ttk.Frame, "__init__", lambda *_: None)
    monkeypatch.setattr(browser_tab_module.tk, "StringVar", lambda **_: Mock())
    monkeypatch.setattr(browser_tab_module.tk, "BooleanVar", lambda **_: Mock())
    monkeypatch.setattr(BrowserTab, "_load_browser_paths", lambda _: {})

    def build_widgets(tab):
        for name in ("start_btn", "stop_btn", "launch_btn", "export_btn", "proxy_state"):
            setattr(tab, name, Mock())

    monkeypatch.setattr(BrowserTab, "_build_widgets", build_widgets)
    config_path = tmp_path / "media_proxy_config.yaml"
    config = Config(
        save_dir=tmp_path / "native-captures", allowed_mime_groups=["image"],
        whitelist=[], blacklist=[],
        filter_file_size={"enabled": True, "min_bytes": 0, "max_bytes": 10_000_000},
        filter_pixel_dimensions={
            "min_width": 1, "min_height": 1, "max_width": 10_000, "max_height": 10_000,
        },
    )
    config_manager = ConfigManager(config_path)
    config_manager.save_config(config)
    controller = SimpleNamespace(config_path=config_path, process=None, proxy_port=8080)
    started_paths = []

    def start_proxy():
        started_paths.append(controller.config_path)
        controller.process = SimpleNamespace(poll=lambda: None)

    controller.start_proxy = start_proxy
    controller.stop_proxy = lambda: setattr(controller, "process", None)
    manager = Mock()
    tab = BrowserTab(None, controller, session_manager=manager, config=config,
                     persistent_config_path=config_path)
    assert tab.session_manager is None
    assert tab.export_service is None
    tab._start_proxy()

    watcher = Mock()
    monkeypatch.setattr(save_media, "Observer", lambda: watcher)
    addon = MediaSaver(config_path=controller.config_path)
    watcher.start.assert_called_once()
    assert addon.config.save_dir == config.save_dir
    addon.response(make_flow("http://example.com/first.png", make_png(500, 500)))
    assert (config.save_dir / "first.png").is_file()

    config.save_dir = tmp_path / "changed-captures"
    config_manager.save_config(config)
    # Exercise the watcher's reload callback synchronously, without a timer.
    addon._debounced_reload()
    assert addon.config.save_dir == config.save_dir
    addon.response(make_flow("http://example.com/second.png", make_png(501, 500)))
    assert (config.save_dir / "second.png").is_file()
    addon.done()

    tab._stop_proxy()
    tab.start_btn.config.assert_called_with(state="normal")
    tab.export_btn.config.assert_called_with(state="disabled")
    tab._start_proxy()
    assert started_paths == [config_path, config_path]
    assert tab.session is None
    assert manager.method_calls == []
    tab._stop_proxy()


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
