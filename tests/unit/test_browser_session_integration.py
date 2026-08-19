from types import SimpleNamespace

from tzMCP.gui_bits.browser_tab import BrowserTab
from tzMCP.gui_bits.config_manager import Config
from tzMCP.sessions.manager import SessionManager
from tzMCP.sessions.models import SessionState


def test_session_manager_assigns_capture_config_to_proxy(tmp_path, monkeypatch):
    # Avoid constructing Tk; exercise the controller methods with a minimal
    # object because the lifecycle logic is deliberately kept in the view.
    tab = BrowserTab.__new__(BrowserTab)
    tab.session_manager = SessionManager(tmp_path / "sessions", tmp_path / "runtime")
    tab.config = Config(save_dir=tmp_path / "unused")
    tab.proxy_controller = SimpleNamespace(
        config_path=tmp_path / "persistent.yaml",
        proxy_port=8888,
        process=None,
        start_proxy=lambda: None,
        stop_proxy=lambda: None,
    )
    tab.persistent_config_path = tmp_path / "persistent.yaml"
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
    assert tab.proxy_controller.config_path.name == "capture-config.yaml"
    snapshot = tab.proxy_controller.config_path.read_text(encoding="utf-8")
    assert str(tmp_path / "sessions") in snapshot
