from mimetypes import guess_extension
import os
from pathlib import Path
from time import perf_counter
from mitmproxy import http, ctx
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tzMCP.gui_bits.config_manager import ConfigManager, Config
from tzMCP.save_media_utils import config_provider
from tzMCP.save_media_utils.save_media_utils import (
    log_duration, safe_filename, detect_mime, log,
    is_valid_image, is_mime_type_allowed, is_file_size_out_of_bounds,
    is_domain_blocked_by_whitelist, is_domain_blacklisted,
    is_image_size_out_of_bounds, does_header_match_size,
    is_directory_traversal_attempted, atomic_save
)

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback()

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
        log('info', "brown", f"{fname} -> {mime_type}, {size} bytes")

        if (not does_header_match_size(flow.response.headers.get("Content-Length"), size, url) or 
            is_file_size_out_of_bounds(size, fname) or
            not is_mime_type_allowed(mime_type, fname) or
            is_domain_blocked_by_whitelist(url, fname) or
            is_domain_blacklisted(url, fname)):
            return
        
        if is_valid_image(content) and is_image_size_out_of_bounds(content, fname):
            return

        save_path = (self.config.save_dir / fname).resolve()
        if not is_directory_traversal_attempted(save_path):
            # Ensure save directory exists
            self.config.save_dir.mkdir(parents=True, exist_ok=True)

        atomic_save(content, save_path, size)
        log_duration("response()", start_total)

addons = [MediaSaver()]
