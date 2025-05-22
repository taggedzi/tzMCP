from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import yaml

# Path to YAML containing browser executable commands (moved under config/)
BROWSER_CONFIG_PATH = Path(__file__).parent.parent / "config" / "browser_paths.yaml"


def _load_browser_commands() -> Dict[str, List[str]]:
    """Load browser commands from a YAML file, normalize into lists."""
    commands: Dict[str, List[str]] = {}
    if BROWSER_CONFIG_PATH.exists():
        with BROWSER_CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for key, val in data.items():
            name = key.lower()
            if isinstance(val, str):
                commands[name] = [val]
            elif isinstance(val, list):
                commands[name] = val
            else:
                continue
    return commands

# Loaded at import
LAUNCH_COMMANDS: Dict[str, List[str]] = _load_browser_commands()


def launch_browser(
    browser_name: str,
    url: str,
    proxy_port: Optional[int] = None,
    user_data_dir: Optional[Path] = None
) -> None:
    """
    Launch a browser by name to open the given URL, optionally with proxy and custom profile.

    Raises:
        ValueError: If browser_name not in config
    """
    command = LAUNCH_COMMANDS.get(browser_name.lower())
    if not command:
        raise ValueError(f"Unsupported browser: {browser_name}")
    cmd: List[str] = list(command)
    lower = browser_name.lower()
    if lower in ('chrome', 'google-chrome', 'brave', 'edge'):
        cmd.insert(1, '--new-window')
    if proxy_port:
        cmd.append(f"--proxy-server=127.0.0.1:{proxy_port}")
    if user_data_dir:
        cmd.append(f"--user-data-dir={str(user_data_dir)}")
    cmd.append(url)
    subprocess.Popen(cmd)
