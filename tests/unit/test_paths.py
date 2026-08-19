from tzMCP.gui_bits.config_manager import Config, ConfigManager
from tzMCP.paths import (
    ca_dir,
    config_dir,
    data_dir,
    ensure_runtime_dirs,
    export_ready_dir,
    logs_dir,
    profiles_dir,
    runtime_dir,
    sessions_dir,
)


def test_runtime_paths_use_configured_data_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("TZMCP_DATA_DIR", str(tmp_path / "tzmcp-data"))

    expected = tmp_path / "tzmcp-data"
    assert data_dir() == expected
    assert config_dir() == expected / "config"
    assert logs_dir() == expected / "logs"
    assert profiles_dir() == expected / "profiles"
    assert sessions_dir() == expected / "sessions"
    assert ca_dir() == expected / "ca" / "mitmproxy"
    assert runtime_dir() == expected / "runtime"
    assert export_ready_dir() == expected / "export-ready"


def test_runtime_directories_are_private(tmp_path, monkeypatch):
    monkeypatch.setenv("TZMCP_DATA_DIR", str(tmp_path / "data"))
    ensure_runtime_dirs()
    for path in (sessions_dir(), ca_dir(), runtime_dir(), export_ready_dir()):
        assert path.is_dir()
        if path.stat().st_mode & 0o777 != 0o700:
            # Windows does not expose POSIX owner mode semantics.
            assert __import__("os").name == "nt"


def test_config_defaults_and_location_use_data_directory(tmp_path, monkeypatch):
    data_root = tmp_path / "portable-data"
    monkeypatch.setenv("TZMCP_DATA_DIR", str(data_root))

    config_manager = ConfigManager()
    assert config_manager.config_path == data_root / "config" / "media_proxy_config.yaml"
    assert Config.__dataclass_fields__["save_dir"].default_factory() == data_root / "cache"
