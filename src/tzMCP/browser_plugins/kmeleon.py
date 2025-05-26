from pathlib import Path
from typing import List, Tuple

def setup_browser(path: Path, url: str, proxy_port: int, incognito: bool) -> Tuple[List[str], Path]:
    base_profile_dir = Path("profiles") / "kmeleon"
    profile_name = "default"
    profile_dir = base_profile_dir / profile_name
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Write profiles.dat to tell K-Meleon where to look
    profiles_dat = base_profile_dir / "profiles.ini"
    profiles_dat.write_text("""[General]
StartWithLastProfile=1

[Profile0]
Name=default
Path=default
IsRelative=1
Default=1
""", encoding="utf-8")
    

    # Write user preferences for proxy setup
    prefs = f"""
user_pref("network.proxy.type", 1);
user_pref("network.proxy.http", "127.0.0.1");
user_pref("network.proxy.http_port", {proxy_port});
user_pref("network.proxy.ssl", "127.0.0.1");
user_pref("network.proxy.ssl_port", {proxy_port});
user_pref("network.proxy.no_proxies_on", "localhost, 127.0.0.1");
"""

    prefs_file = profile_dir / "prefs.js"
    prefs_file.write_text(prefs.strip(), encoding="utf-8")

    compat = profile_dir / "compatibility.ini"
    compat.write_text("[Compatibility]\nLastVersion=75.1\n", encoding="utf-8")
    (profile_dir / "chrome").mkdir(exist_ok=True)

    cmd = [
        str(path),
        "-new",
        "-profilesDir", str(base_profile_dir.resolve()),
        "-P", profile_name
    ]
    if url:
        cmd.append(url)

    return cmd, profile_dir
