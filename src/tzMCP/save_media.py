import sys; sys.dont_write_bytecode = True
import os, re, time, threading, sys
from urllib.parse import urlparse, unquote
from pathlib import Path
from io import BytesIO
from datetime import datetime
from mitmproxy import http, ctx
from PIL import Image, UnidentifiedImageError
from tzMCP.config_manager import ConfigManager, Config  # after path tweak

# ---------------------------------------------------------------------------
# Path & import setup
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent.parent           # project root
CONFIG_DIR = BASE_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "media_proxy_config.yaml"
SAVE_MEDIA_DIR = BASE_DIR / "scripts"
SAVE_MEDIA_PY = SAVE_MEDIA_DIR / "save_media.py"
LOGS_DIR  = BASE_DIR / "logs"
DOMAINS_LOG_PATH = LOGS_DIR / "domains_seen.txt"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Ensure project and scripts dirs on sys.path
for p in (BASE_DIR, BASE_DIR / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config() -> Config:
    return ConfigManager(CONFIG_PATH).load_config()


def _log_skip(reason: str):
    """Log a red‑colored skip reason in mitmproxy console."""
    ctx.log.error(f"⏭ {reason}")


class MediaSaver:
    """Addon that saves responses matching config filters and logs skip reasons."""

    def __init__(self):
        print("TRACE-B  ▶  MediaSaver.__init__ started")
        self.config: Config = _load_config()
        self._compile_filters()
        print("TRACE-C  ▶  MediaSaver.__init__ finished")
        ctx.log.info("MediaSaver loaded ✅")
        if self.config.auto_reload_config:
            threading.Thread(target=self._watch_config, daemon=True).start()

    # -------------------------------------------------------------------
    # Config handling
    # -------------------------------------------------------------------
    def _watch_config(self):
        last = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else None
        while True:
            time.sleep(5)
            if CONFIG_PATH.exists():
                m = CONFIG_PATH.stat().st_mtime
                if m != last:
                    self.config = _load_config()
                    self._compile_filters()
                    ctx.log.info("🔄 MediaSaver config reloaded")
                    last = m

    def _compile_filters(self):
        # Extension regex (allow query params)
        exts = [ext.lstrip('.') for ext in self.config.extensions]
        self.ext_pattern = re.compile(r"\.(" + "|".join(re.escape(e) for e in exts) + r")(?:$|\?)", re.I)
        # Whitelist/Blacklist
        wl = [p for p in self.config.whitelist if p.strip()]
        bl = [p for p in self.config.blacklist if p.strip()]
        self.whitelist_pattern = re.compile("|".join(wl)) if wl else None
        self.blacklist_pattern = re.compile("|".join(bl)) if bl else None
        # Pixel + size
        pd = self.config.filter_pixel_dimensions
        self.pixel_enabled = pd.get("enabled", False)
        self.min_w, self.min_h = pd.get("min_width", 0), pd.get("min_height", 0)
        self.max_w, self.max_h = pd.get("max_width", 1e9), pd.get("max_height", 1e9)
        fs = self.config.filter_file_size
        self.size_enabled = fs.get("enabled", False)
        self.min_bytes, self.max_bytes = fs.get("min_bytes", 0), fs.get("max_bytes", 1e12)
        # Save dir
        self.save_dir = self.config.save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------
    # mitmproxy hooks
    # -------------------------------------------------------------------
    def response(self, flow: http.HTTPFlow):
        print("TRACE-D  ▶  response() entered for", flow.request.url[:60])
        url = flow.request.url
        domain = flow.request.host
        content = flow.response.content
        size = len(content)

        # 1. Extension filter
        if not self.ext_pattern.search(url):
            _log_skip(f"{url} extension not allowed")
            return

        # 2. Domain filters
        if self.whitelist_pattern and not self.whitelist_pattern.search(domain):
            _log_skip(f"{url} domain not whitelisted")
            return
        if self.blacklist_pattern and self.blacklist_pattern.search(domain):
            _log_skip(f"{url} domain blacklisted")
            return

        # 3. Size filter
        if self.size_enabled and not (self.min_bytes <= size <= self.max_bytes):
            _log_skip(f"{url} {size}B not in [{self.min_bytes},{self.max_bytes}]")
            return

        # 4. Pixel filter
        if self.pixel_enabled:
            try:
                img = Image.open(BytesIO(content))
                w, h = img.size
                if not (self.min_w <= w <= self.max_w and self.min_h <= h <= self.max_h):
                    _log_skip(f"{url}: {w}x{h}px not in range")
                    return
            except UnidentifiedImageError:
                _log_skip(f"{url} not an image for pixel check")
                return

        # 5. Save file
        fname = unquote(os.path.basename(urlparse(url).path))
        save_path = self.save_dir / fname
        try:
            with save_path.open('wb') as f:
                f.write(content)
            ctx.log.info(f"[+] Saved → {save_path} ({size}B)")
        except Exception as e:
            ctx.log.error(f"[!] Save failed: {e}")
            return

        # 6. Log domain
        if self.config.log_seen_domains:
            with DOMAINS_LOG_PATH.open("a", encoding="utf-8") as domf:
                domf.write(domain + "\n")


# ---------------------------------------------------------------------------
# Activate addon
# ---------------------------------------------------------------------------
ctx.log.info("💡 MediaSaver module loaded")  # optional one-time banner
print("TRACE-E  ▶  module bottom reached, registering addon")
addons = [MediaSaver()]  # <- EXACTLY this, at column 0