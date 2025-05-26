import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
import psutil
import time
import importlib

APP_PROFILE_BASE = Path(__file__).parent.parent.parent.parent / "profiles"
APP_PROFILE_BASE.mkdir(parents=True, exist_ok=True)

# Global tracking for cleanup
BROWSER_PROCESSES: list[Tuple[subprocess.Popen, Path]] = []

def get_browser_profile_dir(browser_name: str) -> Path:
    profile_dir = APP_PROFILE_BASE / browser_name.lower()
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir

def detect_browser_name(path: Path) -> str:
    lower_path = str(path).lower()
    if "iron" in lower_path:
        return "iron"
    if "brave" in lower_path:
        return "brave"
    if "vivaldi" in lower_path:
        return "vivaldi"
    if "opera" in lower_path:
        return "opera"
    if "firefox" in lower_path:
        return "firefox"
    if "chrome" in lower_path:
        return "chrome"
    if "k-meleon" in lower_path:
        return "kmeleon"
    if "librewolf" in lower_path:
        return "librewolf"
    raise ValueError(f"Unknown browser type for path: {path}")

def launch_browser(
    path: Path,
    url: str,
    proxy_port: int,
    incognito: bool = False
) -> subprocess.Popen:
    if not path.exists():
        raise FileNotFoundError(f"Browser executable not found: {path}")

    browser_name = browser_name = detect_browser_name(path)
    print(f"🔧 Detected browser: {browser_name}")

    plugin_map = {
        "chrome": "tzMCP.browser_plugins.chrome",
        "firefox": "tzMCP.browser_plugins.firefox",
        "brave": "tzMCP.browser_plugins.brave",
        "opera": "tzMCP.browser_plugins.opera",
        "iron": "tzMCP.browser_plugins.iron",
        "vivaldi": "tzMCP.browser_plugins.vivaldi",
        "kmeleon": "tzMCP.browser_plugins.kmeleon",
        "librewolf": "tzMCP.browser_plugins.librewolf",
    }

    plugin_module_path = plugin_map.get(browser_name)
    if not plugin_module_path:
        raise NotImplementedError(f"No plugin handler for browser '{browser_name}'")

    plugin = importlib.import_module(plugin_module_path)
    cmd, profile_path = plugin.setup_browser(path, url, proxy_port, incognito)
    

    print("Launching:", " ".join(f'\"{c}\"' if ' ' in c else c for c in cmd))

    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    ps_proc = psutil.Process(proc.pid)
    BROWSER_PROCESSES.append((ps_proc, profile_path))
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
            print(f"⚠️ Could not kill process tree for PID {proc.pid}: {e}")
        try:
            safe_rmtree(path)
        except Exception as e:
            print(f"⚠️ Failed to clean profile: {e}")
    BROWSER_PROCESSES.clear()

def safe_rmtree(path: Path, attempts=5, delay=1.0):
    if not path.exists():
        print(f"🧹 Profile already deleted: {path}")
        return
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            print(f"🧹 Cleaned profile: {path}")
            return
        except Exception as e:
            print(f"⏳ Retry {attempt + 1}/{attempts} failed: {e}")
            time.sleep(delay)
    print(f"❌ Failed to delete profile after {attempts} attempts: {path}")

