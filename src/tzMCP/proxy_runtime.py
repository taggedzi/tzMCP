"""The explicit configuration boundary between tzMCP and mitmdump."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

from tzMCP.gui_bits.config_manager import Config, ConfigManager


@dataclass(frozen=True)
class ProxyLaunchSpec:
    """All configuration needed by one mitmdump process."""

    config_path: Path
    port: int
    host: str = "127.0.0.1"
    log_dir: Path | None = None
    confdir: Path | None = None
    auto_reload: bool = True


def write_config_snapshot(config: Config, directory: Path, name: str = "capture-config.yaml") -> Path:
    """Write a validated config snapshot without changing the persistent YAML."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    data = {
        key: (str(value) if isinstance(value, Path) else value)
        for key, value in vars(config).items()
    }
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return path


def build_proxy_command(spec: ProxyLaunchSpec, script_path: Path, executable: Path) -> list[str]:
    """Build a loopback-only mitmdump command from an explicit launch spec."""
    if spec.host != "127.0.0.1":
        raise ValueError("tzMCP proxy must bind to 127.0.0.1")
    if not 1 <= spec.port <= 65535:
        raise ValueError("proxy port must be between 1 and 65535")
    if not spec.config_path.is_file():
        raise FileNotFoundError(f"Proxy config not found: {spec.config_path}")
    command = [str(executable), "-q", "--set", "console_eventlog_verbosity=info",
               "--listen-host", spec.host, "--listen-port", str(spec.port)]
    if spec.confdir is not None:
        command.extend(["--set", f"confdir={spec.confdir}"])
    command.extend(["-s", str(script_path)])
    return command


def launch_environment(spec: ProxyLaunchSpec) -> dict[str, str]:
    """Return environment values consumed by the addon process."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["TZMCP_CONFIG_PATH"] = str(spec.config_path)
    env["TZMCP_AUTO_RELOAD"] = "1" if spec.auto_reload else "0"
    if spec.log_dir is not None:
        env["TZMCP_LOG_DIR"] = str(spec.log_dir)
    if spec.confdir is not None:
        env["TZMCP_MITM_CONF_DIR"] = str(spec.confdir)
    return env
