from pathlib import Path
from types import SimpleNamespace

from tzMCP.gui import MainApp
from tzMCP.gui_bits.config_manager import Config, ConfigManager
from tzMCP.gui_bits.config_tab import ConfigTab


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class TextValue:
    def __init__(self, value):
        self.value = value

    def get(self, _start, _end):
        return self.value


def test_saving_capture_rules_updates_next_session_config(monkeypatch, tmp_path):
    old_config = Config()
    app = MainApp.__new__(MainApp)
    app.config = old_config
    app.browser_tab = SimpleNamespace(config=old_config)
    app.proxy_controller = SimpleNamespace(process=None, proxy_port=old_config.proxy_port)

    tab = SimpleNamespace(
        config_manager=ConfigManager(tmp_path / "config" / "media_proxy_config.yaml"),
        on_config_saved=app._on_config_saved,
        mime_group_vars={"image": Value(True)},
        proxy_port=Value(8890),
        save_dir_var=Value(str(tmp_path / "cache")),
        whitelist_box=TextValue(""),
        blacklist_box=TextValue("ads\\..*"),
        min_bytes=Value(10240),
        max_bytes=Value(157286400),
        min_width=Value(301),
        min_height=Value(301),
        max_width=Value(12000),
        max_height=Value(12000),
        auto_reload_config=Value(True),
        log_to_file=Value(False),
        log_level=Value("INFO"),
        enable_persistent_dedup=Value(False),
    )
    saved = []
    original_save = tab.config_manager.save_config
    tab.config_manager.save_config = lambda config: (saved.append(config), original_save(config))
    monkeypatch.setattr("tzMCP.gui_bits.config_tab.messagebox.showinfo", lambda *_args: None)

    ConfigTab._save(tab)

    assert len(saved) == 1
    assert app.config is saved[0]
    assert app.browser_tab.config is saved[0]
    assert app.proxy_controller.proxy_port == 8890
    assert saved[0].allowed_mime_groups == ["image"]
    assert saved[0].filter_file_size["min_bytes"] == 10240
    assert saved[0].filter_pixel_dimensions["min_width"] == 301
