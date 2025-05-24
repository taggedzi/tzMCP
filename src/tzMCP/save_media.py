from mimetypes import guess_extension
import os
from io import BytesIO
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse
from PIL import Image
from mitmproxy import http, ctx
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tzMCP.gui_bits.config_manager import ConfigManager, Config
from tzMCP.save_media_utils import config_provider
from tzMCP.save_media_utils.config_provider import get_config
from tzMCP.save_media_utils.save_media_utils import (
    log_duration, safe_filename, detect_mime, log
)

ENABLE_PERFORMANCE_CHECK = True

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback()

def is_extension_blocked(ext:str = None, fname:str = None):
    """Test Extensions against config file requested extensions"""
    start_ext_check = perf_counter()
    response = False
    allowed_exts = set(e.lower() for e in get_config().extensions)
    if ext.lower() not in allowed_exts:
        ctx.log.info(f"Skipping file with extension {ext.lower()} because it is not in the config's extensions list.")
        log("warn", "orange", f"⏭ Skipped file {fname}", f"\tReason: {ext.lower()} is not in the config's extensions list.")
        response = True
    if ENABLE_PERFORMANCE_CHECK:
        log_duration("File Extension Check", start_ext_check)
    return response

def is_file_size_out_of_bounds(size:int, fname:str = None):
    """Test Size against config file requested size"""
    start_size_check = perf_counter()
    response = False
    config = get_config()
    if config.filter_file_size.get("enabled"):
        min_b = config.filter_file_size["min_bytes"]
        max_b = config.filter_file_size["max_bytes"]
        if not min_b <= size <= max_b:
            log("warn", "orange",
                f"⏭ Skipped {fname}", f"\tReason: {size} b not between [{min_b},{max_b}] bytes.")
            response = True
    if ENABLE_PERFORMANCE_CHECK:
        log_duration("File Size Check", start_size_check)
    return response

def is_domain_blocked_by_whitelist(url:str, fname:str = None):
    """
    Check domain whitelist 
    IF whitelist is NOT set (ie []), then allow all domains
    IF whitelist is set, then only allow domains that are in the list
    """
    start_whitelist_check = perf_counter()
    response = False
    config = get_config()
    if config.whitelist:
        netloc = urlparse(url).hostname or ""
        if not any(domain in netloc for domain in config.whitelist):
            log("warn", "orange",
                f"⏭ Skipped {fname}", f"\tURL: {url}", "\tReason: domain not in whitelist.")
            response = True
    if ENABLE_PERFORMANCE_CHECK:
        log_duration("Whitelist check", start_whitelist_check)
    return response

def is_domain_blacklisted(url:str, fname:str = None):
    """
    Check domain blacklist 
    IF blacklist is NOT set (ie []), then allow all domains
    IF blacklist is set, then only allow domains that are not in the list
    """
    start_blacklist_check = perf_counter()
    response = False
    config = get_config()
    if config.blacklist:
        netloc = urlparse(url).hostname or ""
        if any(domain in netloc for domain in config.blacklist):
            log("warn", "orange",
                f"⏭ Skipped {fname}", f"\tURL: {url}", "\tReason: domain in blacklist.")
            response = True
    if ENABLE_PERFORMANCE_CHECK:
        log_duration("Blacklist check", start_blacklist_check)
    return response


def is_valid_image(content: bytes):
    try:
        img = Image.open(BytesIO(content))
        img.verify()  # Verify header-only, no full decode
        return True
    except Exception:
        return False

def is_image_size_out_of_bounds(content: bytes, fname: str = None):
    start_image_pixel_dimension_check = perf_counter()
    response = False
    config = get_config()
    if config.filter_pixel_dimensions:
        try:
            img = Image.open(BytesIO(content))
            w, h = img.size
            min_w = config.filter_pixel_dimensions.get("min_width", 1)
            max_w = config.filter_pixel_dimensions.get("max_width", 999999)
            min_h = config.filter_pixel_dimensions.get("min_height", 1)
            max_h = config.filter_pixel_dimensions.get("max_height", 999999)
            if w < min_w or w > max_w or h < min_h or h > max_h:
                log("warn", "orange", f"⏭ Skipped file {fname}", f"Reason: ({w}x{h} not in allowed ranges)")
                response = True
        except Exception as e:
            log("error", "red", f"⛔ Pixel check failed: {e}")
        if ENABLE_PERFORMANCE_CHECK:
            log_duration("Image Size Check", start_image_pixel_dimension_check)
        return response


class MediaSaver:
    def __init__(self):
        # Setup Pathing
        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = self.project_root / "config" / "media_proxy_config.yaml"
        self.log_path = self.project_root / "logs" / "domains_seen.txt"
        
        # Setup Config Manager
        self.cfg_manager = ConfigManager(self.config_path)
        self.config = Config()   # Start with empty config
        self._observer = None
        self._load_config()      # Load the config file and share with other files in real time.
        self._start_watcher()    # Setup Watchdog to monitor the config file for updates.
        
        ctx.log.info(f"MediaSaver addon initialized → {self.config.save_dir}")
        log("info", "black", f"MediaSaver addon initialized → {self.config.save_dir}")

    def _load_config(self):
        try:
            self.config: Config = self.cfg_manager.load_config()  # Load config from file and store locally
            config_provider.set_config(self.config)       # Share with other files in real time.
            
            ctx.log.info("MediaServer: 🔄 Reloaded config")
            log("info", "blue", "MediaServer: 🔄 Reloaded config")
        except Exception as e:
            
            ctx.log.error(f"Failed to load config: {e}")
            log("error", "red", f"Failed to load config: {e}")
            config_provider.set_config({})

    def _start_watcher(self):
        """Start watchdog observer to watch the config file."""
        if not self.config_path.exists():
            ctx.log.error(f"⚠ Cannot watch config; file does not exist: {self.config_path}")
            log("error", "red", f"⚠ Cannot watch config; file does not exist: {self.config_path}")
            return
        
        try:
            event_handler = ConfigChangeHandler(self._on_config_change)
            observer = Observer()
            observer.schedule(event_handler, str(self.config_path), recursive=False)
            observer.daemon = True
            observer.start()
            self._observer = observer  # Store if you ever need to stop it

        except Exception as e:
            ctx.log.error(f"⚠ Failed to start config watcher: {e}")
            log("error", "red", f"Failed to start config watcher: {e}")

    def _on_config_change(self):
        self._load_config()
        ctx.log.info("🔄 Config reloaded via watcher.")
        log("info", "blue", "🔄 Config reloaded via watcher.")

    def done(self):
        """Called when mitmproxy shuts down."""
        if hasattr(self, "_observer") and self._observer:
            self._observer.stop()
            self._observer.join()
            ctx.log.info("🛑 Config watcher stopped cleanly.")
            log("info", "blue", "🛑 Config watcher stopped cleanly.")

    def response(self, flow: http.HTTPFlow):
        start_total = perf_counter()
        content = flow.response.content
        url = flow.request.pretty_url
        size = len(content)

        clean_url = url.split("?", 1)[0]
        basename = os.path.basename(clean_url)
        ext = os.path.splitext(basename)[1] or guess_extension(flow.response.headers.get("content-type", "").split(";")[0]) or ".bin"
        fname = safe_filename(basename, ext, fallback_url=url)
        mime_type = detect_mime(content)
        log('info', "green", f"{fname}{ext} -> {mime_type}, {size} bytes")

        # Test Extensions against config file requested extensions
        if is_extension_blocked(ext, fname):
            return
        
        if is_file_size_out_of_bounds(size, fname):
            return

        if is_domain_blocked_by_whitelist(url, fname):
            return

        if is_domain_blacklisted(url, fname):
            return

        if is_valid_image(content) and is_image_size_out_of_bounds(content, fname):
            return



        save_path = self.config.save_dir / fname
        try:
            with save_path.open('wb') as f:
                f.write(content)
            log("info", "green", f"💾 Saved → {save_path} ({size} B)")
        except Exception as e:
            log("error", "red", f"❌ Save failed: {e}")
        log_duration("response()", start_total)

addons = [MediaSaver()]
