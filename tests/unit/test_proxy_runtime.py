from pathlib import Path

import pytest

from tzMCP.appliance import is_appliance_mode
from tzMCP.gui_bits.config_manager import Config
from tzMCP.proxy_runtime import ProxyLaunchSpec, build_proxy_command, launch_environment, write_config_snapshot


def test_appliance_mode_requires_exact_one(monkeypatch):
    monkeypatch.delenv("TZMCP_APPLIANCE", raising=False)
    assert is_appliance_mode() is False
    for value in ("0", "true", "yes", " 1"):
        monkeypatch.setenv("TZMCP_APPLIANCE", value)
        assert is_appliance_mode() is False
    monkeypatch.setenv("TZMCP_APPLIANCE", "1")
    assert is_appliance_mode() is True


def test_snapshot_and_command_use_explicit_config(tmp_path):
    cfg = Config(save_dir=tmp_path / "capture")
    snapshot = write_config_snapshot(cfg, tmp_path / "runtime")
    spec = ProxyLaunchSpec(snapshot, 9191, confdir=tmp_path / "ca", auto_reload=False)
    command = build_proxy_command(spec, tmp_path / "save_media.py", Path("mitmdump"))
    assert str(snapshot) not in command  # config crosses the addon boundary via env
    assert ["--listen-host", "127.0.0.1"] == command[command.index("--listen-host"):command.index("--listen-host") + 2]
    assert "confdir=" + str(tmp_path / "ca") in command
    env = launch_environment(spec)
    assert env["TZMCP_CONFIG_PATH"] == str(snapshot)
    assert env["TZMCP_AUTO_RELOAD"] == "0"


def test_command_rejects_missing_config(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_proxy_command(
            ProxyLaunchSpec(tmp_path / "missing.yaml", 8080),
            tmp_path / "save_media.py",
            Path("mitmdump"),
        )


def test_command_rejects_non_loopback_host(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("proxy_port: 8080\n", encoding="utf-8")
    with pytest.raises(ValueError, match="127.0.0.1"):
        build_proxy_command(
            ProxyLaunchSpec(config, 8080, host="0.0.0.0"),
            tmp_path / "save_media.py",
            Path("mitmdump"),
        )
