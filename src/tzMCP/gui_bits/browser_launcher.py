from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import yaml
import tempfile

# Path to YAML containing browser executable commands (moved under config/)
BROWSER_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "browser_paths.yaml"

def setup_chromium_browser(
    base_cmd: List[str],
    url: str,
    proxy_port: int
) -> List[str]:
    cmd = list(base_cmd)

    temp_profile = Path(tempfile.mkdtemp(prefix="edge_proxy_profile_"))

    cmd += [
        # f"--proxy-server=127.0.0.1:{proxy_port}",
        f"--proxy-server=http=127.0.0.1:{proxy_port};https=127.0.0.1:{proxy_port}",
        "--dns-prefetch-disable",
        "--disable-features=DNSOverHTTPS,PrefetchPrivacyChanges",
        "--no-first-run",
        "--no-default-browser-check",
        # f"--user-data-dir={str(temp_profile)}",
        "--new-window",
        # "--inprivate",
        url
    ]

    return cmd



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
    user_data_dir: Optional[Path] = None  # unused now
) -> None:
    """
    Launch a browser by name with optional proxy, using system profile.
    """
    command = LAUNCH_COMMANDS.get(browser_name.lower())
    if not command:
        raise ValueError(f"Unsupported browser: {browser_name}")

    lower = browser_name.lower()
    if lower in ("chrome", "brave", "edge", "google-chrome"):
        cmd = setup_chromium_browser(command, url, proxy_port)
    elif lower == "firefox":
        # We'll handle this separately later
        raise NotImplementedError("Firefox launch logic not implemented yet.")
    else:
        # Generic fallback
        cmd = list(command)
        if proxy_port:
            cmd.insert(1, f"--proxy-server=127.0.0.1:{proxy_port}")
        cmd.append(url)

    print("Launching browser:", " ".join(cmd))
    subprocess.Popen(cmd)
