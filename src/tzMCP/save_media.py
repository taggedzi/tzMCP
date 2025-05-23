import os
import sys
import time
import mimetypes
import threading
from urllib.parse import urlparse, unquote
from mitmproxy import http, ctx
from pathlib import Path
import yaml
import re
from io import BytesIO

# ---------------------------------------------------------------------------
# Path & import setup
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent.parent.parent           # project root
CONFIG_DIR = BASE_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "media_proxy_config.yaml"
LOGS_DIR  = BASE_DIR / "logs"
DOMAINS_LOG_PATH = LOGS_DIR / "domains_seen.txt"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Ensure project and scripts dirs on sys.path
for p in (BASE_DIR, BASE_DIR / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tzMCP.config_manager import ConfigManager, Config  # after path tweak

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}

def detect_mime(content: bytes, headers: dict) -> str:
    mime = headers.get("content-type", "").lower().split(";")[0].strip()

    if not mime and HAS_MAGIC:
        try:
            mime = magic.from_buffer(content, mime=True)
        except Exception:
            mime = ""

    if not mime or mime == "application/x-empty":
        if content.startswith(b"RIFF") and b"WEBP" in content[8:16]:
            mime = "image/webp"

    return mime

class MediaSaver:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.save_dir = Path(self.config.save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        if self.config.auto_reload_config:
            self._start_watcher()
        
        self.last_config_time = 0
        ctx.log.info(f"MediaSaver addon initialized 💡→ {self.save_dir}")
        print(f"MediaSaver addon initialized 💡→ {self.save_dir}", flush=True)

    def _watch_config(self):
        try:
            self.config = self.config_manager.load_config()
            ctx.log.info("MediaServer: 🔄 Reloaded config")
            print("MediaServer: 🔄 Reloaded config")
        except Exception as e:
            ctx.log.error(f"MediaSaver: Failed to reload config: {e}")
            print(f"MediaSaver: Failed to reload config: {e}")

    def _start_watcher(self):
        def watch():
            while True:
                self._watch_config()
                time.sleep(2)
        threading.Thread(target=watch, daemon=True).start()

    def response(self, flow: http.HTTPFlow):
        url = flow.request.pretty_url
        content = flow.response.content
        size = len(content)
        mime = detect_mime(content, flow.response.headers)

        ext = EXT_MAP.get(mime, mimetypes.guess_extension(mime) or ".bin")

        # Extract filename or generate
        raw_path = urlparse(url).path
        fname = unquote(os.path.basename(raw_path))
        if not fname or "." not in fname:
            fname = f"file_{int(time.time() * 1000)}{ext}"
        elif not os.path.splitext(fname)[1]:
            fname += ext

        # Check extension filter
        if self.config.extensions and ext.lower() not in [e.lower() for e in self.config.extensions]:
            print(f"⏭ Skipped {fname} \n\tURL: {url}\n\tReason: extension {ext} not allowed", flush=True)
            return

        # Check whitelist
        if self.config.whitelist and not any(re.search(pat, url) for pat in self.config.whitelist):
            print(f"⏭ Skipped {fname}\n\tURL: {url}\n\tReason not in whitelist.", flush=True)
            return

        # Check blacklist
        if any(re.search(pat, url) for pat in self.config.blacklist):
            print(f"⏭ Skipped {fname}\n\tURL: {url}\n\tReason in blacklist.", flush=True)
            return

        # Image/video filtering by size/dimensions
        is_image = mime.startswith("image/")
        is_video = mime.startswith("video/")

        if is_image and self.config.filter_pixel_dimensions.get("enabled"):
            try:
                from PIL import Image
                img = Image.open(BytesIO(content))
                w, h = img.size
                if not (self.config.filter_pixel_dimensions["min_width"] <= w <= self.config.filter_pixel_dimensions["max_width"] and
                        self.config.filter_pixel_dimensions["min_height"] <= h <= self.config.filter_pixel_dimensions["max_height"]):
                    print(f"⏭ Skipped {fname}\n\tURL: {url}\n\tReason: dimensions {w}x{h} outside range", flush=True)
                    return
            except Exception as e:
                print(f"⏭ Skipped {fname}\n\tURL: {url}\n\tReason: could not read image size\n{e}", flush=True)
                return

        if (is_image or is_video) and self.config.filter_file_size.get("enabled"):
            min_b = self.config.filter_file_size["min_bytes"]
            max_b = self.config.filter_file_size["max_bytes"]
            if not (min_b <= size <= max_b):
                print(f"⏭ Skipped {fname}\n\tURL: {url}\n\tReason: {size} bytes not between [{byte_cfg['min_bytes']},{byte_cfg['max_bytes']}]) bytes", flush=True)
                return

        save_path = self.save_dir / fname
        try:
            with save_path.open('wb') as f:
                f.write(content)
            print(f"💾 Saved → {save_path} ({size}B)", flush=True)
        except Exception as e:
            print(f"Save failed: {e}", flush=True)

addons = [MediaSaver()]