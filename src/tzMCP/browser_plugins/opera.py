from pathlib import Path
from typing import List, Tuple

def setup_browser(path: Path, url: str, proxy_port: int, incognito: bool) -> Tuple[List[str], Path]:
    profile_dir = Path("profiles") / "opera"
    profile_dir.mkdir(parents=True, exist_ok=True)

    cmd = [str(path)]
    cmd += [
        f"--proxy-server=127.0.0.1:{proxy_port}",
        f"--user-data-dir={str(profile_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-default-apps",
        "--new-window"
    ]
    if incognito:
        cmd.append("--incognito")

    cmd.append(url)
    return cmd, profile_dir
