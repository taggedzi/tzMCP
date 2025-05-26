# pylint: disable=logging-fstring-interpolation,redefined-outer-name,broad-exception-caught,line-too-long
import os
from pathlib import Path
from time import perf_counter
from threading import Timer
from mitmproxy import http
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tzMCP.gui_bits.config_manager import ConfigManager, Config
from tzMCP.save_media_utils import config_provider
from tzMCP.save_media_utils.mime_categories import IMAGE_TYPES
from tzMCP.save_media_utils.save_media_utils import (
    log_duration, safe_filename, is_valid_image, is_mime_type_allowed,
    is_file_size_out_of_bounds, is_domain_blocked_by_whitelist,
    is_domain_blacklisted, is_image_size_out_of_bounds, does_header_match_size,
    is_directory_traversal_attempted, atomic_save, detect_mime_and_extension
)
from tzMCP.common_utils.log_config import setup_logging, log_proxy


class ConfigChangeHandler(FileSystemEventHandler):
    """Watchdog event handler class"""
    def __init__(self, callback):
        """Init and accept the callback function."""
        self.callback = callback

    def on_any_event(self, event):
        """Process ANY change int the target directory."""
        log_proxy.debug(f"[watchdog] Event: {event.event_type} → {event.src_path}")
        if not event.is_directory and event.src_path.endswith("media_proxy_config.yaml"):
            self.callback()

class MediaSaver:
    """Media Server Addon for mitmproxy"""
    def __init__(self):
        # Setup Pathing
        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = self.project_root / "config" / "media_proxy_config.yaml"
        self.log_path = self.project_root / "logs"

        # Setup Config Manager
        self.cfg_manager = ConfigManager(self.config_path)
        self.config = Config()   # Start with empty config
        self._reload_timer = None
        self._observer = None
        self._load_config()
        setup_logging()
        self._start_watcher()    # Setup Watchdog to monitor the config file for updates.
        log_proxy.info(f"MediaSaver addon initialized → {self.config.save_dir}")

    def _load_config(self):
        """Load configs from the config file if possible."""
        try:
            self.config: Config = self.cfg_manager.load_config()  # Load config from file and store locally
            config_provider.set_config(self.config)               # Share with other files in real time.
            log_proxy.info("MediaServer: 🔄 Reloaded config")
        except Exception as e:
            log_proxy.error(f"Failed to load config: {e}")
            config_provider.set_config({})

    def _start_watcher(self):
        """Start watchdog observer to watch the config file."""
        if not self.config_path.exists():
            log_proxy.error(f"⚠ Cannot watch config; file does not exist: {self.config_path}")
            return
        try:
            event_handler = ConfigChangeHandler(self._on_config_change)
            observer = Observer()
            observer.schedule(event_handler, str(self.config_path.parent), recursive=False)
            observer.daemon = True
            observer.start()
            self._observer = observer  # Store if you ever need to stop it
        except Exception as e:
            log_proxy.error(f"⚠ Failed to start config watcher: {e}")

    def _on_config_change(self):
        """Prevent operations from triggering multiple operations/loads in a short time."""
        if self._reload_timer and self._reload_timer.is_alive():
            self._reload_timer.cancel()
        self._reload_timer = Timer(0.25, self._debounced_reload)
        self._reload_timer.start()

    def _debounced_reload(self):
        """Load config after bouncing is done."""
        self._load_config()
        log_proxy.info("🔄 Config reloaded via debounced watcher.")

    def done(self):
        """Called when mitmproxy shuts down."""
        if hasattr(self, "_observer") and self._observer:
            self._observer.stop()
            self._observer.join()
            log_proxy.info("🛑 Config watcher stopped cleanly.")

    def response(self, flow: http.HTTPFlow):
        """Process a response from a user request."""
        start_total = perf_counter()

        # Determine response details if possible.
        content = flow.response.content
        url = flow.request.pretty_url
        size = len(content)
        clean_url = url.split("?", 1)[0]
        basename = os.path.basename(clean_url)
        mime_type, ext = detect_mime_and_extension(content, fallback_url=url)
        fname = safe_filename(basename, ext, fallback_url=url)
        log_proxy.info(f"Received: {fname} → {mime_type}, {size} bytes")

        # These are ordered to try to get the fastest to fail done first.
        if (not does_header_match_size(flow.response.headers.get("Content-Length"), size, url) or
            is_file_size_out_of_bounds(size, fname) or
            not is_mime_type_allowed(mime_type, fname) or
            is_domain_blocked_by_whitelist(url, fname) or
            is_domain_blacklisted(url, fname)):
            return

        if mime_type in IMAGE_TYPES:
            if is_valid_image(content) and is_image_size_out_of_bounds(content, fname):
                return

        save_path = (self.config.save_dir / fname).resolve()
        if not is_directory_traversal_attempted(save_path):
            self.config.save_dir.mkdir(parents=True, exist_ok=True)

        atomic_save(content, save_path, size)
        log_duration("response()", start_total)

addons = [MediaSaver()]
