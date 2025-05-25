import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
import psutil
import time

APP_PROFILE_BASE = Path(__file__).parent.parent.parent.parent / "profiles"
APP_PROFILE_BASE.mkdir(parents=True, exist_ok=True)

# Global tracking for cleanup
BROWSER_PROCESSES: list[Tuple[subprocess.Popen, Path]] = []

def get_browser_profile_dir(browser_name: str) -> Path:
    profile_dir = APP_PROFILE_BASE / browser_name.lower()
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir

def launch_browser(
    path: Path,
    url: str,
    proxy_port: int,
    incognito: bool = False
) -> subprocess.Popen:
    if not path.exists():
        raise FileNotFoundError(f"Browser executable not found: {path}")

    cmd = [str(path)]
    name = path.stem.lower()
    profile_path = get_browser_profile_dir(name)

    if "firefox" in name:
        cmd += ["-profile", str(profile_path)]
        if incognito:
            cmd.append("-private-window")
        _write_firefox_userjs(profile_path, proxy_port)
    else:
        cmd += [
            f"--proxy-server=127.0.0.1:{proxy_port}",
            f"--user-data-dir={str(profile_path)}",
        ]
        if incognito:
            cmd.append("--incognito")

    cmd.append(url)
    print("Launching:", " ".join(f'\"{c}\"' if ' ' in c else c for c in cmd))

    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    browser_proc = psutil.Process(proc.pid)
    BROWSER_PROCESSES.append((browser_proc, profile_path))

    BROWSER_PROCESSES.append((proc, profile_path))
    return proc

def _write_firefox_userjs(profile_path: Path, port: int):
    userjs = profile_path / "user.js"
    prefs = f"""
user_pref("network.proxy.type", 1);
user_pref("network.proxy.http", "127.0.0.1");
user_pref("network.proxy.http_port", {port});
user_pref("network.proxy.ssl", "127.0.0.1");
user_pref("network.proxy.ssl_port", {port});
user_pref("network.proxy.no_proxies_on", "");
user_pref("security.enterprise_roots.enabled", true);
"""
    userjs.write_text(prefs.strip(), encoding="utf-8")

def cleanup_browsers():
    for proc, path in BROWSER_PROCESSES:
        try:
            children = proc.children(recursive=True)
            for child in children:
                child.kill()
            proc.kill()
            print(f"✓ Killed browser tree for PID {proc.pid}")
        except Exception as e:
            print(f"⚠️ Failed to kill browser tree: {e}")
        try:
            safe_rmtree(path)
            print(f"🧹 Cleaned profile: {path}")
        except Exception as e:
            print(f"⚠️ Failed to clean profile: {e}")
    BROWSER_PROCESSES.clear()

def safe_rmtree(path: Path, attempts=5, delay=1.0):
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            print(f"🧹 Cleaned profile: {path}")
            return
        except Exception as e:
            print(f"⏳ Retry {attempt + 1}/{attempts} failed: {e}")
            time.sleep(delay)
    print(f"❌ Failed to delete profile after {attempts} attempts: {path}")

