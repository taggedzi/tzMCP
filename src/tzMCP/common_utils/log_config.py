# log_config.py
import logging
from pathlib import Path
from threading import Thread
import requests
from tzMCP.save_media_utils.config_provider import get_config

# Preloaded global loggers
log_proxy = logging.getLogger("tzMCP.proxy")
log_browser = logging.getLogger("tzMCP.browser")
log_gui = logging.getLogger("tzMCP.gui")

def send_log_to_gui(entry):
    def _post():
        try:
            requests.post("http://localhost:5001", json=entry, timeout=0.1)
        except requests.exceptions.RequestException:
            pass
    Thread(target=_post, daemon=True).start()

class GuiLogHandler(logging.Handler):
    def emit(self, record):
        try:
            config = get_config()
            level = getattr(config, "log_level", "INFO").upper()
            if record.levelno >= logging.getLevelName(level):
                msg = self.format(record)
                color = {
                    "DEBUG": "grey",
                    "INFO": "black",
                    "WARNING": "orange",
                    "ERROR": "red",
                    "CRITICAL": "red"
                }.get(record.levelname, "black")

                send_log_to_gui({
                    "color": color,
                    "weight": "bold",
                    "lines": [msg]
                })
        except Exception:
            pass  # Don't crash if GUI logging fails

def setup_logging():
    """
    Setup hierarchical logging for tzMCP components.
    Log files are hardcoded to 'logs/tzMCP_proxy.log', etc.
    Enable/disable file logging via config: config.log_to_file
    """
    config = get_config()
    enable_file = getattr(config, "log_to_file", False)
    level_name = getattr(config, "log_level", "INFO").upper()
    level = logging.getLevelName(level_name)

    log_dir = Path(__file__).parent.parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger_map = {
        log_proxy: log_dir / "tzMCP_proxy.log",
        log_browser: log_dir / "tzMCP_browser.log",
        log_gui: log_dir / "tzMCP_gui.log"
    }

    for logger, file_path in logger_map.items():
        logger.setLevel(level)

        # Prevent duplicate handlers
        if logger.hasHandlers():
            logger.handlers.clear()

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

        # Console output (always shown)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Optional file output (only if enabled)
        if enable_file:
            fh = logging.FileHandler(file_path, encoding="utf-8")
            fh.setLevel(level)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

        # GUI log output (always shown)
        gh = GuiLogHandler()
        gh.setLevel(level)
        gh.setFormatter(formatter)
        logger.addHandler(gh)

    return {
        "proxy": log_proxy,
        "browser": log_browser,
        "gui": log_gui,
    }
