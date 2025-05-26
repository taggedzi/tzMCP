from pathlib import Path
from typing import List, Tuple

def setup_browser(path: Path, url: str, proxy_port: int, incognito: bool) -> Tuple[List[str], Path]:
    profile_dir = Path("profiles") / "librewolf"
    profile_dir.mkdir(parents=True, exist_ok=True)

    userjs = profile_dir / "user.js"
    prefs = f"""
user_pref("network.proxy.type", 1);
user_pref("network.proxy.http", "127.0.0.1");
user_pref("network.proxy.http_port", {proxy_port});
user_pref("network.proxy.ssl", "127.0.0.1");
user_pref("network.proxy.ssl_port", {proxy_port});
user_pref("network.proxy.no_proxies_on", "localhost, 127.0.0.1");
user_pref("security.enterprise_roots.enabled", true);
"""
    userjs.write_text(prefs.strip(), encoding="utf-8")

    cmd = [str(path), "-profile", str(profile_dir.resolve())]
    if incognito:
        cmd.append("-private-window")
    cmd.append(url)

    return cmd, profile_dir
